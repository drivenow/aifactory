# -*- coding:utf-8 -*-
from MDCDataProvider.stockdata import StockDataDP
# from MDCDataProvider.stockdata.stock_data import StockDataDP as MDCStockDataDP
from xquant.factorframework.rayframe.mkdata.MDCStockData import MDCStockDataDP
from MDCDataProvider.funddata import FundDataDP
from MDCDataProvider.funddata.fund_data import FundDataDP as MDCFundDataDP
from MDCDataProvider.DataProvider_ini import get_dataprovider
from xquant.factorframework.rayframe.constant import DataCollectMode, transform_datamode
from .helper import *
import os
from tqdm import trange
from .settings import *
from xquant.factordata import FactorData
import pyarrow.parquet as pq
import polars as pl
from xquant.factorframework.rayframe.util.util import  check_date

class EmptyException(Exception):
    pass

data_instance = {}
s = FactorData()

def collect_market_data(security_code, start_date, end_date, collect_mode=[DataCollectMode.TICK_RAW],
                        tick_sample_interval=None, security_type=None):
    """
    :param security_code: 标的名称
    :param security_type: 标的类型
    :param start_datetime: 取数开始时间
    :param end_datetime: 取数结束时间
    :param collect_mode: list，订阅的数据类型，目前支持TICK_RAW、TICK_SAMPLE（采样Tick数据）、TRANSACTION_RAW、ORDER_RAW、ORDER_SAMPLE、KLINE1M_RAW
    :param sample_period: int，采样的时间间隔，单位为秒，当且仅当DataCollectMode为TICK_SAMPLE时必传
    :return:
    """
    start_datetime = start_date + " 080000000"
    end_datetime = end_date + " 235900250"
    # if not security_type:
    #     from tquant.basic_data import BasicData
    #     bd = BasicData()
    #     security_type = bd.get_security_type(security_code)

    assert type(collect_mode) == list, "collect_mode参数类型必须为列表！"
    df_dict = {}
    for mode in collect_mode:
        mode = transform_datamode(mode)
        if mode == DataCollectMode.TICK_RAW:
            if security_type.upper() == "STOCK":
                bar_size = "STOCK"
            else:
                bar_size = "TICK"
            if df_dict.get("tick"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            df_dict["tick"] = get_market_data(security_code, start_datetime, end_datetime, bar_size=bar_size,
                                              security_type=security_type)
        elif mode == DataCollectMode.TICK_SAMPLE:
            if security_type.upper() == "STOCK":
                bar_size = "STOCK"
            else:
                bar_size = "TICK"
            if df_dict.get("tick"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            assert type(
                tick_sample_interval) == int, "DataCollectMode.TICK_SAMPLE模式下，需要指定TICK的采样时间间隔参数tick_sample_interval, 单位为秒!"
            df_tick = get_market_data(security_code, start_datetime, end_datetime, bar_size=bar_size,
                                      security_type=security_type)
            df_dict["tick"] = df_tick
            df_dict["tick_sample_args"] = {"security_type": security_type, "sample_period": tick_sample_interval}
        elif mode == DataCollectMode.TRANSACTION_RAW:
            if df_dict.get("transaction"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            df_dict["transaction"] = get_market_data(security_code, start_datetime, end_datetime,
                                                     bar_size="TRANSACTION", security_type=security_type)
        elif mode == DataCollectMode.TRANSACTION_SAMPLE:
            if df_dict.get("transaction"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            df_dict["transaction"] = get_market_data(security_code, start_datetime, end_datetime,
                                                     bar_size="TRANSACTION", security_type=security_type)
            df_dict["transaction_sample_args"] = {"sample_period": tick_sample_interval}
        elif mode == DataCollectMode.ORDER_RAW:
            if df_dict.get("order"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            df_dict["order"] = get_market_data(security_code, start_datetime, end_datetime, bar_size="ORDER",
                                               security_type=security_type)
        elif mode == DataCollectMode.ORDER_SAMPLE:
            if df_dict.get("order"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            df_dict["order"] = get_market_data(security_code, start_datetime, end_datetime, bar_size="ORDER",
                                               security_type=security_type)
            df_dict["order_sample_args"] = {"sample_period": tick_sample_interval}
        elif mode == DataCollectMode.KLINE1M_RAW:
            if df_dict.get("kline"):
                raise Exception("DataCollectMode中存在重复的行情数据类型{}，请重新传入！".format(mode))
            df_dict["kline"] = get_market_data(security_code, start_datetime, end_datetime, bar_size="Kline1M4ZT",
                                               security_type=security_type)
        else:
            raise Exception("DataCollectMode不支持此枚举类型: {}！".format(mode))
    return df_dict


def get_market_data(security_code, start_datetime, end_datetime, bar_size, security_type):
    """
    获取 tick级行情数据
    :param security_code: string
    :param fac_names: list
    :param date： string
    :return:  multiindex DataFrame
                    Factor1 Factor2 Factor3 ...
    MDDate MDTime
    """
    # TODO Stock多一种KLine1M4ZT的的bar_size
    # data = pd.DataFrame()
    global data_instance
    data_list = []
    if security_type.upper() == "STOCK":
        for dp_type, dp_values in get_dataprovider('stock', bar_size, start_datetime, end_datetime).items():
            if dp_type == 'mdc_dp':
                if not data_instance.get("stock_mdc"):
                    # TODO： 是否增加global关键词
                    data_instance["stock_mdc"] = MDCStockDataDP()
                mdp = data_instance["stock_mdc"]
                # data = data.append(mdp.get_stock_data(symbol=security_code, start_time=dp_values['start_time'],
                #                                       end_time=dp_values['end_time'], bar_size=bar_size))
                data_p = mdp.get_stock_data(symbol=security_code, start_time=dp_values['start_time'],
                                            end_time=dp_values['end_time'], bar_size=bar_size)
                if not data_p.empty:
                    data_list.append(data_p)
            else:
                if not data_instance.get("stock"):
                    # TODO： 是否增加global关键词
                    data_instance["stock"] = StockDataDP()
                    data_instance["stock"].dp.file_type = "DFS"
                mdp = data_instance["stock"]
                # data = data.append(mdp.get_stock_data(symbol=security_code, start_time=dp_values['start_time'],
                #                                       end_time=dp_values['end_time'], bar_size=bar_size))
                data_p = mdp.get_stock_data(symbol=security_code, start_time=dp_values['start_time'],
                                                      end_time=dp_values['end_time'], bar_size=bar_size)
                if not data_p.empty:
                    data_list.append(data_p)
    elif security_type.upper() == 'FUND':
        for dp_type, dp_values in get_dataprovider('fund', bar_size, start_datetime, end_datetime).items():
            if dp_type == 'mdc_dp':
                if not data_instance.get("fund_mdc"):
                    # TODO： 是否增加global关键词
                    data_instance["fund_mdc"] = MDCFundDataDP()
                mdp = data_instance["fund_mdc"]
                # data = data.append(mdp.get_fund_data(symbol=security_code, start_time=dp_values['start_time'],
                #                                      end_time=dp_values['end_time'], bar_size=bar_size))
                data_p = mdp.get_fund_data(symbol=security_code, start_time=dp_values['start_time'],
                                                     end_time=dp_values['end_time'], bar_size=bar_size)
                if not data_p.empty:
                    data_list.append(data_p)
            else:
                if not data_instance.get("fund"):
                    # TODO： 是否增加global关键词
                    data_instance["fund"] = FundDataDP()
                    data_instance["fund"].dp.file_type = "DFS"
                mdp = data_instance["fund"]
                # data = data.append(mdp.get_fund_data(symbol=security_code, start_time=dp_values['start_time'],
                #                                      end_time=dp_values['end_time'], bar_size=bar_size))
                data_p = mdp.get_fund_data(symbol=security_code, start_time=dp_values['start_time'],
                                                     end_time=dp_values['end_time'], bar_size=bar_size)
                if not data_p.empty:
                    data_list.append(data_p)
    # 之后会支持扩展其他证券类型的因子 bond fund future
    else:
        raise Exception("目前仅支持证券类型为stock,fund的因子开发！")
    if data_list:
        data = pd.concat(data_list)
    else:
        raise EmptyException("标的：{0}，在时间范围{1}--{2}内暂无行情数据".format(security_code, start_datetime, end_datetime))
    return data

def collect_market_data_dfs(symbol, date_list, collect_mode=[DataCollectMode.KLINE1M_RAW]):
    # list，订阅的数据类型，目前支持TICK_RAW、TRANSACTION_RAW、ORDER_RAW、KLINE1M_RAW
    assert type(collect_mode) == list, "collect_mode参数类型必须为列表！"
    df_dict = {}
    for mode in collect_mode:
        mode = transform_datamode(mode)
        if mode == DataCollectMode.TICK_RAW:
            if df_dict.get("tick"):
                continue
            df_dict["tick"] = get_level2_data(symbol, date_list)
        elif mode == DataCollectMode.TRANSACTION_RAW:
            if df_dict.get("transaction"):
                continue
            df_dict["transaction"], df_dict["order"] = get_trans_order_data(symbol, date_list)
        elif mode == DataCollectMode.ORDER_RAW:
            if df_dict.get("order"):
                continue
            df_dict["transaction"], df_dict["order"] = get_trans_order_data(symbol, date_list)
        elif mode == DataCollectMode.KLINE1M_RAW:
            if df_dict.get("kline"):
                continue
            df_dict["kline"] = get_sample_kline1m_data(symbol, date_list)
        else:
            raise Exception("DataCollectMode不支持此枚举类型: {}！".format(mode))
    return df_dict


def get_sample_kline1m_data(symbol, date_list):
    file_list = []
    for date in date_list:
        file_path = os.path.join(l3_data_dir, f"{symbol}/{symbol}_{date}.parquet")
        if os.path.exists(file_path):
            file_list.append(file_path)
        else:
            print(f"暂未缓存{symbol}_{date}的分钟数据！")
    if file_list:
        tick_df_all = pl.read_parquet(file_list)
        tick_df_all = tick_df_all.with_columns(
                                mdate = pl.col("mdtime").cast(pl.String).str.slice(0,8).alias("mdate")
                                )
        df_1m = pl.DataFrame()
        for date in date_list:
            tick_df = tick_df_all.filter(
                pl.col("mdate").eq(date)
            )
            if len(tick_df) > 0:
                tick_df_1m = sample_kline1m(tick_df, date)
                if len(df_1m) == 0:
                    df_1m = tick_df_1m
                else:
                    df_1m = df_1m.vstack(tick_df_1m)
        df_1m = df_1m.to_pandas()
    else:
        df_1m = pd.DataFrame(columns=["MDDate", "MDTime", "HTSCSecurityID", "OpenPx", "ClosePx",
                                     "HighPx", "LowPx", "NumTrades", "TotalVolumeTrade", "TotalValueTrade",
                                     "PeriodType", "MacroDetail", "KLineCategory"])
    return df_1m


def sample_kline1m(tick_df, date):
    prev_close_price = tick_df[0, "prev_close_price"]
    # （1）rust会遍历逐笔盘口匹配3s快照，如果3s快照的盘口跟逐笔盘口完全一致，
    # 赋值mdtimestamp_3s表明3s快照就是这一条逐笔数据合成的（如果有多条逐笔盘口匹配一致，找mdtime和mdtimestamp_3s时间差最小的一条）
    tick_df_3s = tick_df.with_columns(pl.col("mdtime").cast(pl.Int64)).filter(
        (pl.col("mdtimestamp_3s").ne(0)) |
        (pl.col("mdtime").ge(int(f"{date}092500000")) & pl.col("mdtime").lt(int(f"{date}093000000"))) |
        (pl.col("mdtime").ge(int(f"{date}145700000")) & pl.col("mdtime").le(int(f"{date}150100000")))
    ).with_columns(
        mdtimestamp_3s=pl.when(pl.col("mdtimestamp_3s") == 0).then(pl.col("mdtimestamp")).otherwise(
            pl.col("mdtimestamp_3s")),
    )

    # (2)time_diff计算相邻两条3s快照的时间差
    tick_df_3s = tick_df_3s.with_columns(
        unchange_mdtimestamp_3s=pl.from_epoch(pl.col("finished_time")+ 8 * 3600 * 1000, time_unit="ms").shift(),
        Datetime=pl.from_epoch(pl.col("mdtimestamp_3s") + 8 * 3600 * 1000, time_unit="ms"),
    )
    # (3) rust合成数据会对mdtimestamp_3s字段赋值，举个例子，如果mdtimestamp_3s相邻的两条数据为093058秒和093104，那么说明093101秒这一条盘口在rust那边缺失，这时候该补齐一条3s快照数据，全部值都延续093057的盘口状态。
    # 总结起来就是，如果上一条数据的unchange_mdtimestamp_3s为本分钟，那这一分钟的开盘价就沿用上一条
    time_0 = datetime.datetime.strptime("1970-01-01 08:00:00", "%Y-%m-%d %H:%M:%S")
    tick_df_3s = tick_df_3s.with_columns(mdtime_3s=pl.col("Datetime").dt.strftime("%Y%m%d%H%M%S%3f").cast(pl.Int64),
                   last_condition=pl.when((pl.col("unchange_mdtimestamp_3s") != time_0) & (
                               pl.col("unchange_mdtimestamp_3s").dt.strftime("%M") == pl.col("Datetime").dt.strftime("%M")))
                               .then(True)
                               .otherwise(False),
                               ).sort("Datetime")

    tick_df_1m = tick_df_3s.group_by_dynamic(
        index_column='Datetime',
        every="1m", closed="left",
        label="left").agg(pl.col("code_str").last(),
                          pl.col("last_price").first().alias("OpenPx"),
                          pl.col("last_price").last().alias("ClosePx"),
                          pl.col("last_price").max().alias("HighPx"),
                          pl.col("last_price").min().alias("LowPx"),
                          pl.col("last_price").last(),
                          pl.col("ttl_trade_num").last(),
                          pl.col("ttl_volume").last(),
                          pl.col("ttl_turn_over").last(),
                          pl.col("msg_trade_type").last(),
                          pl.col("unchange_mdtimestamp_3s").first(),
                          pl.col("last_condition").first(),
                          ).sort("Datetime")
    # (3) rust合成数据会对mdtimestamp_3s字段赋值，举个例子，如果mdtimestamp_3s相邻的两条数据为093058秒和093104，那么说明093101秒这一条盘口在rust那边缺失，这时候该补齐一条3s快照数据，全部值都延续093057的盘口状态。
    # 总结起来就是，如果这一分钟第一条和上一分钟最后一条差的时间超过3s，那这一分钟的开盘价就沿用上一条；
    tick_df_1m = tick_df_1m.with_columns(
        MDTime=pl.col("Datetime").dt.strftime("%H%M%S%3f"),
        MDDate=pl.col("Datetime").dt.strftime("%Y%m%d"),
    ).with_columns(
        OpenPx = pl.when(pl.col("last_condition").eq(True))
                       .then(pl.col("ClosePx").shift(1)).otherwise(pl.col("OpenPx")),
    ).with_columns(
        # OpenPx价格变化之后，需要重新修正最高、最低价
        HighPx=pl.when(pl.col("OpenPx") > pl.col("HighPx")).then(pl.col("OpenPx")).otherwise(pl.col("HighPx")),
        LowPx=pl.when(pl.col("OpenPx") < pl.col("LowPx")).then(pl.col("OpenPx")).otherwise(pl.col("LowPx"))
    )


    # 当日最后一条K线的开高低收均为当日收盘价，（除沪深债券外）成交量为收盘集合竞价阶段成交总量

    if "150000000" not in tick_df_1m["MDTime"].unique():
        # TODO tick_df_1m合成的数据没有15:00这跟K线，新增时把price_cols几列的数据按照59分的last_price填充值；成交量数据是累计的，无法计算竞价阶段成交总量
        # 集合竞价3分钟的成交量时一样的，15点的成交量按前一分钟填充
        columns = tick_df_1m.columns
        price_cols = ["last_price", "HighPx", "LowPx", "OpenPx", "ClosePx"]
        # 添加15:00分钟K线
        last_price = tick_df_1m[-1, "last_price"]
        row_data_15 = {}
        for col in columns:
            if col in price_cols:
                row_data_15[col] = [last_price]
            elif col == "Datetime":
                row_data_15[col] = [date + "150000000"]
            elif col == "MDTime":
                row_data_15[col] = ["150000000"]
            else:
                row_data_15[col] = [None]
        df_15 = pl.DataFrame(row_data_15)
        df_15 = df_15.with_columns(pl.col("Datetime").str.strptime(pl.Datetime(time_unit="ms"), "%Y%m%d%H%M%S%3f"))
        tick_df_1m = tick_df_1m.vstack(df_15)

    # 一天全部分钟k数据槽
    df_valid_time = pl.DataFrame().with_columns(
        Datetime=pl.datetime_range(start=datetime.datetime.strptime(date + "000000000", "%Y%m%d%H%M%S%f"),
                                   end=datetime.datetime.strptime(date + "235959000", "%Y%m%d%H%M%S%f"),
                                   interval="60s").dt.cast_time_unit("ms")
    )
    # 242根分钟k数据槽
    df_valid_time = df_valid_time.filter(
        (pl.col("Datetime").cast(pl.Time).is_between(datetime.time(9, 30), datetime.time(11, 29))) |
        (pl.col("Datetime").cast(pl.Time).is_between(datetime.time(13, 0), datetime.time(15, 0))) |
        (pl.col("Datetime").cast(pl.Time).is_in([datetime.time(9, 25)]))
    )
    tick_df_1m = df_valid_time.join(tick_df_1m, on="Datetime", how="left").sort("Datetime")

    # 设置KLineCategory初始值为0
    tick_df_1m = tick_df_1m.with_columns(
        KLineCategory=pl.lit(0),
        PeriodType=pl.lit(1),
        MacroDetail=pl.lit(False),
    )

    # 判断9:25分是否有tick存在
    if tick_df_1m[0, "last_price"] is None:
        tick_df_1m[0, "last_price"] = prev_close_price
        tick_df_1m[0, "HighPx"] = prev_close_price
        tick_df_1m[0, "LowPx"] = prev_close_price
        tick_df_1m[0, "OpenPx"] = prev_close_price
        tick_df_1m[0, "ClosePx"] = prev_close_price
        tick_df_1m[0, "ttl_trade_num"] = 0
        tick_df_1m[0, "ttl_volume"] = 0
        tick_df_1m[0, "ttl_turn_over"] = 0
        tick_df_1m[0, "MDTime"] = "092500000"
        tick_df_1m[0, "KLineCategory"] = 2
        tick_df_1m[0, "MacroDetail"] = True

    # TODO 判断分钟周期内是否有Tick，没有tick则判断前一分钟K是否存在，
    #  1> 若存在前一分钟K：则将其开高低收价格字段用前一分钟K的ClosePx填充，因为没有tick所以也不存在成交和委托，KLineCategory置为2，
    #  2> 若不存在前一分钟K：则先将该分钟填入null
    is_null_kline = pl.col("last_price").is_null()
    is_valid_kline = pl.col("last_price").is_not_null()
    prev_is_valid = pl.col("last_price").shift(1).is_not_null()
    is_not_trade_type = pl.col("msg_trade_type").is_not_null()
    tick_df_1m = tick_df_1m.with_columns(
        last_price=pl.when(is_null_kline & prev_is_valid)
            .then(pl.col("last_price").shift(1))
            .otherwise(pl.col("last_price")),
        HighPx=pl.when(is_null_kline & prev_is_valid)
            .then(pl.col("last_price").shift(1))
            .otherwise(pl.col("HighPx")),
        OpenPx=pl.when(is_null_kline & prev_is_valid)
            .then(pl.col("last_price").shift(1))
            .otherwise(pl.col("OpenPx")),
        ClosePx=pl.when(is_null_kline & prev_is_valid)
            .then(pl.col("last_price").shift(1))
            .otherwise(pl.col("ClosePx")),
        LowPx=pl.when(is_null_kline & prev_is_valid)
            .then(pl.col("last_price").shift(1))
            .otherwise(pl.col("LowPx")),
        MacroDetail=pl.when(is_null_kline)
            .then(True)
            .otherwise(pl.col('MacroDetail')),
        # 设置KLineCategory为2（如果满足条件）
        KLineCategory=pl.when(is_null_kline & prev_is_valid)
            .then(pl.lit(2))
            .otherwise(pl.col("KLineCategory"))
    )

    # TODO 周期内存在Tick，则取周期内最后一条Tick。判断该Tick的总成交量TotalVolumeTrade是否为0，
    #  若总成交量为0，表明开盘至今成交量为0，KLineCategory置为1，开高低收字段均使用昨收盘价PreClosePx填充。
    tick_df_1m = tick_df_1m.with_columns(
        last_price=pl.when(is_valid_kline & (pl.col("ttl_volume") == 0))
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("last_price")),
        OpenPx=pl.when(is_valid_kline & (pl.col("ttl_volume") == 0))
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("OpenPx")),
        ClosePx=pl.when(is_valid_kline & (pl.col("ttl_volume") == 0))
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("ClosePx")),
        HighPx=pl.when(is_valid_kline & (pl.col("ttl_volume") == 0))
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("HighPx")),
        LowPx=pl.when(is_valid_kline & (pl.col("ttl_volume") == 0))
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("LowPx")),
        # 设置KLineCategory为1（如果满足条件）
        KLineCategory=pl.when(is_valid_kline & (pl.col("ttl_volume") == 0))
            .then(pl.lit(1))
            .otherwise(pl.col("KLineCategory"))
    )

    # TODO 若PrevMinLastTick存在，对比本条Tick与PrevMinLastTick的TotalVolumeTrade是否相等，
    #  若TotalVolumeTrade相等，则表明该分钟周期内无成交产生以及最新价未发生变化，若无委托，KLineCategory置为2
    tick_df_1m = tick_df_1m.with_columns(
        KLineCategory=pl.when(is_valid_kline & prev_is_valid & is_not_trade_type & (
                pl.col("ttl_volume") == pl.col("ttl_volume").shift(1)))
            .then(pl.lit(2))
            .otherwise(pl.col("KLineCategory"))
    )
    # TODO 最终再对所有数据槽进行顺序遍历，检查是否有槽填充的是null值，
    #  若有null值则开高低收价格使用昨收盘价填充，KLineCategory置为1。
    is_null_kline_2 = pl.col("last_price").is_null()
    tick_df_1m = tick_df_1m.with_columns(
        last_price=pl.when(is_null_kline_2)
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("last_price")),
        OpenPx=pl.when(is_null_kline_2)
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("OpenPx")),
        ClosePx=pl.when(is_null_kline_2)
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("ClosePx")),
        HighPx=pl.when(is_null_kline_2)
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("HighPx")),
        LowPx=pl.when(is_null_kline_2)
            .then(pl.lit(prev_close_price))
            .otherwise(pl.col("LowPx")),
        # 设置KLineCategory为1（如果满足条件）
        KLineCategory=pl.when(is_null_kline_2)
            .then(pl.lit(1))
            .otherwise(pl.col("KLineCategory"))
    )
    # TODO 增加字段-成交笔数
    tick_df_1m = tick_df_1m.with_columns(
        trade_num=pl.when(pl.col("ttl_trade_num").shift(1).is_not_null())
            .then(pl.col("ttl_trade_num") - pl.col("ttl_trade_num").shift(1))
            .otherwise(pl.col("ttl_trade_num")),
        volume=pl.when(pl.col("ttl_volume").shift(1).is_not_null())
            .then(pl.col("ttl_volume") - pl.col("ttl_volume").shift(1))
            .otherwise(pl.col("ttl_volume")),
        turn_over=pl.when(pl.col("ttl_turn_over").shift(1).is_not_null())
            .then(pl.col("ttl_turn_over") - pl.col("ttl_turn_over").shift(1))
            .otherwise(pl.col("ttl_turn_over")),
    )
    tick_df_1m = tick_df_1m.fill_null(strategy="forward")
    tick_df_1m = tick_df_1m.select(
        pl.col("MDDate"),
        pl.col("MDTime"),
        pl.col("code_str").alias("HTSCSecurityID"),
        pl.col("OpenPx"),
        pl.col("ClosePx"),
        pl.col("HighPx"),
        pl.col("LowPx"),
        pl.col("trade_num").alias("NumTrades"),
        pl.col("volume").alias("TotalVolumeTrade"),
        pl.col("turn_over").alias("TotalValueTrade"),
        pl.col('PeriodType'),
        pl.col('MacroDetail'),
        pl.col("KLineCategory"),
    )
    return tick_df_1m


