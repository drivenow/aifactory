import os
import datetime as dt
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import polars as pl
from pydantic import BaseModel, Field

from AIQuant.meta_service import ExcelMetaFactorService, MetaFactorService
from xquant.setXquantEnv import xquantEnv

try:
    from AIQuant.data_api.index_platform_data import IndicatorData
except Exception:
    IndicatorData = None

fd = None
_FACTOR_DATA_ERR = None
try:
    from xquant.factordata.factor import FactorData  # type: ignore
except Exception as exc:  # pragma: no cover - 缺依赖环境下提供兜底
    _FACTOR_DATA_ERR = exc

_THIRD_FD_ERR = None
tfd = None
try:
    from xquant.thirdpartydata.factordata import FactorData as third_FD  # type: ignore
except Exception as exc:  # pragma: no cover
    _THIRD_FD_ERR = exc

_FIC_ERR = None
fic = None
try:
    from xquant.thirdpartydata.fic_api_data import FicApiData  # type: ignore
except Exception as exc:  # pragma: no cover
    _FIC_ERR = exc

_IDA_ERR = None
ida = None
try:
    ida = IndicatorData() if IndicatorData else None  # type: ignore
except Exception as exc:  # pragma: no cover
    _IDA_ERR = exc

try:
    from AIQuant.data_api.hive_data import get_hive_data
except Exception:
    get_hive_data = None

DEFAULT_CACHE_BASE_PATH = "/mnt/x/RPA-github/langgraph_source/aifactory/backend/thirdparty/daily_factor"


