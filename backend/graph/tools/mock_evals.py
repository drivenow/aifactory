from typing import Dict, Any


def factor_ic_mock() -> Dict[str, Any]:
    return {"ic": 0.1, "ic_mean": 0.08, "ic_std": 0.12}


def factor_turnover_mock() -> Dict[str, Any]:
    return {"turnover": 0.3}


def factor_group_perf_mock() -> Dict[str, Any]:
    return {"group_returns": [0.01, 0.008, 0.006, 0.004, 0.002]}


def write_factor_and_metrics_mock(factor_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "factor": factor_name, "metrics_keys": list(metrics.keys())}