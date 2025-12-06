from __future__ import annotations

from typing import Any, Dict

from domain.codegen.tools.l3_factor_tool import _mock_run
from domain.codegen.view import CodeGenView, CodeMode, FactorAgentState
from global_tools.sandbox_runner import sandbox_run_code


def run_factor(state) -> Dict[str, Any]:
    view = CodeGenView.from_state(state)
    if view.code_mode == CodeMode.L3_PY or view.code_mode == "l3_py":
        res = _mock_run(view.factor_code)
        if res.get("ok"):
            # Map L3 result to stdout for display compatibility
            val_preview = str(res.get("result"))
            if len(val_preview) > 1000:
                val_preview = val_preview[:1000] + "... (truncated)"
            return {
                "success": True,
                "stdout": f"[L3 Mock Result]\n{val_preview}",
            }
        return {
            "success": False,
            "stderr": res.get("state_error"),
        }
    if view.code_mode == CodeMode.L3_CPP or view.code_mode == "l3_cpp":
        return {
            "success": False,
            "stderr": "C++ 因子暂不支持本地 mock 运行，请在 SDK 环境中编译执行。",
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
            "stdout": result_preview,
            "stderr": None,
        }
    return {
        "success": False,
        "stdout": None,
        "stderr": sandbox_res.get("result"),
    }


def run_factor_dryrun(state) -> Dict[str, Any]:
    """Alias to keep compatibility with older callers/tests."""
    return run_factor(state)
