import pandas as pd
import numpy as np
import time
import traceback
from xquant.factorframework.rayframe.util.data_context import get_trade_days, get_stocks_pool, get_before_trade_day, \
    get_before_report_day, get_before_trade_days
from xquant.factorframework.rayframe.util.util import check_date, check_lag_date, check_security_type, check_factor_type, \
    check_factor_name, get_factor_attr, check_security_list, check_data_input_mode_consist, check_factor_sample_consist, \
    get_factor_module, check_run_end_df, get_fac_task_cls_list, get_fac_class
from xquant.factorframework.rayframe.mkdata.DataCollector import collect_market_data, EmptyException,collect_market_data_dfs
from xquant.factorframework.rayframe.mkdata.helper import sample_data_aux, \
    precross_data_from_tquant, sample_transaction_data, sample_orderbook
from xquant.xqutils.utils import statisticLog
from xquant.factorframework.rayframe.mkdata.settings import *
from xquant.factorframework.rayframe.external_actor_server import create_cache_actor


#  低频因子的调试方法
def run_day_factor_value(fac_cls, start_date, end_date, factor_path):
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
    # 日期校验
    check_date(start_date, end_date)

    # 校验depend_factor
    if len(fac.depend_factor) == 0 and fac.factor_type == "DAY":
        raise Exception("低频因子的开发必须传入所依赖的因子")
    # 校验数据播放窗口
    check_lag_date(fac.day_lag, fac.quarter_lag)
    tradingdays = get_trade_days(start_date, end_date)
    if not tradingdays:
        raise Exception("在日期{0}~{1}之间没有交易日".format(start_date, end_date))

    start_date = tradingdays[0]
    end_date = tradingdays[-1]
    res_df_list = list()

    all_depend_start_date = get_before_trade_day(start_date, fac.day_lag + fac.reform_window - 1)
    all_depend_tradingdays = get_trade_days(all_depend_start_date, end_date)

    reform_start_date = get_before_trade_day(start_date, fac.reform_window - 1)
    reform_tradingdays = get_trade_days(reform_start_date, end_date)
    # 前置计算函数
    fac.onRunDaysStart(start_date=all_depend_start_date, end_date=end_date)
    securities_list = get_stocks_pool(day=end_date, security_type=fac.security_type,
                                      securities=fac.security_pool)
    quarterlag_dt_list = get_before_report_day(reform_start_date, fac.quarter_lag, end_date=end_date)
    # factor_data_ori = fac.get_factor_data(quarterlag_dt_list=quarterlag_dt_list,
    #                                       start_date=all_depend_start_date,
    #                                       end_date=end_date,
    #                                       securities_list=securities_list)
    factor_data_ori = fac.add_dfs_lf_data(stock_list=securities_list, start_date=all_depend_start_date, end_date=end_date, report_date_list=quarterlag_dt_list)
    min_indicators = [i for i in fac.depend_factor if i.split(".")[0]=='PanelMinData']
    if len(min_indicators)==0:
        stock_price_data_ori = dict()
    else:
        stock_price_data_ori = fac.add_panel_min_data(reform_tradingdays[0],reform_tradingdays[-1], indicators=min_indicators, security_type="STOCK")

    for tradingday in reform_tradingdays:

        # factor_data: dict key:因子名 values: DataFrame
        factor_data = {}
        # price_data: dict key：指标 values ：DataFrame
        price_data = {}
        trade_date_list = all_depend_tradingdays[
                          all_depend_tradingdays.index(tradingday) - fac.day_lag:all_depend_tradingdays.index(
                              tradingday) + 1]
        # trade_date_list = get_before_trade_days(tradingday, fac.day_lag) if fac.day_lag else [tradingday]
        report_date_list = get_before_report_day(tradingday, fac.quarter_lag)

        for factor_describe in factor_data_ori.keys():
            factor_type = factor_describe.split(".")[0]
            if factor_type == "BasicFinancialFactor":
                factor_data[factor_describe] = factor_data_ori[factor_describe][
                    factor_data_ori[factor_describe].index.get_level_values(
                        0).isin(report_date_list)]
            elif factor_type == "BasicDayFactor":
                factor_data[factor_describe] = factor_data_ori[factor_describe][
                    factor_data_ori[factor_describe].index.get_level_values(
                        0).isin(trade_date_list)]
            elif factor_type.upper() == "ZX":
                table_name = factor_describe.split(".")[1].upper()
                table_save_format = data_save_format["ZX_DATA"][table_name]
                if table_save_format['save_type'] == 'Fully':
                    factor_data[factor_describe] = factor_data_ori[factor_describe]
                elif table_save_format['save_type'] == 'Daily':
                    date_column = table_save_format['date_column']
                    factor_data[factor_describe] = factor_data_ori[factor_describe][
                                                    factor_data_ori[factor_describe][date_column].isin(trade_date_list)]
            elif factor_type.upper() == "L3_MINUTE_DATA":
                factor_data[factor_describe] = factor_data_ori[factor_describe].query("MDDate in @trade_date_list")
            elif factor_type == "BARRA":
                date_column = "MDDATE"
                factor_data[factor_describe] = factor_data_ori[factor_describe][
                            factor_data_ori[factor_describe][date_column].isin(trade_date_list)]
            elif factor_type == "IndexWeight":
                table_name = factor_describe.split(".")[1]
                if table_name.endswith("SH") or table_name.endswith("SZ"):
                    table_name = table_name[:-2] + "." + table_name[-2:]
                table_save_format = data_save_format["INDEX_WEIGHT"][table_name]
                date_column = table_save_format['date_column']
                factor_data[factor_describe] = factor_data_ori[factor_describe][
                        factor_data_ori[factor_describe][date_column].isin(trade_date_list)]
            else:
                raise Exception("目前低频依赖数据的类型仅支持 ZX BARRA IndexWeight BasicDayFactor BasicFinancialFactor")

