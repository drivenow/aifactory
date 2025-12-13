# -*- coding:utf-8 -*-
import datetime
import numpy as np
import pandas as pd


def str2time(strdate):
    """
    时间字符串格式化
    :param str: 时间字符串
    :return: 日期
    """
    Time = datetime.datetime.strptime(strdate[0:-3], "%H%M%S").time()
    return Time


def strlst2lst(s):
    return np.array(s)


def str2date(str):
    try:
        Date = datetime.datetime.strptime(str, "%Y%m%d").date()
    except:
        Date = datetime.datetime.strptime(str, "%Y/%m/%d").date()
    return Date


def price_crafting(prices):
    price_craft = []
    for price in prices:
        price_craft.append(price)
    return price_craft


def precross_data_from_tquant(df_tick, security_type):
    if df_tick.empty:
        return df_tick

    def transpose_to_list(BuyPriceQueue: list):
        BuyPriceQueue = np.array(BuyPriceQueue)
        BuyPriceQueue = BuyPriceQueue.transpose()
        BuyPriceQueue = BuyPriceQueue.astype(int)
        return BuyPriceQueue.tolist()

    def split_detail(detailinfo):
        if len(detailinfo) <= 2:
            return [0]
        else:
            temp = detailinfo[1:-1].split('|')
            ans = [float(num) for num in temp]
            ans = [int(num) for num in ans]
            return ans

    # 只看当天交易阶段
    df_new = df_tick
    df_new = df_new[df_new['TradingPhaseCode'] == '3']
    df_new.reset_index(drop=True, inplace=True)
    if df_new.empty:
        return df_new

    columns = ['HTSCSecurityID', 'MDDate', 'MDTime', 'TradingPhaseCode', 'securityIDSource', 'securityType',
               'MaxPx',
               'MinPx',
               'PreClosePx', 'NumTrades', 'TotalVolumeTrade', 'TotalValueTrade', 'LastPx', 'OpenPx', 'ClosePx',
               'HighPx', 'LowPx',
               'DiffPx1', 'DiffPx2', 'TotalBuyQty', 'TotalSellQty', 'WeightedAvgBuyPx', 'WeightedAvgSellPx',
               'WithdrawBuyNumber',
               'WithdrawBuyAmount', 'WithdrawBuyMoney', 'WithdrawSellNumber', 'WithdrawSellAmount',
               'WithdrawSellMoney',
               'TotalBuyNumber', 'TotalSellNumber', 'BuyTradeMaxDuration', 'SellTradeMaxDuration', 'NumBuyOrders',
               'NumSellOrders', 'PurchaseNumber', 'PurchaseAmount', 'PurchaseMoney',
               'RedemptionNumber',
               'RedemptionAmount', 'RedemptionMoney', 'BuyPriceQueue', 'BuyOrderQtyQueue', 'SellPriceQueue',
               'SellOrderQtyQueue',
               'BuyOrderQueue', 'SellOrderQueue', 'BuyNumOrdersQueue', 'SellNumOrdersQueue']
    tmp_columns = []
    if security_type.upper() == "FUND":
        tmp_columns = ['IOPV', 'PreIOPV']
    columns = columns + tmp_columns

    BuyPriceQueue = []
    BuyOrderQtyQueue = []
    BuyNumOrdersQueue = []
    SellPriceQueue = []
    SellOrderQtyQueue = []
    SellNumOrdersQueue = []

    # 10档行情
    for i in range(1, 11):
        BuyPriceQueue.append(df_new['Buy{}Price'.format(i)].values * 10000)
        BuyOrderQtyQueue.append(df_new['Buy{}OrderQty'.format(i)])
        BuyNumOrdersQueue.append(df_new['Buy{}NumOrders'.format(i)])

        SellPriceQueue.append(
            df_new['Sell{}Price'.format(i)].values * 10000)
        SellOrderQtyQueue.append(df_new['Sell{}OrderQty'.format(i)])
        SellNumOrdersQueue.append(df_new['Sell{}NumOrders'.format(i)])

    df_new = df_new.copy()
    df_new['BuyPriceQueue'] = transpose_to_list(BuyPriceQueue)
    df_new['BuyOrderQtyQueue'] = transpose_to_list(BuyOrderQtyQueue)
    df_new['BuyNumOrdersQueue'] = transpose_to_list(BuyNumOrdersQueue)
    df_new['SellPriceQueue'] = transpose_to_list(SellPriceQueue)
    df_new['SellOrderQtyQueue'] = transpose_to_list(SellOrderQtyQueue)
    df_new['SellNumOrdersQueue'] = transpose_to_list(SellNumOrdersQueue)

    df_new[['LastPx', 'OpenPx', 'ClosePx', 'HighPx', 'LowPx',
            'DiffPx1', 'DiffPx2', 'MaxPx', 'MinPx']] *= 10000
    df_new[['WeightedAvgBidPx', 'WeightedAvgOfferPx']] *= 10000
    if security_type.upper() == "FUND":
        df_new[['IOPV', 'PreIOPV', 'PreClosePx']] *= 10000
    else:
        df_new[['PreClosePx']] *= 10000

    df_new['BuyOrderQueue'] = df_new['Buy1OrderDetail'].apply(split_detail)
    df_new['SellOrderQueue'] = df_new['Sell1OrderDetail'].apply(
        split_detail)
    df_new.rename(columns={'TotalBidQty': 'TotalBuyQty',
                           'TotalOfferQty': 'TotalSellQty',
                           'WeightedAvgBidPx': 'WeightedAvgBuyPx',
                           'WeightedAvgOfferPx': 'WeightedAvgSellPx',
                           'TotalBidNumber': 'TotalBuyNumber',
                           'TotalOfferNumber': 'TotalSellNumber',
                           'BidTradeMaxDuration': 'BuyTradeMaxDuration',
                           'OfferTradeMaxDuration': 'SellTradeMaxDuration',
                           'SecurityIDSource': 'securityIDSource',
                           'SecurityType': 'securityType',
                           }, inplace=True)
    df_save = pd.DataFrame(df_new, columns=columns)
    return df_save


