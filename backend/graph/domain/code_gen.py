# backend/graph/domain/code_gen.py
from __future__ import annotations

from typing import Dict, Any, Optional, List
from pydantic import Field

from ..state import FactorAgentState, ViewBase
from ..tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)
from ..tools.sandbox_runner import run_code
from ..config import get_llm
from ..prompts.factor_l3_py import PROMPT_FACTOR_L3_PY
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage
import re

from ..tools.l3_factor_tool import l3_syntax_check, l3_mock_run, _mock_run


class CodeGenView(ViewBase):
    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""
    dryrun_result: Dict[str, Any] = Field(default_factory=dict)
    semantic_check: Optional[Dict[str, Any]] = Field(default_factory=dict)  # 语义一致性：{pass, diffs, reason}
    code_mode: str = "pandas"

    @classmethod
    @ViewBase._wrap_from_state("CodeGenView.from_state")
    def from_state(cls, state: FactorAgentState) -> "CodeGenView":
        return cls(
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
            factor_code=state.get("factor_code") or "",
            dryrun_result=state.get("dryrun_result") or {},
            semantic_check=state.get("semantic_check") or {},
            code_mode=state.get("code_mode") or "pandas",
        )


def _build_l3_codegen_agent():
    llm = get_llm()
    if (not llm) or (create_agent is None):
        return None
    return create_agent(llm, tools=[l3_syntax_check, l3_mock_run])


_L3_AGENT = _build_l3_codegen_agent()


def _extract_last_assistant_content(messages: List[Any]) -> str:
    """从 agent 返回的消息列表中提取最后一条 assistant 内容。"""
    for m in reversed(messages):
        role = getattr(m, "type", None) or getattr(m, "role", None)
        if role in ("assistant", "ai"):
            return getattr(m, "content", "") or ""
    return ""


def _strip_code_fences(txt: str) -> str:
    m = re.search(r"```(?:python)?\n([\s\S]*?)```", txt)
    if m:
        return m.group(1)
    return txt


def _generate_l3_code_with_agent(view: CodeGenView) -> str:
    """使用 L3 专用 ReAct agent 生成 FactorBase 规范代码。"""
    agent = _L3_AGENT or _build_l3_codegen_agent()
    if agent is None:
        print("[DBG] _generate_l3_code_with_agent fallback without llm")
        # 简单回退：生成一个占位因子，避免空结果影响流程
        return (
            "from L3FactorFrame.FactorBase import FactorBase\n\n"
            f"class {view.factor_name}(FactorBase):\n"
            "    def __init__(self, config, factorManager, marketDataManager):\n"
            "        super().__init__(config, factorManager, marketDataManager)\n"
            "    def calculate(self):\n"
            "        self.addFactorValue(0.0)\n"
        )

    sem = view.semantic_check or {}
    last_error = sem.get("last_error") or ""
    if isinstance(sem.get("reason"), list) and not last_error:
        last_error = "; ".join(str(x) for x in sem.get("reason"))

    sys = SystemMessage(
        content=(
            PROMPT_FACTOR_L3_PY
            + "\n\n工具使用要求：\n"
            "- 至少调用一次 l3_syntax_check 做结构校验；必要时调用 l3_mock_run 做自检。\n"
            "- 禁止输出工具日志或解释，最终只输出完整的 Python 源代码，不要使用 ``` 包裹。\n"
        )
    )

    user = HumanMessage(
        content=(
            f"因子类名: {view.factor_name}\n"
            f"因子需求描述: {view.user_spec}\n"
            f"上次错误摘要: {last_error[:1000] if last_error else '无'}\n"
        )
    )

    out = agent.invoke({"messages": [sys, user]})
    msgs = out.get("messages") or []
    print(
        "[DBG] _generate_l3_code_with_agent agent invoked",
        f"msgs={len(msgs)} last_error={(last_error[:80]+'...') if last_error else 'none'}",
    )
    txt = _extract_last_assistant_content(msgs)
    return _strip_code_fences(txt).strip()


def generate_factor_code_from_spec(state: FactorAgentState) -> str:
    view = CodeGenView.from_state(state)
    if view.code_mode == "l3_py":
        return _generate_l3_code_with_agent(view)

    body = simple_factor_body_from_spec(view.user_spec)
    return render_factor_code(view.factor_name, view.user_spec, body)


def run_factor_dryrun(state: FactorAgentState) -> Dict[str, Any]:
    view = CodeGenView.from_state(state)
    if view.code_mode == "l3_py":
        res = _mock_run(view.factor_code)
        if res.get("ok"):
            return {"success": True, "result": res.get("result")}
        return {"success": False, "traceback": res.get("error")}

    return run_code(
        view.factor_code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )

def is_semantic_check_ok(state: FactorAgentState) -> bool:
    view = CodeGenView.from_state(state)
    # pandas 模式保持兼容：默认通过，除非显式标记失败
    if view.code_mode != "l3_py":
        return view.semantic_check.get("pass", True), view.semantic_check

    return view.semantic_check.get("pass", True), view.semantic_check


if __name__ == "__main__":
    state = {
        "user_spec": "Compute 5-day moving average of close price",
        "factor_name": "MovingAvgFactor",
    }
    code = generate_factor_code_from_spec(state)
    print(code)
