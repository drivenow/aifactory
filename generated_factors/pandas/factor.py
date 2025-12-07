
# Factor: factor
# Description: 动量因子

import pandas as pd


def load_data(start, end, universe):
    return pd.DataFrame({'close': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]})

def compute_factor(df: pd.DataFrame) -> pd.Series:
        lookback = 5
        price = df['close'] if isinstance(df, dict) else df['close']
        return price.pct_change(lookback)


def run_factor(start, end, universe):
    df = load_data(start, end, universe)
    return compute_factor(df)
