# backend/cli_debug.py
"""
命令行调试入口（CLI runner）

用法（在项目根目录）:
    python -m backend.graph.cli_debug

流程:
- 询问用户输入因子描述（user_spec）
- 创建一个新的 thread_id
- 使用 while 循环调用 graph.invoke(...)
  - 捕获 GraphInterrupt 时打印 payload，并从命令行读入 resume 值
  - 继续传入 Command(resume=...) 进行恢复

⚠️ 特别说明（与前端一致的 HITL 协议）:
- 当 interrupt payload 为 {"type": "code_review", ...} 时:
  - CLI 会提示你选择:
      1) approve
      2) reject
      3) review (只写审核意见)
      4) edit   (编辑代码)
  - 然后返回给后端的 resume 值为:
      {
        "type": "code_review",
        "action": "approve" | "reject" | "review" | "edit",
        "payload": {
          "review_comment"?: str,
          "edited_code"?: str
        }
      }
  - 与前端 resolve 的新协议完全一致。
"""

import json
import uuid
from typing import Any, Callable, Dict, Optional

from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from backend.graph.graph import graph
from backend.graph.global_state import FactorAgentState


def _unwrap_interrupt(payload: Any) -> Any:
    """
    统一解包 interrupt payload，兼容几种情况:

    - 单个 Interrupt 实例 (有 .value 属性)
    - list[Interrupt]
    - 已经是 dict / str / 其他可序列化对象
    """
    # 单个 Interrupt
    if hasattr(payload, "value"):
        return payload.value

    # list/tuple 里是 Interrupt
    if isinstance(payload, (list, tuple)):
        out = []
        for p in payload:
            if hasattr(p, "value"):
                out.append(p.value)
            else:
                out.append(p)
        # 一般只会有一个，这里返回第一个方便使用
        return out[0] if len(out) == 1 else out

    # 其他情况（dict/str/number...）
    return payload


# =========================
# 专门用于 code_review 的 CLI 交互
# =========================