def sample_data_aux(cur_df, sample_period, security_type):
    # Step 1 保留时间信息
    cur_df['MDDate'] = cur_df['MDDate'].apply(str2date)
    cur_df['MDTime'] = cur_df['MDTime'].apply(str2time)
    cur_df['DateTime'] = cur_df.apply(lambda x: datetime.datetime.combine(x['MDDate'], x['MDTime']),
                                      axis=1)  # 结合MDTime与DateTime
    # Step 2 先把从Tquant里补齐的数据全部去掉。
    cur_df.set_index(['DateTime'], drop=True, inplace=True)
    # cur_df = cur_df[~cur_df.index.duplicated(keep='first')]
    # step3 价格还原
    # 实盘数据不需要
    # sell_columns = ['Sell1Price','Sell2Price','Sell3Price','Sell4Price','Sell5Price','Sell6Price','Sell7Price','Sell8Price','Sell9Price','Sell10Price']
    # buy_columns = ['Buy1Price','Buy2Price','Buy3Price','Buy4Price','Buy5Price','Buy6Price','Buy7Price','Buy8Price','Buy9Price','Buy10Price']
    # sell_price = pd.DataFrame(cur_df, columns = sell_columns)
    # buy_price = pd.DataFrame(cur_df, columns = buy_columns)
    # cur_df['BuyPriceQueue'] = buy_price.apply(price_crafting)
    r = 10000
    cur_df['BuyPriceQueue'] = cur_df['BuyPriceQueue'].map(
        strlst2lst) / r
    cur_df['SellPriceQueue'] = cur_df['SellPriceQueue'].map(
        strlst2lst) / r
    cur_df['BuyOrderQtyQueue'] = cur_df['BuyOrderQtyQueue'].map(
        strlst2lst)
    cur_df['SellOrderQtyQueue'] = cur_df['SellOrderQtyQueue'].map(
        strlst2lst)

    # cur_df.to_csv("cur_df4.csv")
    buy_px1 = cur_df['BuyPriceQueue'].apply(lambda x: x[0])
    sell_px1 = cur_df['SellPriceQueue'].apply(lambda x: x[0])
    cur_df['mid_price'] = (buy_px1 + sell_px1) / 2
    cur_df['MaxPx'] = cur_df['MaxPx'] / r
    cur_df['MinPx'] = cur_df['MinPx'] / r
    cur_df['PreClosePx'] = cur_df['PreClosePx'] / r
    cur_df['LastPx'] = cur_df['LastPx'] / r
    cur_df['OpenPx'] = cur_df['OpenPx'] / r
    # cur_df['ClosePx'] = cur_df['ClosePx'] / r
    cur_df['HighPx'] = cur_df['HighPx'] / r
    cur_df['LowPx'] = cur_df['LowPx'] / r
    cur_df['WeightedAvgBuyPx'] = cur_df['WeightedAvgBuyPx'] / r
    cur_df['WeightedAvgSellPx'] = cur_df['WeightedAvgSellPx'] / r

    # cur_df['PreIOPV'] = cur_df['PreIOPV'] / r

    # Step4  重写OpenPx, ClosePx, HighPx, LowPx，
    #        构造Twap, IntervalHigh, IntervalLow
    #        构造SellVol, BuyVol
    #        构造Volume, Turnover
    """ 
    注意0：HighPx_{t} = max(LastPx_{t}),  
           LowPx_{t}=min(LastPx_{t}),
           where t = [0, t] 
    注意1：IntervalHighPx, IntervalLowPx采样区间内的最高价、最低价
           IntervalHighPx_{t} = max(LastPx_{t}),  
           IntervalLowPx{t}=min(LastPx_{t}),  
           where t = [0, t+T] 
    注意2：改写过后的OpenPx, ClosePx为采样区间内的开盘、收盘价
    """
    cur_df['IntervalOpenPx'] = cur_df['LastPx']
    cur_df['IntervalClosePx'] = cur_df['LastPx']
    cur_df['IntervalHighPx'] = cur_df['LastPx']
    cur_df['IntervalLowPx'] = cur_df['LastPx']
    cur_df['Twap'] = cur_df['LastPx']
    cur_df['SellVol'] = cur_df.apply(lambda x: np.sum(x['SellOrderQtyQueue']), axis=1)
    cur_df['BuyVol'] = cur_df.apply(lambda x: np.sum(x['BuyOrderQtyQueue']), axis=1)
    cur_df['VolumeTrade'] = cur_df['TotalVolumeTrade'].diff(1)
    cur_df['ValueTrade'] = cur_df['TotalValueTrade'].diff(1)

    # step5 构造采样的字典
    how_method_dict = {
        # 'HTSCSecurityID': 'last',
        'MDDate': 'last',
        'MDTime': 'last',
        'MaxPx': 'last',
        'MinPx': 'last',
        'PreClosePx': 'last',
        'TotalVolumeTrade': 'last',
        'TotalValueTrade': 'last',
        'VolumeTrade': 'sum',
        'ValueTrade': 'sum',
        'LastPx': 'last',
        'OpenPx': 'last',
        # 'ClosePx': 'last',
        'HighPx': 'last',
        'LowPx': 'last',
        'mid_price': 'last',
        'IntervalOpenPx': 'first',
        'IntervalClosePx': 'last',
        'IntervalHighPx': 'max',
        'IntervalLowPx': 'min',
        'TotalBuyQty': 'sum',
        'TotalSellQty': 'sum',
        'WeightedAvgBuyPx': 'last',  # ??? 应该加权重构
        'WeightedAvgSellPx': 'last',  # ??? 应该加权重构
        # # 'PreIOPV': 'last',
        'BuyPriceQueue': 'last',
        'BuyOrderQtyQueue': 'last',
        'SellPriceQueue': 'last',
        'SellOrderQtyQueue': 'last',
        'SellVol': 'sum',
        'BuyVol': 'sum',
        'Twap': 'mean',
    }

    if security_type.upper() == "FUND":
        cur_df['IOPV'] = cur_df['IOPV'] / r
        how_method_dict['IOPV'] = 'last'
    # step6 重采样, 需要将array转为list，才可以进行降采样
    cur_df['BuyPriceQueue'] = cur_df.apply(lambda x: x['BuyPriceQueue'].tolist(), axis=1)
    cur_df['SellPriceQueue'] = cur_df.apply(lambda x: x['SellPriceQueue'].tolist(), axis=1)
    cur_df['BuyOrderQtyQueue'] = cur_df.apply(lambda x: x['BuyOrderQtyQueue'].tolist(), axis=1)
    cur_df['SellOrderQtyQueue'] = cur_df.apply(lambda x: x['SellOrderQtyQueue'].tolist(), axis=1)

    # step7 重采样
    df_resample = cur_df.resample(rule=str(sample_period) + 's', closed='left', label='right').agg(
        how_method_dict)
    if df_resample.empty:
        return df_resample
    # step8 选择交易时间段上的数据
    df_resample['MDTime'] = df_resample.index.to_series().apply(lambda x: x.strftime('%H%M%S%f')[:9])
    df_resample['MDDate'] = df_resample.index.to_series().apply(lambda x: x.strftime('%Y%m%d'))

    df_result = df_resample

    # step9 填充NA, 不同NA的fill方式: sum 形式的NA用0代替，其他时间截面上的NA数据padding
    df_result[['VolumeTrade', 'ValueTrade', 'TotalBuyQty', 'TotalSellQty', 'SellVol', 'BuyVol']] = \
        df_result[['VolumeTrade', 'ValueTrade', 'TotalBuyQty', 'TotalSellQty', 'SellVol', 'BuyVol']].fillna(0)
    df_result.fillna(method='ffill', inplace=True)
    df_result = df_resample.loc[
        ((df_resample["MDTime"] >= '093000000') & (df_resample["MDTime"] <= '113000000'))
        | ((df_resample["MDTime"] >= '130000000') & (df_resample["MDTime"] <= '150000000'))
        ]

    # step10 把list再次转成array
    df_result = df_result.copy()
    df_result['BuyPriceQueue'] = df_result.apply(lambda x: np.array(x['BuyPriceQueue']), axis=1)
    df_result['SellPriceQueue'] = df_result.apply(lambda x: np.array(x['SellPriceQueue']), axis=1)
    df_result['BuyOrderQtyQueue'] = df_result.apply(lambda x: np.array(x['BuyOrderQtyQueue']), axis=1)
    df_result['SellOrderQtyQueue'] = df_result.apply(lambda x: np.array(x['SellOrderQtyQueue']), axis=1)

    # step11 去掉不需要的列
    # try:
    #     df_result = df_result.drop(['Unnamed: 0', 'MDDate', 'MDTime'], axis=1)
    # except:
    #     df_result = df_result.drop(['MDDate', 'MDTime'], axis=1)

    # step12 再次过滤掉lastpx为0的地方 -- (Tquant上的原始数据有误
    # ，由于inf导致TA-lib中rolling window的计算出现一整列nan)
    # LastPx_invalid_rows = list(df_result[df_result['LastPx'] == 0].index)
    # df_result = df_result.drop(LastPx_invalid_rows)

    # Done
    df_result = df_result.reset_index()
    df_result.set_index(['DateTime'], drop=True, inplace=True)
    return df_result


