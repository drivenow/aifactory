import json
import os
import sys
import re
import calendar
import configparser
from os import path
from datetime import datetime, timedelta
from threading import current_thread
import polars as pl
import numpy as np
import pandas as pd
from retrying import retry
from tqdm import trange
from pyarrow import hdfs
from fastparquet import ParquetFile
from MDCDataProvider.setEnv import sysFlag, xquantEnv
from MDCDataProvider.utils import get_dataprovider_ini
from MDCDataProvider.utils import is_valid_date, sample_kline
from MDCDataProvider import xq_logger
import pyarrow


class MDCStockDataDP:
    def __init__(self):
        self.dp = MDCDataProviderPL()

    def get_stock_data(self, symbol, start_time, end_time, bar_size, trading_phase_code=[]):
        """
        获取股票行情数据
        :param symbol: 股票代码, string类型, 如'123021.SZ'
        :param start_time:起始日期,string类型，如'20190102 000000000'
        :param end_time:终止日期，string类型，如'20190102 235900000'
        :param bar_size:数据周期枚举类，支持Stock, Order, Transaction, Kline1M4ZT, KLINE5M4ZT, KLINE10M4ZT, KLINE60M4ZT
        :return:
        """
        start_time = str(start_time)
        end_time = str(end_time)
        try:
            is_valid_date(start_time, end_time)
        except Exception as e:
            raise e
        bar_size = bar_size.upper()
        
    
        if bar_size == 'STOCK':
            trading_phase_code = [str(code) for code in trading_phase_code]
            df = self.dp.get_data_by_time_frame("stocktick", symbol, start_time,
                                                end_time, trading_phase_code=trading_phase_code)
        elif bar_size == 'ORDER':
            df = self.dp.get_data_by_time_frame(
                "stockorder", symbol, start_time, end_time)
        elif bar_size == 'TRANSACTION':
            df = self.dp.get_data_by_time_frame("stocktransaction", symbol,
                                                start_time, end_time)
        elif 'KLINE' in bar_size:
            df = self.dp.get_data_by_time_frame("kline1m4zt", symbol,
                                                start_time, end_time)
            if bar_size == 'KLINE1M4ZT':
                pass
            elif bar_size == 'KLINE5M4ZT':
                df = sample_kline(df, '5min')
            elif bar_size == 'KLINE10M4ZT':
                df = sample_kline(df, '10min')
            elif bar_size == 'KLINE60M4ZT':
                df = sample_kline(df, '60min')
            else:
                raise Exception("【bar_size参数】暂时只支持支持Stock, Order, Transaction,"
                                " Kline1M4ZT, KLINE5M4ZT, KLINE10M4ZT, KLINE60M4ZT请重新输入！")
        else:
            raise Exception(
                "【bar_size参数】暂时只支持支持Stock, Order, Transaction,"
                " Kline1M4ZT, KLINE5M4ZT, KLINE10M4ZT, KLINE60M4ZT请重新输入！")
    
        return df


hdfsDict = {}
hbase_tables = [
    'STOCKTICK', 'INDEX', 'STOCKTRANSACTION', 'STOCKORDER', 'KLINE1M4ZT',
    'ENHANCEDKLINE1M', 'BONDTICK', 'FUTURETICK', 'FUTUREKLINE1M', 'FUTUREKLINE1D',
    'FUNDTICK', 'BONDKLINE1M', 'BONDKLINE1D', 'FUNDKLINE1M', 'FUNDKLINE1D',
    'BONDTRANSACTION', 'BONDORDER', 'FUNDTRANSACTION', 'FUNDORDER',
    'SWINDEXTICK', 'SWINDEXKLINE1M', 'SWINDEXKLINE1D']

# 新行情类型跟旧行情类型的映射
mdc_to_hbase = {
    'STOCKTICK': 'STOCK',
    'STOCKTRANSACTION': 'TRANSACTION',
    'STOCKORDER': 'ORDER',
    "INDEXTICK": "INDEX",
}


