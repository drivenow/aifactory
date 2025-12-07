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
    """
    Normalized view for code generation state.

    参数
    ----
    user_spec : str, optional
        用户需求描述，默认空字符串。
    factor_name : str, optional
        因子名称，默认 "factor"。
    factor_code : str, optional
        因子代码，默认空字符串。
    code_mode : CodeMode, optional
        代码模式，默认 CodeMode.PANDAS。
    dryrun_result : DryrunResult, optional
        代码执行结果，默认空 DryrunResult。
    check_semantics : SemanticCheckResult, optional
        语义检查结果，默认空 SemanticCheckResult。
    """

    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""
    code_mode: CodeMode = CodeMode.PANDAS
    dryrun_result: DryrunResult = Field(default_factory=DryrunResult)
    check_semantics: SemanticCheckResult = Field(default_factory=SemanticCheckResult)

    def set_dryrun_result(self, dryrun_result: DryrunResult | dict):
        if not isinstance(dryrun_result, DryrunResult):
            assert isinstance(dryrun_result, dict), "dryrun_result must be a DryrunResult or a dict"
            assert "success" in dryrun_result, "dryrun_result must contain 'success' key"
            assert "stdout" in dryrun_result or "stderr" in dryrun_result, "dryrun_result must contain 'stdout' or 'stderr' key"
            self.dryrun_result = self._parse_dryrun(dryrun_result)
        else:
            self.dryrun_result = dryrun_result
    
    def set_semantic_check_result(self, semantic_check_result: SemanticCheckResult | dict):
        if not isinstance(semantic_check_result, SemanticCheckResult):
            assert isinstance(semantic_check_result, dict), "semantic_check_result must be a SemanticCheckResult or a dict"
            assert "passed" in semantic_check_result, "semantic_check_result must contain 'passed' key" 
            assert "reason" in semantic_check_result, "semantic_check_result must contain 'reason' key"
            self.check_semantics = self._parse_semantic(semantic_check_result)
        else:
            self.check_semantics = semantic_check_result

    def _parse_dryrun(self, d):
        if not d:
            return DryrunResult()
        if isinstance(d, DryrunResult):
            return d
        return DryrunResult(**d)

    def _parse_semantic(self, d):
        if not d:
            return SemanticCheckResult()
        if isinstance(d, SemanticCheckResult):
            return d
        return SemanticCheckResult(**d)

    @classmethod
    @ViewBase._wrap_from_state("CodeGenView.from_state")
    def from_state(cls, state: FactorAgentState) -> "CodeGenView":
        """Map FactorAgentState (dict-like) into a normalized view object."""
        if isinstance(state, CodeGenView):
            return state

        return cls(
            user_spec=state.get("user_spec") or "",
            factor_name=state.get("factor_name") or "factor",
            factor_code=state.get("factor_code") or "",
            dryrun_result=cls._parse_dryrun(state.get("dryrun_result")),
            check_semantics=cls._parse_semantic(state.get("check_semantics")),
            code_mode=state.get("code_mode") or CodeMode.PANDAS,
        )

if __name__ == "__main__":
    state = FactorAgentState(
        user_spec="计算因子值",
        factor_name="my_factor",
        factor_code="class MyFactor(FactorBase):\n    def calculate(self):\n        self.addFactorValue(100)",
        code_mode=CodeMode.L3_PY,
    )
    view = CodeGenView.from_state(state)
    view.factor_code = "1111"
    print(view.model_dump())