class DataManager(BaseModel):
    """
    参数占位符，若API_KWARGS中有占位符，需要替换为实际的参数值：
    DATE: 运行日期
    SYMBOL: 标的
    """
    API_TYPE: str = ''  # API类型
    LIB_ID: str = ''  # 唯一数据名，可以是表名或者因子库名 ZX.ASHAREEODPRICES
    API_START: str = ''
    API_END: str = ''
    API_KWARGS: Dict = Field(default_factory=dict)  # API传入的运行参数, SDATE, EDATE预留关键字占位符
    LIB_TYPE: str = ""  # 区分是表还是因子库
    LIB_ID_FEILD: List[str] = Field(default_factory=list)  # DATA_ID下对应的列名（对表可以是列名，对因子库可以是因子名），默认为空取所有因子或列
    API_INDEX_COL: Dict = Field(default_factory=dict)  # 业务日期、标的列映射
    FREQ: Optional[str] = None  # 数据频率，默认从元数据填充
    ALIGN_POLICY: Optional[str] = None  # 跨频对齐策略，默认从元数据填充
    RETURN_FORMAT: str = "long"  # 默认long格式
    if xquantEnv == 0:
        TABLE_BASE_PATH: str = DEFAULT_CACHE_BASE_PATH
        FACTOR_BASE_PATH: str = DEFAULT_CACHE_BASE_PATH
    else:
        TABLE_BASE_PATH: str = '/dfs/group/800657/library_alpha/quant_data/table/'  # /dfs/group/800657/library_alpha/quant_data/table/202511/ASHAREEODPRICES.parquet
        FACTOR_BASE_PATH: str = '/dfs/group/800657/library_alpha/quant_data/factor/daily_factor/'  # /dfs/group/800657/library_alpha/quant_data/factor/daily_factor/202511/Factor_xunfen1.parquet
    EXTRA_KWARGS: Dict = Field(default_factory=dict)  # 个性化的其他字段，如init_date, start_date
    LINK_IDS: List[str] = Field(default_factory=lambda: ['013150', '022917', '011048', '016349'])

    def split_date_by_month(self, statr_date, end_date):
        if fd is not None:
            date_list = fd.tradingday(statr_date, end_date)
        else:
            # 简单兜底：使用日历日范围
            start = dt.datetime.strptime(statr_date, "%Y%m%d")
            end = dt.datetime.strptime(end_date, "%Y%m%d")
            date_list = [(start + dt.timedelta(days=i)).strftime("%Y%m%d") for i in range((end - start).days + 1)]
        month_dct = defaultdict(list)
        for date in date_list:
            month = date[:6]
            month_dct[month].append(date)
        return month_dct

    def merge_df_by_cover(self, old_df, new_df, cover):
        # 如果覆盖 则去掉老数据中和新数据重复objectid的内容  如果不覆盖 去掉新数据中和老数据重复objectid的内容
        if not cover:
            if 'OBJECT_ID' in new_df.columns:
                new_df = new_df[~new_df['OBJECT_ID'].isin(old_df['OBJECT_ID'].values.tolist())]
            else:
                new_df = new_df[~new_df['datetime'].isin(old_df['datetime'].values.tolist())]
            merge_df = pd.concat([old_df, new_df]).sort_values(by='datetime')
            print(f"只更新增量数据")
        else:
            new_df = new_df.sort_values(by='datetime')
            if 'OBJECT_ID' in new_df.columns:
                old_df = old_df[~old_df['OBJECT_ID'].isin(new_df['OBJECT_ID'].values.tolist())]
            else:
                old_df = old_df[~old_df['datetime'].isin(new_df['datetime'].values.tolist())]
            merge_df = pd.concat([old_df, new_df])
            merge_df = merge_df.sort_values(by='datetime')
            print(f"覆盖式更新数据")
        return merge_df

    def save_table_data_bydate(self, df_data, date_col_name, out_path, lib_id, cover):
        """
         存储日频万得数据
        :param month_df_dict: dict，key为年份，value为列表（元素为key年份对应的数据）
        :param out_path: str，数据存储路径
        :param cover: bool，是否覆盖
        :return:
        """
        # 字典中的数据进行汇总 每月的文件存储一次 节省读写数据的时间
        df_data['month'] = df_data[date_col_name].astype(str).apply(lambda x: x[:6])
        for month, new_df in df_data.groupby('month'):
            del new_df['month']
            out_path_m = os.path.join(out_path, month)
            if not os.path.exists(out_path_m):
                os.makedirs(out_path_m, exist_ok=True)
            out_fpath = os.path.join(out_path_m, f"{lib_id}.parquet")
            new_df.rename(columns=self.API_INDEX_COL, inplace=True)
            if 'symbol' not in new_df.columns:
                new_df['symbol'] = 'ALL'
            if 'symbol' in new_df.columns:
                new_df = new_df[['symbol'] + [col for col in new_df.columns if col != 'symbol']]
            if 'datetime' in new_df.columns:
                new_df = new_df[['datetime'] + [col for col in new_df.columns if col != 'datetime']]
                new_df['datetime'] = new_df['datetime'].astype(str)

            if not os.path.exists(out_fpath):
                if 'OBJECT_ID' in new_df.columns:
                    new_df = new_df.drop_duplicates('OBJECT_ID')
                new_df.sort_values(by='datetime').to_parquet(out_fpath)
            else:
                old_df = pd.read_parquet(out_fpath)
                old_df_dtype = pd.DataFrame(old_df.dtypes).rename(columns={0: 'dtype'})
                new_df_dtype = pd.DataFrame(new_df.dtypes).rename(columns={0: 'dtype'})
                new_df_dtype['dtype'] = [ty if ty != 'object' else 'str' for ty in new_df_dtype['dtype']]
                df_types = pd.merge(left=old_df_dtype, right=new_df_dtype, how='inner', left_index=True,
                                    right_index=True, suffixes=['_old', '_new'])
                for col in df_types.index:
                    try:
                        if df_types.loc[col, 'dtype_new'] == 'int64' and df_types.loc[col, 'dtype_old'] == 'object':
                            old_df[col] = old_df[col].replace('nan', np.nan).replace('NA', np.nan).replace('inf',
                                                                                                           np.nan).replace(
                                [np.inf, -np.inf], np.nan)
                            old_df[col] = pd.to_numeric(old_df[col], errors='coerce')
                            old_df[col] = old_df[col].astype('float').astype(df_types.loc[col, 'dtype_new'])
                        elif df_types.loc[col, 'dtype_new'] == 'float64' and df_types.loc[col, 'dtype_old'] == 'object':
                            old_df[col] = old_df[col].replace('nan', np.nan).replace('NA', np.nan).replace('inf',
                                                                                                           np.nan).replace(
                                [np.inf, -np.inf], np.nan)
                            old_df[col] = pd.to_numeric(old_df[col], errors='coerce')
                            old_df[col] = old_df[col].astype('float64')
                        else:
                            old_df[col] = old_df[col].astype(df_types.loc[col, 'dtype_new'])
                    except Exception as e:
                        if "non-finite" in str(e):
                            old_df[col] = old_df[col].replace('nan', np.nan).replace('NA', np.nan).replace('inf',
                                                                                                           np.nan).replace(
                                [np.inf, -np.inf], np.nan)
                            old_df[col] = pd.to_numeric(old_df[col], errors='coerce')
                            old_df[col] = old_df[col].fillna(0)
                            old_df[col] = old_df[col].astype(df_types.loc[col, 'dtype_new'])

                merge_df = self.merge_df_by_cover(old_df=old_df, new_df=new_df, cover=cover)

                if 'OBJECT_ID' in new_df.columns:
                    merge_df = merge_df.drop_duplicates('OBJECT_ID')

                merge_df = merge_df[old_df.columns]
                merge_df_dtype = pd.DataFrame(merge_df.dtypes).rename(columns={0: 'dtype'})
                new_df_dtype = pd.DataFrame(new_df.dtypes).rename(columns={0: 'dtype'})
                new_df_dtype['dtype'] = [ty if ty != 'object' else 'str' for ty in new_df_dtype['dtype']]
                df_types = pd.merge(left=merge_df_dtype, right=new_df_dtype, how='inner', left_index=True,
                                    right_index=True, suffixes=['_mer', '_new'])
                for col in df_types.index:
                    try:
                        if df_types.loc[col, 'dtype_new'] == 'int64' and df_types.loc[col, 'dtype_old'] == 'object':
                            merge_df[col] = merge_df[col].replace('nan', np.nan).replace('NA', np.nan).replace('inf',
                                                                                                               np.nan).replace(
                                [np.inf, -np.inf], np.nan)
                            merge_df[col] = pd.to_numeric(merge_df[col], errors='coerce')
                            merge_df[col] = merge_df[col].astype('float').astype(df_types.loc[col, 'dtype_new'])
                        elif df_types.loc[col, 'dtype_new'] == 'float64':
                            merge_df[col] = merge_df[col].replace('nan', np.nan).replace('NA', np.nan).replace('inf',
                                                                                                               np.nan).replace(
                                [np.inf, -np.inf], np.nan)
                            merge_df[col] = pd.to_numeric(merge_df[col], errors='coerce')
                            merge_df[col] = merge_df[col].astype('float64')
                        else:
                            merge_df[col] = merge_df[col].astype(df_types.loc[col, 'dtype_new'])
                    except Exception as e:
                        if "non-finite" in str(e):
                            merge_df[col] = merge_df[col].replace('nan', np.nan).replace('NA', np.nan).replace('inf',
                                                                                                               np.nan).replace(
                                [np.inf, -np.inf], np.nan)
                            merge_df[col] = pd.to_numeric(merge_df[col], errors='coerce')
                            merge_df[col] = merge_df[col].fillna(0)
                            merge_df[col] = merge_df[col].astype(df_types.loc[col, 'dtype_new'])
                merge_df.to_parquet(out_fpath)
            print(f"{lib_id}-save month:{month} update finished.")

    def save_factor_data_bydate(self, df_data, date_col_name, out_path, lib_id, cover):
        df_data['month'] = df_data[date_col_name].astype(str).apply(lambda x: x[:6])
        for month, df_new in df_data.groupby('month'):
            out_path_m = os.path.join(out_path, month)
            os.makedirs(out_path_m, exist_ok=True)
            file_path = os.path.join(out_path_m, f"{lib_id}.parquet")
            df_new.rename(columns=self.API_INDEX_COL, inplace=True)
            df_new.drop(columns=['month'], axis=1, inplace=True, errors='ignore')
            if 'symbol' in df_new.columns:
                df_new = df_new[['symbol'] + [col for col in df_new.columns if col != 'symbol']]
            if 'datetime' in df_new.columns:
                df_new = df_new[['datetime'] + [col for col in df_new.columns if col != 'datetime']]
                df_new['datetime'] = df_new['datetime'].astype(str)
            if not os.path.exists(file_path):
                df_new.sort_values(by='datetime', inplace=True)
                df_new.to_parquet(file_path)
            else:
                df_his = pd.read_parquet(file_path, engine="pyarrow")
                df = self.merge_df_by_cover(old_df=df_his, new_df=df_new, cover=cover)
                df.to_parquet(file_path)
            print(f"{lib_id}-save month:{month} update finished.")

    def is_valid_date(self, check_date):
        try:
            if isinstance(check_date, int):
                check_date = str(check_date)
            assert len(check_date) == 8
            dt.datetime.strptime(check_date, '%Y%m%d')
            return True
        except Exception as e:
            print("日期-{0}的格式有误，请传入正确格式如'20200201'".format(check_date))
            return False

    def get_data(self, conf, meta_service: Optional[MetaFactorService] = None):
        """
        统一取数入口：
        1) 有 LIB_ID：通过元数据定位缓存，命中 parquet 读取（优先走缓存）。
        2) 无 LIB_ID 但有 API_TYPE：透传原有查询分支。
        """
        if conf.LIB_ID:
            return get(conf, meta_service=meta_service)

        if conf.API_TYPE:
            if conf.API_TYPE.lower() in ["wind", "productinfo"]:
                if tfd is None:
                    raise ImportError(f"thirdparty FactorData not available: {_THIRD_FD_ERR}")
                assert "library_name" in conf.API_KWARGS, "透传查询源数据，API_KWARGS需要有表名或库名library_name"
                df = tfd.get_factor_value(**conf.API_KWARGS)
                return df
            elif conf.API_TYPE.lower() == "zx":
                if fic is None:
                    raise ImportError(f"FicApiData not available: {_FIC_ERR}")
                assert "resource" in conf.API_KWARGS, "resource：资源名称，表名，conf.API_KWARGS必传"
                assert "paramMaps" in conf.API_KWARGS, "paramMaps：查询参数，dict，需根据表名确认可传参数，conf.API_KWARGS必传"
                df = fic.get_fic_api_data(**conf.API_KWARGS)['data']
                return df
            elif conf.API_TYPE.lower() == "indicator":
                if ida is None:
                    raise ImportError(f"IndicatorData not available: {_IDA_ERR}")
                condition_dct = {}
                for key, value in conf.API_KWARGS.items():
                    if key != "library_name":
                        condition_dct[key] = value
                df = ida.get_indicator_data(**condition_dct)
                return df
            elif conf.API_TYPE.lower() == "indicator_min":
                if ida is None:
                    raise ImportError(f"IndicatorData not available: {_IDA_ERR}")
                condition_dct = {}
                for key, value in conf.API_KWARGS.items():
                    if key != "library_name":
                        condition_dct[key] = value
                if "codes" in condition_dct:
                    df = ida.get_min_indicator_data(**condition_dct)
                else:
                    df = ida.get_min_indicator_data(stock_all=True, **condition_dct)
                return df
            elif conf.API_TYPE.lower() == "hive":
                assert "library_name" in conf.API_KWARGS, "透传查询源数据，API_KWARGS需要有表名或库名library_name"
                if not get_hive_data:
                    print("当前环境没有htds包，无法查询hives数据！！！")
                else:
                    df = get_hive_data(**conf.API_KWARGS)
                    return df
        return pd.DataFrame()