def realtime_data_aux(cur_df, sample_period, security_type):
    date_arr = np.core.defchararray.add(cur_df["MDDate"].values.astype(int).astype(str),
                                        cur_df["MDTime"].values.astype(int).astype(str))

    cur_df['DateTime'] = pd.DataFrame(date_arr, index=cur_df.index)
    cur_df['DateTime'] = cur_df['DateTime'].apply(lambda x: datetime.datetime.strptime(x[:-3], "%Y%m%d%H%M%S"))
    cur_df = cur_df.sort_index()
    cur_df.set_index(['DateTime'], drop=True, inplace=True)
    # Step 1 保留时间信息
    resample_sample_period = sample_period

    r = 10000
    cur_df['BuyPriceQueue'] = cur_df['BuyPriceQueue'].map(
        lambda x: [int(ix) / r for ix in x])
    cur_df['SellPriceQueue'] = cur_df['SellPriceQueue'].map(
        lambda x: [int(ix) / r for ix in x])
    cur_df['BuyOrderQtyQueue'] = cur_df['BuyOrderQtyQueue'].map(
        lambda x: [int(ix) for ix in x])
    cur_df['SellOrderQtyQueue'] = cur_df['SellOrderQtyQueue'].map(
        lambda x: [int(ix) for ix in x])
    # 无BuyPriceQueue时，十档为0
    buy_px1 = cur_df['BuyPriceQueue'].apply(lambda x: x[0])
    sell_px1 = cur_df['SellPriceQueue'].apply(lambda x: x[0])
    cur_df['mid_price'] = (buy_px1 + sell_px1) / 2

    cur_df['MaxPx'] = cur_df['MaxPx'] / r
    cur_df['MinPx'] = cur_df['MinPx'] / r
    cur_df['PreClosePx'] = cur_df['PreClosePx'] / r
    cur_df['LastPx'] = cur_df['LastPx'] / r
    cur_df['OpenPx'] = cur_df['OpenPx'] / r
    # cur_df['ClosePx'] = cur_df['ClosePx'] / r
    cur_df['HighPx'] = cur_df['HighPx'] / r
    cur_df['LowPx'] = cur_df['LowPx'] / r
    cur_df['WeightedAvgBuyPx'] = cur_df['WeightedAvgBuyPx'] / r
    cur_df['WeightedAvgSellPx'] = cur_df['WeightedAvgSellPx'] / r

    cur_df['IntervalOpenPx'] = cur_df['LastPx']
    cur_df['IntervalClosePx'] = cur_df['LastPx']
    cur_df['IntervalHighPx'] = cur_df['LastPx']
    cur_df['IntervalLowPx'] = cur_df['LastPx']
    cur_df['Twap'] = cur_df['LastPx']
    cur_df['SellVol'] = cur_df.apply(lambda x: np.sum(x['SellOrderQtyQueue']), axis=1)
    cur_df['BuyVol'] = cur_df.apply(lambda x: np.sum(x['BuyOrderQtyQueue']), axis=1)
    cur_df['VolumeTrade'] = cur_df['TotalVolumeTrade'].diff(1)
    cur_df['ValueTrade'] = cur_df['TotalValueTrade'].diff(1)

    # cur_df['IOPV'] = cur_df['IOPV'] / r
    # cur_df.to_csv("cur_df5.csv")

    # step5 构造采样的字典
    how_method_dict = {
        'HTSCSecurityID': 'last',
        'MDDate': 'last',
        'MaxPx': 'last',
        'MinPx': 'last',
        'PreClosePx': 'last',
        'TotalVolumeTrade': 'last',
        'TotalValueTrade': 'last',
        'VolumeTrade': 'sum',
        'ValueTrade': 'sum',
        'LastPx': 'last',
        'OpenPx': 'last',
        # 'ClosePx': 'last',
        'HighPx': 'last',
        'LowPx': 'last',
        'mid_price': 'last',
        'IntervalOpenPx': 'first',
        'IntervalClosePx': 'last',
        'IntervalHighPx': 'max',
        'IntervalLowPx': 'min',
        'TotalBuyQty': 'sum',
        'TotalSellQty': 'sum',
        'WeightedAvgBuyPx': 'last',  # ??? 应该加权重构
        'WeightedAvgSellPx': 'last',  # ??? 应该加权重构
        # 'IOPV': 'last',
        # # 'PreIOPV': 'last',
        'BuyPriceQueue': 'last',
        'BuyOrderQtyQueue': 'last',
        'SellPriceQueue': 'last',
        'SellOrderQtyQueue': 'last',
        'SellVol': 'sum',
        'BuyVol': 'sum',
        'Twap': 'mean',
    }

    if security_type == "FUND":
        cur_df['IOPV'] = cur_df['IOPV'] / r
        how_method_dict['IOPV'] = 'last'

    # step7 重采样
    # how 执行不了，就用agg.()
    try:
        df_resample = cur_df.resample(rule="{}S".format(resample_sample_period), closed='left',
                                      label='right').agg(how_method_dict)
    except:
        df_resample = cur_df.resample(rule="{}S".format(resample_sample_period), closed='left',
                                      label='right', how=how_method_dict)

    # step8 选择交易时间段上的数据
    df_resample['MDTime'] = df_resample.index.to_series().apply(lambda x: x.strftime('%H%M%S%f')[:9])

    df_result = df_resample.loc[
        ((df_resample["MDTime"] >= '093000000') & (df_resample["MDTime"] <= '113000000'))
        | ((df_resample["MDTime"] >= '130000000') & (df_resample["MDTime"] <= '150000000'))
        ]
    if df_result.empty:
        return df_result
    df_result[['VolumeTrade', 'ValueTrade', 'TotalBuyQty', 'TotalSellQty', 'SellVol', 'BuyVol']] = \
        df_result[['VolumeTrade', 'ValueTrade', 'TotalBuyQty', 'TotalSellQty', 'SellVol', 'BuyVol']].fillna(0)
    df_result.fillna(method='ffill', inplace=True)

    df_result['BuyPriceQueue'] = df_result.apply(lambda x: np.array(x['BuyPriceQueue']), axis=1)
    df_result['SellPriceQueue'] = df_result.apply(lambda x: np.array(x['SellPriceQueue']), axis=1)
    df_result['BuyOrderQtyQueue'] = df_result.apply(lambda x: np.array(x['BuyOrderQtyQueue']), axis=1)
    df_result['SellOrderQtyQueue'] = df_result.apply(lambda x: np.array(x['SellOrderQtyQueue']), axis=1)

    df_result = df_result.reset_index()
    df_result.set_index(['DateTime'], drop=True, inplace=True)
    return df_result


