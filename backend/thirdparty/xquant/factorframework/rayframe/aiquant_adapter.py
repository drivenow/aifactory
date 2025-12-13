from __future__ import annotations

from typing import Dict, Optional, Union

import pandas as pd

from AIQuant.data_process import align
from AIQuant.datamanager import DataManager, get
from AIQuant.meta_service import ExcelMetaFactorService, MetaFactor, MetaFactorService


def _to_panel(df: pd.DataFrame) -> pd.DataFrame:
    """
    将 long 转换为 panel：
    - index: datetime
    - columns: symbol（若有多个值列，则为 MultiIndex(field, symbol)）
    """
    if df.empty:
        return df
    df = df.copy()
    if "__index_level_0__" in df.columns:
        df = df.drop(columns="__index_level_0__")
    if "datetime" not in df.columns or "symbol" not in df.columns:
        return df
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["symbol"] = df["symbol"].astype(str)
    value_cols = [c for c in df.columns if c not in ["datetime", "symbol"]]
    if not value_cols:
        return df
    panels = []
    for col in value_cols:
        wide = df.pivot(index="datetime", columns="symbol", values=col).sort_index()
        if len(value_cols) == 1:
            panels.append(wide)
        else:
            wide.columns = pd.MultiIndex.from_product([[col], wide.columns])
            panels.append(wide)
    if len(panels) == 1:
        return panels[0]
    return pd.concat(panels, axis=1).sort_index()


def _as_datamanager(conf: Union[DataManager, dict]) -> DataManager:
    if isinstance(conf, DataManager):
        return conf
    if isinstance(conf, dict):
        return DataManager(**conf)
    raise TypeError(f"aiquant_requirements 的配置需为 DataManager 或 dict，当前为 {type(conf)}")


class AIQuantDataAdapter:
    """将 AIQuant SDK 对接到 rayframe 的轻量适配器。"""

    def __init__(self, meta_service: Optional[MetaFactorService] = None):
        self.meta_service = meta_service or ExcelMetaFactorService()

    def resolve_meta(self, conf: DataManager) -> MetaFactor:
        return self.meta_service.get_library_meta(conf.LIB_ID)

    def fetch(self,
              conf: Union[DataManager, dict],
              target_freq: Optional[str] = None,
              target_index: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        dm_conf = _as_datamanager(conf).copy()
        meta = self.resolve_meta(dm_conf)
        dm_conf.FREQ = dm_conf.FREQ or meta.freq
        dm_conf.ALIGN_POLICY = dm_conf.ALIGN_POLICY or meta.align_policy
        dm_conf.LIB_TYPE = dm_conf.LIB_TYPE or meta.lib_type

        df = get(dm_conf, meta_service=self.meta_service)

        if target_freq and meta.freq and target_freq.lower() != meta.freq.lower():
            method = dm_conf.ALIGN_POLICY or meta.align_policy
            if not method:
                if meta.freq.lower() == "1m" and target_freq.lower() == "1d":
                    method = "agg_last"
                else:
                    method = "broadcast"
            df = align(df, meta.freq, target_freq, method, target_index=target_index)
        return df

    def load_all(self,
                 requirements: Dict[str, Union[DataManager, dict]],
                 target_freq: str,
                 start_date: str,
                 end_date: str) -> Dict[str, pd.DataFrame]:
        if not requirements:
            return {}

        meta_by_alias: Dict[str, MetaFactor] = {
            alias: self.resolve_meta(_as_datamanager(conf)) for alias, conf in requirements.items()
        }
        # 分钟频因子优先拉取，以便日频对齐时复用时间轴
        ordered_aliases = list(requirements.keys())
        if target_freq.lower() == "1m":
            ordered_aliases = sorted(
                requirements.keys(),
                key=lambda alias: 0 if meta_by_alias[alias].freq == "1m" else 1
            )

        minute_index = None
        raw_result: Dict[str, pd.DataFrame] = {}
        for alias in ordered_aliases:
            conf = _as_datamanager(requirements[alias]).copy()
            conf.API_START = conf.API_START or start_date
            conf.API_END = conf.API_END or end_date
            df = self.fetch(conf, target_freq=target_freq, target_index=minute_index)
            raw_result[alias] = df
            if target_freq.lower() == "1m" and meta_by_alias[alias].freq == "1m" and minute_index is None:
                minute_index = df[["datetime", "symbol"]]
        # 转 panel，并对齐标的列
        panels: Dict[str, pd.DataFrame] = {alias: _to_panel(df) for alias, df in raw_result.items()}
        all_symbols = set()
        for df in panels.values():
            if isinstance(df, pd.DataFrame):
                if df.columns.nlevels > 1:
                    all_symbols.update(df.columns.get_level_values(-1))
                else:
                    all_symbols.update(df.columns)
        for alias, df in panels.items():
            if not isinstance(df, pd.DataFrame) or df.empty or not all_symbols:
                continue
            if df.columns.nlevels > 1:
                fields = df.columns.get_level_values(0).unique()
                new_cols = pd.MultiIndex.from_product([fields, sorted(all_symbols)])
                df = df.reindex(columns=new_cols)
            else:
                df = df.reindex(columns=sorted(all_symbols))
            panels[alias] = df
        return panels


__all__ = ["AIQuantDataAdapter"]
