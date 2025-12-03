from typing import Dict


FACTOR_TEMPLATE = """
# Factor: {factor_name}
# Description: {user_spec}

import pandas as pd

def load_data(start, end, universe):
    return pd.DataFrame({{'close': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]}})

def compute_factor(df: pd.DataFrame) -> pd.Series:
{factor_body}

def run_factor(start, end, universe):
    df = load_data(start, end, universe)
    return compute_factor(df)
"""


def render_factor_code(factor_name: str, user_spec: str, factor_body: str) -> str:
    """渲染因子模板

    参数：
    - factor_name: 因子名称标识
    - user_spec: 用户自然语言描述
    - factor_body: 计算主体代码（需正确缩进）
    """
    return FACTOR_TEMPLATE.format(
        factor_name=factor_name,
        user_spec=user_spec,
        factor_body=factor_body,
    )


def simple_factor_body_from_spec(user_spec: str) -> str:
    """根据描述生成简易因子主体（mock）

    说明：
    - 识别“滚动均值/MA”等关键词，返回相应计算逻辑
    - 未识别时返回 `raise NotImplementedError`，便于触发 run_factor_dryrun 失败与人审
    """
    s = user_spec.lower()
    if "moving average" in s or "ma" in s or "滚动均值" in s or "均值" in s:
        return (
            "    window = 5\n"
            "    price = df['close']\n"
            "    return price.rolling(window).mean()\n"
        )
    if "momentum" in s or "动量" in s:
        return (
            "        lookback = 5\n"
            "        price = df['close'] if isinstance(df, dict) else df['close']\n"
            "        return price.pct_change(lookback)\n"
        )
    return "        raise NotImplementedError\n"
"""
因子模板与渲染工具

该模块提供统一的因子代码模板 FACTOR_TEMPLATE，以及将因子名/描述/主体填入模板的渲染函数。
同时提供一个基于用户描述的简易主体生成器（mock），用于 MVP 阶段的快速演示。
"""