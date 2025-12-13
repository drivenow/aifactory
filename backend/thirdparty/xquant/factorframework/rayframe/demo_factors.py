import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))  # 添加 backend/thirdparty 到路径以便本地运行示例
import os
os.environ.setdefault("ENV_VERSION", "uat")

import pandas as pd

try:
    from AIQuant.datamanager import DataManager
    from xquant.factorframework.rayframe.BaseFactor import Factor
    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - 便于在缺依赖环境下演示
    DataManager = None

    class Factor:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(f"AIQuant/xquant dependencies missing: {exc}")

    _IMPORT_ERROR = exc


if DataManager is not None:
    class FactorDemoDay(Factor):
        """示例日频因子：读取 DEMO_DAY_TABLE 并返回当日 close 序列。"""

        factor_type = "DAY"
        factor_name = "FactorDemoDay"
        security_pool = ["000001.SZ", "000002.SZ"]
        aiquant_requirements = {
            "DAY_EOD": DataManager(LIB_ID="DEMO_DAY_TABLE", API_START="20240101", API_END="20240228"),
        }

        def calc(self, factor_data=None, price_data=None, dt_to=None, **kwargs):
            inputs = self.load_inputs(start_date="20240101", end_date="20240228", dt_to=dt_to)
            df = inputs.get("DAY_EOD", pd.DataFrame())
            if df.empty:
                return pd.Series(dtype=float)
            target_ts = pd.to_datetime(dt_to) if dt_to is not None else df["datetime"].max()
            slice_df = df[df["datetime"] == target_ts]
            ser = slice_df.set_index("symbol")["close"]
            return ser.reindex(self.security_pool).fillna(0.0)


    class FactorDemoMin(Factor):
        """示例分钟因子：读取 DEMO_MIN_FACTOR，输出最新时间点的分钟因子值。"""

        factor_type = "MIN"
        factor_name = "FactorDemoMin"
        security_pool = ["000001.SZ", "000002.SZ"]
        aiquant_requirements = {
            "DERIVED_MIN": DataManager(LIB_ID="DEMO_MIN_FACTOR", API_START="20240101", API_END="20240228"),
        }

        def calc(self, factor_data=None, price_data=None, dt_to=None, **kwargs):
            inputs = self.load_inputs(start_date="20240101", end_date="20240228", dt_to=dt_to)
            df = inputs.get("DERIVED_MIN", pd.DataFrame())
            if df.empty:
                return pd.DataFrame()
            if dt_to is not None:
                ts = pd.to_datetime(dt_to)
                df = df[df["datetime"] <= ts]
            latest_ts = df["datetime"].max()
            latest_slice = df[df["datetime"] == latest_ts]
            return latest_slice.set_index("symbol")[["factorA", "factorB"]]
else:  # pragma: no cover - 占位，缺依赖环境下给出友好提示
    class FactorDemoDay:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"AIQuant/xquant dependencies missing: {_IMPORT_ERROR}")

    class FactorDemoMin:
        def __init__(self, *args, **kwargs):
            raise ImportError(f"AIQuant/xquant dependencies missing: {_IMPORT_ERROR}")


if __name__ == "__main__":
    if _IMPORT_ERROR:
        print(f"Skip demo: missing dependencies -> {_IMPORT_ERROR}")
        raise SystemExit(0)
    # 简单 smoke 测试：直接加载示例数据
    fac = FactorDemoDay()
    fac.preload_aiquant_inputs(start_date="20240101", end_date="20240228")
    print(fac.load_inputs(dt_to="20240102")["DAY_EOD"])