def get_trans_order_data(symbol, date_list):
    file_list = []
    for date in date_list:
        file_path = os.path.join(l3_data_dir, f"{symbol}/{symbol}_{date}.parquet")
        if os.path.exists(file_path):
            file_list.append(file_path)
        else:
            print(f"暂未缓存{symbol}_{date}的逐笔数据！")
    if file_list:
        tick_df_all = pl.read_parquet(file_list)
        tick_df_all = tick_df_all.with_columns(
                                mdate = pl.col("mdtime").cast(pl.String).str.slice(0,8).alias("mdate")
                                )
        df_transaction = pl.DataFrame()
        df_order = pl.DataFrame()
        for date in date_list:
            tick_df = tick_df_all.filter(
                pl.col("mdate").eq(date)
            )
            if len(tick_df) > 0:
                tick_df_trans, tick_df_order,  = sample_trans_order(tick_df, date)
                if len(df_transaction) == 0:
                    df_transaction = tick_df_trans
                else:
                    df_transaction = df_transaction.vstack(tick_df_trans)
                if len(df_order) == 0:
                    df_order = tick_df_order
                else:
                    df_order = df_order.vstack(tick_df_order)
        df_transaction = df_transaction.to_pandas()
        df_order = df_order.to_pandas()
    else:
        df_transaction = pd.DataFrame(columns=["MDDate", "MDTime", "HTSCSecurityID", "TradeType",
                                               "TradeBSFlag", "TradePrice", "TradeQty",
                                               "TradeMoney", "TradeBuyNo", "TradeSellNo",
                                               "ApplSeqNum"])
        df_order = pd.DataFrame(columns=["MDDate", "MDTime", "HTSCSecurityID", "OrderType",
                                         "OrderBSFlag", "OrderPrice", "OrderQty",
                                         "OrderMoney", "OrderBuyNo", "OrderSellNo",
                                         "ApplSeqNum"])
    return df_transaction, df_order


