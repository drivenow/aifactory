from __future__ import annotations

from typing import Dict, Tuple
import os

from domain.codegen.agent_with_prompt import agent_semantic_check
from domain.codegen.view import CodeGenView, CodeMode, SemanticCheckResult, DryrunResult


def check_semantics_static(state:  CodeGenView | FactorAgentState) -> Tuple[bool, Dict]:
    """
    静态语义检查，检查因子代码是否符合语法规范。

    参数
    ----
    state : FactorAgentState
        包含因子代码、代码模式（L3_PY/L3_CPP/普通模式）等信息的完整状态对象。

    返回
    ----
    Tuple[bool, Dict]
        包含检查是否通过（bool）和详细结果（Dict）的元组。
    """
    view = CodeGenView.from_state(state)

    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        reasons = []
        code = view.factor_code

        if "FactorBase" not in code:
            reasons.append("未继承 FactorBase。")
        if "def calculate" not in code:
            reasons.append("未定义 calculate 方法。")
        if "addFactorValue" not in code:
            reasons.append("未调用 addFactorValue 写回因子值。")

        passed = len(reasons) == 0
        last_err = "; ".join(reasons) if reasons else ""

        result = SemanticCheckResult(
            passed=passed,
            reason=reasons,
            last_error=last_err,
        )
        return passed, result.model_dump()

    detail = view.check_semantics or SemanticCheckResult()
    if not isinstance(detail, SemanticCheckResult):
        detail = SemanticCheckResult(**detail)
    return detail.passed, detail.model_dump()


def check_semantics_agent(state: CodeGenView | FactorAgentState) -> Tuple[bool, Dict]:
    """
    调用语义 agent 检查运行结果和代码，容错降级。

    参数
    ----
    state : CodeGenView | FactorAgentState
        包含因子代码、代码模式（L3_PY/L3_CPP/普通模式）、dryrun 结果等信息的完整状态对象。

    返回
    ----
    Tuple[bool, Dict]
        包含检查是否通过（bool）和详细结果（Dict）的元组。
    """
    view = CodeGenView.from_state(state)
    dr = view.dryrun_result or DryrunResult()
    if not isinstance(dr, DryrunResult):
        dr = DryrunResult(**dr)

    # 调用语义 agent 检查运行结果和代码
    parsed = agent_semantic_check.invoke_semantic_agent(view, dr)
    return parsed.passed, parsed.model_dump()