def _prompt_code_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    当 interrupt payload 为 {"type": "code_review", ...} 时，走这个分支。

    返回与前端一致的新协议:
    {
      "type": "code_review",
      "action": "approve" | "reject" | "review" | "edit",
      "payload": {
        "review_comment"?: str,
        "edited_code"?: str
      }
    }
    """
    title = payload.get("title") or "Code review"
    code = payload.get("code") or ""
    retry_count = payload.get("retry_count")

    print("\n========== [HITL] 代码审核请求 ==========")
    print(f"标题: {title}")
    if isinstance(retry_count, int):
        print(f"当前自动重试次数: {retry_count}")
    print("\n--- 因子代码 ---")
    print(code)
    print("------ 结束 ------\n")

    while True:
        print("请选择操作:")
        print("  1) approve  （通过，进入回填+评价）")
        print("  2) reject   （拒绝，直接结束）")
        print("  3) review   （只写审核意见，交给模型再生成）")
        print("  4) edit     （直接修改代码，再继续流程）")
        choice = input("> ").strip()

        # 1) approve
        if choice == "1":
            return {
                "type": "code_review",
                "action": "approve",
                "payload": {},
            }

        # 2) reject
        if choice == "2":
            return {
                "type": "code_review",
                "action": "reject",
                "payload": {},
            }

        # 3) review: 不能改代码，只写审核意见
        if choice == "3":
            print("\n请输入审核意见（review_comment），输入完后回车提交：")
            comment = input("> ").strip()
            return {
                "type": "code_review",
                "action": "review",
                "payload": {
                    "review_comment": comment,
                },
            }

        # 4) edit: 编辑代码
        if choice == "4":
            print("\n当前代码如下（仅供参考）：")
            print("--------------------------------")
            print(code)
            print("--------------------------------")
            print(
                "\n请在下面输入修改后的完整代码（多行）。\n"
                "输入单独一行 `###END###` 结束输入："
            )

            lines = []
            while True:
                line = input()
                if line.strip() == "###END###":
                    break
                lines.append(line)
            new_code = "\n".join(lines).strip()

            if not new_code:
                print("\n⚠️ 未输入任何内容，将保留原代码。")
                new_code = code

            return {
                "type": "code_review",
                "action": "edit",
                "payload": {
                    "edited_code": new_code,
                },
            }

        print("\n无效选项，请输入 1 / 2 / 3 / 4。")


# =========================
# 通用 resume 提示函数
# =========================

def _default_prompt_resume(payload: Any) -> Any:
    """
    默认的 resume 输入方式:

    - 如果是 code_review 请求 → 使用专门的 CLI 审核流程
    - 否则:
      - 回车        → True
      - JSON 文本   → json.loads
      - 普通字符串   → 原样字符串
    """
    # 如果 payload 里明确是 code_review，则走专门的流程
    if isinstance(payload, dict) and payload.get("type") == "code_review":
        return _prompt_code_review(payload)

    print("\n⏸️  Graph interrupted. Payload:")
    try:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        print(str(payload))

    s = input("\n请输入 resume 值（回车=True；JSON 自动解析）：\n> ").strip()

    if s == "":
        return True

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


# =========================
# 主循环
# =========================

def cli_debug_loop(
    graph_obj,
    init_input: Any,
    *,
    thread_id: Optional[str] = None,
    base_config: Optional[Dict[str, Any]] = None,
    prompt_resume: Callable[[Any], Any] = _default_prompt_resume,
) -> Dict[str, Any]:
    """
    通用 CLI 调试主循环:

    - 支持 GraphInterrupt 异常风格
    - 也支持结果 dict["__interrupt__"] 风格
    - 每次遇到 interrupt，就调用 prompt_resume(prompt_payload) 拿一个 resume 值，
      然后用 Command(resume=...) 继续同一个 thread

    参数:
        graph_obj:     已 compile 的 LangGraph 图（例如 backend.graph.graph.graph）
        init_input:    初始输入，可以是 state dict 或 Command(...)
        thread_id:     可选，未提供时会自动生成一个 cli-UUID
        base_config:   传给 graph.invoke 的 config（可带其他 configurable 字段）
        prompt_resume: 一个函数 (payload) -> resume_val，方便以后自定义 UI

    返回:
        最终一次 graph.invoke 的返回结果（通常是完整 state dict）
    """
    # 1) thread_id & config 统一处理
    if thread_id is None:
        thread_id = f"cli-{uuid.uuid4()}"

    config = dict(base_config or {})
    configurable = dict(config.get("configurable") or {})
    configurable.setdefault("thread_id", thread_id)
    config["configurable"] = configurable

    print(f"[CLI] 使用 thread_id = {thread_id}\n")

    current_input: Any = init_input

    # 2) 主循环：不断调用 graph.invoke，直到没有 __interrupt__
    while True:
        try:
            result = graph_obj.invoke(current_input, config=config)
        except GraphInterrupt as gi:
            # 兼容“抛异常”的风格：统一转成带 __interrupt__ 的结果
            result = {"__interrupt__": gi.value}

        raw = result.get("__interrupt__")
        if not raw:
            # 没有 __interrupt__ → 图已经正常结束
            print("\n✅ Graph finished. 最终状态:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result

        # 有中断 → 解包 payload，交给 prompt_resume 决定下一步
        payload = _unwrap_interrupt(raw)
        resume_val = prompt_resume(payload)

        # 下一轮以 Command(resume=...) 继续同一个 thread
        current_input = Command(resume=resume_val)


def main():
    print("请输入因子的自然语言描述（例如：动量因子，lookback 20 天）：")
    spec = input("> ").strip()

    # 初始 state：让图从 entry node (collect_spec) 开始
    init_state: FactorAgentState = {
        "user_spec": spec,
        "retry_count": 0,
        "human_review_status": "pending",
    }

    cli_debug_loop(graph, init_state)


if __name__ == "__main__":
    main()
