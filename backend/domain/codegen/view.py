from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
try:
    from global_state import FactorAgentState, ViewBase
except (ImportError, ValueError):  # pragma: no cover
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
    L3_CPP = "l3_cpp"


class SemanticCheckResult(BaseModel):
    passed: bool = True  # 语义分析是否通过
    reason: List[str] = Field(default_factory=list)  # 语义分析的成功或者失败原因
    last_error: Optional[str] = None  # 语义检查失败原因摘要（可选）


class DryrunResult(BaseModel):
    success: bool = True  # 代码执行是否成功
    stdout: Optional[str] = None  # 代码执行的标准输出
    stderr: Optional[str] = None  # 代码执行的标准错误输出


class CodeGenView(ViewBase):
    """Normalized view for code generation state."""

    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""
    code_mode: CodeMode = CodeMode.PANDAS
    dryrun_result: DryrunResult = Field(default_factory=DryrunResult)
    check_semantics: SemanticCheckResult = Field(default_factory=SemanticCheckResult)

    @classmethod
    @ViewBase._wrap_from_state("CodeGenView.from_state")
    def from_state(cls, state: FactorAgentState) -> "CodeGenView":
        """Map FactorAgentState (dict-like) into a normalized view object."""

        def _parse_dryrun(d):
            if not d:
                return DryrunResult()
            if isinstance(d, DryrunResult):
                return d
            return DryrunResult(**d)

        def _parse_semantic(d):
            if not d:
                return SemanticCheckResult()
            if isinstance(d, SemanticCheckResult):
                return d
            return SemanticCheckResult(**d)

        return cls(
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
            factor_code=state.get("factor_code") or "",
            dryrun_result=_parse_dryrun(state.get("dryrun_result")),
            check_semantics=_parse_semantic(state.get("check_semantics")),
            code_mode=state.get("code_mode") or CodeMode.PANDAS,
        )
