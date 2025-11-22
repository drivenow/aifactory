from typing import Dict


FACTOR_TEMPLATE = """
# Factor: {factor_name}
# Description: {user_spec}

import pandas as pd
import numpy as np

def load_data(start: str, end: str, universe: list[str]) -> pd.DataFrame:
    raise NotImplementedError

def compute_factor(df: pd.DataFrame) -> pd.Series:
    {factor_body}

def run_factor(start, end, universe):
    df = load_data(start, end, universe)
    fac = compute_factor(df)
    return fac
"""


def render_factor_code(factor_name: str, user_spec: str, factor_body: str) -> str:
    return FACTOR_TEMPLATE.format(
        factor_name=factor_name,
        user_spec=user_spec,
        factor_body=factor_body,
    )


def simple_factor_body_from_spec(user_spec: str) -> str:
    s = user_spec.lower()
    if "moving average" in s or "ma" in s or "滚动均值" in s:
        return (
            "window = 5\n"
            "price = df['close']\n"
            "return price.rolling(window).mean()\n"
        )
    if "momentum" in s or "动量" in s:
        return (
            "return df['close'].pct_change(5)\n"
        )
    return "raise NotImplementedError\n"