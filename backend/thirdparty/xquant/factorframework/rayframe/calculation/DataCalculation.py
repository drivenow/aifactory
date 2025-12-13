# -*- coding:utf-8 -*-
import ray
import pandas as pd
import numpy as np
import traceback
import time
from collections import defaultdict
from xquant.factorframework.rayframe.util.util import get_fac_class, check_date, check_return_and_lib, \
    check_factor_list, check_security_list, get_fac_task_cls_list
from xquant.factorframework.rayframe.util.data_context import get_trade_days, get_stocks_pool, get_before_trade_day, get_before_report_day
from xquant.factorframework.rayframe.mkdata.DataCollector import collect_market_data, EmptyException,collect_market_data_dfs
from xquant.factorframework.rayframe.mkdata.helper import sample_data_aux, \
    precross_data_from_tquant, sample_transaction_data, sample_orderbook
from xquant.factorframework.rayframe.calculation.helper import set_ray_options
from xquant.factorframework.rayframe.external_actor_server import *
from xquant.factorframework.rayframe.mkdata.DFSDataLoader import get_panel_min_data_dfs, get_daily_data_from_dfs,get_ori_min_data_dfs
from xquant.factorframework.rayframe.util.util import check_date, check_lag_date, check_security_type, check_factor_type, \
       check_factor_name, get_factor_module, check_run_end_df, get_fac_class
from xquant.factorframework.rayframe.mkdata.settings import *
from xquant.xqutils.helper import multicore_init
from xquant.xqutils.utils import statisticLog
from itertools import chain
import gc