def _validate_date_str(date_str: str) -> str:
    if not date_str:
        raise ValueError("API_START/API_END 不能为空")
    if isinstance(date_str, int):
        date_str = str(date_str)
    if len(date_str) != 8:
        raise ValueError(f"日期格式需为YYYYMMDD，当前值：{date_str}")
    try:
        dt.datetime.strptime(date_str, "%Y%m%d")
    except Exception as exc:  # pragma: no cover - 统一抛出友好错误
        raise ValueError(f"日期格式需为YYYYMMDD，当前值：{date_str}") from exc
    return date_str


def _month_range(start_date: str, end_date: str) -> List[str]:
    start = dt.datetime.strptime(start_date, "%Y%m%d").date().replace(day=1)
    end = dt.datetime.strptime(end_date, "%Y%m%d").date().replace(day=1)
    if start > end:
        raise ValueError("API_START 不能大于 API_END")
    months: List[str] = []
    cursor = start
    while cursor <= end:
        months.append(cursor.strftime("%Y%m"))
        if cursor.month == 12:
            cursor = dt.date(cursor.year + 1, 1, 1)
        else:
            cursor = dt.date(cursor.year, cursor.month + 1, 1)
    return months


def _collect_file_paths(base_path: str, library_name: str, months: Iterable[str]) -> List[str]:
    file_path_list: List[str] = []
    for month in months:
        file_path = os.path.join(base_path, month, f"{library_name}.parquet")
        if os.path.exists(file_path):
            file_path_list.append(file_path)
        else:
            print(f"【WARNING】{library_name} 无 {month}月份的缓存数据")
    return file_path_list


