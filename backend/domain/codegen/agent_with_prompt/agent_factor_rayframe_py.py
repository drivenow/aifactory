from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from domain.codegen.framework.factor_rayframe_standard import (
    PROMPT_RAYFRAME_PY_RULE,
    PROMPT_RAYFRAME_PY_DEMO_DAY,
    PROMPT_RAYFRAME_PY_DEMO_MIN,
)
from domain.codegen.view import CodeGenView
from domain.llm import _extract_last_assistant_content, _unwrap_agent_code, create_agent


PROMPT_RAYFRAME_PY = """你是一个量化因子工程师助手，使用 xquant.rayframe 框架开发日/分钟因子。
你的任务：根据需求生成 rayframe Python 因子代码，按模板填槽输出：
- aiquant_requirements: Python dict，声明所需数据（DataManager 配置，LIB_ID 必填，LIB_ID_FEILD 必填：需加载的字段列表）。
- calc_body: calc 函数内的代码块（不含 def/类定义，已提供 inputs = self.load_inputs(dt_to=dt_to)）。
我会把这两段代码放进标准模板，不需要你生成类定义。

# 框架规范
{rules}

# 示例（便于模仿）
{demo_day}
{demo_min}

# 输出要求（严格遵守）
- 只输出两段 Python 代码，不要 Markdown 代码块、不要类定义：
  1) aiquant_requirements = {{...}}  # Python 字典
     - 必须填写 LIB_ID、API_START/API_END、LIB_ID_FEILD（字段列表）
  2) calc_body = '''
     inputs = self.load_inputs(dt_to=dt_to)
     ...你的计算逻辑...
     '''
- 禁止出现 import/class 定义/def calc 关键字。
- 禁止使用 FactorData/get_hive_data/requests 等直接取数或 IO。
- inputs 结构：dict[alias] -> DataFrame 或 dict[field->DataFrame]（字段名取自 LIB_ID_FEILD），index=datetime，columns=symbol，列已对齐统一标的。
- 注意 dt_to 切片、空数据兜底和分母为 0 的健壮性。
"""

_RAYFRAME_AGENT: Optional[Any] = None


def build_rayframe_codegen_agent():
    """Build or reuse cached rayframe codegen agent."""
    global _RAYFRAME_AGENT
    if _RAYFRAME_AGENT is not None:
        return _RAYFRAME_AGENT
    _RAYFRAME_AGENT = create_agent(tools=None)
    return _RAYFRAME_AGENT


def build_rayframe_user_message(view: CodeGenView) -> HumanMessage:
    sem = view.check_semantics
    last_error = sem.last_error if sem else ""
    if sem and sem.reason and not last_error:
        last_error = "; ".join(sem.reason)
    dryrun = view.dryrun_result
    dryrun_err = ""
    if dryrun and getattr(dryrun, "stderr", None):
        dryrun_err = str(dryrun.stderr)

    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec}\n"
        f"已知问题: {last_error}\n"
        f"dryrun 错误: {dryrun_err}\n"
        "请输出符合规范的完整 rayframe Python 因子代码。"
    )
    return HumanMessage(content=user_content)


def invoke_rayframe_agent(view: CodeGenView) -> str:
    """使用 rayframe 专用 ReAct agent 生成 Factor 规范代码。"""
    agent = build_rayframe_codegen_agent()
    # 回退：生成占位模板，避免阻塞流程
    fallback_requirements = (
        "{\n"
        "    \"DAY_EOD\": DataManager(LIB_ID=\"ASHAREEODPRICES\", API_START=\"\", API_END=\"\"),\n"
        "}\n"
    )
    fallback_calc = (
        "inputs = self.load_inputs(dt_to=dt_to)\n"
        "df = inputs.get(\"DAY_EOD\", pd.DataFrame())\n"
        "if df is None or df.empty:\n"
        "    return pd.Series(dtype=float)\n"
        "ts = pd.to_datetime(dt_to) if dt_to is not None else df.index.max()\n"
        "ser = df.loc[ts]\n"
        "return ser\n"
    )
    template = (
        "import pandas as pd\n"
        "from AIQuant.datamanager import DataManager\n"
        "from xquant.factorframework.rayframe.BaseFactor import Factor\n\n"
        f"class {view.factor_name}(Factor):\n"
        f"    factor_type = \"DAY\"\n"
        f"    factor_name = \"{view.factor_name}\"\n"
        f"    security_pool = None\n"
        "    aiquant_requirements = {requirements}\n\n"
        "    def calc(self, factor_data=None, price_data=None, dt_to=None, **kwargs):\n"
        "        inputs = self.load_inputs(dt_to=dt_to)\n"
        "{calc_body}\n"
    )
    if agent is None:
        calc_body = "\n".join("        " + line for line in fallback_calc.strip().splitlines())
        return template.format(requirements=fallback_requirements.strip(), calc_body=calc_body)

    sys_msg = SystemMessage(
        content=PROMPT_RAYFRAME_PY.format(
            rules=PROMPT_RAYFRAME_PY_RULE,
            demo_day=PROMPT_RAYFRAME_PY_DEMO_DAY,
            demo_min=PROMPT_RAYFRAME_PY_DEMO_MIN,
        )
    )
    user_msg = build_rayframe_user_message(view)

    try:
        out = agent.invoke({"messages": [sys_msg, user_msg]})
        msgs = out.get("messages") or []
        txt = _extract_last_assistant_content(msgs)
        code = _unwrap_agent_code(txt).strip()
        # 解析 requirements 和 calc_body
        req, body = fallback_requirements, fallback_calc
        lines = code.splitlines()
        req_lines = []
        body_lines = []
        mode = None
        for ln in lines:
            if "aiquant_requirements" in ln:
                mode = "req"
                maybe = ln.split("=", 1)[-1].strip()
                if maybe:
                    req_lines.append(maybe)
                continue
            if "calc_body" in ln:
                mode = "body"
                continue
            if mode == "req":
                req_lines.append(ln)
            elif mode == "body":
                body_lines.append(ln)
        if req_lines:
            req = "\n".join(req_lines).strip()
        if body_lines:
            body = "\n".join(body_lines).strip().strip("'''").strip('\"\"\"')
        if not body_lines and code:
            body = code
        calc_body_indented = "\n".join("        " + ln for ln in body.strip().splitlines())
        return template.format(requirements=req, calc_body=calc_body_indented)
    except Exception as exc:
        calc_body = "\n".join("        " + line for line in fallback_calc.strip().splitlines())
        return template.format(requirements=fallback_requirements.strip(), calc_body=calc_body) + f"\n# Agent error: {exc}"


if __name__ == "__main__":  # pragma: no cover
    print(PROMPT_RAYFRAME_PY)
