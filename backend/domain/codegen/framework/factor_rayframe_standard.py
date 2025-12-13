"""Rayframe Python 因子开发规范与示例（供 codegen prompt 使用）。"""

PROMPT_RAYFRAME_PY_RULE = """
1) 因子类定义
- 继承 xquant.factorframework.rayframe.BaseFactor.Factor。
- 类名=因子名=文件名，保持一致；设置 class 属性 factor_name = "<类名>"。
- 设置 factor_type: "DAY"（日频）或 "MIN"（分钟）。
- 如需股票池，使用 security_pool（列表或 None）；不直接硬编码数据。

2) 数据声明（唯一入口）
- 必须通过 aiquant_requirements 声明所需数据，键为别名，值为 DataManager。
- DataManager 关键字段：LIB_ID（必填），API_START/API_END（回放窗口），LIB_ID_FEILD（必填：需加载的字段名列表），RETURN_FORMAT 保持默认 long。
- 不允许在 calc 中直接调用 FactorData、get_hive_data、requests 等外部接口，也不允许硬编码 parquet 路径。

3) 取数方式
- 框架在 run_factors_days 前已调用 preload_aiquant_inputs 完成取数/对齐并缓存，calc 中只需 self.load_inputs(dt_to=...) 获取缓存。
- inputs 结构：dict[alias] -> DataFrame 或 dict[field->DataFrame]：
  - DataFrame: index=datetime，columns=symbol（单字段）
  - dict: key=字段名（LIB_ID_FEILD 指定的字段），value=DataFrame（index=datetime，columns=symbol）
  列已对齐统一标的；calc 内无需传 start/end，可选 dt_from/dt_to 作为回看窗口。
- dt_to 为当前回放时间点，需用它切片：df[df["datetime"] <= dt_to] 或 df[df["datetime"] == dt_to]。
- MIN_BASE 仍由框架处理，aiquant_requirements 适用于缓存表/因子（如 Factormin、DEMO_DAY_TABLE 等）。

4) 返回约束
- 日频因子：返回索引为 symbol 的 pd.Series。
- 分钟因子：返回以 symbol 为索引/列的 pd.DataFrame 或 pd.Series（与现有 demo 保持一致）。
- 当数据为空或分母为 0 时，需做健壮性处理，避免异常。

5) 禁止事项
- 禁止直接读写文件/网络请求/系统调用。
- 禁止直接实例化 FactorData/第三方 API；必须走 aiquant_requirements + load_inputs。
- 禁止在模块顶层执行取数或耗时逻辑。
"""


PROMPT_RAYFRAME_PY_DEMO_DAY = """
日频示例（取日行情并返回当日 close）：
```
import pandas as pd
from AIQuant.datamanager import DataManager
from xquant.factorframework.rayframe.BaseFactor import Factor

class FactorDemoDay(Factor):
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
        ts = pd.to_datetime(dt_to) if dt_to is not None else df["datetime"].max()
        slice_df = df[df["datetime"] == ts]
        return slice_df.set_index("symbol")["close"].reindex(self.security_pool).fillna(0.0)
```
"""


PROMPT_RAYFRAME_PY_DEMO_MIN = """
分钟示例（取分钟衍生因子并输出最新时间点的两个列）：
```
import pandas as pd
from AIQuant.datamanager import DataManager
from xquant.factorframework.rayframe.BaseFactor import Factor

class FactorDemoMin(Factor):
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
```
"""
