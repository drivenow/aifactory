from __future__ import annotations

from typing import Any, Dict

from .tools.l3_factor_tool import _mock_run
from backend.graph.tools.sandbox_runner import run_code
from .view import CodeGenView, CodeMode


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
                "result": res.get("result"),
                "stdout": f"[L3 Mock Result]\n{val_preview}",
            }
        return {
            "success": False,
            "traceback": res.get("error"),
            "stderr": res.get("error"),
        }

    return run_code(
        view.factor_code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )


def run_factor_dryrun(state) -> Dict[str, Any]:
    """Alias to keep compatibility with older callers/tests."""
    return run_factor(state)
