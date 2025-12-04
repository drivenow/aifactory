from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

try:
    from pydantic import BaseModel
except Exception:  # pragma: no cover
    class BaseModel:  # minimal stub to avoid hard dependency when standalone
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self):
            return self.__dict__

try:
    from backend.graph.state import FactorAgentState, ViewBase
except Exception:  # pragma: no cover
    class ViewBase(BaseModel):
        @classmethod
        def _wrap_from_state(cls, name):
            def deco(func):
                return func
            return deco

    class FactorAgentState(dict):
        pass


class CodeMode(str, Enum):
    PANDAS = "pandas"
    L3_PY = "l3_py"


class SemanticCheckResult(BaseModel):
    passed: bool = True
    reason: List[str] = []
    last_error: Optional[str] = None


class DryrunResult(BaseModel):
    success: bool = True
    traceback: Optional[str] = None
    result_preview: Optional[Any] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class CodeGenView(ViewBase):
    """Normalized view for code generation state."""

    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""
    code_mode: CodeMode = CodeMode.PANDAS
    dryrun_result: DryrunResult = DryrunResult(success=True)
    check_semantics: SemanticCheckResult = SemanticCheckResult()

    @classmethod
    @ViewBase._wrap_from_state("CodeGenView.from_state")
    def from_state(cls, state: FactorAgentState) -> "CodeGenView":
        """Map FactorAgentState (dict-like) into a normalized view object."""

        def _parse_dryrun(d):
            if not d:
                return DryrunResult(success=True)
            return DryrunResult(**d)

        def _parse_semantic(d):
            if not d:
                return SemanticCheckResult()
            return SemanticCheckResult(**d)

        return cls(
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
            factor_code=state.get("factor_code") or "",
            dryrun_result=_parse_dryrun(state.get("dryrun_result")),
            check_semantics=_parse_semantic(state.get("check_semantics")),
            code_mode=state.get("code_mode") or CodeMode.PANDAS,
        )
