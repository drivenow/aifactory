from typing import Dict, Any
from domain.evaluate.view import FactorAgentState, EvalView

def factor_ic_mock() -> Dict[str, Any]:
    """返回 IC 相关统计的占位结果"""
    return {"ic": 0.1, "ic_mean": 0.08, "ic_std": 0.12}


def factor_turnover_mock() -> Dict[str, Any]:
    """返回换手率的占位结果"""
    return {"turnover": 0.3}


def factor_group_perf_mock() -> Dict[str, Any]:
    """返回分组收益的占位结果"""
    return {"group_returns": [0.01, 0.008, 0.006, 0.004, 0.002]}


def mock_compute_eval_metrics(state: FactorAgentState) -> Dict[str, Any]:
    # fallback mock
    ic = factor_ic_mock()
    to = factor_turnover_mock()
    gp = factor_group_perf_mock()
    return {"ic": ic, "turnover": to, "group_perf": gp}

def write_factor_and_metrics_mock(factor_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """模拟将因子与评价指标入库"""
    return {"status": "success", "factor": factor_name, "metrics_keys": list(metrics.keys())}
"""因子评价与入库（mock 版）

提供 IC/换手率/分组收益等简易指标的占位实现，以及入库操作的占位实现。
后续可替换为真实业务逻辑。
"""