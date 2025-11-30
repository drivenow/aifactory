# backend/graph/domain/code_gen.py
from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ..state import FactorAgentState, ViewBase
from ..tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)
from ..tools.sandbox_runner import run_code
from ..config import get_llm
from ..prompts.factor_l3_py import PROMPT_FACTOR_L3_PY
from langgraph.agents import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
import re


class CodeGenView(ViewBase):
    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""
    dryrun_result: Dict[str, Any] = Field(default_factory=dict)
    semantic_check: Optional[Dict[str, Any]] = Field(default_factory=dict)  # 语义一致性：{pass, diffs, reason}

    @classmethod
    @ViewBase._wrap_from_state("CodeGenView.from_state")
    def from_state(cls, state: FactorAgentState) -> "CodeGenView":
        return cls(
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
            factor_code=state.get("factor_code") or "",
            dryrun_result=state.get("dryrun_result") or {},
            semantic_check=state.get("semantic_check") or {},
        )


def generate_factor_code_from_spec(state: FactorAgentState) -> str:
    view = CodeGenView.from_state(state)
    llm = get_llm()

    if not llm:
        body = simple_factor_body_from_spec(view.user_spec)
        return render_factor_code(view.factor_name, view.user_spec, body)

    agent = create_react_agent(llm)

    sys = SystemMessage(
        content=(
            "你是量化高频因子工程师助手。根据用户描述生成因子代码，"
            "必须生成符合高频因子计算的模板，获取指定的的行情数据，返回规定的数据格式。"
            "优先调用 propose_body 生成主体，再用 render_factor 渲染完整代码。"
            "如需验证，调用 dryrun_code。最终只返回三引号包裹的完整 Python 代码。\n\n" + PROMPT_FACTOR_L3_PY
        )
    )

    user = HumanMessage(
        content=(
            f"因子名: {view.factor_name}\n"
            f"描述: {view.user_spec}\n"
            "请输出完整代码。"
        )
    )

    out = agent.invoke({"messages": [sys, user]})
    msgs = out.get("messages") or []
    txt = ""
    if msgs:
        last = msgs[-1]
        txt = getattr(last, "content", "") or str(last)
    m = re.search(r"```(?:python)?\n([\s\S]*?)```", txt)
    if m:
        return m.group(1)
    body = simple_factor_body_from_spec(view.user_spec)
    return render_factor_code(view.factor_name, view.user_spec, body)


def run_factor_dryrun(state: FactorAgentState) -> Dict[str, Any]:
    view = CodeGenView.from_state(state)
    result = run_code(
        view.factor_code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )
    return result

def is_semantic_check_ok(state: FactorAgentState) -> bool:
    view = CodeGenView.from_state(state)
    return view.semantic_check.get("pass", True), view.semantic_check


if __name__ == "__main__":
    state = {
        "user_spec": "Compute 5-day moving average of close price",
        "factor_name": "MovingAvgFactor",
    }
    code = generate_factor_code_from_spec(state)
    print(code)