def sample_trans_order(tick_df, date):
    tick_df = tick_df.with_columns(
        pl.col("mdtime").cast(pl.Int64)
    ).filter(
        (pl.col("mdtime").ge(int(f"{date}092500000")) & pl.col("mdtime").le(int(f"{date}150100000")))
    )
    tick_df = tick_df.with_columns(
                Datetime=pl.from_epoch(pl.col("mdtimestamp") + 8 * 3600 * 1000, time_unit="ms"),
            ).with_columns(
        MDTime=pl.col("Datetime").dt.strftime("%H%M%S%3f"),
        MDDate=pl.col("Datetime").dt.strftime("%Y%m%d"),
    )
    df_transaction = tick_df.filter(pl.col("msg_trade_type").ge(0)).select(
        pl.col("MDDate"),
        pl.col("MDTime"),
        pl.col("code_str").alias("HTSCSecurityID"),
        pl.col("msg_trade_type").alias("TradeType"),
        pl.col("msg_bsflag").alias("TradeBSFlag"),
        pl.col("msg_price").alias("TradePrice"),
        pl.col("msg_qty").alias("TradeQty"),
        pl.col("msg_amt").alias("TradeMoney"),
        pl.col("msg_buy_no").alias("TradeBuyNo"),
        pl.col("msg_sell_no").alias("TradeSellNo"),
        pl.col("last_seq_num").alias("ApplSeqNum"),
        )
    df_order = tick_df.filter(pl.col("msg_order_type").ge(0)).select(
        pl.col("MDDate"),
        pl.col("MDTime"),
        pl.col("code_str").alias("HTSCSecurityID"),
        pl.col("msg_order_type").alias("OrderType"),
        pl.col("msg_bsflag").alias("OrderBSFlag"),
        pl.col("msg_price").alias("OrderPrice"),
        pl.col("msg_qty").alias("OrderQty"),
        pl.col("msg_amt").alias("OrderMoney"),
        pl.col("msg_buy_no").alias("OrderBuyNo"),
        pl.col("msg_sell_no").alias("OrderSellNo"),
        pl.col("last_seq_num").alias("ApplSeqNum"),
        )

    return df_transaction, df_order