@ray.remote
def run_day_factor_value(fac_cls, start_date, end_date, factor_path, depend_factors_df, depend_price_df):
    """
    :params : fac_cls : 因子类
    : return : DataFrame
    """
    fac = fac_cls()
    # 校验factor_name
    check_factor_name(fac.factor_name)
    # 校验因子名和因子类名和因子文件名的一致性
    if not fac.__class__.__name__ == fac.factor_name:
        raise Exception("因子类名:{0}与因子名:{1} 不完全一致".format(fac.__class__.__name__, fac.factor_name))
    get_factor_module(fac.factor_name, factor_path)
    # 校验factor_type
    check_factor_type(fac.factor_type)
    # 校验security_type
    check_security_type(fac.security_type)
    # 校验依赖声明：允许 depend_factor 或 aiquant_requirements（二者至少一个）
    aiquant_reqs = getattr(fac, "aiquant_requirements", {}) or {}
    if len(fac.depend_factor) == 0 and fac.factor_type == "DAY" and not aiquant_reqs:
        raise Exception("低频因子的开发必须传入所依赖的因子或 aiquant_requirements")
    # 校验数据播放窗口
    check_lag_date(fac.day_lag, fac.quarter_lag)
    tradingdays = get_trade_days(start_date, end_date)
    if not tradingdays:
        raise Exception("在日期{0}~{1}之间没有交易日".format(start_date, end_date))

    start_date = tradingdays[0]
    end_date = tradingdays[-1]
    res_df_list = list()
    error_code_list = []
    all_depend_start_date = get_before_trade_day(start_date, fac.day_lag + fac.reform_window - 1)
    all_depend_tradingdays = get_trade_days(all_depend_start_date, end_date)

    reform_start_date = get_before_trade_day(start_date, fac.reform_window - 1)
    reform_tradingdays = get_trade_days(reform_start_date, end_date)
    # 前置计算函数
    fac.onRunDaysStart(start_date=all_depend_start_date, end_date=end_date)
    securities_list = get_stocks_pool(day=end_date, security_type=fac.security_type,
                                      securities=fac.security_pool)
    # 预加载 AIQuant 声明的输入数据，calc 内部可按 dt_to 切片
    try:
        fac.preload_aiquant_inputs(stocks=securities_list, start_date=all_depend_start_date, end_date=end_date)
    except Exception as e:
        print(f"[WARNING] preload_aiquant_inputs failed: {e}")
    # quarterlag_dt_list = get_before_report_day(reform_start_date, fac.quarter_lag, end_date=end_date)
    # factor_data_ori = fac.add_dfs_lf_data(stock_list=securities_list, start_date=all_depend_start_date,
    #                                       end_date=end_date, report_date_list=quarterlag_dt_list)
    min_indicators = [i for i in fac.depend_factor if i.split(".")[0] == 'PanelMinData']
    for tradingday in reform_tradingdays:
        trade_date_list = all_depend_tradingdays[
                          all_depend_tradingdays.index(tradingday) - fac.day_lag:all_depend_tradingdays.index(
                              tradingday) + 1]
        report_date_list = get_before_report_day(tradingday, fac.quarter_lag)
        factor_data = {}
        price_data = {}
        for factor_describe in depend_factors_df.keys():
            factor_type, table_name = factor_describe.split(".")
            if factor_type == "BasicFinancialFactor":
                factor_data[factor_describe] = depend_factors_df[factor_describe][
                    depend_factors_df[factor_describe].index.get_level_values(
                        0).isin(report_date_list)]
            elif factor_type == "BasicDayFactor":
                factor_data[factor_describe] = depend_factors_df[factor_describe][
                    depend_factors_df[factor_describe].index.get_level_values(
                        0).isin(trade_date_list)]
            elif factor_type.upper() == "ZX":
                table_name = factor_describe.split(".")[1].upper()
                table_save_format = data_save_format["ZX_DATA"][table_name]
                if table_save_format['save_type'] == 'Fully':
                    factor_data[factor_describe] = depend_factors_df[factor_describe]
                elif table_save_format['save_type'] == 'Daily':
                    date_column = table_save_format['date_column']
                    factor_data[factor_describe] = depend_factors_df[factor_describe][
                        depend_factors_df[factor_describe][date_column].isin(trade_date_list)]
            elif factor_type.upper() == "L3_MINUTE_DATA":
                factor_data[factor_describe] = depend_factors_df[factor_describe].query("MDDate in @trade_date_list")

            elif factor_type == "BARRA":
                date_column = "MDDATE"
                factor_data[factor_describe] = depend_factors_df[factor_describe][
                    depend_factors_df[factor_describe][date_column].isin(trade_date_list)]
            elif factor_type == "IndexWeight":
                if table_name.endswith("SH") or table_name.endswith("SZ"):
                    table_name = table_name[:-2] + "." + table_name[-2:]
                table_save_format = data_save_format["INDEX_WEIGHT"][table_name]
                date_column = table_save_format['date_column']
                factor_data[factor_describe] = depend_factors_df[factor_describe][
                    depend_factors_df[factor_describe][date_column].isin(trade_date_list)]
            else:
                raise Exception("目前低频依赖数据的类型仅支持 WIND BARRA MSCI IndexWeight BasicDayFactor BasicFinancialFactor")

        # 加载分钟行情数据
        for ind in min_indicators:
            price_data[ind] = depend_price_df[ind][depend_price_df[ind]['MDDate'] == tradingday]

        # 调用因子计算函数，注意如果函数计算过程有异常，抛出返回到结果当中
        try:
            df_series = fac.calc(factor_data=factor_data, price_data=price_data, dt_to=tradingday)
            # 　判断低频因子calc（）方法返回的数据格式是否正确
            if not isinstance(df_series, pd.Series):
                raise Exception("【calc方法返回值错误】低频因子的calc方法需要返回pd.Series格式的数据！目前是：{}".format(type(df_series)))
            if df_series.index[0][-2:] not in ["SZ", "SH"]:
                raise Exception("【calc方法返回值错误】低频因子的calc方法返回的pd.Series的索引必须是标的名！目前是：{}".format(df_series.index[0][-2:]))
            df = pd.DataFrame()
            df[tradingday] = df_series.reindex(securities_list)
            df = df.T
            res_df_list.append(df)
        except Exception as e:
            traceback.print_exc()
            error_code_list.append([tradingday, fac_cls.__name__, e])

    # 统计因子计算结果 转成panel形式
    if len(res_df_list) > 0:
        res_df = pd.concat(res_df_list)
        res_df = fac.onRunDaysEnd(res_df)
        check_run_end_df(factor_data=res_df, start_date=reform_tradingdays[0], end_date=reform_tradingdays[-1])
        res_df = res_df.loc[tradingdays, :]
    else:
        res_df = pd.DataFrame()
    # 统计计算错误的结果转成dataframe的形式
    if len(error_code_list) > 0:
        error_df = pd.DataFrame(error_code_list, columns=['MDDate', 'FactorName', 'Reason'])
    else:
        error_df = pd.DataFrame(columns=['MDDate', 'FactorName', 'Reason'])
    # 新增adjust后置函数，校验格式

    return res_df, error_df

