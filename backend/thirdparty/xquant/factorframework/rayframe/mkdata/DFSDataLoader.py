# -*- coding:utf-8 -*-
import os
from .settings import *
from xquant.factordata import FactorData
fd = FactorData()
import pyarrow.parquet as pq
import polars as pl
import pandas as pd


def check_datetime(st,et):
    if not isinstance(st,str):
        raise Exception("start time 是不合法的")
        return

    if not isinstance(et, str):
        raise Exception("end time 是不合法的")
        return

    if len(st) != 8:
        raise Exception("start time 是不合法的")
    if len(et) != 8:
        raise Exception("end time 是不合法的")
    if et<st:
        raise Exception("end time 小于 start time")

    return

def load_data_from_dfs(data_type, table_name=None, start_date=None, end_date=None):
    """
    :param data_type:  数据类型，目前支持IndexWeight,BARRA,ZX......
    :param table_name: 表名
    :param date_column: 日期列，全表存储的可以不传(不传认为是全表存储的方式)
    :param start_date: 起止日期 日期列没传这个不生效
    :param end_date: 起止日期 日期列没传这个不生效
    :param stocks: 标的
    :return: 
    """
    if data_type.upper() == "ZX":
        table_name = table_name.upper()
        table_save_format = data_save_format["ZX_DATA"].get(table_name)
        if not table_save_format:
            raise Exception(f"【data_type】-{data_type}暂未缓存表：{table_name}的数据！")
        if table_save_format['save_type']=='Fully':
            file_path = os.path.join(base_dir_new, f"{table_name}.parquet")
            df_polars = pl.read_parquet(file_path)
            return df_polars
        elif table_save_format['save_type'] == 'Daily':
            dir_path = os.path.join(base_dir_new, f"{table_name}")
            date_list = fd.tradingday(start_date, end_date)
            real_st = date_list[0]
            real_et = date_list[-1]
            year_list = list(set([i[:4] for i in date_list]))
            date_column = table_save_format['date_column']
            df_polars_res_list = []
            for year in year_list:
                file_path  = os.path.join(dir_path,f"{year}.parquet")
                df_polars = pl.read_parquet(file_path)
                df_polars_filter = df_polars.filter((df_polars[date_column]>=real_st)&(df_polars[date_column]<=real_et))
                df_polars_res_list.append(df_polars_filter)
            df_polars_res = pl.concat(df_polars_res_list)
            return df_polars_res

    elif data_type.upper() == "BARRA":
        # TODO 待光卫缓存过BARRA的数据，可写为从绝对路径读取
        #  BARRA_TABLE 待替换为表名
        barra_base_dir = os.path.join(base_dir_new, "BARRA_TABLE")
        date_list = fd.tradingday(start_date, end_date)
        real_st = date_list[0]
        real_et = date_list[-1]
        year_list = list(set([i[:4] for i in date_list]))
        date_column = "datetime"
        df_polars_res_list = []
        for year in year_list:
            file_path = os.path.join(barra_base_dir, f"{year}.parquet")
            df_polars = pl.read_parquet(file_path)
            df_polars_filter = df_polars.filter(
                (df_polars[date_column] >= real_st) & (df_polars[date_column] <= real_et))
            df_polars_res_list.append(df_polars_filter)
        df_polars_res = pl.concat(df_polars_res_list)
        return df_polars_res

    elif data_type.upper() == "INDEX_WEIGHT":
        # TODO 这个看到数据存储路径及个时候修改
        type_base_dir = panel_index_weight_base_dir
        if table_name.endswith("SH") or table_name.endswith("SZ"):
            table_name = table_name[:-2]+"."+table_name[-2:]
        table_save_format = data_save_format["INDEX_WEIGHT"][table_name]
        dir_path = os.path.join(type_base_dir, f"{table_name}")
        date_list = fd.tradingday(start_date, end_date)
        real_st = date_list[0][:4]+"-"+date_list[0][4:6]+"-"+date_list[-1][6:]
        real_et = date_list[-1][:4]+"-"+date_list[-1][4:6]+"-"+date_list[-1][6:]
        year_list = list(set([i[:4] for i in date_list]))
        date_column = table_save_format['date_column']
        df_polars_res_list = []
        for year in year_list:
            file_path = os.path.join(dir_path, f"{year}.parquet")
            df_polars = pl.read_parquet(file_path)
            # df_polars[date_column] = df_polars[date_column].astype(str)
            df_polars = df_polars.with_columns(pl.col(date_column).cast(str))
            df_polars_filter = df_polars.filter(
                (df_polars[date_column] >= real_st) & (df_polars[date_column] <= real_et))
            df_polars_res_list.append(df_polars_filter)
        df_polars_res = pl.concat(df_polars_res_list)
        return df_polars_res

    else:
        raise Exception(f"目前数据类型仅包括ZX INDEX_WEIGHT BARRA_DATA ,不支持：{data_type.upper()}")

    return

