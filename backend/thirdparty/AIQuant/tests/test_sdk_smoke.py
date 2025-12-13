"""轻量 smoke 测试：验证 meta_service/datamanager/align/aiquant_adapter 基础链路。

运行方式：
    PYTHONPATH=backend/thirdparty pytest backend/thirdparty/AIQuant/tests/test_sdk_smoke.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

# 确保 backend/thirdparty 在路径中，便于导入 xquant/AIQuant
thirdparty_root = Path(__file__).resolve().parents[2]
if str(thirdparty_root) not in sys.path:
    sys.path.append(str(thirdparty_root))

os.environ.setdefault("ENV_VERSION", "uat")

from AIQuant.data_process import align  # noqa: E402
from AIQuant.datamanager import DataManager, get  # noqa: E402
from AIQuant.meta_service import ExcelMetaFactorService  # noqa: E402
from xquant.factorframework.rayframe.aiquant_adapter import AIQuantDataAdapter  # noqa: E402


def test_meta_service_basic():
    svc = ExcelMetaFactorService()
    meta = svc.get_library_meta("DEMO_DAY_TABLE")
    assert meta.lib_id == "DEMO_DAY_TABLE"
    assert meta.freq in {"1d", "1m"}
    assert meta.library_name  # 默认回退为 lib_id


def test_datamanager_get_demo_day():
    conf = DataManager(LIB_ID="DEMO_DAY_TABLE", API_START="20240101", API_END="20240228")
    df = get(conf)
    assert not df.empty
    assert {"datetime", "symbol"}.issubset(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["datetime"])


def test_align_and_adapter_day_to_min():
    adapter = AIQuantDataAdapter()
    min_conf = DataManager(LIB_ID="DEMO_MIN_FACTOR", API_START="20240101", API_END="20240228")
    day_conf = DataManager(LIB_ID="DEMO_DAY_TABLE", API_START="20240101", API_END="20240228")

    min_df = adapter.fetch(min_conf, target_freq="1m")
    assert not min_df.empty

    day_df = adapter.fetch(day_conf, target_freq="1m", target_index=min_df[["datetime", "symbol"]])
    assert len(day_df) == len(min_df)  # broadcast/ffill 保持分钟轴

    # 分钟 -> 日聚合
    agg_df = align(min_df, "1m", "1d", "agg_last")
    assert not agg_df.empty
    assert agg_df["datetime"].dt.date.nunique() >= 1


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__])
