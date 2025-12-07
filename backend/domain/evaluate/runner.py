# backend/domain/evaluate/runner.py
from __future__ import annotations

from typing import Any, Dict

from domain.evaluate.view import EvalView, FactorAgentState
from domain.evaluate.tools.l3_factor_evals import l3_factor_eval_tool
from domain.evaluate.tools import mock_evals


def compute_eval_metrics(state:  EvalView | FactorAgentState) -> Dict[str, Any]:
    """
    根据 state.eval_type 选择评价方式：
    - "l3": 调用 L3 择时因子评价（当前实现）
    - "alpha"/其他：暂未实现，回退 mock

    参数
    ----
    state : EvalView | FactorAgentState
        包含因子代码、代码模式（L3_PY/L3_CPP/普通模式）、dryrun 结果等信息的完整状态对象。

    返回
    ----
    Dict[str, Any]
        包含评价指标的字典，格式为 {"metric_name": metric_value}。
    """
    eval_type = (state.get("eval_type") or "mock").lower()

    if eval_type == "l3":
        try:
            return l3_factor_eval_tool(**state)  # l3_factor_eval_tool 接受参数字典
        except Exception as e:
            state.setdefault("error", []).append(f"l3_factor_eval failed: {e}")

    # fallback mock
    return mock_evals.mock_compute_eval_metrics(state)


def write_factor_and_metrics(state: EvalView | FactorAgentState) -> Dict[str, Any]:
    view = EvalView.from_state(state)
    metrics = view.eval_metrics
    return mock_evals.write_factor_and_metrics_mock(view.factor_name, metrics)