def _read_parquet_with_filter(file_paths: List[str], start_date: str, end_date: str, query_cols: List[str]) -> pd.DataFrame:
    if not file_paths:
        return pd.DataFrame()
    lazy_frames = [pl.scan_parquet(path).with_columns(pl.col("datetime").cast(pl.Utf8).alias("datetime")) for path in
                   file_paths]
    combined_lazy = pl.concat(lazy_frames).filter(
        (pl.col("datetime") >= start_date) & (pl.col("datetime") <= end_date)
    )
    if query_cols:
        combined_lazy = combined_lazy.select(query_cols)
    df = combined_lazy.collect().to_pandas()
    return df


def _standardize_df(df: pd.DataFrame, required_cols: Optional[List[str]] = None) -> pd.DataFrame:
    if df.empty:
        return df
    if "__index_level_0__" in df.columns:
        df = df.drop("__index_level_0__", axis=1)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    if "symbol" in df.columns:
        df["symbol"] = df["symbol"].astype(str)
    if required_cols:
        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan
        df = df[[col for col in required_cols if col in df.columns] + [col for col in df.columns if col not in required_cols]]
    df = df.drop_duplicates(subset=[col for col in ["datetime", "symbol"] if col in df.columns]).sort_values(
        by=[col for col in ["datetime", "symbol"] if col in df.columns]
    )
    df.reset_index(drop=True, inplace=True)
    return df


