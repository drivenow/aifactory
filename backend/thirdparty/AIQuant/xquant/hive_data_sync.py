import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import configparser
import pandas as pd
import numpy as np

pd.set_option("display.width", None)
import time
import datetime as dt
from collections import defaultdict
from typing import Dict, List
import datetime
from xquant.xqutils.helper.link import LinkMessage
from xquant.factordata.factor import FactorData
from AIQuant.utils import check_cur_parse_date, logger_handler, MetaData
from AIQuant.configs import config_list
from AIQuant.data_api.hive_data import get_hive_data


class SyncHiveDataByDate:
    def __init__(self, table_name=None):
        # table_name可以为string类型或list类型
        self.task_list = []
        for config in config_list:
            if config.API_TYPE.lower() == "hive":
                lib_id = config.LIB_ID
                assert lib_id, "同步数据配置必须包含库名或表名，如：FND_FEERATECHANGE"
                condition_dct = config.API_KWARGS
                assert "library_name" in condition_dct, "同步数据的条件必须包含库名或表名，如：SRC_CENTER_ADMIN.stk_blocktrade"
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
        self.logger = logger_handler("SyncHIveDataByDate", "sync-hive-data-bydate.log", self.base_dir)
        self.fd = FactorData()
        # self.md = MetaData()
        self.today_date = check_cur_parse_date()


    # 运行前的校验，校验接口是否准备好了数据
    def check_hive_data_before_start(self):
        error_list = []
        i = 0
        for config in self.task_list:
            i += 1
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
            df_p =get_hive_data(**condition_dct)
            if df_p.empty and date_col_name in ['TRADE_DT']:
                # self.link_message.sendMessage(
                #    f"[交易室-Alpha研究框架][PRODUCTINFOByDate]以下表无数据：{table_name}-{self.today_date}")
                error_list.append(f"{lib_id}-{self.today_date}")
            else:
                self.logger.info(f"运行前检查通过:{lib_id}-{self.today_date}")
        return error_list

    # 更新完成并且校验通过之后,生成一个标志文件
    def gen_flag(self, parse_date, table_name):
        TABLE_BASE_PATH = self.task_list[0].TABLE_BASE_PATH
        flag_path = os.path.join(TABLE_BASE_PATH, "FLAG", parse_date)
        if not os.path.exists(flag_path):
            os.makedirs(flag_path)
        flag_name = os.path.join(flag_path, f"{table_name}.success")
        with open(flag_name, "w") as f:
            pass
        return

    # 每日更新完成之后的校验
    def check_panel_hive_data(self):
        self.logger.info(f"运行完成检查开始:{self.today_date}")
        error_list = []
        month = self.today_date[:6]
        for config in self.task_list:
            TABLE_BASE_PATH = config.TABLE_BASE_PATH
            lib_id = config.LIB_ID
            table_path = os.path.join(TABLE_BASE_PATH, month)
            date_col = 'datetime'
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
        # 每日更新
        self.total_sync(init_date=self.today_date, end_date=self.today_date)

        # 更新完成后校验数据是否缺失
        error_list = self.check_panel_hive_data()
        if error_list:
            error_log = ",".join(error_list[:5])
            error_log_all = ",".join(error_list)
            self.logger.info("SyncByDateStrategy存在未更新数据的表：{}".format(error_log_all))
            self.link_message.sendMessage("[交易室-Alpha研究框架][HiveByDate]未更新数据的表：{} 等。".format(error_log))
        else:
            self.link_message.sendMessage("[交易室-Alpha研究框架][HiveByDate]表更新成功")
            # self.gen_flag(self.today_date)

    def __get_data(self, date_col_name, date, data_condition, config):
        retry_time = 0
        flag = False
        df_p = pd.DataFrame()
        library_name = data_condition["library_name"]
        while retry_time < 5 and not flag:
            try:
                df_p = get_hive_data(**data_condition)
                flag = True
                self.logger.info(f"{library_name}-{date} get data num: {len(df_p)}")
            except Exception as e:
                self.logger.warning(
                    f"{library_name}-{date}-{date} 接口获取数据失败，自动重试{retry_time}！")
                time.sleep(10)
                if "查询超时" in str(e):
                    self.logger.warning(f"{library_name}-{date}-{date}查询超时，获取数据失败请关注！")
                    break
            finally:
                retry_time += 1
        return df_p

    def total_sync(self, init_date=None, end_date=None, cover=True):
        t = 0
        for config in self.task_list:
            API_INDEX_COL = config.API_INDEX_COL
            condition_dct = config.API_KWARGS
            lib_id = config.LIB_ID
            library_name = condition_dct["library_name"]

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
            t += 1
            self.logger.info(
                f"{t}/{len(self.task_list)} - Total syncing daily [{lib_id}] from {init_date} - {end_date}")

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
                                           date=self.today_date, data_condition=config.API_KWARGS,
                                           config=config)
                if df_today.shape[0] == 0:
                    continue
                # 有数据的话按年存储到一个字典里
                else:
                    df_today[date_col_name] = df_today[date_col_name].astype(str)
                    df_today[date_col_name] = df_today[date_col_name].apply(pd.to_datetime)
                    df_today[date_col_name] = df_today[date_col_name].apply(lambda x: dt.datetime.strftime(x, "%Y%m%d"))
                    func_save(df_data=df_today, date_col_name=date_col_name, out_path=TABLE_BASE_PATH,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")
            else:
                sync_date_field = ""
                for key, value in condition_dct.items():
                    if key != "library_name":
                        sync_date_field = key
                df_list = []
                for date in date_list:
                    start_time = date[:4] + "-" + date[4:6] + "-" + date[6:8] + " 00:00:00"
                    end_time = date[:4] + "-" + date[4:6] + "-" + date[6:8] + " 23:59:59"
                    data_condition = {"library_name": library_name, sync_date_field: [f">={start_time}", f"<={end_time}"]}
                    df_p = self.__get_data(date_col_name=date_col_name,
                                           date=date, data_condition=data_condition,
                                           config=config)
                    # 如果没有数据或while5次都没取到数据 则跳过这一天
                    if df_p.shape[0] == 0:
                        continue
                    else:
                        # 有数据的话按月存储到一个字典里
                        df_list.append(df_p)
                if df_list:
                    df = pd.concat(df_list, ignore_index=True)
                    df[date_col_name] = df[date_col_name].astype(str)
                    df[date_col_name] = df[date_col_name].apply(pd.to_datetime)
                    df[date_col_name] = df[date_col_name].apply(lambda x: dt.datetime.strftime(x, "%Y%m%d"))
                    func_save(df_data=df, date_col_name=date_col_name, out_path=TABLE_BASE_PATH,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")

    def total_sync_all(self, init_date, end_date, cover=True):
        t = 0
        for config in self.task_list:
            API_INDEX_COL = config.API_INDEX_COL
            condition_dct = config.API_KWARGS
            lib_id = config.LIB_ID
            library_name = condition_dct["library_name"]

            date_col_name = ""
            for key, value in API_INDEX_COL.items():
                if value == "datetime":
                    date_col_name = key
            if not date_col_name:
                raise Exception(f"{lib_id} 未配置日期映射：API_INDEX_COL")
            start_date_table = init_date
            end_date_table = end_date
            t += 1
            self.logger.info(
                f"{t}/{len(self.task_list)} - Total syncing daily [{lib_id}] from {init_date} - {end_date}")

            date_list = self.fd.tradingday(start_date_table, end_date_table)
            if len(date_list) == 0:
                continue
            # start_date_table==self.today_date时 用原始的data_condition，否则重新构建
            # 存储数据，存储目录都以月份为一级目录
            TABLE_BASE_PATH = config.TABLE_BASE_PATH
            # 按月来存储数据
            func_save = config.save_table_data_bydate
            sync_date_field = ""
            for key, value in condition_dct.items():
                if key != "library_name":
                    sync_date_field = key
            start_time = init_date[:4] + "-" + init_date[4:6] + "-" + init_date[6:8] + " 00:00:00"
            end_time = end_date[:4] + "-" + end_date[4:6] + "-" + end_date[6:8] + " 23:59:59"
            data_condition = {"library_name": library_name, sync_date_field: [f">={start_time}", f"<={end_time}"]}
            df_all = self.__get_data(date_col_name=date_col_name,
                                   date=init_date, data_condition=data_condition,
                                   config=config)
            if len(df_all) > 0:
                df_all[date_col_name] = df_all[date_col_name].astype(str)
                df_all[date_col_name] = df_all[date_col_name].apply(pd.to_datetime)
                df_all[date_col_name] = df_all[date_col_name].apply(lambda x: dt.datetime.strftime(x, "%Y%m%d"))
                func_save(df_data=df_all, date_col_name=date_col_name, out_path=TABLE_BASE_PATH,
                          lib_id=lib_id, cover=cover)
                self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")



if __name__ == '__main__':
    swd = SyncHiveDataByDate(table_name=['STK_ASHAREFREEFLOATCALENDAR',
                                         'STK_SEOWIND',
                                         'STK_ASHARESTOCKREPO'])
    # # 补所有历史数据
    swd.total_sync_all(init_date="20241201", end_date="20251203", cover=True)
    # 每日更新数据
    # swd.run_daily()




