from __future__ import annotations

from typing import Dict, Optional, Union

import pandas as pd

from AIQuant.data_process import align
from AIQuant.datamanager import DataManager, get
from AIQuant.meta_service import ExcelMetaFactorService, MetaFactor, MetaFactorService


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
            method = dm_conf.ALIGN_POLICY or meta.align_policy or "broadcast"
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
        result: Dict[str, pd.DataFrame] = {}
        for alias in ordered_aliases:
            conf = _as_datamanager(requirements[alias]).copy()
            conf.API_START = conf.API_START or start_date
            conf.API_END = conf.API_END or end_date
            df = self.fetch(conf, target_freq=target_freq, target_index=minute_index)
            result[alias] = df
            if target_freq.lower() == "1m" and meta_by_alias[alias].freq == "1m" and minute_index is None:
                minute_index = df[["datetime", "symbol"]]
        return result


__all__ = ["AIQuantDataAdapter"]