def _to_panel(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    value_cols = [col for col in df.columns if col not in ["datetime", "symbol"]]
    if not value_cols:
        return df
    panel_df = df.pivot(index="datetime", columns="symbol")
    panel_df = panel_df.sort_index()
    return panel_df


def get(conf: DataManager, meta_service: Optional[MetaFactorService] = None) -> pd.DataFrame:
    """
    统一数据读取接口：
    1) 通过 LIB_ID 查元数据，定位 library_name/lib_type/freq
    2) 读取月度 parquet 缓存并按 datetime/symbol 标准化
    3) 按 LIB_ID_FEILD 裁剪字段（保留 datetime/symbol）
    """
    meta_service = meta_service or ExcelMetaFactorService()
    conf.API_START = _validate_date_str(conf.API_START)
    conf.API_END = _validate_date_str(conf.API_END)

    meta = meta_service.get_library_meta(conf.LIB_ID)
    conf.FREQ = conf.FREQ or getattr(meta, "freq", None)
    conf.ALIGN_POLICY = conf.ALIGN_POLICY or getattr(meta, "align_policy", None)
    library_name = meta.library_name
    lib_type = meta.lib_type
    base_path = getattr(meta, "base_path", None) or (
        conf.TABLE_BASE_PATH if lib_type == "table" else conf.FACTOR_BASE_PATH
    )

    months = _month_range(conf.API_START, conf.API_END)
    file_path_list = _collect_file_paths(base_path, library_name, months)
    if not file_path_list:
        raise FileNotFoundError(f"{library_name} 在 {base_path} 未找到可用缓存文件")

    lib_fields = list(conf.LIB_ID_FEILD) if conf.LIB_ID_FEILD else []
    if lib_fields:
        query_cols = ["datetime", "symbol"] + [i for i in lib_fields if i.lower() not in ["datetime", "symbol"]]
    else:
        query_cols = []

    df = _read_parquet_with_filter(file_path_list, conf.API_START, conf.API_END, query_cols)
    df = _standardize_df(df, required_cols=["datetime", "symbol"] + lib_fields)
    if str(conf.RETURN_FORMAT).lower() == "panel":
        df = _to_panel(df)
    return df


if __name__ == '__main__':
    # 场景一：查询缓存数据
    conf = DataManager(LIB_ID="ASHAREEODPRICES", API_START="19910101", API_END="19911205", LIB_TYPE="table")
    df = conf.get_data(conf)
    print(df)

    # 场景一：查询ZX缓存数据
    conf = DataManager(LIB_ID="ZX_STKDEPTTRADINFO", API_START="20251101", API_END="20251114", LIB_TYPE="table")
    df = conf.get_data(conf)
    print(df)

    # 场景一：查询productinfo缓存数据
    conf = DataManager(LIB_ID="ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY", API_START="20250619",
                       API_END="20250619", LIB_TYPE="table")
    df = conf.get_data(conf)
    print(df)
    # 查询indicator因子缓存数据
    conf = DataManager(LIB_ID="INDICATOR_PLATFORM_1", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
    df = conf.get_data(conf)
    print(df)

    # 查询indicator_min因子缓存数据
    conf = DataManager(LIB_ID="INDICATOR_PLATFORM_MINUTE_1", API_START="20251114", API_END="20251124", LIB_TYPE="factor")
    df = conf.get_data(conf)
    print(df)

    # 场景二：查询wind源表
    conf = DataManager(API_TYPE='wind',
                       API_KWARGS={"library_name": "WIND_ASHAREEODPRICES", "OPDATE": [f">=20020101", f"<=20031231"]})
    df = conf.get_data(conf)
    print(df)

    # 场景二：查询ZX源表
    conf = DataManager(API_TYPE='zx',
                       API_KWARGS={"resource": "ZX_STKDEPTTRADINFO", "paramMaps": {"LISTDATE": "20251113"},
                                   "rownum": 10000})
    df = conf.get_data(conf)
    print(df)

    # 场景二：查询productinfo源表
    conf = DataManager(API_TYPE='productinfo',
                       API_KWARGS={"library_name": "PRODUCTINFO_ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY",
                                   "ARCHIVEDATE": f"20250619"})
    df = conf.get_data(conf)
    print(df)

    # 查询indicator源数据
    conf = DataManager(API_TYPE="indicator",
                       API_KWARGS={"library_name": "index_platform", "start_date": "20251112", "end_date": "20251113"})
    df = conf.get_data(conf)
    print(df)

    # 分钟频测试
    conf = DataManager(API_TYPE='L3Factor', LIB_ID='Factormin',LIB_TYPE='factor',
                       API_START='20240101',
                       API_END='20240301',
                       API_INDEX_COL={'datetime': 'datetime', 'symbol': 'symbol'})
    df = conf.get_data(conf)
    print(df)
