import sys
import os
# sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import time
import pandas as pd
import datetime

from xquant.xqutils.helper.link import LinkMessage
from xquant.factordata.factor import FactorData
from AIQuant.utils import check_cur_parse_date, logger_handler, MetaData
from AIQuant.configs import config_list
from AIQuant.data_api.index_platform_data import IndicatorData


class SyncIndicatorData:
    def __init__(self, table_name=None):
        # table_name可以为string类型或list类型
        self.task_list = []
        for config in config_list:
            if config.API_TYPE.lower() in ["indicator", "indicator_min"]:
                lib_id = config.LIB_ID
                assert lib_id, "同步数据配置必须包含库名或表名，如：INDEX_PLATFORM_1"
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
        self.base_dir = config.FACTOR_BASE_PATH
        self.ida = IndicatorData()
        self.fd = FactorData()
        self.md = MetaData()
        self.link_message = LinkMessage(user_ids=self.link_ids)
        self.logger = logger_handler("SyncIndicatorData", "sync-indicator-data-bydate.log", self.base_dir)
        self.today_date = check_cur_parse_date()

    # 运行前的校验，校验接口是否准备好了数据
    def check_indicator_data_before_start(self):
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
            data_condition = {}
            for key, value in condition_dct.items():
                if key != "library_name":
                    data_condition[key] = value
            if config.API_TYPE.lower() == "indicator_min":
                df_p = self.ida.get_min_indicator_data(**data_condition)
            else:
                df_p = self.ida.get_indicator_data(**data_condition)
            if df_p.empty:
                error_list.append(f"{lib_id}-{self.today_date}")
            else:
                self.logger.info(f"运行前检查通过:{lib_id}-{self.today_date}")
        return error_list

    # 更新完成并且校验通过之后,生成一个标志文件
    def gen_flag(self, parse_date, table_name):
        flag_path = os.path.join(self.base_dir, "FLAG", parse_date)
        if not os.path.exists(flag_path):
            os.makedirs(flag_path)
        flag_name = os.path.join(flag_path, f"{table_name}.success")
        with open(flag_name, "w") as f:
            pass
        return

    # 每日更新完成之后的校验
    def check_panel_indicator_data(self):
        self.logger.info(f"运行完成检查开始:{self.today_date}")

        error_list = []
        month = self.today_date[:6]
        for config in self.task_list:
            lib_id = config.LIB_ID
            table_path = os.path.join(self.base_dir, month)
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
        # 更新前校验接口是否准备好了数据
        ready_flag = False
        s_checktime = datetime.datetime.now()
        # TODO：调试
        time_delta = datetime.timedelta(minutes=30)  # 没有数据时持续校验30分钟
        e_checktime = s_checktime + time_delta
        while not ready_flag and datetime.datetime.now() < e_checktime:
            error_list = self.check_indicator_data_before_start()
            if len(error_list) == 0:
                ready_flag = True
            # 一分钟巡检一次
            else:
                self.logger.info(f"运行前检查不通过，等待一分钟:{str(error_list)}")
                # TODO：调试
                time.sleep(60)

        # 每日更新
        self.total_sync(init_date=self.today_date, end_date=self.today_date)

        # 更新完成后校验数据是否缺失
        error_list = self.check_panel_indicator_data()
        if error_list:
            error_log = ",".join(error_list[:5])
            error_log_all = ",".join(error_list)
            self.logger.info("SyncIndicatorData存在未更新数据的表：{}".format(error_log_all))
            self.link_message.sendMessage("[交易室-Alpha研究框架][SyncIndicatorData]未更新数据的表：{} 等。".format(error_log))
        else:
            self.link_message.sendMessage("[交易室-Alpha研究框架][SyncIndicatorData]表更新成功")

    def __get_data(self, data_condition, config):
        # wind接口不稳定 需要多次访问获取数据,最大尝试次数为5次
        retry_time = 1
        flag = False
        df_p = pd.DataFrame()
        lib_id = config.LIB_ID
        condition_dct = {}
        for key, value in data_condition.items():
            if key != "library_name":
                condition_dct[key] = value
        while retry_time < 5 and not flag:
            try:
                if config.API_TYPE.lower() == "indicator_min":
                    df_p = self.ida.get_min_indicator_data(stock_all=True, **condition_dct)
                else:
                    df_p = self.ida.get_indicator_data(**condition_dct)
                flag = True
                self.logger.info(f"{lib_id}-get data num: {len(df_p)}")
            except Exception as e:
                self.logger.warning(
                    f"{lib_id}-接口获取数据失败，自动重试第{retry_time}次！")
            finally:
                retry_time += 1
                time.sleep(5)
        return df_p

    def total_sync(self, init_date=None, end_date=None, cover=True):
        t = 0
        for config in self.task_list:
            API_INDEX_COL = config.API_INDEX_COL
            condition_dct = config.API_KWARGS
            lib_id = config.LIB_ID

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
            # 按月来存储数据
            func_save = config.save_factor_data_bydate
            if start_date_table == self.today_date:
                df = self.__get_data(data_condition=config.API_KWARGS, config=config)
                if len(df) == 0:
                    continue
                else:
                    func_save(df_data=df, date_col_name=date_col_name, out_path=self.base_dir,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")
            else:
                df_list = []
                for date in date_list:
                    data_condition = {}
                    for key, value in config.API_KWARGS.items():
                        if key == "date":
                            data_condition[key] = date
                        else:
                            data_condition[key] = value
                    df_p = self.__get_data(data_condition=data_condition, config=config)
                    if len(df_p) == 0:
                        continue
                    else:
                        df_list.append(df_p)
                if df_list:
                    df = pd.concat(df_list, ignore_index=True)
                    func_save(df_data=df, date_col_name=date_col_name, out_path=self.base_dir,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")


if __name__ == "__main__":
    sid = SyncIndicatorData()
    # # 补所有历史数据
    # sid.total_sync(init_date="20251112", end_date="20251113")
    # # 每日更新数据
    sid.run_daily()
