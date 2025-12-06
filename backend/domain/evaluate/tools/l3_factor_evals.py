from __future__ import annotations

import os
from typing import Any, Dict, Optional

import pandas as pd
from langchain_core.tools import tool

from .factor_eval.FactorEvaluate import Factor_with_code, Factor_with_data

# 默认配置参考 README 示例
DEFAULT_FACTOR_LIST = {
    "FactorOBIC": [{}],
    "FactorOrderOBIC": [{}],
    "FactorTradeOBIC": [{}],
    "FactorCancelOBIC": [{}],
    "FactorOBIS": [{}],
    "FactorOrderOBIS": [{}],
    "FactorTradeOBIS": [{}],
    "FactorCancelOBIS": [{}],
}
DEFAULT_BASE_PATH = "/dfs/group/800657/025036/scratch/"
DEFAULT_CORR_PATH = "/dfs/group/800657/025036/factor_eval_std/result/corr.csv"
DEFAULT_RESULT_PATH = "/dfs/group/800657/025036/factor_eval_std/result/result_modify.csv"
DEFAULT_NUM_CPUS = 20
DEFAULT_MODE = "code"  # "code" 使用 Factor_with_code；"data" 使用 Factor_with_data


def run_factor_eval(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    按 README 示例调用 Factor_with_code / Factor_with_data 完成因子评价。
    必需依赖：ray、polars、FactorLib、FactorData 等外部环境。
    """
    factor_list = state.get("factor_list") or DEFAULT_FACTOR_LIST
    base_path = state.get("base_path") or DEFAULT_BASE_PATH
    corr_path = state.get("corr_path") or DEFAULT_CORR_PATH
    result_path = state.get("result_path") or DEFAULT_RESULT_PATH
    num_cpus = int(state.get("num_cpus") or DEFAULT_NUM_CPUS)
    eval_mode = (state.get("eval_mode") or DEFAULT_MODE).lower()

    if eval_mode == "data":
        data_path: Optional[str] = state.get("data_path")
        if not data_path:
            raise ValueError("data_mode requires data_path")
        evaluator = Factor_with_data(data_path=data_path, factor_list=factor_list, num_cpus=num_cpus)
        evaluator.factor_data_generate()
        evaluator.calculate_correlation(corr_path)
        evaluator.factor_eval_data(corr_path, result_path)
    else:
        evaluator = Factor_with_code(factor_list=factor_list, base_path=base_path, num_cpus=num_cpus)
        evaluator.factor_data_generate()
        evaluator.calculate_correlation(corr_path)
        evaluator.factor_eval_code(corr_path, result_path)

    metrics = {
        "result_path": result_path,
        "corr_path": corr_path,
    }
    state["eval_metrics"] = metrics
    return metrics


@tool("l3_factor_eval")
def l3_factor_eval_tool(
    factor_list: Optional[Dict[str, Any]] = None,
    base_path: str = DEFAULT_BASE_PATH,
    corr_path: str = DEFAULT_CORR_PATH,
    result_path: str = DEFAULT_RESULT_PATH,
    num_cpus: int = DEFAULT_NUM_CPUS,
    eval_mode: str = DEFAULT_MODE,
    data_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    以工具形式触发 L3 因子评价。
    参数同 run_factor_eval；eval_mode="code" 使用因子代码生成数据，"data" 直接用已有数据。
    返回结果路径。
    """
    state: Dict[str, Any] = {
        "factor_list": factor_list or DEFAULT_FACTOR_LIST,
        "base_path": base_path,
        "corr_path": corr_path,
        "result_path": result_path,
        "num_cpus": num_cpus,
        "eval_mode": eval_mode,
    }
    if data_path:
        state["data_path"] = data_path
    return run_factor_eval(state)
