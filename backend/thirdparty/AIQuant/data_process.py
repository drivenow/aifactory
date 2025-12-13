from __future__ import annotations

from typing import Optional

import pandas as pd


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    df = df.copy()
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def _extract_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.date


def align(source_df: pd.DataFrame,
          source_freq: str,
          target_freq: str,
          method: str,
          target_index: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    频率对齐工具，仅支持 1d/1m 之间的 broadcast/ffill/agg_last。

    参数
    ----
    source_df : pd.DataFrame
        原始数据，需包含 datetime/symbol。
    source_freq : str
        原始数据频率，1d 或 1m。
    target_freq : str
        目标频率，1d 或 1m。
    method : str
        broadcast/ffill/agg_last。
    target_index : pd.DataFrame, optional
        目标频率的时间轴（如分钟行情）；日->分的对齐需要该参数。
    """
    source_freq = (source_freq or "").lower()
    target_freq = (target_freq or "").lower()
    method = (method or "").lower()
    if source_freq == target_freq:
        return _ensure_datetime(source_df)

    if source_freq == "1d" and target_freq == "1m":
        if target_index is None or target_index.empty:
            raise ValueError("日频对齐到分钟频需要提供 target_index 作为时间轴")
        base_df = _ensure_datetime(target_index)
        src = _ensure_datetime(source_df)
        src["date"] = _extract_date(src["datetime"])
        value_cols = [col for col in src.columns if col not in ["datetime", "symbol", "date"]]

        if method == "broadcast":
            base_df = base_df.copy()
            base_df["date"] = _extract_date(base_df["datetime"])
            merged = base_df.merge(
                src.drop(columns=["datetime"]), on=["date", "symbol"], how="left"
            )
            merged = merged.drop(columns=["date"])
            return merged

        if method == "ffill":
            # merge_asof 在同一 symbol 内向前填充
            base_df = base_df.sort_values(["symbol", "datetime"])
            src = src.sort_values(["symbol", "datetime"])
            aligned = pd.merge_asof(
                base_df,
                src[["datetime", "symbol"] + value_cols],
                by="symbol",
                on="datetime",
                direction="backward",
            )
            return aligned

        raise ValueError(f"不支持的日->分对齐策略：{method}")

    if source_freq == "1m" and target_freq == "1d":
        if method != "agg_last":
            raise ValueError("分钟->日仅支持 agg_last 策略")
        src = _ensure_datetime(source_df)
        src["date"] = _extract_date(src["datetime"])
        value_cols = [col for col in src.columns if col not in ["datetime", "symbol", "date"]]
        agg_df = (
            src.sort_values("datetime")
            .groupby(["date", "symbol"], as_index=False)[value_cols]
            .last()
        )
        agg_df = agg_df.rename(columns={"date": "datetime"})
        agg_df["datetime"] = pd.to_datetime(agg_df["datetime"])
        return agg_df

    raise ValueError(f"暂不支持 {source_freq}->{target_freq} 的对齐")


__all__ = ["align"]
