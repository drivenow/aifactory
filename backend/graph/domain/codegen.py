# backend/graph/domain/codegen.py
from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ..state import FactorAgentState, ViewBase
from ..tools.factor_template import (
    render_factor_code,
    simple_factor_body_from_spec,
)
from ..tools.sandbox_runner import run_code


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
    """
    根据用户的自然语言 spec 生成模板化因子代码。

    目前是简单模板：
    - simple_factor_body_from_spec: 生成函数 body
    - render_factor_code: 根据因子名 + 描述 + body 渲染出完整 Python 代码
    """
    view = CodeGenView.from_state(state)
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
    return view.semantic_check.get("pass", False), view.semantic_check
