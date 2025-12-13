import pandas as pd
import polars as pl
import numpy as np
import os
from pydantic import BaseModel
from xquant.thirdpartydata.factordata import FactorData as third_FD
from xquant.factordata.factor import FactorData
from xquant.thirdpartydata.fic_api_data import FicApiData
from xquant.setXquantEnv import xquantEnv
import datetime as dt
from collections import defaultdict
from AIQuant.data_api.index_platform_data import IndicatorData

try:
    from AIQuant.data_api.hive_data import get_hive_data
except:
    get_hive_data=None

fd = FactorData()
tfd = third_FD()
fic = FicApiData()
ida = IndicatorData()


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
    API_KWARGS: dict = {}  # API传入的运行参数, SDATE, EDATE预留关键字占位符
    LIB_TYPE: str = ""  # 区分是表还是因子库
    LIB_ID_FEILD: list = []  # DATA_ID下对应的列名（对表可以是列名，对因子库可以是因子名），默认为空取所有因子或列
    API_INDEX_COL: dict = {}  # 业务日期、标的列映射
    if xquantEnv == 0:
        TABLE_BASE_PATH: str = '/data/user/quanttest007/library_alpha/quant_data/SOURCE_TABLES'
        FACTOR_BASE_PATH: str = '/data/user/quanttest007/library_alpha/quant_data/daily_factor'
    else:
        TABLE_BASE_PATH: str = '/dfs/group/800657/library_alpha/quant_data/table/'  # /dfs/group/800657/library_alpha/quant_data/table/202511/ASHAREEODPRICES.parquet
        FACTOR_BASE_PATH: str = '/dfs/group/800657/library_alpha/quant_data/factor/daily_factor/'  # /dfs/group/800657/library_alpha/quant_data/factor/daily_factor/202511/Factor_xunfen1.parquet
    EXTRA_KWARGS: dict = {}  # 个性化的其他字段，如init_date, start_date
    LINK_IDS: list = ['013150', '022917', '011048', '016349']

    def split_date_by_month(self, statr_date, end_date):
        date_list = fd.tradingday(statr_date, end_date)
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

    def get_data(self, conf):
        # 1. 查询带缓存的数据，必传LIB_ID,API_START,API_END
        # TODO LIB_ID为表名，如ASHAREEODPRICES 区分大小写
        if conf.LIB_ID:
            assert self.is_valid_date(conf.API_START)
            assert self.is_valid_date(conf.API_END)
            month_dct = self.split_date_by_month(conf.API_START, conf.API_END)
            # TODO 1. 元数据查询LIB_ID是整表还是库因子
            assert conf.LIB_TYPE in ["table", "factor"], "LIB_TYPE只支持 table, factor"
            LIB_TYPE = conf.LIB_TYPE
            if LIB_TYPE == "table":
                base_path = conf.TABLE_BASE_PATH
            else:
                base_path = conf.FACTOR_BASE_PATH
            if conf.LIB_ID_FEILD:
                query_cols = ["datetime", "symbol"] + [i for i in conf.LIB_ID_FEILD if
                                                       i.lower() not in ["datetime", "symbol"]]
            else:
                query_cols = []
            file_path_list = []
            for month in month_dct:
                file_path = os.path.join(base_path, month, f"{conf.LIB_ID}.parquet")
                if os.path.exists(file_path):
                    file_path_list.append(file_path)
                else:
                    print(f"【WARNING】{conf.LIB_ID} 无 {month}月份的缓存数据")
            if file_path_list:
                lazy_dfs = [pl.scan_parquet(f) for f in file_path_list]
                if query_cols:
                    combined_lazy = pl.concat(lazy_dfs).filter(
                        (pl.col("datetime") >= conf.API_START) & (pl.col("datetime") <= conf.API_END)).select(
                        query_cols)
                else:
                    combined_lazy = pl.concat(lazy_dfs).filter(
                        (pl.col("datetime") >= conf.API_START) & (pl.col("datetime") <= conf.API_END))
                df = combined_lazy.collect()
                df = df.to_pandas()
                df = df.sort_values(by=["datetime", "symbol"])
                df.reset_index(drop=True, inplace=True)
                if "__index_level_0__" in df.columns:
                    df = df.drop("__index_level_0__", axis=1)
                return df
            else:
                return pd.DataFrame()
        elif conf.API_TYPE:
            if conf.API_TYPE.lower() in ["wind", "productinfo"]:
                assert "library_name" in conf.API_KWARGS, "透传查询源数据，API_KWARGS需要有表名或库名library_name"
                df = tfd.get_factor_value(**conf.API_KWARGS)
                return df
            elif conf.API_TYPE.lower() == "zx":
                assert "resource" in conf.API_KWARGS, "resource：资源名称，表名，conf.API_KWARGS必传"
                assert "paramMaps" in conf.API_KWARGS, "paramMaps：查询参数，dict，需根据表名确认可传参数，conf.API_KWARGS必传"
                df = fic.get_fic_api_data(**conf.API_KWARGS)['data']
                return df
            elif conf.API_TYPE.lower() == "indicator":
                condition_dct = {}
                for key, value in conf.API_KWARGS.items():
                    if key != "library_name":
                        condition_dct[key] = value
                df = ida.get_indicator_data(**condition_dct)
                return df
            elif conf.API_TYPE.lower() == "indicator_min":
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