import polars as pl
import pandas as pd
import datetime
import os
from xquant.factordata import FactorData
from xquant.setXquantEnv import xquantEnv

if xquantEnv == 1:
    l3_data_dir = "/dfs/group/800657/library/l3_data/"
    l3_minute_data_dir = "/dfs/group/800657/library_alpha/quant_data/L3_MINUTE_DATA"
else:
    l3_data_dir = "/data/user/quanttest007/K0321499/keep/dataset"
    l3_minute_data_dir = "/data/user/quanttest007/library_alpha/quant_data/L3_MINUTE_DATA"


s = FactorData()


def get_sample_kline1m_data(symbol, date_list):
    file_list = []
    for date in date_list:
        file_path = os.path.join(l3_data_dir, f"{symbol}/{symbol}_{date}.parquet")
        if os.path.exists(file_path):
            file_list.append(file_path)
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

def generate_l3_minute_data(symbol, date):
    file_path = os.path.join(l3_data_dir, f"{symbol}/{symbol}_{date}.parquet")
    if os.path.exists(file_path):
        tick_df = pl.read_parquet(file_path)
        df_1m = sample_kline1m(tick_df, date)
    else:
        df_1m = pd.DataFrame(columns=["MDDate", "MDTime", "HTSCSecurityID", "OpenPx", "ClosePx",
                                     "HighPx", "LowPx", "NumTrades", "TotalVolumeTrade", "TotalValueTrade",
                                     "PeriodType", "MacroDetail", "KLineCategory"])
    return df_1m

def __save_minute_data_bak(df_1m, month):
    factors = ["OpenPx", "ClosePx", "HighPx", "LowPx", "NumTrades", "TotalVolumeTrade", "TotalValueTrade"]
    df_1m = df_1m[~df_1m["MDDate"].isnull()]
    df_1m = df_1m.drop_duplicates(subset=["MDDate", "MDTime", "HTSCSecurityID"], keep="last")
    for factor in factors:
        l3_minute_data_dir_factor = os.path.join(l3_minute_data_dir, factor.upper())
        os.makedirs(l3_minute_data_dir_factor, exist_ok=True)
        file_path = os.path.join(l3_minute_data_dir_factor, f"{month}.parquet")
        if not os.path.exists(file_path):
            df_fac = df_1m.pivot(
                                index=['MDDate', 'MDTime'],  # 索引列
                                columns='HTSCSecurityID',  # 作为新列名的列
                                values=factor  # 填充到新列中的值
                                )
            df_fac = df_fac.sort_index()
            df_fac.to_parquet(file_path)
        else:
            df_new = df_1m[['MDDate', 'MDTime', 'HTSCSecurityID', factor]].copy()
            df_his = pd.read_parquet(file_path, engine="pyarrow")
            # 把DataFrame转回长格式，concat后方便去重
            df_his.reset_index(inplace=True)
            df_his = df_his.melt(
                            id_vars=['MDDate', 'MDTime'],
                            var_name='HTSCSecurityID',
                            value_name=factor
                          ).dropna(subset=[factor])
            df_fac = pd.concat([df_his, df_new], ignore_index=True)
            df_fac = df_fac.drop_duplicates(subset=["MDDate", "MDTime", "HTSCSecurityID"], keep="last")
            df_fac = df_fac.pivot(
                            index=['MDDate', 'MDTime'],  # 索引列
                            columns='HTSCSecurityID',  # 作为新列名的列
                            values=factor  # 填充到新列中的值
                        )
            df_fac = df_fac.sort_index()
            df_fac.to_parquet(file_path)
    return True


def __save_minute_data(df_1m, month):
    factors = ["OpenPx", "ClosePx", "HighPx", "LowPx", "NumTrades", "TotalVolumeTrade", "TotalValueTrade"]
    df_1m = df_1m[~df_1m["MDDate"].isnull()]
    df_1m = df_1m[["MDDate", "MDTime", "HTSCSecurityID"] + factors]
    df_1m = df_1m.drop_duplicates(subset=["MDDate", "MDTime", "HTSCSecurityID"], keep="last")
    os.makedirs(l3_minute_data_dir, exist_ok=True)
    file_path = os.path.join(l3_minute_data_dir, f"{month}.parquet")
    if not os.path.exists(file_path):
        df_1m = df_1m.sort_values(by=["MDDate", "MDTime", "HTSCSecurityID"])
        df_1m.to_parquet(file_path)
    else:
        df_his = pd.read_parquet(file_path, engine="pyarrow")
        df = pd.concat([df_his, df_1m], ignore_index=True)
        df = df.drop_duplicates(subset=["MDDate", "MDTime", "HTSCSecurityID"], keep="last")
        df = df.sort_values(by=["MDDate", "MDTime", "HTSCSecurityID"])
        df.to_parquet(file_path)

    return True

def save_minute_data(start_date, end_date):
    date_list = s.tradingday(start_date, end_date)
    if not date_list:
        raise Exception("在日期{0}~{1}之间没有交易日".format(start_date, end_date))
    per_month_dates = {}
    for i in date_list:
        if i[:6] not in per_month_dates:
            per_month_dates[i[:6]] = [i]
        else:
            per_month_dates[i[:6]].append(i)

    for month, date_list_month in per_month_dates.items():
        stock_list = s.hset('MARKET', date_list_month[-1], 'ALLA_HIS')['stock'].tolist()
        # stock_list = ["600060.SH"]
        df_1m_list = []
        for stock in stock_list:
            try:
                df_1m_p = get_sample_kline1m_data(symbol=stock, date_list=date_list_month)
                df_1m_list.append(df_1m_p)
            except:
                print(f"stock:{stock} 计算失败！")
        if df_1m_list:
            df_1m = pd.concat(df_1m_list)
            __save_minute_data(df_1m, month)


if __name__ == '__main__':
    today_date = datetime.datetime.now().strftime("%Y%m%d")
    calc_date = s.tradingday(today_date, -2)[-2]
    # print(today_date)
    # print(calc_date)
    start_date = "20250301"
    end_date = "20250331"
    save_minute_data(start_date=calc_date, end_date=calc_date)