def get_panel_min_data_dfs(start_time, end_time, indicators, security_type="STOCK"):
    res_dict = {}
    fd = FactorData()
    check_datetime(start_time, end_time)
    dt_list = fd.tradingday(start_time, end_time)
    month_list = sorted(list(set([i[:6] for i in dt_list])))
    for ind in indicators:
        df_ind_list = []
        for month in month_list:
            src_file = os.path.join(panel_min_base_dir, security_type, ind.split(".")[1], "{}.parquet".format(month))
            df_ind_month = pl.read_parquet(src_file)
            if month == dt_list[0][:6]:
                # 过滤条件，选择指定日期范围内的记录
                df_ind_month = df_ind_month.filter(df_ind_month['MDDate'] >= dt_list[0])
            elif month == dt_list[-1][:6]:
                df_ind_month = df_ind_month.filter(df_ind_month['MDDate'] <= dt_list[-1])
            df_ind_list.append(df_ind_month)
        res_dict[ind] = pl.concat(df_ind_list)

    return res_dict

def get_ori_min_data_dfs(start_time, end_time,stocks=None, indicators=None,security_type="STOCK"):
    df_ind_month_per_ind_list = []
    fd = FactorData()
    check_datetime(start_time, end_time)
    dt_list = fd.tradingday(start_time, end_time)
    month_list = sorted(list(set([i[:6] for i in dt_list])))
    for month in month_list:
        src_file = os.path.join(ori_min_base_dir, security_type, "{}.parquet".format(month))
        if indicators:
            assert isinstance(indicators,list), "indicators必须是字符串"
            indicators = ['HTSCSecurityID','MDDate','MDTime']+[i for i in indicators if i not in ['HTSCSecurityID','MDDate','MDTime']]
        if os.path.exists(src_file):
            df_ind_month = pl.read_parquet(src_file,columns=indicators)
        else:
            continue
        if month == dt_list[0][:6]:
            # 过滤条件，选择指定日期范围内的记录
            df_ind_month = df_ind_month.filter(df_ind_month['MDDate'] >= dt_list[0])
        elif month == dt_list[-1][:6]:
            df_ind_month = df_ind_month.filter(df_ind_month['MDDate'] <= dt_list[-1])

        if stocks:
            df_ind_month = df_ind_month.filter(pl.col('HTSCSecurityID').is_in(stocks))
        df_ind_month_per_ind_list.append(df_ind_month)
    if df_ind_month_per_ind_list:
        res_df_polars = pl.concat(df_ind_month_per_ind_list)
        return res_df_polars
    else:
        return pl.DataFrame()


def load_l3_minute_data(securities_list, date_list, factor_list=[]):
    per_month_dates = {}
    for i in date_list:
        if i[:6] not in per_month_dates:
            per_month_dates[i[:6]] = [i]
        else:
            per_month_dates[i[:6]].append(i)

    data_path_list = []
    for month, month_dates in per_month_dates.items():
        data_path = os.path.join(l3_minute_data_dir, f"{month}.parquet")
        if os.path.exists(data_path):
            data_path_list.append(data_path)
    if data_path_list:
        # 大文件/多文件，先过滤后加载，减少 I/O 和内存占用
        # 1. 延迟扫描所有文件（不加载数据）
        lazy_dfs = [pl.scan_parquet(f) for f in data_path_list]
        # 2. 合并延迟DataFrame + 添加过滤条件
        combined_lazy = pl.concat(lazy_dfs).filter((pl.col("HTSCSecurityID").is_in(securities_list))&(pl.col("MDDate").is_in(date_list)))
        if factor_list:
            combined_lazy = combined_lazy.select(["MDDate", "MDTime", "HTSCSecurityID"]+factor_list)
        # 3. 执行计算（实际加载并过滤数据）
        df = combined_lazy.collect()
        df = df.to_pandas()
        return df
    else:
        return None