class MDCDataProviderPL:
    def __init__(self, dfs=None):
        if sysFlag == "big_data":
            self.__config = get_dataprovider_ini("mdc")
        else:
            conf_dir = path.join(os.path.dirname(pyarrow.__file__), "../MDCDataProvider/conf")
            conf_path = path.join(conf_dir, "MDCDataProvider.ini")
            self.__config = configparser.ConfigParser()
            self.__config.read(conf_path, encoding="utf-8")

        self.__tmp_dir = self.__config['local']['tmp.dir']
        self.__base_dir = self.__config['hadoop']['base.dir']
        self.__timeframe_max = int(self.__config['task']['timeframe.max'])
        self.__table_names = self.__get_table_names()
        self.__etl_finish_time = int(self.__config['task']['etl.finish.time'])
        self.__hbase_dp = None

        if dfs is None:
            self.__created_by_own = True
            global hdfsDict
            if hdfsDict.get(current_thread().ident) is None:
                os.environ['JAVA_HOME'] = self.__config['hadoop']['java.home']
                os.environ['JAVA_TOOL_OPTIONS'] = '-Xss1280K'
                os.environ['ARROW_LIBHDFS_DIR'] = self.__config['hadoop']['libhdfs.dir']
                os.environ['HADOOP_HOME'] = self.__config['hadoop']['hadoop.home']
                os.environ['HADOOP_CONF_DIR'] = self.__config['hadoop']['hadoop.conf.dir']
                os.environ['YARN_CONF_DIR'] = self.__config['yarn']['yarn.conf.dir']
                hdfsDict[current_thread().ident] = hdfs.connect()
                hdfsDict[str(current_thread().ident) + "_refs"] = 0
            self.dfs = hdfsDict.get(current_thread().ident)
            hdfsDict[str(current_thread().ident) + "_refs"] += 1
        else:
            self.__created_by_own = False
            self.dfs = dfs

    def __del__(self):
        try:
            if self.__created_by_own:
                hdfsDict[str(current_thread().ident) + "_refs"] -= 1
                if hdfsDict[str(current_thread().ident) + "_refs"] <= 0:
                    del hdfsDict[current_thread().ident]
                    del hdfsDict[str(current_thread().ident) + "_refs"]
                    try:
                        self.dfs.close()
                    except Exception:
                        self.dfs = None
        except:
            pass

    def __get_table_names(self):
        hdfs_tables = self.__config['hdfs']
        table_names = {}
        for key, value in hdfs_tables.items():
            _, table_name, exchange_type = key.split('.')
            if not table_name in table_names:
                table_names[table_name] = {}
            table_names[table_name][exchange_type.upper()] = value
        return table_names

    def __check_connect(self):
        try:
            self.dfs.exists('/')
        except Exception as e:
            global hdfsDict
            os.environ['JAVA_HOME'] = self.__config['hadoop']['java.home']
            os.environ['JAVA_TOOL_OPTIONS'] = '-Xss1280K'
            os.environ['ARROW_LIBHDFS_DIR'] = self.__config['hadoop'][
                'libhdfs.dir']
            os.environ['HADOOP_HOME'] = self.__config['hadoop']['hadoop.home']
            os.environ['HADOOP_CONF_DIR'] = self.__config['hadoop'][
                'hadoop.conf.dir']
            os.environ['YARN_CONF_DIR'] = self.__config['yarn'][
                'yarn.conf.dir']
            hdfsDict[current_thread().ident] = hdfs.connect()
            hdfsDict[str(current_thread().ident) + "_refs"] = 0
            self.dfs = hdfsDict.get(current_thread().ident)
            hdfsDict[str(current_thread().ident) + "_refs"] += 1
            self.__created_by_own = True
            raise Exception('hdfs连接创建失败:{}'.format(repr(e)))

    def __check_time_format(self, time_str):
        mat = re.search(r"(\d{8}\s\d{9})", time_str)
        if not mat:
            raise Exception("Illegal time format {}.".format(time_str))

    def __get_table_name(self, table_type, security_id=None, security_type=None):
        if table_type not in self.__table_names:
            raise Exception(
                '表类型{}不存在'.format(table_type))
        if not security_type:
            if not security_id:
                raise Exception('必须传入security_id')
            security_type = security_id.split('.')[-1]
        table_name = self.__table_names[table_type].get(security_type)
        if not table_name:
            raise Exception('表类型{}不包含该标的类型{}'.format(
                table_type, security_type))
        return table_name

    def __str2time(self, time_str):
        """
        Transfer time string to datetime
        :param time_str:    time string shaped as %Y-%m-%d %H:%M:%S.%f
        :return:            datetime
        """
        return datetime.strptime(time_str, "%Y%m%d %H%M%S%f")

    def __isTick(self, table_type):
        # MDC配置文件中股票Tick数据为stocktick
        table_type_tmp = table_type.upper()
        return table_type_tmp == "STOCK" or "TICK" in table_type_tmp

    def __get_diff_days(self, start_time, end_time):
        return (end_time - start_time).days

    def __get_year_month(self, date_time):
        return format(date_time.year, '04d') + format(date_time.month, '02d')

    def __get_md_date(self, date_time):
        return format(date_time.year, '04d') + format(date_time.month, '02d') + format(date_time.day, '02d')

    def __get_md_time(self, date_time):
        return format(date_time.hour, '02d') + format(date_time.minute, '02d') + \
               format(date_time.second, '02d') + format(int(date_time.microsecond / 1000), '03d')

    def __add_one_month(self, year_month):
        year = int(year_month[:4])
        month = int(year_month[-2:])
        month += 1
        if month == 13:
            month = 1
            year += 1
        return format(year, "04d") + format(month, "02d")

    def __get_days_of_month(self, year, month):
        return calendar.monthrange(year, month)[1]

    def __fetch_dir(self, src_dir, security_id):
        xq_logger.debug('fetch文件路径：{} '.format(src_dir))
        df = pd.DataFrame()
        if not self.dfs.exists(src_dir):
            return df
        files = [file_path for file_path in self.dfs.ls(src_dir) if security_id in file_path]
        if len(files) == 0:
            return df
        files.sort()
        for f in files:
            df = df.append(self.__fetch_file(f))
        return df

    def __fetch_file(self, src_file):
        xq_logger.debug('fetch文件路径：{} '.format(src_file))
        if not self.dfs.exists(src_file):
            return pd.DataFrame()
        df = pl.from_arrow(self.dfs.read_parquet(src_file))
        xq_logger.debug('原始数据格式： ')
        xq_logger.debug(df.head())
        return df

    def __fetch(self, src_path, data_type='Month', security_id=None):
        """
        Fetch Pandas DataFrame from source file.
        :param :    source file
        :return:            Pandas DataFrame
        """
        if data_type == 'Month':
            df = self.__fetch_file(src_path)
            if len(df) == 0:
                src_path = '/'.join(src_path.split('/')[:-1])
                df = self.__fetch_dir(src_path, security_id)
        else:
            df = self.__fetch_file(src_path)
        # xq_logger.debug('原始数据格式： ')
        # xq_logger.debug(df.head())
        return df

    def __get_data_by_month(self, table_name, security_id, month):
        data_path = os.path.join(self.__base_dir, '{}_Month'.format(table_name),
                                 'month={}'.format(month), '{}_{}_{}.parquet'.format(
                table_name, security_id, month))
        data = self.__fetch(data_path, 'Month', security_id)
        if len(data) == 0 and table_name in ['XSHG_Stock_KLine1Min', 'XSHE_Stock_KLine1Min', 'XSHG_Stock_KLine1D',
                                             'XSHE_Stock_KLine1D']:
            table_name = table_name.replace("Stock", "Index")
            data_path = os.path.join(self.__base_dir, '{}_Month'.format(table_name),
                                     'month={}'.format(month), '{}_{}_{}.parquet'.format(
                    table_name, security_id, month))
            data = self.__fetch(data_path, 'Month', security_id)
        return data

    def __trading_phase_filter(self, df, trading_phase_code=[]):
        if 'TradingPhaseCode' in df.columns:
            df_ret = df.filter(pl.col("TradingPhaseCode").is_in(trading_phase_code)) if trading_phase_code else df
        else:
            try:
                df_ret = df.filter(pl.col("tradingphasecode").is_in(trading_phase_code)) if trading_phase_code else df
            except:
                df_ret = df
        return df_ret

    def __get_data_by_time_frame_in_a_month(self, table_name, security_id, year_month, start_md_date, start_md_time,
                                            end_md_date, end_md_time, trading_phase_code=[]):
        df_month = self.__get_data_by_month(table_name, security_id, year_month)
        if len(df_month):
            if start_md_date == end_md_date:
                data_filter = df_month.filter(
                    (pl.col("MDDate") == start_md_date) & (pl.col("MDTime") >= start_md_time) & (
                                pl.col("MDTime") <= end_md_time))
            else:
                data_filter = df_month.filter(
                    (pl.col("MDDate") == start_md_date) & (pl.col("MDTime") >= start_md_time) |
                    (pl.col("MDDate") > start_md_date) & (pl.col("MDDate") < end_md_date) |
                    (pl.col("MDDate") == end_md_date) & (pl.col("MDTime") <= end_md_time)
                    )
            df_month = data_filter
            return self.__trading_phase_filter(df_month,
                                               trading_phase_code)
        else:
            return pd.DataFrame()


    def __convert_kline_nan(self, df):
        """
        根据KLineCategory字段对部分无成交k线填充nan值
        #20200626#ETL程序更新，对所有k线类型都增加KlineCategory字段，若行情中心无此字段，ETL程序赋值为0.0。
        情况1：业务只需KLine1m4ZT有此字段，只重跑Kline1M4ZT数据，其余k线数据的parquet文件，在20200626前无此字段，之后有次字段
        情况2：若用新ETL补Kline1m4zt历史数据，前后parquet文件格式一致，无问题。
        情况3：若用新ETL其他k线类型某一天历史，生成的parquet文件会多一列KlineCategory字段，在这一天值为0.0,其余天值为nan.
        :return:
        """
        if len(df)==0 or 'KLineCategory' not in df.columns:
            return df
        try:
            # 股票行情填充空值
            def need_nan(kline):
                if isinstance(kline, int) and kline != 0:
                    return True
                return False
            df = df.with_columns(pl.col("KLineCategory").fill_null(0).cast(pl.Int64, strict=False).alias("KLineCategory"))
            df = df.with_columns(pl.when(pl.col("KLineCategory") != 0)  # 判断条件
                                .then(True)  # 如果满足条件，则转换为 True
                                .otherwise(False)  # 否则转换为 False
                                .alias("flag") )
            for col1 in ["OpenPx", "ClosePx", "HighPx", "LowPx", "NumTrades", "TotalVolumeTrade", "TotalValueTrade"]:
                df = df.with_columns(pl.when(pl.col('flag')==True)
                                     .then(None)
                                     .otherwise(pl.col(col1))
                                     .alias(col1))

            df = df.drop(['flag', 'KLineCategory'])
        except Exception as e:
            print(f"An error occurred: {e}")
            pass
        return df


    def __data_transform(self, dataframe, table_type, sort_by_receive_time=False, sort_by_mddate=True):
        # 对部分k线填充nan值
        if table_type.lower() == 'kline1m4zt':
            dataframe = self.__convert_kline_nan(dataframe)
        if 'KLineCategory' in dataframe.columns:
            # 保持返回格式与之前一致
            dataframe = dataframe.drop(['KLineCategory'])
        if 'Sell1OrderDetail' in dataframe.columns:
            dataframe = dataframe.with_columns(pl.col("Sell1OrderDetail").fill_null('[]').cast(pl.Utf8).str.replace(",", "|"))

        if 'Buy1OrderDetail' in dataframe.columns:
            dataframe = dataframe.with_columns(pl.col("Buy1OrderDetail").fill_null('[]').cast(pl.Utf8).str.replace(",", "|"))

        # if not df_month.empty and "CashBondQuotes" in df_month.columns:
        #     df_month = self.__convert_cash_bond_quotes(df_month)

        # 根据表类型转换数据格式
        if "OtcTotalVolumeTrade" in dataframe.columns:
            df_columns = self.__get_columns(table_type, 'hk')
        else:
            df_columns = self.__get_columns(table_type, 'other')
        if df_columns:
            initial_empty_df = dataframe.with_columns(
                pl.Series([0.0 if col_type == pl.Float64 else (0 if col_type == pl.Int32 else None)] * len(dataframe),
                          dtype=col_type).alias(col_name) for col_name, col_type in df_columns.items()
                if col_name not in dataframe.columns)
            # for col_name, col_type in df_columns.items():
            #     # 处理缺失值
            #     if col_type==pl.String:  # 字符串类型
            #         initial_empty_df = initial_empty_df.with_columns(pl.col(col_name).fill_null("None"))
            #     elif col_type==pl.Float64:
            #         initial_empty_df = initial_empty_df.with_columns(pl.col(col_name).fill_null(0.0))
            #     else :
            #         initial_empty_df = initial_empty_df.with_columns(pl.col(col_name).fill_null(0))
        dataframe = initial_empty_df.to_pandas()
        dataframe = dataframe.reindex(columns=df_columns)
        return dataframe



    def get_data_by_time_frame(self, table_type, security_id, start_time_str, end_time_str, trading_phase_code=[],
                               sort_by_receive_time=False):
        """
        :param table_type:   证券类型如"STOCK"
        :param security_id:     股票号如"000001.SH"
        :param start_time_str:  时间如"20180301 220000000"
        :param end_time_str:    时间如"20180303 230000600"
        :param trading_phase_code   过滤出需要的交易阶段代码，默认为空不过滤
        :param sort_by_receive_time 是否按照ReceiveTime字段排序，默认为否不排序
        :return:                Pandas DataFrame
        """
        self.__check_connect()
        if start_time_str > end_time_str:
            raise Exception('开始日期大于结束日期')
        self.__check_time_format(start_time_str)
        self.__check_time_format(end_time_str)
        table_type = table_type.lower()
        table_name = self.__get_table_name(table_type, security_id)

        start_time = self.__str2time(start_time_str)
        end_time = self.__str2time(end_time_str)

        diff_days = self.__get_diff_days(start_time, end_time)
        if diff_days < 0:
            raise Exception("End time must be later than start time.")

        if not self.__isTick(table_type):
            trading_phase_code = []

        current_time = datetime.now()
        standard_time = datetime(current_time.year, current_time.month,
                                 current_time.day, self.__etl_finish_time, 0,
                                 0, 0)
        today = datetime(current_time.year, current_time.month,
                         current_time.day, 0, 0, 0, 0)

        df_today = pd.DataFrame()
        if current_time < standard_time and table_type.upper() in hbase_tables:
            if table_type.upper() in mdc_to_hbase:
                hbase_table_type = mdc_to_hbase[table_type.upper()]
            else:
                hbase_table_type = table_type.upper()
            if today <= start_time:
                raise Exception()
            elif start_time < today < end_time:
                raise Exception()

        start_year_month = self.__get_year_month(start_time)
        end_year_month = self.__get_year_month(end_time)
        start_md_date = self.__get_md_date(start_time)
        start_md_time = self.__get_md_time(start_time)
        end_md_date = self.__get_md_date(end_time)
        end_md_time = self.__get_md_time(end_time)

        cur_year_month = start_year_month
        df_month = pl.DataFrame()
        show_bar = True
        if diff_days > self.__timeframe_max:
            show_bar = False
        loop_times = 0
        loop_year_month = cur_year_month
        while loop_year_month <= end_year_month:
            loop_year_month = self.__add_one_month(loop_year_month)
            loop_times += 1
        for i in trange(loop_times, desc='loading data', disable=True):
            if cur_year_month == start_year_month:
                days_of_month = self.__get_days_of_month(int(cur_year_month[:4]), int(cur_year_month[-2:]))
                if start_year_month != end_year_month:
                    tmp_md_date = cur_year_month + format(days_of_month, '02d')
                    df_part = self.__get_data_by_time_frame_in_a_month(table_name, security_id, cur_year_month,
                                                                       start_md_date, start_md_time, tmp_md_date,
                                                                       "235959999", trading_phase_code)
                else:
                    df_part = self.__get_data_by_time_frame_in_a_month(table_name, security_id, cur_year_month,
                                                                       start_md_date, start_md_time, end_md_date,
                                                                       end_md_time, trading_phase_code)
            elif cur_year_month == end_year_month:
                df_part = self.__get_data_by_time_frame_in_a_month(table_name, security_id, cur_year_month,
                                                                   cur_year_month + "01", "000000000", end_md_date,
                                                                   end_md_time, trading_phase_code)
            else:
                df_part = self.__get_data_by_time_frame_in_a_month(table_name, security_id, cur_year_month,
                                                                   cur_year_month + "01", "000000000",
                                                                   cur_year_month + '31', '235959999',
                                                                   trading_phase_code)
            if not len(df_part) == 0:
                if len(df_month) == 0:
                    df_month = df_part
                else:
                    df_month = pl.concat([df_month, df_part])
            cur_year_month = self.__add_one_month(cur_year_month)

        if not df_today.empty:
            # hbase数据
            df_month = pl.concat([df_month, df_part])
        df_month = self.__data_transform(df_month, table_type, sort_by_receive_time)
        return df_month

    def __get_columns(self, table_type, exchange_house='other'):
        table_type = table_type.lower()
        if table_type == 'indextick':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'PreClosePx': pl.Float64,
                       'TotalVolumeTrade': pl.Float64, 'TotalValueTrade': pl.Float64,
                       'LastPx': pl.Float64, 'OpenPx': pl.Float64, 'ClosePx': pl.Float64,
                       'HighPx': pl.Float64, 'LowPx': pl.Float64, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'ArrivalDateTime': pl.Int32}
        elif table_type == 'stocktick':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'PreClosePx': pl.Float64,
                       'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'LastPx': pl.Float64,
                       'OpenPx': pl.Float64, 'ClosePx': pl.Float64, 'HighPx': pl.Float64,
                       'LowPx': pl.Float64, 'DiffPx1': pl.Float64, 'DiffPx2': pl.Float64,
                       'MaxPx': pl.Float64, 'MinPx': pl.Float64, 'TotalBidQty': pl.Float64,
                       'TotalOfferQty': pl.Float64, 'WeightedAvgBidPx': pl.Float64,
                       'WeightedAvgOfferPx': pl.Float64, 'WithdrawBuyNumber': pl.Int32,
                       'WithdrawBuyAmount': pl.Float64, 'WithdrawBuyMoney': pl.Float64,
                       'WithdrawSellNumber': pl.Int32, 'WithdrawSellAmount': pl.Float64,
                       'WithdrawSellMoney': pl.Float64, 'TotalBidNumber': pl.Int32,
                       'TotalOfferNumber': pl.Int32, 'BidTradeMaxDuration': pl.Int32,
                       'OfferTradeMaxDuration': pl.Int32, 'NumBidOrders': pl.Int32,
                       'NumOfferOrders': pl.Int32, 'SLYOne': pl.Float64, 'SLYTwo': pl.Float64,
                       'NorminalPx': pl.Float64, 'ShortSellSharepl.Utf8aded': pl.Float64,
                       'ShortSellTurnover': pl.Float64, 'ReferencePx': pl.Float64,
                       'ComplexEventStartTime': pl.Int32,
                       'ComplexEventEndTime': pl.Int32, 'Buy1Price': pl.Float64,
                       'Buy1OrderQty': pl.Float64, 'Buy1NumOrders': pl.Int32,
                       'Buy1NoOrders': pl.Int32, 'Buy1OrderDetail': pl.Utf8,
                       'Sell1Price': pl.Float64, 'Sell1OrderQty': pl.Float64,
                       'Sell1NumOrders': pl.Int32, 'Sell1NoOrders': pl.Int32,
                       'Sell1OrderDetail': pl.Utf8, 'Buy2Price': pl.Float64,
                       'Buy2OrderQty': pl.Float64, 'Buy2NumOrders': pl.Int32,
                       'Sell2Price': pl.Float64, 'Sell2OrderQty': pl.Float64,
                       'Sell2NumOrders': pl.Int32, 'Buy3Price': pl.Float64,
                       'Buy3OrderQty': pl.Float64, 'Buy3NumOrders': pl.Int32,
                       'Sell3Price': pl.Float64, 'Sell3OrderQty': pl.Float64,
                       'Sell3NumOrders': pl.Int32, 'Buy4Price': pl.Float64,
                       'Buy4OrderQty': pl.Float64, 'Buy4NumOrders': pl.Int32,
                       'Sell4Price': pl.Float64, 'Sell4OrderQty': pl.Float64,
                       'Sell4NumOrders': pl.Int32, 'Buy5Price': pl.Float64,
                       'Buy5OrderQty': pl.Float64, 'Buy5NumOrders': pl.Int32,
                       'Sell5Price': pl.Float64, 'Sell5OrderQty': pl.Float64,
                       'Sell5NumOrders': pl.Int32, 'Buy6Price': pl.Float64,
                       'Buy6OrderQty': pl.Float64, 'Buy6NumOrders': pl.Int32,
                       'Sell6Price': pl.Float64, 'Sell6OrderQty': pl.Float64,
                       'Sell6NumOrders': pl.Int32, 'Buy7Price': pl.Float64,
                       'Buy7OrderQty': pl.Float64, 'Buy7NumOrders': pl.Int32,
                       'Sell7Price': pl.Float64, 'Sell7OrderQty': pl.Float64,
                       'Sell7NumOrders': pl.Int32, 'Buy8Price': pl.Float64,
                       'Buy8OrderQty': pl.Float64, 'Buy8NumOrders': pl.Int32,
                       'Sell8Price': pl.Float64, 'Sell8OrderQty': pl.Float64,
                       'Sell8NumOrders': pl.Int32, 'Buy9Price': pl.Float64,
                       'Buy9OrderQty': pl.Float64, 'Buy9NumOrders': pl.Int32,
                       'Sell9Price': pl.Float64, 'Sell9OrderQty': pl.Float64,
                       'Sell9NumOrders': pl.Int32, 'Buy10Price': pl.Float64,
                       'Buy10OrderQty': pl.Float64, 'Buy10NumOrders': pl.Int32,
                       'Sell10Price': pl.Float64, 'Sell10OrderQty': pl.Float64,
                       'Sell10NumOrders': pl.Int32, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'ArrivalDateTime': pl.Int32,
                       'ChannelNo': pl.Int32}
            if exchange_house == 'hk':
                columns['OtcTotalVolumeTrade'] = pl.Float64
        elif table_type == 'fundtick':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'PreClosePx': pl.Float64,
                       'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'LastPx': pl.Float64,
                       'OpenPx': pl.Float64, 'ClosePx': pl.Float64, 'HighPx': pl.Float64,
                       'LowPx': pl.Float64, 'DiffPx1': pl.Float64, 'DiffPx2': pl.Float64,
                       'MaxPx': pl.Float64, 'MinPx': pl.Float64, 'TotalBidQty': pl.Float64,
                       'TotalOfferQty': pl.Float64, 'WeightedAvgBidPx': pl.Float64,
                       'WeightedAvgOfferPx': pl.Float64, 'WithdrawBuyNumber': pl.Int32,
                       'WithdrawBuyAmount': pl.Float64, 'WithdrawBuyMoney': pl.Float64,
                       'WithdrawSellNumber': pl.Int32, 'WithdrawSellAmount': pl.Float64,
                       'WithdrawSellMoney': pl.Float64, 'TotalBidNumber': pl.Int32,
                       'TotalOfferNumber': pl.Int32, 'BidTradeMaxDuration': pl.Int32,
                       'OfferTradeMaxDuration': pl.Int32, 'NumBidOrders': pl.Int32,
                       'NumOfferOrders': pl.Int32, 'IOPV': pl.Float64, 'PreIOPV': pl.Float64,
                       'BuyNumber': pl.Int32, 'BuyAmount': pl.Float64, 'BuyMoney': pl.Float64,
                       'SellNumber': pl.Int32, 'SellAmount': pl.Float64,
                       'SellMoney': pl.Float64, 'Buy1Price': pl.Float64,
                       'Buy1OrderQty': pl.Float64, 'Buy1NumOrders': pl.Int32,
                       'Buy1NoOrders': pl.Int32, 'Buy1OrderDetail': pl.Utf8,
                       'Sell1Price': pl.Float64, 'Sell1OrderQty': pl.Float64,
                       'Sell1NumOrders': pl.Int32, 'Sell1NoOrders': pl.Int32,
                       'Sell1OrderDetail': pl.Utf8, 'Buy2Price': pl.Float64,
                       'Buy2OrderQty': pl.Float64, 'Buy2NumOrders': pl.Int32,
                       'Sell2Price': pl.Float64, 'Sell2OrderQty': pl.Float64,
                       'Sell2NumOrders': pl.Int32, 'Buy3Price': pl.Float64,
                       'Buy3OrderQty': pl.Float64, 'Buy3NumOrders': pl.Int32,
                       'Sell3Price': pl.Float64, 'Sell3OrderQty': pl.Float64,
                       'Sell3NumOrders': pl.Int32, 'Buy4Price': pl.Float64,
                       'Buy4OrderQty': pl.Float64, 'Buy4NumOrders': pl.Int32,
                       'Sell4Price': pl.Float64, 'Sell4OrderQty': pl.Float64,
                       'Sell4NumOrders': pl.Int32, 'Buy5Price': pl.Float64,
                       'Buy5OrderQty': pl.Float64, 'Buy5NumOrders': pl.Int32,
                       'Sell5Price': pl.Float64, 'Sell5OrderQty': pl.Float64,
                       'Sell5NumOrders': pl.Int32, 'Buy6Price': pl.Float64,
                       'Buy6OrderQty': pl.Float64, 'Buy6NumOrders': pl.Int32,
                       'Sell6Price': pl.Float64, 'Sell6OrderQty': pl.Float64,
                       'Sell6NumOrders': pl.Int32, 'Buy7Price': pl.Float64,
                       'Buy7OrderQty': pl.Float64, 'Buy7NumOrders': pl.Int32,
                       'Sell7Price': pl.Float64, 'Sell7OrderQty': pl.Float64,
                       'Sell7NumOrders': pl.Int32, 'Buy8Price': pl.Float64,
                       'Buy8OrderQty': pl.Float64, 'Buy8NumOrders': pl.Int32,
                       'Sell8Price': pl.Float64, 'Sell8OrderQty': pl.Float64,
                       'Sell8NumOrders': pl.Int32, 'Buy9Price': pl.Float64,
                       'Buy9OrderQty': pl.Float64, 'Buy9NumOrders': pl.Int32,
                       'Sell9Price': pl.Float64, 'Sell9OrderQty': pl.Float64,
                       'Sell9NumOrders': pl.Int32, 'Buy10Price': pl.Float64,
                       'Buy10OrderQty': pl.Float64, 'Buy10NumOrders': pl.Int32,
                       'Sell10Price': pl.Float64, 'Sell10OrderQty': pl.Float64,
                       'Sell10NumOrders': pl.Int32, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'ChannelNo': pl.Int32}
        elif table_type == 'bondtick':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'PreClosePx': pl.Float64,
                       'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'LastPx': pl.Float64,
                       'OpenPx': pl.Float64, 'ClosePx': pl.Float64, 'HighPx': pl.Float64,
                       'LowPx': pl.Float64, 'DiffPx1': pl.Float64, 'DiffPx2': pl.Float64,
                       'MaxPx': pl.Float64, 'MinPx': pl.Float64, 'TotalBidQty': pl.Float64,
                       'TotalOfferQty': pl.Float64, 'WeightedAvgBidPx': pl.Float64,
                       'WeightedAvgOfferPx': pl.Float64, 'WithdrawBuyNumber': pl.Int32,
                       'WithdrawBuyAmount': pl.Float64, 'WithdrawBuyMoney': pl.Float64,
                       'WithdrawSellNumber': pl.Int32, 'WithdrawSellAmount': pl.Float64,
                       'WithdrawSellMoney': pl.Float64, 'TotalBidNumber': pl.Int32,
                       'TotalOfferNumber': pl.Int32, 'BidTradeMaxDuration': pl.Int32,
                       'OfferTradeMaxDuration': pl.Int32, 'NumBidOrders': pl.Int32,
                       'NumOfferOrders': pl.Int32, 'YieldToMaturity': pl.Float64,
                       'WeightedAvgPx': pl.Float64, 'WeightedAvgPxBP': pl.Float64,
                       'PreCloseWeightedAvgPx': pl.Float64, 'Buy1Price': pl.Float64,
                       'Buy1OrderQty': pl.Float64, 'Buy1NumOrders': pl.Int32,
                       'Buy1NoOrders': pl.Int32, 'Buy1OrderDetail': pl.Utf8,
                       'Sell1Price': pl.Float64, 'Sell1OrderQty': pl.Float64,
                       'Sell1NumOrders': pl.Int32, 'Sell1NoOrders': pl.Int32,
                       'Sell1OrderDetail': pl.Utf8, 'Buy2Price': pl.Float64,
                       'Buy2OrderQty': pl.Float64, 'Buy2NumOrders': pl.Int32,
                       'Sell2Price': pl.Float64, 'Sell2OrderQty': pl.Float64,
                       'Sell2NumOrders': pl.Int32, 'Buy3Price': pl.Float64,
                       'Buy3OrderQty': pl.Float64, 'Buy3NumOrders': pl.Int32,
                       'Sell3Price': pl.Float64, 'Sell3OrderQty': pl.Float64,
                       'Sell3NumOrders': pl.Int32, 'Buy4Price': pl.Float64,
                       'Buy4OrderQty': pl.Float64, 'Buy4NumOrders': pl.Int32,
                       'Sell4Price': pl.Float64, 'Sell4OrderQty': pl.Float64,
                       'Sell4NumOrders': pl.Int32, 'Buy5Price': pl.Float64,
                       'Buy5OrderQty': pl.Float64, 'Buy5NumOrders': pl.Int32,
                       'Sell5Price': pl.Float64, 'Sell5OrderQty': pl.Float64,
                       'Sell5NumOrders': pl.Int32, 'Buy6Price': pl.Float64,
                       'Buy6OrderQty': pl.Float64, 'Buy6NumOrders': pl.Int32,
                       'Sell6Price': pl.Float64, 'Sell6OrderQty': pl.Float64,
                       'Sell6NumOrders': pl.Int32, 'Buy7Price': pl.Float64,
                       'Buy7OrderQty': pl.Float64, 'Buy7NumOrders': pl.Int32,
                       'Sell7Price': pl.Float64, 'Sell7OrderQty': pl.Float64,
                       'Sell7NumOrders': pl.Int32, 'Buy8Price': pl.Float64,
                       'Buy8OrderQty': pl.Float64, 'Buy8NumOrders': pl.Int32,
                       'Sell8Price': pl.Float64, 'Sell8OrderQty': pl.Float64,
                       'Sell8NumOrders': pl.Int32, 'Buy9Price': pl.Float64,
                       'Buy9OrderQty': pl.Float64, 'Buy9NumOrders': pl.Int32,
                       'Sell9Price': pl.Float64, 'Sell9OrderQty': pl.Float64,
                       'Sell9NumOrders': pl.Int32, 'Buy10Price': pl.Float64,
                       'Buy10OrderQty': pl.Float64, 'Buy10NumOrders': pl.Int32,
                       'Sell10Price': pl.Float64, 'Sell10OrderQty': pl.Float64,
                       'Sell10NumOrders': pl.Int32, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'ChannelNo': pl.Int32}
        elif table_type == 'futuretick':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'TradingDate': pl.Utf8,
                       'PreOpenpl.Int32erest': pl.Float64, 'PreClosePx': pl.Float64,
                       'PreSettlePrice': pl.Float64, 'OpenPx': pl.Float64,
                       'HighPx': pl.Float64, 'LowPx': pl.Float64, 'LastPx': pl.Float64,
                       'TotalVolumeTrade': pl.Float64, 'TotalValueTrade': pl.Float64,
                       'Openpl.Int32erest': pl.Float64, 'ClosePx': pl.Float64,
                       'SettlePrice': pl.Float64, 'MaxPx': pl.Float64, 'MinPx': pl.Float64,
                       'PreDelta': pl.Float64, 'CurrDelta': pl.Float64,
                       'Buy1Price': pl.Float64, 'Buy1OrderQty': pl.Float64,
                       'Buy1NumOrders': pl.Int32, 'Buy1NoOrders': pl.Int32,
                       'Buy1OrderDetail': pl.Utf8, 'Sell1Price': pl.Float64,
                       'Sell1OrderQty': pl.Float64, 'Sell1NumOrders': pl.Int32,
                       'Sell1NoOrders': pl.Int32, 'Sell1OrderDetail': pl.Utf8,
                       'Buy2Price': pl.Float64, 'Buy2OrderQty': pl.Float64,
                       'Buy2NumOrders': pl.Int32, 'Sell2Price': pl.Float64,
                       'Sell2OrderQty': pl.Float64, 'Sell2NumOrders': pl.Int32,
                       'Buy3Price': pl.Float64, 'Buy3OrderQty': pl.Float64,
                       'Buy3NumOrders': pl.Int32, 'Sell3Price': pl.Float64,
                       'Sell3OrderQty': pl.Float64, 'Sell3NumOrders': pl.Int32,
                       'Buy4Price': pl.Float64, 'Buy4OrderQty': pl.Float64,
                       'Buy4NumOrders': pl.Int32, 'Sell4Price': pl.Float64,
                       'Sell4OrderQty': pl.Float64, 'Sell4NumOrders': pl.Int32,
                       'Buy5Price': pl.Float64, 'Buy5OrderQty': pl.Float64,
                       'Buy5NumOrders': pl.Int32, 'Sell5Price': pl.Float64,
                       'Sell5OrderQty': pl.Float64, 'Sell5NumOrders': pl.Int32,
                       'MDRecordType': pl.Utf8, 'HTSCSecurityID': pl.Utf8,
                       'ReceiveDateTime': pl.Int32, 'MDValidType': pl.Utf8,
                       'ChannelNo': pl.Int32}
        elif table_type == 'stockorder':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'OrderIndex': pl.Int32, 'OrderType': pl.Int32,
                       'OrderPrice': pl.Float64, 'OrderQty': pl.Float64,
                       'OrderBSFlag': pl.Int32, 'ExpirationType': pl.Int32,
                       'ExpirationDays': pl.Int32, 'Contactor': pl.Utf8,
                       'ContactInfo': pl.Utf8, 'ConfirmID': pl.Utf8,
                       'ArrivalDateTime': pl.Int32, 'ApplSeqNum': pl.Int32, 'OrderNO': pl.Int32,
                       'ChannelNo': pl.Int32, 'SecurityStatus': pl.Utf8, 'TradedQty': pl.Float64}
        elif table_type == 'stocktransaction':
            # columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
            #            'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
            #            'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
            #            'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
            #            'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
            #            'SwitchStatus': pl.Utf8, 'MDRecordType': pl.Utf8,
            #            'TradeIndex': pl.Int32, 'TradeBuyNo': pl.Int32,
            #            'TradeSellNo': pl.Int32, 'TradeType': pl.Int32,
            #            'TradeBSFlag': pl.Int32, 'TradePrice': pl.Float64,
            #            'TradeQty': pl.Float64, 'TradeMoney': pl.Float64,
            #            'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
            #            'NumTrades': pl.Int32, 'MDValidType': pl.Utf8,
            #            'ArrivalDateTime': pl.Int32, 'ChannelNo': pl.Int32, 'ApplSeqNum': pl.Int32}
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'MDRecordType': pl.Utf8,
                       'TradeIndex': pl.Int32, 'TradeBuyNo': pl.Int32,
                       'TradeSellNo': pl.Int32, 'TradeType': pl.Int32,
                       'TradeBSFlag': pl.Int32, 'TradePrice': pl.Float64,
                       'TradeQty': pl.Float64, 'TradeMoney': pl.Float64,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'NumTrades': pl.Int32, 'MDValidType': pl.Utf8,
                       'ArrivalDateTime': pl.Int32, 'ChannelNo': pl.Int32, 'ApplSeqNum': pl.Int32}

        elif table_type == 'fundorder':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'OrderIndex': pl.Int32, 'OrderType': pl.Int32,
                       'OrderPrice': pl.Float64, 'OrderQty': pl.Float64,
                       'OrderBSFlag': pl.Int32, 'ExpirationType': pl.Int32,
                       'ExpirationDays': pl.Int32, 'Contactor': pl.Utf8,
                       'ContactInfo': pl.Utf8, 'ConfirmID': pl.Utf8, 'ApplSeqNum': pl.Int32,
                       'OrderNO': pl.Int32, 'ChannelNo': pl.Int32, 'SecurityStatus': pl.Utf8, 'TradedQty': pl.Float64}

        elif table_type == 'bondorder':
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'MDRecordType': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'MDValidType': pl.Utf8, 'OrderIndex': pl.Int32, 'OrderType': pl.Int32,
                       'OrderPrice': pl.Float64, 'OrderQty': pl.Float64,
                       'OrderBSFlag': pl.Int32, 'ExpirationType': pl.Int32,
                       'ExpirationDays': pl.Int32, 'Contactor': pl.Utf8,
                       'ContactInfo': pl.Utf8, 'ConfirmID': pl.Utf8, 'ApplSeqNum': pl.Int32,
                       'OrderNO': pl.Int32, 'ChannelNo': pl.Int32, 'SecurityStatus': pl.Utf8}


        elif table_type in ['bondtransaction', 'fundtransaction']:
            columns = {'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8, 'TradingPhaseCode': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'MDRecordType': pl.Utf8,
                       'TradeIndex': pl.Int32, 'TradeBuyNo': pl.Int32, 'TradeSellNo': pl.Int32,
                       'TradeType': pl.Int32, 'TradeBSFlag': pl.Int32, 'TradePrice': pl.Float64,
                       'TradeQty': pl.Float64, 'TradeMoney': pl.Float64,
                       'HTSCSecurityID': pl.Utf8, 'ReceiveDateTime': pl.Int32,
                       'NumTrades': pl.Int32, 'MDValidType': pl.Utf8, 'ChannelNo': pl.Int32,
                       'ApplSeqNum': pl.Int32}
        elif table_type == 'optiontick':
            columns = {'MDDate': pl.Utf8, 'MDTime': pl.Utf8, 'SecurityType': pl.Utf8,
                       'SecuritySubType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'Symbol': pl.Utf8,
                       'TradingPhaseCode': pl.Utf8, 'PreClosePx': pl.Utf8,
                       'NumTrades': pl.Utf8, 'TotalVolumeTrade': pl.Utf8,
                       'TotalValueTrade': pl.Utf8, 'LastPx': pl.Utf8, 'OpenPx': pl.Utf8,
                       'ClosePx': pl.Utf8, 'HighPx': pl.Utf8, 'LowPx': pl.Utf8, 'MaxPx': pl.Utf8,
                       'MinPx': pl.Utf8, 'OptionPosition': pl.Utf8, 'PreOpenpl.Int32erest': pl.Utf8,
                       'PreSettlePrice': pl.Utf8, 'Openpl.Int32erest': pl.Utf8,
                       'SettlePrice': pl.Utf8, 'ReferencePrice': pl.Utf8, 'Buy1Price': pl.Utf8,
                       'Buy1OrderQty': pl.Utf8, 'Sell1Price': pl.Utf8,
                       'Sell1OrderQty': pl.Utf8, 'Buy2Price': pl.Utf8, 'Buy2OrderQty': pl.Utf8,
                       'Sell2Price': pl.Utf8, 'Sell2OrderQty': pl.Utf8, 'Buy3Price': pl.Utf8,
                       'Buy3OrderQty': pl.Utf8, 'Sell3Price': pl.Utf8,
                       'Sell3OrderQty': pl.Utf8, 'Buy4Price': pl.Utf8, 'Buy4OrderQty': pl.Utf8,
                       'Sell4Price': pl.Utf8, 'Sell4OrderQty': pl.Utf8, 'Buy5Price': pl.Utf8,
                       'Buy5OrderQty': pl.Utf8, 'Sell5Price': pl.Utf8,
                       'Sell5OrderQty': pl.Utf8, 'HTSCSecurityID': pl.Utf8,
                       'ReceiveDateTime': pl.Utf8, 'Buy10NumOrders': pl.Utf8,
                       'WithdrawSellNumber': pl.Utf8, 'Sell1OrderDetail': pl.Utf8,
                       'DiffPx1': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'Buy9NumOrders': pl.Utf8,
                       'Sell6NumOrders': pl.Utf8, 'Buy6OrderQty': pl.Utf8,
                       'Sell9Price': pl.Utf8, 'BidTradeMaxDuration': pl.Utf8,
                       'Buy1NoOrders': pl.Utf8, 'Sell10OrderQty': pl.Utf8,
                       'Sell1NumOrders': pl.Utf8, 'Buy3NumOrders': pl.Utf8,
                       'Buy1OrderDetail': pl.Utf8, 'NumOfferOrders': pl.Utf8,
                       'MDReportID': pl.Utf8, 'WeightedAvgOfferPx': pl.Utf8,
                       'Buy1NumOrders': pl.Utf8, 'Buy8OrderQty': pl.Utf8,
                       'WithdrawSellAmount': pl.Utf8, 'NumBidOrders': pl.Utf8,
                       'TotalOfferQty': pl.Utf8, 'MDLevel': pl.Utf8,
                       'WeightedAvgBidPx': pl.Utf8, 'MDRecordID': pl.Utf8,
                       'TotalBidQty': pl.Utf8, 'Sell8Price': pl.Utf8, 'Buy9OrderQty': pl.Utf8,
                       'DiffPx2': pl.Utf8, 'Buy2NumOrders': pl.Utf8, 'Sell6Price': pl.Utf8,
                       'Buy9Price': pl.Utf8, 'Sell6OrderQty': pl.Utf8, 'Buy10Price': pl.Utf8,
                       'Buy5NumOrders': pl.Utf8, 'Buy7Price': pl.Utf8,
                       'Sell5NumOrders': pl.Utf8, 'Buy6NumOrders': pl.Utf8,
                       'WithdrawBuyNumber': pl.Utf8, 'Sell9NumOrders': pl.Utf8,
                       'Sell3NumOrders': pl.Utf8, 'Sell1NoOrders': pl.Utf8,
                       'MDValidType': pl.Utf8, 'TotalBidNumber': pl.Utf8,
                       'WithdrawBuyAmount': pl.Utf8, 'Buy8Price': pl.Utf8,
                       'Buy4NumOrders': pl.Utf8, 'Sell7Price': pl.Utf8,
                       'Buy8NumOrders': pl.Utf8, 'OfferTradeMaxDuration': pl.Utf8,
                       'SwitchStatus': pl.Utf8, 'WithdrawBuyMoney': pl.Utf8,
                       'Buy10OrderQty': pl.Utf8, 'Buy6Price': pl.Utf8,
                       'WithdrawSellMoney': pl.Utf8, 'MDChannel': pl.Utf8,
                       'Buy7OrderQty': pl.Utf8, 'Sell9OrderQty': pl.Utf8,
                       'Buy7NumOrders': pl.Utf8, 'Sell10Price': pl.Utf8,
                       'Sell4NumOrders': pl.Utf8, 'Sell10NumOrders': pl.Utf8,
                       'MDRecordType': pl.Utf8, 'Sell7OrderQty': pl.Utf8,
                       'Sell2NumOrders': pl.Utf8, 'Sell7NumOrders': pl.Utf8,
                       'Sell8NumOrders': pl.Utf8, 'TotalOfferNumber': pl.Utf8,
                       'Sell8OrderQty': pl.Utf8, 'TradingDate': pl.Utf8, 'PreDelta': pl.Utf8,
                       'CurrDelta': pl.Utf8, 'HDBusinessDate': pl.Utf8}
        elif table_type in ['kline1m4zt']:
            columns = {'MDRecordID': pl.Utf8, 'KLineType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'MDDate': pl.Utf8, 'MDTime': pl.Utf8,
                       'OpenPx': pl.Float64, 'ClosePx': pl.Float64, 'HighPx': pl.Float64,
                       'LowPx': pl.Float64, 'NumTrades': pl.Float64, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'PeriodType': pl.Utf8, 'IOPV': pl.Float64,
                       'Openpl.Int32erest': pl.Float64, 'SettlePrice': pl.Float64}
        elif table_type in ['bondkline1m', 'bondkline1d', 'fundkline1m', 'fundkline1d', 'futurekline1m',
                            'futurekline1d']:
            columns = {'MDRecordID': pl.Utf8, 'KLineType': pl.Utf8, 'SecurityID': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'MDDate': pl.Utf8, 'MDTime': pl.Utf8,
                       'OpenPx': pl.Float64, 'ClosePx': pl.Float64, 'HighPx': pl.Float64,
                       'LowPx': pl.Float64, 'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'PeriodType': pl.Utf8, 'IOPV': pl.Float64,
                       'Openpl.Int32erest': pl.Float64, 'SettlePrice': pl.Float64}
        elif table_type in ['optionkline1d', 'optionkline1m']:
            columns = {'MDRecordID': pl.Utf8, 'SecurityID': pl.Utf8, 'AfterHoursNumTrades': pl.Float64,
                       'AfterHoursTotalVolumeTrade': pl.Float64, 'AfterHoursTotalValueTrade': pl.Float64,
                       'MacroDetail': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'MDDate': pl.Utf8, 'MDTime': pl.Utf8,
                       'OpenPx': pl.Float64, 'ClosePx': pl.Float64, 'HighPx': pl.Float64,
                       'LowPx': pl.Float64, 'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'PeriodType': pl.Utf8, 'IOPV': pl.Float64,
                       'Openpl.Int32erest': pl.Float64, 'SettlePrice': pl.Float64}
        elif table_type in ['northboundkline1m']:
            columns = {'MDDate': pl.Utf8, 'MDTime': pl.Utf8, 'SecurityType': pl.Utf8, 'SecuritySubType': pl.Utf8,
                       'SecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Utf8, 'HTSCSecurityID': pl.Utf8, 'Symbol': pl.Utf8,
                       'PreClosePx': pl.Float64,
                       'TotalVolumeTrade': pl.Float64, 'TotalValueTrade': pl.Float64, 'LastPx': pl.Float64,
                       'OpenPx': pl.Float64,
                       'ClosePx': pl.Float64, 'HighPx': pl.Float64, 'LowPx': pl.Float64,
                       'TotalBidValueTrade': pl.Float64,
                       'TotalOfferValueTrade': pl.Float64, 'TradingPhaseCode': pl.Utf8, 'ChannelNo': pl.Utf8,
                       'ReceiveDateTime': pl.Utf8,
                       'MDRecordID': pl.Utf8, 'MDReportID': pl.Utf8, 'MDpl.Utf8eamID': pl.Utf8, 'MDLevel': pl.Utf8,
                       'MDChannel': pl.Utf8}
        elif table_type in ['stockenhancedtick']:
            # TODO:根据增强tick数据格式的表结构进行调整
            columns = {'MDDate': pl.Utf8, 'MDTime': pl.Utf8, 'SecurityType': pl.Utf8, 'SecuritySubType': pl.Utf8,
                       'SecurityID': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8, 'SecurityIDSource': pl.Int32, 'Symbol': pl.Utf8,
                       'PreClosePx': pl.Float64,
                       'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64, 'TotalValueTrade': pl.Float64,
                       'LastPx': pl.Float64,
                       'OpenPx': pl.Float64, 'HighPx': pl.Float64, 'LowPx': pl.Float64, 'MaxPx': pl.Float64,
                       'MinPx': pl.Float64,
                       'TotalBidQty': pl.Float64, 'TotalOfferQty': pl.Float64, 'WeightedAvgBidPx': pl.Float64,
                       'WeightedAvgOfferPx': pl.Float64,
                       'TotalBidNumber': pl.Int32, 'TotalOfferNumber': pl.Int32, 'NumBidOrders': pl.Int32,
                       'NumOfferOrders': pl.Int32,
                       'ReceiveDateTime': pl.Int32, 'ChannelNo': pl.Int32, 'ApplSeqNum': pl.Int32,
                       'Buy1Price': pl.Float64,
                       'Buy1OrderQty': pl.Float64, 'Buy1NumOrders': pl.Int32, 'Buy1OrderDetail': pl.Utf8,
                       'Sell1Price': pl.Float64,
                       'Sell1OrderQty': pl.Float64, 'Sell1NumOrders': pl.Int32, 'Sell1OrderDetail': pl.Utf8,
                       'Buy2Price': pl.Float64,
                       'Buy2OrderQty': pl.Int32, 'Buy2NumOrders': pl.Utf8,
                       'Buy2OrderDetail': pl.Utf8, 'Sell2Price': pl.Float64, 'Sell2OrderQty': pl.Float64,
                       'Sell2NumOrders': pl.Int32,
                       'Sell2OrderDetail': pl.Utf8, 'Buy3Price': pl.Float64,
                       'Buy3OrderQty': pl.Float64, 'Buy3NumOrders': pl.Int32, 'Buy3OrderDetail': pl.Utf8,
                       'Sell3Price': pl.Float64,
                       'Sell3OrderQty': pl.Float64, 'Sell3NumOrders': pl.Int32,
                       'Sell3OrderDetail': pl.Utf8, 'Buy4Price': pl.Float64, 'Buy4OrderQty': pl.Float64,
                       'Buy4NumOrders': pl.Int32,
                       'Buy4OrderDetail': pl.Utf8, 'Sell4Price': pl.Float64,
                       'Sell4OrderQty': pl.Float64, 'Sell4NumOrders': pl.Int32, 'Sell4OrderDetail': pl.Utf8,
                       'Buy5Price': pl.Float64,
                       'Buy5OrderQty': pl.Float64, 'Buy5NumOrders': pl.Int32,
                       'Buy5OrderDetail': pl.Utf8, 'Sell5Price': pl.Float64, 'Sell5OrderQty': pl.Float64,
                       'Sell5NumOrders': pl.Int32,
                       'Sell5OrderDetail': pl.Utf8, 'Buy6Price': pl.Float64,
                       'Buy6OrderQty': pl.Float64, 'Buy6NumOrders': pl.Int32, 'Buy6OrderDetail': pl.Utf8,
                       'Sell6Price': pl.Float64,
                       'Sell6OrderQty': pl.Float64, 'Sell6NumOrders': pl.Int32,
                       'Sell6OrderDetail': pl.Utf8, 'Buy7Price': pl.Float64, 'Buy7OrderQty': pl.Float64,
                       'Buy7NumOrders': pl.Int32,
                       'Buy7OrderDetail': pl.Utf8, 'Sell7Price': pl.Float64,
                       'Sell7OrderQty': pl.Float64, 'Sell7NumOrders': pl.Int32, 'Sell7OrderDetail': pl.Utf8,
                       'Buy8Price': pl.Float64,
                       'Buy8OrderQty': pl.Float64, 'Buy8NumOrders': pl.Int32,
                       'Buy8OrderDetail': pl.Utf8, 'Sell8Price': pl.Float64, 'Sell8OrderQty': pl.Float64,
                       'Sell8NumOrders': pl.Int32,
                       'Sell8OrderDetail': pl.Utf8, 'Buy9Price': pl.Float64,
                       'Buy9OrderQty': pl.Float64, 'Buy9NumOrders': pl.Int32, 'Buy9OrderDetail': pl.Utf8,
                       'Sell9Price': pl.Float64,
                       'Sell9OrderQty': pl.Float64, 'Sell9NumOrders': pl.Int32,
                       'Sell9OrderDetail': pl.Utf8, 'Buy10Price': pl.Float64, 'Buy10OrderQty': pl.Float64,
                       'Buy10NumOrders': pl.Int32,
                       'Buy10OrderDetail': pl.Utf8, 'Sell10Price': pl.Float64,
                       'Sell10OrderQty': pl.Float64, 'Sell10NumOrders': pl.Int32, 'Sell10OrderDetail': pl.Utf8,
                       'Buy11Price': pl.Float64,
                       'Buy11OrderQty': pl.Float64, 'Buy11NumOrders': pl.Int32,
                       'Buy11OrderDetail': pl.Utf8, 'Sell11Price': pl.Float64, 'Sell11OrderQty': pl.Float64,
                       'Sell11NumOrders': pl.Int32,
                       'Sell11OrderDetail': pl.Utf8, 'Buy12Price': pl.Float64,
                       'Buy12OrderQty': pl.Float64, 'Buy12NumOrders': pl.Int32, 'Buy12OrderDetail': pl.Utf8,
                       'Sell12Price': pl.Float64,
                       'Sell12OrderQty': pl.Float64, 'Sell12NumOrders': pl.Int32,
                       'Sell12OrderDetail': pl.Utf8, 'Buy13Price': pl.Float64, 'Buy13OrderQty': pl.Float64,
                       'Buy13NumOrders': pl.Int32,
                       'Buy13OrderDetail': pl.Utf8, 'Sell13Price': pl.Float64,
                       'Sell13OrderQty': pl.Float64, 'Sell13NumOrders': pl.Int32, 'Sell13OrderDetail': pl.Utf8,
                       'Buy14Price': pl.Float64,
                       'Buy14OrderQty': pl.Float64, 'Buy14NumOrders': pl.Int32,
                       'Buy14OrderDetail': pl.Utf8, 'Sell14Price': pl.Float64, 'Sell14OrderQty': pl.Float64,
                       'Sell14NumOrders': pl.Int32,
                       'Sell14OrderDetail': pl.Utf8, 'Buy15Price': pl.Float64,
                       'Buy15OrderQty': pl.Float64, 'Buy15NumOrders': pl.Int32, 'Buy15OrderDetail': pl.Utf8,
                       'Sell15Price': pl.Float64,
                       'Sell15OrderQty': pl.Float64, 'Sell15NumOrders': pl.Int32,
                       'Sell15OrderDetail': pl.Utf8, 'Buy16Price': pl.Float64, 'Buy16OrderQty': pl.Float64,
                       'Buy16NumOrders': pl.Int32,
                       'Buy16OrderDetail': pl.Utf8, 'Sell16Price': pl.Float64,
                       'Sell16OrderQty': pl.Float64, 'Sell16NumOrders': pl.Int32, 'Sell16OrderDetail': pl.Utf8,
                       'Buy17Price': pl.Float64,
                       'Buy17OrderQty': pl.Float64, 'Buy17NumOrders': pl.Int32,
                       'Buy17OrderDetail': pl.Utf8, 'Sell17Price': pl.Float64, 'Sell17OrderQty': pl.Float64,
                       'Sell17NumOrders': pl.Int32,
                       'Sell17OrderDetail': pl.Utf8, 'Buy18Price': pl.Float64,
                       'Buy18OrderQty': pl.Float64, 'Buy18NumOrders': pl.Int32, 'Buy18OrderDetail': pl.Utf8,
                       'Sell18Price': pl.Float64,
                       'Sell18OrderQty': pl.Float64, 'Sell18NumOrders': pl.Int32,
                       'Sell18OrderDetail': pl.Utf8, 'Buy19Price': pl.Float64, 'Buy19OrderQty': pl.Float64,
                       'Buy19NumOrders': pl.Int32,
                       'Buy19OrderDetail': pl.Utf8, 'Sell19Price': pl.Float64,
                       'Sell19OrderQty': pl.Float64, 'Sell19NumOrders': pl.Int32, 'Sell19OrderDetail': pl.Utf8,
                       'Buy20Price': pl.Float64, 'Buy20OrderQty': pl.Float64, 'Buy20NumOrders': pl.Int32,
                       'Buy20OrderDetail': pl.Utf8,
                       'Sell20Price': pl.Float64, 'Sell20OrderQty': pl.Float64, 'Sell20NumOrders': pl.Int32,
                       'Sell20OrderDetail': pl.Utf8}
        elif table_type in ['kline1dpreadj']:
            columns = {'CrtBy': pl.Utf8, 'CrtDate': pl.Utf8, 'LastModfBy': pl.Utf8, 'LastModfDate': pl.Utf8,
                       'CrtBusiDate': pl.Utf8,
                       'LastModfBusiDate': pl.Utf8, 'EtlSrcTable': pl.Utf8, 'PeriodId': pl.Utf8,
                       'HTSCSecurityID': pl.Utf8,
                       'MDDate': pl.Utf8,
                       'MDTime': pl.Utf8, 'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64,
                       'OpeningPrice': pl.Float64, 'HighsetPrice': pl.Float64, 'LowsetPrice': pl.Float64,
                       'ClosePrice': pl.Float64,
                       'BadjustOpeningPrice': pl.Float64, 'BadjustHighsetPrice': pl.Float64,
                       'BadjustLowsetPrice': pl.Float64,
                       'BadjustClosingPrice': pl.Float64}
        elif table_type == "kline1d":
            columns = {'MDDate': pl.Utf8, 'MDTime': pl.Utf8,
                       'SecurityType': pl.Int32, 'SecuritySubType': pl.Utf8,
                       'SecurityID': pl.Utf8, 'HTSCSecurityID': pl.Utf8,
                       'SecurityIDSource': pl.Int32, 'Symbol': pl.Utf8,
                       'PreClosePx': pl.Float64, 'OpenPx': pl.Float64,
                       'ClosePx': pl.Float64, 'HighPx': pl.Float64, 'LowPx': pl.Float64,
                       'NumTrades': pl.Int32, 'TotalVolumeTrade': pl.Float64,
                       'TotalValueTrade': pl.Float64, 'PeriodType': pl.Int32,
                       'Openpl.Int32erest': pl.Float64, 'SettlePrice': pl.Float64,
                       'ExchangeDate': pl.Utf8, 'ExchangeTime': pl.Utf8}
        else:
            raise Exception('暂不支持{}类型'.format(table_type))
        return columns


# if __name__ == '__main__':
#     mdp = MDCStockDataDP()
#     df = mdp.get_stock_data("300760.SZ", "20241101 000000000", "20241102 000000000", bar_size="STOCK")# TRANSACTION KLINE1M4ZT
#     print(df)
#     print(df.columns)
#
#     df = mdp.get_stock_data("000009.SZ", "20230201 000000000", "20230210 000000000", bar_size="KLINE1M4ZT")
#     print(df)
#     print(df.columns)