def sample_transaction_data_aux(df, sample_period):
    def get_std(array_like):
        return np.std(array_like)

    def get_mean(array_like):
        return np.mean(array_like)

    def get_squared_sum(array_like):
        return sum([i ** 2 for i in array_like])

    def get_outlier_sum(array_like):
        k = 1.96
        threshold = np.mean(array_like) + k * np.std(array_like)
        outlier = []
        for i in array_like:
            if i >= threshold:
                outlier.append(i)
        return sum(outlier)

    def get_quantile_1_8(x):
        return x.quantile(0.125)

    def get_quantile_7_8(x):
        return x.quantile(0.875)

        # 降采样字典

    df['aux_count'] = 1
    how_method_dict = {
        'TradeMoney': ['std', 'mean', 'sum', get_outlier_sum, get_squared_sum],
        'TradeQty': ['std', 'mean', 'sum', get_outlier_sum, get_squared_sum],
        'aux_count': 'sum'
    }
    # Step 1 保留时间信息
    df = df.copy()
    try:
        df_resample = df.resample(rule=str(sample_period) + "s", closed='left', label='right').agg(how_method_dict)
    except:
        df_resample = df.resample(rule=str(sample_period) + "s", how=how_method_dict, closed='left', label='right')
    if df_resample.empty:
        return df_resample

    # step8 选择交易时间段上的数据
    df_resample['MDTime'] = df_resample.index.to_series().apply(lambda x: x.strftime('%H%M%S%f')[:9])
    df_resample['MDDate'] = df_resample.index.to_series().apply(lambda x: x.strftime('%Y%m%d'))

    if list(set(df['HTSCSecurityID']))[0][-2:] == 'SH':
        df_result = df_resample.loc[
            ((df_resample['MDTime'] >= '093000000') & (df_resample['MDTime'] <= '113000000')) | \
            ((df_resample['MDTime'] >= '130000000') & (df_resample['MDTime'] <= '150000000'))]
    else:
        df_result = df_resample.loc[
            ((df_resample['MDTime'] >= '093000000') & (df_resample['MDTime'] <= '113000000')) | \
            ((df_resample['MDTime'] >= '130000000') & (df_resample['MDTime'] <= '145700000'))]
    return df_result