@ray.remote
def run_factor_month(fac, month_list, factor_path, factor_data_id, price_data_id):
    res_dict = {}
    tasks = [run_day_factor_value.remote(fac, st, et, factor_path, factor_data_id, price_data_id) for st, et in month_list]
    results = ray.get(tasks)
    for i in range(len(month_list)):
        month = month_list[i][0][:6]
        res_dict[month] = results[i]
    return res_dict


def run_factors_days(factor_list=[], factor_path="", start_date="", end_date="", num_cpus=None,
                     object_store_memory=None, options=None, parallel_dim="factor"):
    """
    :param factor_list: list，需要计算的因子列表，每个元素代表一个因子，可以是srt或者因子类
    :param start_date: str， 计算开始时间，如20190701.
    :param end_date: str，计算结束时间，如20190701.
    :param num_cpus: int，通过Ray并行计算的进程数， 如1。
    :param object_store_memory: int，通过Ray并行计算的共享内存大小，如1e9,单位B
    :param factor_path: 默认值为’./’，factor_path表示因子类文件的存储路径（绝对路径与相对路径均可），用于递归搜索并加载因子类。若factor_list中传的因子名为str，会从factor_path下搜索。
    :param verbose: int 默认为0。大于0时显示详细的错误信息
    :return:
    """
    # 校验日期
    check_date(start_date, end_date)
    # 校验因子数据
    check_factor_list(factor_list, factor_freq="DAY")
    # 初始化ray
    assert multicore_init() == True
    set_ray_options(num_cpus=num_cpus, object_store_memory=object_store_memory, options=options)

    # 将因子列表统一为因子任务类
    fac_cls_list = []
    for fac_cls in factor_list:
        if type(fac_cls) == str:
            fac_cls = get_fac_class(fac_cls, factor_path)
        fac_cls_list.append(fac_cls)

    # 日期列表返回可能为空，为空时影响接下来的计算
    calc_tradingdays = get_trade_days(start_date, end_date)
    if not calc_tradingdays:
        raise Exception("在日期{0}~{1}之间没有交易日".format(start_date, end_date))  # 映射因子与标的的关系

    # 获取所有因子的lag中的最大值
    max_day_lag = max([fac.day_lag for fac in fac_cls_list])
    max_reform_window = max([fac.reform_window for fac in fac_cls_list])
    max_quarter_lag = max([fac.quarter_lag for fac in fac_cls_list])

    # 获取所有因子的depend_factors 并且去重
    depend_factors_all = [fac.depend_factor for fac in fac_cls_list]
    flattened_set = set(chain(*depend_factors_all))
    depend_factors_all = list(flattened_set)

    # 获取所有因子的最大股票池
    max_securities_list = []
    all_security_pool = [fac.security_pool for fac in fac_cls_list]
    for pool in all_security_pool:
        if isinstance(pool, str):
            pool = get_stocks_pool(day=end_date, security_type='stock', securities=pool)
        max_securities_list.append(pool)
    flattened_set = set(chain(*max_securities_list))
    max_securities_list = list(flattened_set)

    # 将需要计算的日期列表转化成月份列表
    month_bounds = {}
    # 遍历日期列表，更新字典
    for date_str in calc_tradingdays:
        year_month = date_str[:6]
        if year_month not in month_bounds:
            # 第一次出现的日期即为起始日期
            month_bounds[year_month] = [date_str, date_str]
        else:
            # 否则，更新结束日期
            month_bounds[year_month][1] = date_str
    month_list = list(month_bounds.values())

    # 区分需要加载的分钟数据和低频因子数据
    non_min_indicators = [i for i in depend_factors_all if i.split(".")[0] != 'PanelMinData']
    min_indicators = [i for i in depend_factors_all if i.split(".")[0] == 'PanelMinData']
    # 按月串行，按因子并行 ，每个月的数据只加载一次
    factor_res_dict = defaultdict(dict)
    # 记录失败的结果
    error_res_df_list = []

    # 低频
    lf_depend_start_date = get_before_trade_day(start_date, max_day_lag + max_reform_window - 1)

    # 分别加载需要的分钟数据和低频因子数据
    # 分钟数据
    price_data = {}
    if len(min_indicators) > 0:
        stock_price_data_ori = get_panel_min_data_dfs(lf_depend_start_date, end_date, indicators=min_indicators,
                                                      security_type="STOCK")
        for ind in min_indicators:
            price_data[ind] = stock_price_data_ori[ind].to_pandas()
    price_data_id = ray.put(price_data)
    # 低频数据
    factor_data = {}
    if len(non_min_indicators) > 0:
        report_date_list = get_before_report_day(lf_depend_start_date, max_quarter_lag)
        factor_data = get_daily_data_from_dfs(report_date_list, lf_depend_start_date, end_date, max_securities_list,
                                              non_min_indicators)
    factor_data_id = ray.put(factor_data)

    if parallel_dim == "factor":
        # 按因子并行计算
        for st, et in month_list:
            tasks = [run_day_factor_value.remote(fac_cls, st, et, factor_path, factor_data_id, price_data_id) for fac_cls in
                     fac_cls_list]
            factors_month_res_list = ray.get(tasks)
            # 汇总因子计算结果
            if len(month_list) == 1 and st == et:
                for i in range(len(factors_month_res_list)):
                    factor_name = fac_cls_list[i].__name__
                    factor_res_dict[st][factor_name] = factors_month_res_list[i][0]
                    # 汇总因子计算错误表
                    error_res_df_list.append(factors_month_res_list[i][1])
            else:
                for i in range(len(factors_month_res_list)):
                    factor_name = fac_cls_list[i].__name__
                    factor_res_dict[st[:6]][factor_name] = factors_month_res_list[i][0]
                    # 汇总因子计算错误表
                    error_res_df_list.append(factors_month_res_list[i][1])
    elif parallel_dim == "month":
        # 按月并行
        for fac_cls in fac_cls_list:
            tasks = [run_day_factor_value.remote(fac_cls, st, et, factor_path, factor_data_id, price_data_id) for st, et in
                     month_list]
            factors_month_res_list = ray.get(tasks)
            for i in range(len(factors_month_res_list)):
                factor_name = fac_cls.__name__
                month = month_list[i][0][:6]
                factor_res_dict[month][factor_name] = factors_month_res_list[i][0]
                # 汇总因子计算错误表
                error_res_df_list.append(factors_month_res_list[i][1])

        # tasks = defaultdict(list)
        # for fac_cls in fac_cls_list:
        #     factor_name = fac_cls.__name__
        #     for st, et in month_list:
        #         task = run_day_factor_value.remote(fac_cls, st, et, factor_path, factor_data_id, price_data_id)
        #         tasks[factor_name].append(task)
        #
        # for task_id in tasks:
        #     if not tasks[task_id]:
        #         continue
        #     # 结果为dict，key为月份，值为(df, df_error)
        #     factors_month_res_list = ray.get(tasks[task_id])
        #     for i in range(len(factors_month_res_list)):
        #         month = month_list[i][0][:6]
        #         factor_res_dict[month][task_id] = factors_month_res_list[i][0]
        #         error_res_df_list.append(factors_month_res_list[i][1])
    # elif parallel_dim == "all":
    #     # 按因子、月并行计算
    #     tasks = [run_factor_month.remote(fac_cls, month_list, factor_path, factor_data_id, price_data_id) for fac_cls in
    #                     fac_cls_list]
    #     factors_month_res_list = ray.get(tasks)
    #     for i in range(len(factors_month_res_list)):
    #         factor_name = fac_cls_list[i].__name__
    #         # dict类型
    #         month_data_dct = factors_month_res_list[i]
    #         for month in month_data_dct:
    #             factor_res_dict[month][factor_name] = month_data_dct[month][0]
    #             error_res_df_list.append(month_data_dct[month][1])
    else:
        raise Exception("parallel_dim-并行维度默认按因子并行(factor)，可选按照月份并行(month)")

    return factor_res_dict, error_res_df_list



if __name__ == '__main__':
    # "pxchange","roll_measure_autocorr", "weighted_buysell_px_spread_delta"
    factor_list = [
        "pxchange"]  # ["pxchange", "roll_measure_autocorr", "TotalBuySellOrderQtyMinus", "order_dispersion", "cor_px_vol",
    # "px_vol_corr_slope", "px_to_high_premium_discount",
    # "sell_buy_qty_spread", "rsi", "roc"]
    res = run_securities_days(factor_list, '20180119', '20200904', num_cpus=1,
                              data_input_mode=["TICK_SAMPLE"],
                              security_list=["159915.SZ"],
                              security_type="fund", library_name='xx_high11',
                              return_mode='show', factor_path='../factors/',
                              options={"local_mode": False})

    print(res['159915.SZ'])
