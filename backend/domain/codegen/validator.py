from __future__ import annotations

from typing import Dict, Tuple

from domain.codegen.view import CodeGenView, CodeMode, SemanticCheckResult


def is_semantic_check_ok(state) -> Tuple[bool, Dict]:
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

    # pandas 模式保持兼容
    detail = view.check_semantics or SemanticCheckResult()
    if isinstance(detail, SemanticCheckResult):
        return detail.passed, detail.model_dump()

    ok = detail.get("passed", detail.get("pass", True))
    return ok, detail
