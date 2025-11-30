# backend/graph/domain/eval.py
from __future__ import annotations

from typing import Dict, Any

from ..tools import mock_evals


def compute_eval_metrics() -> Dict[str, Any]:
    """
    使用 mock_evals 模块生成因子评价指标。

    这里只是 mock，方便前端展示图表：
    - ic
    - turnover
    - group_perf
    """
    ic = mock_evals.factor_ic_mock()
    to = mock_evals.factor_turnover_mock()
    gp = mock_evals.factor_group_perf_mock()
    metrics = {"ic": ic, "turnover": to, "group_perf": gp}
    return metrics


def write_factor_and_metrics(name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    将因子与评价结果“写入数据库”（mock）。

    返回值示例：
    - {"status": "success"} / {"status": "failed"}
    """
    res = mock_evals.write_factor_and_metrics_mock(name, metrics)
    return res