# 加载分钟行情数据
        for ind in min_indicators:
            price_data[ind] = stock_price_data_ori[ind].filter((stock_price_data_ori[ind]['MDDate']==tradingday)).to_pandas()

        if int(fac.calc.__code__.co_argcount) == 4:
            df_series = fac.calc(factor_data=factor_data, price_data=price_data, dt_to=tradingday)
        else:
            df_series = fac.calc(factor_data=factor_data, price_data=price_data)

        # 　判断低频因子calc（）方法返回的数据格式是否正确
        if not isinstance(df_series, pd.Series):
            raise Exception("【calc方法返回值错误】低频因子的calc方法需要返回pd.Series格式的数据！目前是：{}".format(type(df_series)))
        if df_series.index[0][-2:] not in ["SZ", "SH"]:
            raise Exception("【calc方法返回值错误】低频因子的calc方法返回的pd.Series的索引必须是标的名！目前是：{}".format(df_series.index[0][-2:]))
        df = pd.DataFrame()
        df[tradingday] = df_series.reindex(securities_list)
        df = df.T
        res_df_list.append(df)
    res_df = pd.concat(res_df_list)

    # 新增adjust后置函数，校验格式
    res_df = fac.onRunDaysEnd(res_df)
    check_run_end_df(factor_data=res_df, start_date=reform_tradingdays[0], end_date=reform_tradingdays[-1])
    res_df = res_df.loc[tradingdays, :]
    return res_df


def concat_factor_in_a_day(res_df_list, factor_type, security_id, date):
    """
    将因子计算结果合并
    :param res_df_list:
    :param factor_type:
    :param security_id:
    :param date:
    :return: 返回符合存储要求的因子DataFrame
    """
    if res_df_list:
        if not factor_type == "DAY":
            res = pd.concat(res_df_list, axis=1)
            res.index.name = 'MDTime'
            res = res.reset_index()
            res['MDDate'] = date
        else:
            # 一天每个因子一个因子值
            # res = pd.concat(res_df_list, axis=1).to_frame()
            res = pd.concat(res_df_list)
            res["MDDate"] = date
            res["HTSCSecurityID"] = security_id
    else:
        res = pd.DataFrame()

    return res