def sample_transaction_data(df, sample_period):
    date_arr = np.core.defchararray.add(df["MDDate"].values.astype(int).astype(str),
                                        df["MDTime"].values.astype(int).astype(str))
    df = df.copy()
    df['DateTime'] = pd.DataFrame(date_arr, index=df.index)
    df['DateTime'] = df['DateTime'].apply(lambda x: datetime.datetime.strptime(x[:-3], "%Y%m%d%H%M%S"))
    df.set_index(['DateTime'], drop=True, inplace=True)

    if 'TradeType' not in df.columns:
        df['TradeType'] = 0
    df['TradeType'].fillna(0, inplace=True)
    df_buy_deal = df.loc[(df['TradeType'] == 0) & (df['TradeBSFlag'] == 1)].reindex(
        columns=["MDDate", "MDTime", "TradeMoney", "TradeQty", "HTSCSecurityID"])
    df_sell_deal = df.loc[(df['TradeType'] == 0) & (df['TradeBSFlag'] == 2)].reindex(
        columns=["MDDate", "MDTime", "TradeMoney", "TradeQty", "HTSCSecurityID"])
    df_buy_deal = df_buy_deal.sort_index()
    df_sell_deal = df_sell_deal.sort_index()
    df_buy_deal = sample_transaction_data_aux(df_buy_deal, sample_period)
    df_buy_deal.rename(columns={"TradeMoney": "BuyMoney", "TradeQty": "BuyQty", "aux_count": "buy_aux_count"},
                       inplace=True)
    if not df_buy_deal.empty:
        df_buy_deal.drop(columns=["MDDate", "MDTime"], inplace=True)

    df_sell_deal = sample_transaction_data_aux(df_sell_deal, sample_period)
    df_sell_deal.rename(columns={"TradeMoney": "SellMoney", "TradeQty": "SellQty", "aux_count": "sell_aux_count"},
                        inplace=True)
    if not df_sell_deal.empty:
        df_sell_deal.drop(columns=["MDDate", "MDTime"], inplace=True)

    df = df_buy_deal.merge(df_sell_deal, how="outer", left_index=True, right_index=True, copy=False)
    # 防止Buy和Sell数据分开后，中间时间段的数据没采样到
    if not df.empty:
        start_time = df.index[0]
        end_time = df.index[-1]
        complete_time = []
        while start_time <= end_time:
            complete_time.append(start_time)
            start_time = start_time + datetime.timedelta(
                seconds=sample_period)
        df = df.reindex(complete_time)

    df['MDTime'] = df.index.to_series().apply(lambda x: x.strftime('%H%M%S%f')[:9])
    df['MDDate'] = df.index.to_series().apply(lambda x: x.strftime('%Y%m%d'))
    df.fillna(value=0, inplace=True)
    return df