def get_daily_data_from_dfs(quarterlag_dt_list, start_date, end_date, securities_list, non_hf_depend_factors):
    depend_factor_dict = {}
    s = FactorData()
    date_list = s.tradingday(start_date, end_date)
    for depend_factor_describe in non_hf_depend_factors:
        if len(depend_factor_describe.split('.')) != 2:
            raise Exception("请按照 因子类型（因子库名）.因子名 的方式书写依赖因子！")
        depend_factor_type, depend_factor_name = depend_factor_describe.split('.')
        if depend_factor_type not in depend_factor_dict:
            depend_factor_dict[depend_factor_type] = [depend_factor_name]
        else:
            depend_factor_dict[depend_factor_type].append(depend_factor_name)

    res_dict = {}
    # 从xquant接口或者 nas上加载 低频依赖数据，注意获取之后统一依赖数据的mddate
    for depend_type, depend_factor_list in depend_factor_dict.items():
        if depend_type in ['BasicDayFactor', 'BasicFinancialFactor']:
            if depend_type == 'BasicDayFactor':
                temp_data = s.get_factor_value("Basic_factor", securities_list, date_list, depend_factor_list,
                                               fill_na=True)
            else:
                temp_data = s.get_factor_value("Basic_factor", securities_list, quarterlag_dt_list, depend_factor_list,
                                               fill_na=True)
            temp_data.index.names = ['datetime', 'symbol']
            for depend_factor_name in depend_factor_list:
                temp_data_u = temp_data[depend_factor_name].unstack()
                temp_data_u = temp_data_u.reindex(columns=securities_list)
                res_dict[depend_type + "." + depend_factor_name] = temp_data_u

        if depend_type == 'IndexWeight':
            # TODO 加载指数权重数据
            for depend_index_name in depend_factor_list:
                df_polars = load_data_from_dfs(data_type="INDEX_WEIGHT",table_name=depend_index_name,
                                               start_date=date_list[0],end_date=date_list[-1])
                res_dict[depend_type + "." + depend_index_name] = df_polars.to_pandas()
        if depend_type.upper() == 'ZX':
            # TODO 加载第三方整表数据
            for depend_table_name in depend_factor_list:
                df_polars = load_data_from_dfs(data_type='ZX',table_name=depend_table_name,start_date=date_list[0],end_date=date_list[-1])
                res_dict[depend_type + "." + depend_table_name] = df_polars.to_pandas()

        if depend_type.upper() == "L3_MINUTE_DATA":
            factor_map = {"OpenPx".upper(): "OpenPx", "ClosePx".upper():"ClosePx",
                          "HighPx".upper(): "HighPx", "LowPx".upper(): "LowPx",
                          "NumTrades".upper(): "NumTrades", "TotalVolumeTrade".upper(): "TotalVolumeTrade",
                          "TotalValueTrade".upper(): "TotalValueTrade"}
            depend_factor_list_e = []
            for i in depend_factor_list:
                if i.upper() not in factor_map:
                    print(f"Warning：暂无{i}的L3分钟因子数据, 可查询的因子有{','.join(list(factor_map.keys()))}")
                    res_dict[depend_type + "." + i] = pd.DataFrame(columns=["MDDate", "MDTime"])
                else:
                    depend_factor_list_e.append(factor_map[i.upper()])

            df_all = load_l3_minute_data(securities_list=securities_list,
                                         date_list=date_list, factor_list=depend_factor_list_e)
            for depend_factor_name in depend_factor_list_e:
                if df_all is not None:
                    df_p = df_all[["MDDate", "MDTime", "HTSCSecurityID", factor_map[depend_factor_name.upper()]]]
                    df_fac = df_p.pivot(
                                        index=['MDDate', 'MDTime'],  # 索引列
                                        columns='HTSCSecurityID',  # 作为新列名的列
                                        values=factor_map[depend_factor_name.upper()]  # 填充到新列中的值
                                         )
                    df_fac = df_fac.reindex(columns=securities_list)
                    res_dict[depend_type + "." + depend_factor_name] = df_fac
                else:
                    res_dict[depend_type + "." + depend_factor_name] = pd.DataFrame(columns=["MDDate", "MDTime"])

        if depend_type == 'BARRA':
            # TODO 加载barra数据
            # TODO  STOCK_NAME字段名未知
            df_polars = load_data_from_dfs(data_type='BARRA',start_date=date_list[0],end_date=date_list[-1])
            df_polars = df_polars[["datetime","symbol","STOCK_NAME"]+depend_factor_list]
            for depend_index_name in depend_factor_list:
                res_dict[depend_type + "." + depend_index_name] = df_polars.to_pandas()
    return res_dict