@statisticLog("rayframe", "FactorDebug")
def run_hfre_factor_value(fac_cls, start_date, end_date, security_pool, factor_path, verbose = 0, data_source="hdfs"):
    """
    : params : fac_cls : 因子类
    : return : DataFrame
    """
    create_cache_actor(local_mode=True, global_start_date = start_date, global_end_date = end_date)
    fac = fac_cls()

    # 日期校验
    check_date(start_date, end_date)

    # 加入判断条件（时间是否按照要求进行输入）
    tradingdays = get_trade_days(start_date, end_date)
    if not tradingdays:
        raise Exception("在日期{0}~{1}之间没有交易日".format(start_date, end_date))
    securities_list = get_stocks_pool(day=start_date, security_type=fac.security_type,
                                      securities=security_pool)
    # 校验security_list,list 每个元素为（str,list,tuple）中的一个，且必须保持一致
    check_security_list(securities_list)

    # ---------------
    fac_task_cls_list = get_fac_task_cls_list([fac_cls], factor_path)
    first_order_factor_list = []
    second_order_factor_list = []
    first_order_factor_name_list = []
    for fac_task in fac_task_cls_list:
        # 先简单假设，depend_factor_task只有一层，且不会出现因子相互依赖
        if fac_task.depend_factor_task:
            assert type(
                fac_task.depend_factor_task) == list, f"因子任务的depend_factor_task属性必须为list类型！错误因子为：{fac_task.__name__}！"
        for d_task in fac_task.depend_factor_task:
            if type(d_task) == str:
                d_task = get_fac_class(d_task, factor_path)
            if hasattr(d_task, "depend_factor_task") and d_task.depend_factor_task:
                raise Exception("因子依赖的因子加工任务，只支持一级依赖!")
            assert d_task.__name__.startswith("DEPEND"), "因子任务的depend_factor_task属性中的任务必须以DEPEND开头！"
            if not d_task.__name__ in first_order_factor_name_list:
                first_order_factor_list.append(d_task)
                first_order_factor_name_list.append(d_task.__name__)
    # 校验依赖因子是否有data_input_mode属性
    if first_order_factor_list:
        for order_factor in first_order_factor_list:
            if not getattr(order_factor, "data_input_mode"):
                raise Exception("data_input_mode缺失错误： 因子：{} 缺少属性data_input_mode".format(order_factor.__name__))

    for fac_task in fac_task_cls_list:
        if fac_task.__name__ not in first_order_factor_name_list:
            second_order_factor_list.append(fac_task)
    all_order_factor_list = first_order_factor_list + second_order_factor_list
    get_fac_task_cls_list(all_order_factor_list)
    data_input_mode_collect = []
    for fac_ in all_order_factor_list:
        if hasattr(fac_, "data_input_mode"):
            data_input_mode_collect.extend(fac_.data_input_mode)
    data_input_mode_collect = list(set(data_input_mode_collect))
    factor_type = second_order_factor_list[0].factor_type

    res_df_dict = {}
    for security_code in securities_list:
        res_df_list = []
        # 获取依赖的高频基础因子数据
        # base_data,factor_data: dict key:factor value:dataframe
        # if len(fac.depend_factor) > 0:
        #     factor_data = fac.get_factor_data(start_date=tradingday, end_date=tradingday,
        #                                       security_id=security_code)
        # else:
        #     factor_data = dict()
        # 获取依赖的高频的行情数据 DataFrame
        if isinstance(security_code, (list, tuple)):
            security_id_list = security_code
            security_code = security_id_list[0]
            security_id_extra_list = security_id_list[1:]

        sample_period = fac.custom_params.get("sample_period")

        try:
            if data_source.lower() == "dfs" and fac.security_type.upper() == "STOCK":
                price_data_dict_ori = collect_market_data_dfs(symbol=security_code, date_list=tradingdays,
                                                          collect_mode=data_input_mode_collect)
            else:
                price_data_dict_ori = collect_market_data(security_code=security_code, security_type=fac.security_type,
                                                        start_date=tradingdays[0], end_date=tradingdays[-1],
                                                        collect_mode=data_input_mode_collect,
                                                        tick_sample_interval=sample_period)
        except Exception as e:
            print(f'数据加载报错: {e}')
            continue
        
        start_time = time.time()
        for tradingday in tradingdays:
            res_df_list_day = []
            price_data_dict = {}  # 主标的字典 形如：{‘tick’:pd.DataFrame,'transaction':pd.DataFrame}
            extra_price_data_dict = {}  # 副标的的字典 形如{'159901.SZ':{‘tick’:pd.DataFrame,'transaction':pd.DataFrame}}
            # if data_source.lower() == "dfs" and len(data_input_mode_collect) == 1 and data_input_mode_collect[0].upper() == "KLINE1M_RAW":
            #
            #     price_data_dict["kline"] = price_data_dict_ori[price_data_dict_ori["MDDate"]==tradingday]
            # else:
            # 获取主标的的行情数据
            for key in price_data_dict_ori:
                if "args" in key:
                    price_data_dict[key] = price_data_dict_ori[key]
                    continue
                price_data_dict[key] = price_data_dict_ori[key][price_data_dict_ori[key]['MDDate'] == tradingday]
            # price_data: 高频行情数据 格式 DataFrame
            if "tick_sample_args" in price_data_dict.keys():
                price_data_dict["tick"] = precross_data_from_tquant(price_data_dict["tick"], fac.security_type)
                price_data_dict["tick"] = sample_data_aux(price_data_dict["tick"],
                                                          **price_data_dict["tick_sample_args"])
            if "transaction_sample_args" in price_data_dict.keys():
                price_data_dict["transaction"] = sample_transaction_data(price_data_dict["transaction"],
                                                                         **price_data_dict[
                                                                             "transaction_sample_args"])
            if "order_sample_args" in price_data_dict.keys():
                price_data_dict['order'] = sample_orderbook(price_data_dict['order'],
                                                            **price_data_dict['order_sample_args'])

            for fidx, factor_list in enumerate([first_order_factor_list, second_order_factor_list]):
                if fidx == 1:
                    if res_df_list_day:
                        depend_factor_df = concat_factor_in_a_day(res_df_list_day, fac.factor_type, security_code, tradingday)#pd.concat(res_df_list_day, axis=1)
                        if factor_type == "DAY":
                            depend_factor_df = depend_factor_df.iloc[:, 0]
                    else:
                        depend_factor_df = pd.DataFrame()
                for fac_cls_sub in factor_list:
                    fac_sub = fac_cls_sub()
                    if fidx == 1:
                        # TODO: 添加从共享内存中读取数据依赖任务
                        fac_sub.set_depend_data(depend_factor_df, {})
                    if hasattr(fac, "depend_factor") and fac.depend_factor:
                        # TODO 暂时只支持一个类型的依赖数据
                        if len(fac.depend_factor[0].split('.')) != 2:
                            raise Exception("请按照 因子类型（因子库名）.因子名 的方式书写依赖因子！")
                        depend_factor_type, _ = fac.depend_factor[0].split('.')
                        depend_factor_data = fac.get_factor_data(tradingday, tradingday, security_code)
                        factor_data = {depend_factor_type: depend_factor_data}
                    else:
                        factor_data = {}
                    try:
                        # start_time = time.time()
                        # 调用计算逻辑
                        tmp_res = fac_sub.calc(price_data=price_data_dict, factor_data=factor_data,
                                               custom_params={**fac_sub.custom_params, 'security_code':security_code, 'tradingday':tradingday})
                        # print("The fac: {0}, security_id:{1}, date:{2} calc function cost {3} s".format(
                        #     fac_sub.__class__.__name__, security_code, tradingday, time.time() - start_time))
                    except Exception as e:
                        if verbose>0:
                            print(traceback.print_exc())
                        print("The calc function has error !!: Factor:{0}, Date:{1},Security:{2}".format(
                            fac_sub.__class__.__name__, tradingday, security_code))
                        print("run_hfre_factor_value Exception: ", e)
                        if not fac_sub.factor_type == "DAY":
                            res_df_list_day.append(pd.DataFrame(columns=[fac_sub.__class__.__name__]))
                        continue

                    if fac_sub.factor_type == "DAY":
                        # series，index为因子名，value为值
                        # TODO： 异常校验
                        if not isinstance(tmp_res, pd.Series):
                            raise Exception(
                                "【Calc Func Error】The function calc of factor task {} must return Series[index: factor_name] for factor_type {}! Not {}!".format(
                                    fac_sub.__class__.__name__, fac_sub.factor_type, type(tmp_res)))
                        if len(tmp_res) > 0 and len(tmp_res) != len(fac_sub.output_factor_names):
                            lack_factor_list = list(set(fac_sub.output_factor_names) - set(list(tmp_res.index)))
                            lack_factor_list.sort()
                            extra_factor_list = list(set(list(tmp_res.index)) - set(fac_sub.output_factor_names))
                            extra_factor_list.sort()
                            if len(lack_factor_list) > 0:
                                t1 = "calc计算结果较output_factor_names缺少 {0} 个因子：{1}；\n".format(len(lack_factor_list),
                                                                                            ",".join(lack_factor_list))
                            else:
                                t1 = ""
                            if len(extra_factor_list):
                                t2 = "calc计算结果较output_factor_names多出 {0} 个因子：{1}；\n".format(len(extra_factor_list),
                                                                                            ",".join(extra_factor_list))
                            else:
                                t2 = ""
                            if lack_factor_list or extra_factor_list:
                                t3 = "可以在calc函数中通过res = res.reindex(index=self.output_factor_names)解决！"
                            else:
                                t3 = ""
                            text_raise = "因子：{0}, 日期：{1}, 标的：{2} 计算结果与output_factor_names的因子数不一致：\n".format(
                                fac_sub.__class__.__name__, tradingday, security_code) + t1 + t2 + t3

                            raise Exception(text_raise)

                        tmp_res = tmp_res.to_frame()
                        tmp_res.columns = ['Value']
                        tmp_res.index.name = 'subfactors'
                        for f in list(tmp_res.index):
                            if f not in fac_sub.output_factor_names:
                                raise Exception("返回结果的因子名: {0} 应与output_factor_names内的一致！".format(f))
                    else:
                        if not isinstance(tmp_res, pd.Series) and not isinstance(tmp_res, pd.DataFrame):
                            raise Exception(
                                "【Calc Func Error】The function calc of factor task{} must return DataFrame[index: mdtime, columns: factor_name] for factor_type {}! Not {}!".format(
                                    fac_sub.__class__.__name__, fac_sub.factor_type, type(tmp_res)))
                        try:
                            assert len(tmp_res) > 0
                        except:
                            print(f"Factor:{0}, Date:{1},Security:{2}计算结果为空".format(fac_sub.__class__.__name__, tradingday, security_code))
                        else:
                            # 没有异常时执行
                            if len(str(tmp_res.index[0])) not in [8, 9]:
                                raise Exception(
                                    "【Calc Func Error】The index of the DataFrame of factor task returned by the calc method must be timestamp of length 8 or 9 for factor_type {}! Not {}.".format(
                                        fac_sub.__class__.__name__, fac_sub.factor_type, tmp_res.index[0]))
                        if isinstance(tmp_res, pd.Series):
                            # 高频因子统一处理成DataFrame
                            tmp_res = tmp_res.to_frame()
                            for f in list(tmp_res.columns):
                                if f not in fac_sub.output_factor_names:
                                    raise Exception("返回结果的因子名: {0} 应与output_factor_names内的一致！".format(f))
                        elif isinstance(tmp_res, pd.DataFrame):
                            for f in list(tmp_res.columns):
                                if f not in fac_sub.output_factor_names:
                                    raise Exception("返回结果的因子名: {0} 应与output_factor_names内的一致！".format(f))
                        else:
                            raise Exception(
                                "【Calc Func Error】The function calc of factor task {} must return Series or DataFrame for factor_type {}! Not {}!".format(
                                    fac_sub.__class__.__name__, fac_sub.factor_type, type(tmp_res)))
                    if not tmp_res.empty:
                        res_df_list_day.append(tmp_res)
            res = concat_factor_in_a_day(res_df_list_day, fac.factor_type, security_code, tradingday)
            res_df_list.append(res)
        print("The fac: {0}, security_id:{1}, calc function cost {2} s".format(
                        fac_sub.__class__.__name__, security_code, time.time() - start_time))

        if res_df_list:
            df = pd.concat(res_df_list)
            res_df_dict[security_code] = df
        else:
            res_df_dict[security_code] = pd.DataFrame()
    if fac.factor_type == "DAY":
        if res_df_dict:
            df_secs_list = []
            # df_secs = pd.DataFrame()
            for sec in list(res_df_dict.keys()):
                # df_secs = df_secs.append(res_df_dict[sec])
                df_secs_list.append(res_df_dict[sec])
            df_secs = pd.concat(df_secs_list)
            if df_secs.empty:
                return pd.DataFrame(securities_list, columns=['HTSCSecurityID'])
            else:
                if df_secs.dropna().empty:
                    df_secs_t = pd.DataFrame(securities_list, columns=['HTSCSecurityID'])
                else:
                    df_secs_t = \
                        pd.pivot_table(df_secs, index=['MDDate', 'HTSCSecurityID'], columns=['subfactors'],
                                       values=['Value'])['Value']
                    df_secs_t.columns.name = None
                return df_secs_t
        else:
            return pd.DataFrame()
    else:
        return res_df_dict