def sample_orderbook(df_raw, sample_period):
    def sample_order_data(df, sample_period):
        how_method_dict = {'OrderQty': 'sum', 'OrderMoney': 'sum',
                           'NumTrades': 'sum', }
        # Step 1 保留时间信息
        df = df.copy()
        try:
            df_resample = df.resample(rule=str(sample_period) + "s", closed='left', label='right').agg(
                how_method_dict)
        except:
            df_resample = df.resample(rule=str(sample_period) + "s", how=how_method_dict, closed='left', label='right')
        if df_resample.empty:
            return df_resample

        # step8 选择交易时间段上的数据
        df_resample['MDTime'] = df_resample.index.to_series().apply(
            lambda x: x.strftime('%H%M%S%f')[:9])
        df_resample['MDDate'] = df_resample.index.to_series().apply(
            lambda x: x.strftime('%Y%m%d'))

        if list(set(df['HTSCSecurityID']))[0][-2:] == 'SH':
            df_result = df_resample.loc[((df_resample[
                                              'MDTime'] >= '093000000') & (
                                                 df_resample[
                                                     'MDTime'] <= '113000000')) | (
                                                (df_resample[
                                                     'MDTime'] >= '130000000') & (
                                                        df_resample[
                                                            'MDTime'] <= '150000000'))]
        else:
            df_result = df_resample.loc[((df_resample[
                                              'MDTime'] >= '093000000') & (
                                                 df_resample[
                                                     'MDTime'] <= '113000000')) | (
                                                (df_resample[
                                                     'MDTime'] >= '130000000') & (
                                                        df_resample[
                                                            'MDTime'] <= '145700000'))]
        df_result.fillna(value=0, inplace=True)
        return df_result

    keepcol = ['MDDate', 'MDTime', 'HTSCSecurityID', 'OrderIndex', 'OrderType',
               'OrderPrice', 'OrderQty', 'OrderBSFlag']
    df_raw = df_raw.copy()
    df_raw = df_raw[keepcol]
    date_arr = np.core.defchararray.add(
        df_raw["MDDate"].values.astype(int).astype(str),
        df_raw["MDTime"].values.astype(int).astype(str))

    df_raw['DateTime'] = pd.DataFrame(date_arr, index=df_raw.index)
    df_raw['DateTime'] = df_raw['DateTime'].apply(
        lambda x: datetime.datetime.strptime(x[:-3], "%Y%m%d%H%M%S"))
    df_raw.set_index(['DateTime'], drop=True, inplace=True)
    df_raw['NumTrades'] = 1
    df_raw['OrderMoney'] = df_raw['OrderQty'] * df_raw['OrderPrice']
    df_buy_deal = df_raw.loc[
                  (df_raw['OrderType'] != 10) & (df_raw['OrderBSFlag'] == 1),
                  :]
    df_sell_deal = df_raw.loc[
                   (df_raw['OrderType'] != 10) & (df_raw['OrderBSFlag'] == 2),
                   :]

    df_buy_deal = sample_order_data(df_buy_deal, sample_period)
    df_buy_deal.rename(columns={"OrderMoney": "BuyMoney", "OrderQty": "BuyQty",
                                "NumTrades": "BuyNumTrades", }, inplace=True)
    if not df_buy_deal.empty:
        df_buy_deal.drop(columns=["MDDate", "MDTime"], inplace=True)

    df_sell_deal = sample_order_data(df_sell_deal, sample_period)
    df_sell_deal.rename(
        columns={"OrderMoney": "SellMoney", "OrderQty": "SellQty",
                 "NumTrades": "SellNumTrades", }, inplace=True)
    if not df_sell_deal.empty:
        df_sell_deal.drop(columns=["MDDate", "MDTime"], inplace=True)

    # todo should fillna after concat
    df = df_buy_deal.merge(df_sell_deal, how="outer", left_index=True,
                           right_index=True, copy=False)
    df.fillna(value=0, inplace=True)
    df['MDTime'] = df.index.to_series().apply(
        lambda x: x.strftime('%H%M%S%f')[:9])
    df['MDDate'] = df.index.to_series().apply(lambda x: x.strftime('%Y%m%d'))
    return df
