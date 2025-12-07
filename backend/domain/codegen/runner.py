from __future__ import annotations

from typing import Any, Dict

from domain.codegen.framework.factor_l3_py_tool import _mock_run
from domain.codegen.view import CodeGenView, CodeMode, FactorAgentState
from global_tools.sandbox_runner import sandbox_run_code


def run_factor(state: CodeGenView | FactorAgentState) -> Dict[str, Any]:
    """
    根据给定的状态运行因子代码并返回执行结果。

    参数
    ----
    state : FactorAgentState
        包含因子代码、代码模式（L3_PY/L3_CPP/普通模式）等信息的完整状态对象。

    返回
    ----
    Dict[str, Any]
        成功时返回：
        - success: True
        - stdout: 执行结果预览（字符串），若结果过长会被截断并附加提示
        - stderr: None

        失败时返回：
        - success: False
        - stdout: None
        - stderr: 错误信息（字符串）

    说明
    ----
    1. 若 code_mode 为 L3_PY 或 "l3_py"，调用 _mock_run 进行本地 mock 运行，
       并将结果映射到 stdout 字段以便前端展示。
    2. 若 code_mode 为 L3_CPP 或 "l3_cpp"，直接返回不支持本地 mock 的提示。
    3. 其他模式则通过 sandbox_run_code 在沙箱中执行，入口函数为 run_factor，
       默认参数为 ["2020-01-01", "2020-01-10", ["A"]]。结果过长时同样会被截断。
    """
    view = CodeGenView.from_state(state)
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        res = _mock_run(view.factor_code)
        if res.success:
            return {
                "success": True,
                "stdout": res.stdout,
            }
        view.set_dryrun_result(res)
        return {
            "success": False,
            "stderr": res.stderr,
        }
    if view.code_mode == CodeMode.L3_CPP or view.code_mode == "l3_cpp":
        return {
            "success": True,
            "stdout": "C++ 因子暂不支持本地 mock 运行，请在 SDK 环境中编译执行。",
        }

    sandbox_res = sandbox_run_code(
        view.factor_code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )
    if sandbox_res.get("success"):
        result_preview = str(sandbox_res.get("result"))
        if len(result_preview) > 200:
            result_preview = result_preview[:200] + "... (truncated)"
        return {
            "success": True,
            "stdout": "",
            "stderr": None,
        }
    return {
        "success": False,
        "stdout": None,
        "stderr": sandbox_res.get("result"),
    }


def run_factor_dryrun(state:  CodeGenView | FactorAgentState) -> Dict[str, Any]:
    """Alias to keep compatibility with older callers/tests."""
    return run_factor(state)