def get_level2_data(symbol, date_list):
    file_list = []
    for date in date_list:
        file_path = os.path.join(l3_data_dir, f"{symbol}/{symbol}_{date}.parquet")
        if os.path.exists(file_path):
            file_list.append(file_path)
        else:
            print(f"暂未缓存{symbol}_{date}的tick数据！")
    if file_list:
        tick_df_all = pl.read_parquet(file_list)
        tick_df_all = tick_df_all.with_columns(
                                mdate = pl.col("mdtime").cast(pl.String).str.slice(0,8).alias("mdate")
                                )
        df_level2 = pl.DataFrame()
        for date in date_list:
            tick_df = tick_df_all.filter(
                pl.col("mdate").eq(date)
            )
            if len(tick_df) > 0:
                tick_df_level2 = sample_level2_data(tick_df, date)
                if len(df_level2) == 0:
                    df_level2 = tick_df_level2
                else:
                    df_level2 = df_level2.vstack(tick_df_level2)
        df_level2 = df_level2.to_pandas()
    else:
        df_level2 = pd.DataFrame(columns=["MDDate", "MDTime", "HTSCSecurityID", "LastPx",
                                          "HighPx", "LowPx", "PreClosePx", "TotalVolumeTrade",
                                          "TotalValueTrade", "NumTrades", "asks_price",
                                          "bids_price", "asks_qty", "bids_qty", "asks_count",
                                          "bids_count", "ReceiveDateTime"])
    return df_level2

