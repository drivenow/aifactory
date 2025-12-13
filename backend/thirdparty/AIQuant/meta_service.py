from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional, Protocol

import pandas as pd
from pydantic import BaseModel, Field
from typing_extensions import Literal

META_FILE_PATH = Path(__file__).resolve().parent.parent / "aiquant_factor_meta.xlsx"


class MetaFactor(BaseModel):
    lib_id: str
    library_name: str
    lib_type: Literal["table", "factor"]
    freq: Literal["1m", "1d"]
    index_cols: List[str] = Field(default_factory=lambda: ["datetime", "symbol"])
    align_policy: Optional[str] = None

    class Config:
        extra = "allow"


class MetaFactorService(Protocol):
    def get_library_meta(self, lib_id: str) -> MetaFactor: ...

    def list_libraries(self, **filters) -> List[MetaFactor]: ...

    def get(self, lib_id: str) -> Optional[MetaFactor]: ...


class ExcelMetaFactorService:
    """
    简单的 Excel 元数据读取服务：
    - 以 LIB_ID 为唯一键
    - 支持 TTL 缓存，避免频繁读盘
    """

    def __init__(self, meta_path: Path | str = META_FILE_PATH, ttl_seconds: int = 300):
        self.meta_path = Path(meta_path)
        self.ttl_seconds = ttl_seconds
        self._meta_by_id: Dict[str, MetaFactor] = {}
        self._last_loaded_at: float = 0.0

    def _maybe_reload(self):
        now = time.time()
        if self._meta_by_id and (now - self._last_loaded_at) < self.ttl_seconds:
            return
        if not self.meta_path.exists():
            raise FileNotFoundError(f"未找到元数据文件：{self.meta_path}")
        df = pd.read_excel(self.meta_path)
        self._meta_by_id = self._normalize_df(df)
        self._last_loaded_at = now

    def _normalize_df(self, df: pd.DataFrame) -> Dict[str, MetaFactor]:
        meta_dict: Dict[str, MetaFactor] = {}
        if df.empty:
            return meta_dict
        # 统一列名
        df.columns = [str(col).strip() for col in df.columns]
        lower_map = {col.lower(): col for col in df.columns}
        for _, row in df.iterrows():
            raw = row.to_dict()
            lib_id = str(raw.get(lower_map.get("lib_id", "lib_id")) or raw.get(lower_map.get("library_id", "library_id")) or "").strip()
            if not lib_id:
                continue
            library_name = str(raw.get(lower_map.get("library_name", "library_name"), lib_id)).strip() or lib_id
            lib_type_raw = str(raw.get(lower_map.get("lib_type", "lib_type"), "")).strip().lower()
            if not lib_type_raw:
                lib_type_raw = str(raw.get(lower_map.get("category", "category"), "")).strip().lower()
            lib_type = lib_type_raw or "table"
            freq_raw = str(raw.get(lower_map.get("freq", "freq"), "")).strip().lower()
            if not freq_raw:
                freq_raw = str(raw.get(lower_map.get("factor_freq", "factor_freq"), "")).strip().lower()
            freq = freq_raw or "1d"
            index_cols_raw = raw.get(lower_map.get("index_cols", "index_cols"))
            align_policy = raw.get(lower_map.get("align_policy", "align_policy"))
            index_cols: List[str] = ["datetime", "symbol"]
            if isinstance(index_cols_raw, str):
                index_cols = [col.strip() for col in index_cols_raw.replace(";", ",").split(",") if col.strip()]
            elif isinstance(index_cols_raw, (list, tuple, pd.Series)):
                index_cols = [str(col) for col in index_cols_raw]

            extra = {
                k: v
                for k, v in raw.items()
                if k not in {
                    lower_map.get("lib_id", "lib_id"),
                    lower_map.get("library_id", "library_id"),
                    lower_map.get("library_name", "library_name"),
                    lower_map.get("lib_type", "lib_type"),
                    lower_map.get("freq", "freq"),
                    lower_map.get("index_cols", "index_cols"),
                    lower_map.get("align_policy", "align_policy"),
                }
            }
            try:
                meta = MetaFactor(
                    lib_id=lib_id,
                    library_name=library_name,
                    lib_type=lib_type,
                    freq=freq,
                    index_cols=index_cols or ["datetime", "symbol"],
                    align_policy=align_policy if pd.notna(align_policy) else None,
                    **extra,
                )
                meta_dict[lib_id] = meta
            except Exception:
                # 跳过不规范行，避免阻塞整体加载
                continue
        return meta_dict

    def get_library_meta(self, lib_id: str) -> MetaFactor:
        self._maybe_reload()
        if lib_id not in self._meta_by_id:
            raise KeyError(f"未在元数据中找到 LIB_ID={lib_id}")
        return self._meta_by_id[lib_id]

    def list_libraries(self, **filters) -> List[MetaFactor]:
        self._maybe_reload()
        metas = list(self._meta_by_id.values())
        for key, value in filters.items():
            metas = [meta for meta in metas if getattr(meta, key, None) == value]
        return metas

    def get(self, lib_id: str) -> Optional[MetaFactor]:
        try:
            return self.get_library_meta(lib_id)
        except KeyError:
            return None


__all__ = ["MetaFactor", "MetaFactorService", "ExcelMetaFactorService"]
