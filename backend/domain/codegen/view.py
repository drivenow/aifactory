from __future__ import annotations

import os
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path
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
    factor_path: str = ""
    code_mode: CodeMode = CodeMode.PANDAS
    dryrun_result: DryrunResult = Field(default_factory=DryrunResult)
    check_semantics: SemanticCheckResult = Field(default_factory=SemanticCheckResult)

    def set_dryrun_result(self, dryrun_result: DryrunResult | dict):
        self.dryrun_result = self._parse_dryrun(dryrun_result)
    
    def set_semantic_check_result(self, semantic_check_result: SemanticCheckResult | dict):
        self.check_semantics = self._parse_semantic(semantic_check_result)

    def __str__(self):
        """
        返回代码生成视图的字符串表示。
        
        如果语义检查通过且代码执行成功，返回成功信息，包括用户需求描述、生成的代码。
        否则，返回失败信息，包括用户需求描述、生成的代码、语义检查结果、代码执行结果。
        """
        lines = ["+--------------------------------------------------------+"]
        if self.check_semantics.passed and self.dryrun_result.success:
            lines.append(f"[SUCCESS] 因子 {self.factor_name} 语义检查通过！")
            lines.append(f"[User Spec]")
            lines.append(self.user_spec.strip())
            lines.append(f"[Generated Code]")
            lines.append(self.factor_code)
        else:
            lines.append(f"[FAIL] 因子 {self.factor_name} 检查未通过")
            
            lines.append(f"[Dryrun Result]")
            lines.append(self.dryrun_result.model_dump_json(indent=2))
            
            lines.append(f"[Semantic Check]")
            lines.append(self.check_semantics.model_dump_json(indent=2))
            lines.append(f"[Current Code]")
            lines.append(self.factor_code)
        lines += ["+--------------------------------------------------------+"]
        return "\n".join(lines)

    def save_code_to_file(self, base_dir: str = None) -> str:
        """
        Save the factor code to a file under the specified base directory.
        
        The file will be placed in a subdirectory determined by the code_mode,
        and the filename will be the factor_name with the appropriate extension.
        
        Parameters
        ----------
        base_dir : str, optional
            Base directory for saving files. Defaults to the directory of this file
            plus 'generated_factors'.
        
        Returns
        -------
        str
            The absolute path to the saved file.
        """
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../generated_factors")
        print(base_dir)
        
        # Determine subdirectory and file extension based on code_mode
        if self.code_mode in (CodeMode.L3_CPP, "l3_cpp"):
            sub_dir = "l3_cpp"
            suffix = ".cpp"
        elif self.code_mode in (CodeMode.L3_PY, "l3_py"):
            sub_dir = "l3_py"
            suffix = ".py"
        else:
            sub_dir = "pandas"
            suffix = ".py"
        
        # Construct full directory path and ensure it exists
        target_dir = Path(base_dir) / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct file path
        file_path = target_dir / f"{self.factor_name}{suffix}"
        file_path.write_text(self.factor_code, encoding="utf-8")
        
        # Update self.factor_path for consistency
        self.factor_path = str(file_path)
        return str(file_path)


    @classmethod
    def _parse_dryrun(cls, d):
        if not d:
            return DryrunResult()
        if isinstance(d, DryrunResult):
            return d
        assert isinstance(d, dict), "dryrun_result must be a DryrunResult or a dict"
        assert "success" in d, "dryrun_result must contain 'success' key"
        assert "stdout" in d or "stderr" in d, "dryrun_result must contain 'stdout' or 'stderr' key"
        return DryrunResult(**d)

    @classmethod
    def _parse_semantic(cls, d):
        if not d:
            return SemanticCheckResult()
        if isinstance(d, SemanticCheckResult):
            return d
        assert isinstance(d, dict), "semantic_check_result must be a SemanticCheckResult or a dict"
        assert "passed" in d, "semantic_check_result must contain 'passed' key" 
        assert "reason" in d, "semantic_check_result must contain 'reason' key"
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
            factor_path=state.get("factor_path") or "",
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
    print(view)

