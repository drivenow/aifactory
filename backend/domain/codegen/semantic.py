from __future__ import annotations

from typing import Dict, Tuple
import os

from domain.codegen.agent_with_prompt import agent_semantic_check
from domain.codegen.view import CodeGenView, CodeMode, SemanticCheckResult, DryrunResult


def check_semantics_static(state) -> Tuple[bool, Dict]:
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


def check_semantics_agent(state) -> Tuple[bool, Dict]:
    """调用语义 agent 检查运行结果和代码，容错降级。"""
    view = CodeGenView.from_state(state)
    enabled = os.getenv("ENABLE_SEMANTIC_AGENT", "false").lower() in ("1", "true", "yes")
    dr = view.dryrun_result or DryrunResult()
    if not isinstance(dr, DryrunResult):
        dr = DryrunResult(**dr)

    # 如果未启用语义 agent，则基于 dryrun 结果做最小判定
    if not enabled:
        passed = bool(dr.success)
        reason = [] if passed else ["dryrun failed and semantic agent disabled"]
        res = SemanticCheckResult(passed=passed, reason=reason, last_error="; ".join(reason) if reason else None)
        return passed, res.model_dump()

    parsed = agent_semantic_check.invoke_semantic_agent(view, dr)
    return parsed.passed, parsed.model_dump()
