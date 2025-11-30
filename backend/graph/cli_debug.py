# backend/graph/cli_debug.py
"""
命令行调试入口（CLI runner）

用法（在项目根目录）：
    python -m backend.graph.cli_debug

流程：
- 询问用户输入因子描述（user_spec）
- 创建一个新的 thread_id
- 使用 while 循环调用 graph.invoke(...)
  - 捕获 GraphInterrupt 时打印 payload，并从命令行读入 resume 值
  - 继续传入 Command(resume=...) 进行恢复
"""

from __future__ import annotations

import json
import uuid

from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from .graph import graph
from .state import FactorAgentState
from .domain.review import build_human_review_request, normalize_review_response



def _input_resume_value() -> object:
    """
    从命令行读取一个 resume 值：
    - 空行      → True
    - JSON 文本 → json.loads
    - 其他文本   → 原样字符串
    """
    s = input("\n请输入 resume 值（回车=True；JSON 自动解析）：\n> ").strip()
    if s == "":
        return True
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


def cli_debug() -> None:
    """在命令行中交互式运行 FactorAgent graph。"""
    # 1) 读入用户的因子自然语言描述
    print("请输入因子的自然语言描述（例如：\"动量因子，lookback 20 天\"）：")
    spec = input("> ").strip()

    # 2) 为本次 CLI 会话创建一个独立的 thread_id
    thread_id = f"cli-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    # 3) 初始 state：直接写入 user_spec，其他字段留空
    init_state: FactorAgentState = {
        "user_spec": spec,
        "retry_count": 0,
        "human_review_status": "pending",
        "route": "collect_spec",
    }

    current_input: object = init_state

    print(f"\n[CLI] 使用 thread_id = {thread_id}\n")

    while True:
        try:
            # 调用图：若中间无 interrupt，直接跑到 finish
            result = graph.invoke(current_input, config=config)
            print("\n✅ Graph finished. 最终状态：")
            ui_resp, status, edited_code = normalize_review_response(result)
            print(ui_resp, status, edited_code)
            # print(json.dumps(result, ensure_ascii=False, indent=2))
            break
        except GraphInterrupt as gi:
            # 发生中断：打印 payload，等待用户输入 resume
            payload = gi.value
            print("\n⏸️  Graph interrupted. Payload:")
            ui_resp, status, edited_code = normalize_review_response(payload)
            print(ui_resp, status, edited_code)
            # print(json.dumps(payload, ensure_ascii=False, indent=2))

            resume_val = _input_resume_value()

            # 下一轮用 Command(resume=...) 继续同一个 thread
            current_input = Command(resume=resume_val)


if __name__ == "__main__":
    cli_debug()
