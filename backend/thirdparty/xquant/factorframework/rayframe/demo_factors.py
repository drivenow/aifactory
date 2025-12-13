import sys
from pathlib import Path

# 确保可以找到 backend/thirdparty 下的 xquant 包
thirdparty_root = str(Path(__file__).resolve().parents[4])
if thirdparty_root not in sys.path:
    sys.path.append(thirdparty_root)
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
            "DAY_EOD": DataManager(
                LIB_ID="DEMO_DAY_TABLE",
                API_START="20240101",
                API_END="20240228",
                LIB_ID_FEILD=["close", "volume"],
            ),
        }

        def calc(self, factor_data=None, price_data=None, dt_to=None, **kwargs):
            # inputs: dict，键为 alias 或 alias.field，值为 DataFrame(index=datetime, columns=symbol)
            inputs = self.load_inputs(dt_to=dt_to)
            close_df = inputs.get("DEMO_DAY_TABLE.close", pd.DataFrame())
            if close_df.empty:
                return pd.Series(dtype=float)
            ts = pd.to_datetime(dt_to) if dt_to is not None else close_df.index.max()
            ser = close_df.loc[:ts]
            ser = ser.iloc[-1]
            return ser.reindex(self.security_pool).fillna(0.0)


    class FactorDemoMin(Factor):
        """示例分钟因子：读取 DEMO_MIN_FACTOR，输出最新时间点的分钟因子值。"""

        factor_type = "MIN"
        factor_name = "FactorDemoMin"
        security_pool = ["000001.SZ", "000002.SZ"]
        aiquant_requirements = {
            "DERIVED_MIN": DataManager(
                LIB_ID="DEMO_MIN_FACTOR",
                API_START="20240101",
                API_END="20240228",
                LIB_ID_FEILD=["factorA", "factorB"],
            ),
        }

        def calc(self, factor_data=None, price_data=None, dt_to=None, **kwargs):
            inputs = self.load_inputs(dt_to=dt_to)
            factorA = inputs.get("DEMO_MIN_FACTOR.factorA", pd.DataFrame())
            factorB = inputs.get("DEMO_MIN_FACTOR.factorB", pd.DataFrame())
            if factorA.empty:
                return pd.DataFrame()
            ts = pd.to_datetime(dt_to) if dt_to is not None else factorA.index.max()
            fa_window = factorA.loc[:ts]
            fb_window = factorB.loc[:ts] if not factorB.empty else None
            latest_df = pd.DataFrame({"factorA": fa_window.iloc[-1]})
            if fb_window is not None and not fb_window.empty:
                latest_df["factorB"] = fb_window.iloc[-1]
            return latest_df


    class FactorVolMA5OverFloatCap(Factor):
        """
        示例日频因子：读取 factor_d 开头的量价/流通市值数据，
        计算 5 日均成交量 / 流通市值。
        """

        factor_type = "DAY"
        factor_name = "FactorVolMA5OverFloatCap"
        security_pool = None
        aiquant_requirements = {
            "PRICE": DataManager(
                LIB_ID="factor_d_marketindex",
                API_START="20240101",
                API_END="20241231",
                LIB_ID_FEILD=["volume"],
                FREQ="1d",
            ),
            "CAP": DataManager(
                LIB_ID="factor_d_moneyflow",
                API_START="20240101",
                API_END="20241231",
                LIB_ID_FEILD=["float_mkt_cap"],
                FREQ="1d",
            ),
        }

        def calc(self, factor_data=None, price_data=None, dt_to=None, **kwargs):
            # 框架在 run_factors_days 中已按窗口预加载，这里仅按 dt_to 切片，数据为 panel
            inputs = self.load_inputs(dt_to=dt_to)
            volume_panel = inputs.get("factor_d_marketindex.volume", pd.DataFrame())
            cap_df = inputs.get("factor_d_moneyflow.float_mkt_cap", pd.DataFrame())
            if volume_panel.empty or cap_df.empty:
                return pd.Series(dtype=float)

            ts = pd.to_datetime(dt_to) if dt_to is not None else volume_panel.index.max()
            vol_window = volume_panel.loc[:ts]
            vol_ma5 = vol_window.rolling(5, min_periods=1).mean().iloc[-1]

            # 尝试常见流通市值列名
            cap_window = cap_df.loc[:ts]
            cap_latest = cap_window.iloc[-1]

            ratio = vol_ma5 / cap_latest.replace({0: pd.NA})
            ratio = ratio.replace([pd.NA, pd.NaT, float("inf"), -float("inf")], 0)
            if self.security_pool:
                return ratio.reindex(self.security_pool).fillna(0)
            return ratio.fillna(0)
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
