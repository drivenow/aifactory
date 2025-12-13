import os
import sys

# sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd
import numpy as np
import time
import datetime as dt
import datetime
from xquant.xqutils.helper.link import LinkMessage
from xquant.thirdpartydata.factordata import FactorData as third_FD
from xquant.thirdpartydata.fic_api_data import FicApiData
from xquant.factordata.factor import FactorData
from AIQuant.utils import check_cur_parse_date, logger_handler, MetaData
from AIQuant.configs import config_list


class SyncZXDataByDate:
    def __init__(self, table_name=None):
        # table_name可以为string类型或list类型
        self.task_list = []
        for config in config_list:
            if config.API_TYPE.lower() == "zx":
                lib_id = config.LIB_ID
                assert config.LIB_ID, "同步数据配置必须包含库名或表名，如：ZX_STKDEPTTRADINFO"
                condition_dct = config.API_KWARGS
                assert "resource" in condition_dct, "同步数据的条件必须包含库名或表名，如：ZX_STKDEPTTRADINFO"
                if isinstance(table_name, str):
                    if lib_id.lower() == table_name.lower():
                        self.task_list.append(config)
                    else:
                        print(f"{table_name} is not update by date or not in config.")
                elif isinstance(table_name, list):
                    for i in table_name:
                        if lib_id.lower() == i.lower():
                            self.task_list.append(config)
                        else:
                            print(f"{i} is not update by date or not in config.")
                else:
                    self.task_list.append(config)
        if len(self.task_list) == 0:
            raise Exception("没有符合条件的wind的任务配置信息!")

        config = self.task_list[0]
        self.link_ids = config.LINK_IDS
        self.base_dir = config.TABLE_BASE_PATH

        self.link_message = LinkMessage(user_ids=self.link_ids)
        self.logger = logger_handler("SyncZXDataByDate", "sync-zx-data-bydate.log", self.base_dir)
        self.tfd = third_FD()
        self.fd = FactorData()
        self.fad = FicApiData()
        # self.md = MetaData()
        self.today_date = check_cur_parse_date()

    def ticker_match(self, ticker_num):
        ticker_num = str(ticker_num)
        ticker = ticker_num.zfill(6)
        if ticker.startswith("6") or ticker.startswith("900"):
            suffix = ".SH"
        elif ticker.startswith("0") or ticker.startswith("3") or ticker.startswith("2"):
            suffix = ".SZ"
        elif ticker.startswith("8") or ticker.startswith("9") or ticker.startswith("43"):
            suffix = ".BJ"
        else:
            suffix = ""
        ticker = ticker + suffix
        return ticker

    # 运行前的校验，校验接口是否准备好了数据
    def check_wind_data_before_start(self):
        error_list = []
        for config in self.task_list:
            lib_id = config.LIB_ID
            self.logger.info(f"开始运行前检查:{lib_id}")
            API_INDEX_COL = config.API_INDEX_COL
            date_col_name = ""
            for key, value in API_INDEX_COL.items():
                if value == "datetime":
                    date_col_name = key
            if not date_col_name:
                raise Exception(f"{lib_id} 未配置日期映射：API_INDEX_COL")
            condition_dct = config.API_KWARGS
            df_p = self.fad.get_fic_api_data(**condition_dct)['data']
            if df_p.empty and date_col_name in ['TRADE_DT']:
                # self.link_message.sendMessage(
                #    f"[交易室-Alpha研究框架][WINDByDate]以下表无数据：{table_name}-{self.today_date}")
                error_list.append(f"{lib_id}-{self.today_date}")

            else:
                self.logger.info(f"运行前检查通过:{lib_id}-{self.today_date}")
        return error_list

    # 更新完成并且校验通过之后,生成一个标志文件
    def gen_flag(self, parse_date, table_name):
        # TODO 暂时取消，确定路径后添加
        TABLE_BASE_PATH = self.task_list[0].TABLE_BASE_PATH
        flag_path = os.path.join(TABLE_BASE_PATH, "FLAG", parse_date)
        if not os.path.exists(flag_path):
            os.makedirs(flag_path)
        flag_name = os.path.join(flag_path, f"{table_name}.success")
        with open(flag_name, "w") as f:
            pass
        return

    # 每日更新完成之后的校验
    def check_panel_wind_data(self):
        self.logger.info(f"运行完成检查开始:{self.today_date}")

        error_list = []
        month = self.today_date[:6]
        for config in self.task_list:
            TABLE_BASE_PATH = config.TABLE_BASE_PATH
            lib_id = config.LIB_ID
            table_path = os.path.join(TABLE_BASE_PATH, month)
            date_col = "datetime"
            file_path = os.path.join(table_path, f"{lib_id}.parquet")
            if not os.path.exists(file_path):
                error_list.append("{}_{}".format(lib_id, self.today_date))
            else:
                df = pd.read_parquet(file_path)
                if df[df[date_col] == self.today_date].shape[0] == 0:
                    error_list.append("{}_{}".format(lib_id, self.today_date))
                else:
                    self.gen_flag(parse_date=self.today_date, table_name=lib_id)
        self.logger.info(f"运行完成检查完成:{self.today_date}")

        return error_list

    # 每日更新数据
    def run_daily(self):
        # 更新前校验接口是否准备好了数据
        ready_flag = False
        s_checktime = datetime.datetime.now()
        time_delta = datetime.timedelta(minutes=30)  # 没有数据时持续校验30分钟
        e_checktime = s_checktime + time_delta
        while not ready_flag and datetime.datetime.now() < e_checktime:
            error_list = self.check_wind_data_before_start()
            if len(error_list) == 0:
                ready_flag = True
            # 一分钟巡检一次
            else:
                self.logger.info(f"运行前检查不通过，等待一分钟:{str(error_list)}")
                time.sleep(60)

        # 每日更新
        self.total_sync(init_date=self.today_date, end_date=self.today_date)
        before_date = dt.datetime.strptime(self.today_date, "%Y%m%d") + dt.timedelta(days=-1)
        before_date = before_date.strftime("%Y%m%d")
        self.total_sync(init_date=before_date, end_date=before_date)

        # 更新完成后校验数据是否缺失
        error_list = self.check_panel_wind_data()
        if error_list:
            error_log = ",".join(error_list[:5])
            error_log_all = ",".join(error_list)
            self.logger.info("SyncByDateStrategy存在未更新数据的表：{}".format(error_log_all))
            self.link_message.sendMessage("[交易室-Alpha研究框架][ZX]未更新数据的表：{} 等。".format(error_log))
        else:
            self.link_message.sendMessage("[交易室-Alpha研究框架][ZX]表更新成功")

    def __get_data(self, date_col_name, date, data_condition):
        # 接口不稳定 需要多次访问获取数据,最大尝试次数为5次
        retry_time = 0
        flag = False
        df_p = pd.DataFrame()
        resource = data_condition["resource"]
        while retry_time < 3 and not flag:
            try:
                df_p = self.fad.get_fic_api_data(**data_condition)['data']
                if "TRADINGCODE" in df_p.columns:
                    df_p['TRADINGCODE'] = df_p['TRADINGCODE'].apply(lambda x: self.ticker_match(x))

                flag = True
                self.logger.info(f"{resource}-{date} get data num: {len(df_p)}")
            except Exception as e:
                import traceback
                self.logger.warning(
                    f"{resource}-{date}-{date} 接口获取数据失败，自动重试{retry_time}！")
            finally:
                retry_time += 1
        if len(df_p) > 0:
            df_p[date_col_name] = df_p[date_col_name].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000))
            # 只更新当天，不更新历史
            if df_p.dtypes[date_col_name] == 'object':
                df_p[date_col_name] = df_p[date_col_name].apply(lambda x: x[:10].replace('-', ''))
            elif df_p.dtypes[date_col_name] == 'datetime64[ns]':
                df_p[date_col_name] = df_p[date_col_name].apply(lambda x: x.strftime("%Y%m%d"))
            else:
                raise Exception(f"{resource} 的日期字段类型是 {df_p.dtypes[date_col_name]}，需处理")
            df_p = df_p[df_p[date_col_name].isin([date])]
        return df_p

    def total_sync(self, init_date=None, end_date=None, cover=True):
        for config in self.task_list:
            API_INDEX_COL = config.API_INDEX_COL
            condition_dct = config.API_KWARGS
            lib_id = config.LIB_ID
            resource = condition_dct["resource"]
            date_col_name = ""
            for key, value in API_INDEX_COL.items():
                if value == "datetime":
                    date_col_name = key
            if not date_col_name:
                raise Exception(f"{lib_id} 未配置日期映射：API_INDEX_COL")
            if init_date is None or end_date is None:
                start_date_table = self.today_date
                end_date_table = self.today_date
            else:
                start_date_table = init_date
                end_date_table = end_date
            self.logger.info(f"Total syncing daily [{lib_id}] from {init_date} - {end_date}")

            date_list = self.fd.tradingday(start_date_table, end_date_table)
            if len(date_list) == 0:
                continue
            # start_date_table==self.today_date时 用原始的data_condition，否则重新构建
            # 存储数据，存储目录都以月份为一级目录
            TABLE_BASE_PATH = config.TABLE_BASE_PATH
            # 按月来存储数据
            func_save = config.save_table_data_bydate
            if start_date_table == self.today_date:
                df_today = self.__get_data(date_col_name=date_col_name,
                                           date=self.today_date, data_condition=config.API_KWARGS)
                if df_today.shape[0] == 0:
                    continue
                # 有数据的话按年存储到一个字典里
                else:
                    func_save(df_data=df_today, date_col_name=date_col_name, out_path=TABLE_BASE_PATH,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")
            else:
                # 同步日期字段与存储日期字段一致
                df_list = []
                for date in date_list:
                    # 按date_condition_str获取数据 按date_col_name存储 将一年的数据汇总成一个dataframe 然后打开文件更新
                    data_condition = {"resource": resource, "paramMaps": {date_col_name: f"{date}"}, "rownum": 10000}
                    df_p = self.__get_data(date_col_name=date_col_name,
                                           date=date, data_condition=data_condition)
                    # 如果没有数据或while5次都没取到数据 则跳过这一天
                    if df_p.shape[0] == 0:
                        continue
                    else:
                        # 有数据的话按月存储到一个字典里
                        df_list.append(df_p)
                if df_list:
                    df = pd.concat(df_list, ignore_index=True)
                    func_save(df_data=df, date_col_name=date_col_name, out_path=TABLE_BASE_PATH,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")


if __name__ == '__main__':
    swd = SyncZXDataByDate()
    # swd.total_sync(init_date='20251017', end_date='20251114', cover=True)
    # 每日更新数据
    swd.run_daily()

    # 补指定表名或多个表 指定日期区间的数据
    # for table_name_1 in [ 'ZX_STKDEPTTRADINFO',]:
    #     swd = SyncZXDataByDate(table_name=[table_name_1])
    #     swd.total_sync(init_date="20180101", end_date="20250613", cover=True)