def sample_level2_data(tick_df, date):
    tick_df = tick_df.with_columns(pl.col("mdtime").cast(pl.Int64)).filter(
                    pl.col("mdtime").ge(int(f"{date}092500000")) & pl.col("mdtime").le(int(f"{date}150100000"))
                    ).with_columns(
                mdtimestamp_3s=pl.when(pl.col("mdtimestamp_3s") == 0).then(pl.col("mdtimestamp")).otherwise(
                    pl.col("mdtimestamp_3s")),
                )
    tick_df = tick_df.with_columns(
                Datetime=pl.from_epoch(pl.col("mdtimestamp_3s") + 8 * 3600 * 1000, time_unit="ms"),
            ).with_columns(
                MDTime=pl.col("Datetime").dt.strftime("%H%M%S%3f"),
                MDDate=pl.col("Datetime").dt.strftime("%Y%m%d"),
            )
    tick_df_3s = tick_df.select(
        pl.col("MDDate"),
        pl.col("MDTime"),
        pl.col("code_str").alias("HTSCSecurityID"),
        pl.col("last_price").alias("LastPx"),
        pl.col("high_price").alias("HighPx"),
        pl.col("low_price").alias("LowPx"),
        pl.col("prev_close_price").alias("PreClosePx"),
        pl.col("ttl_volume").alias("TotalVolumeTrade"),
        pl.col("ttl_turn_over").alias("TotalValueTrade"),
        pl.col("ttl_trade_num").alias("NumTrades"),
        pl.col("asks_price"),
        pl.col("bids_price"),
        pl.col("asks_qty"),
        pl.col("bids_qty"),
        pl.col("asks_count"),
        pl.col("bids_count"),
        pl.col("recvtime").alias("ReceiveDateTime"),
    )
    return tick_df_3s


