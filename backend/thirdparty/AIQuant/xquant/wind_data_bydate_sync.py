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
from xquant.thirdpartydata.factordata import FactorData as third_FD
from xquant.factordata.factor import FactorData
from AIQuant.utils import check_cur_parse_date, logger_handler, MetaData
from AIQuant.configs import config_list


class SyncWindDataByDate:
    def __init__(self, table_name=None):
        # table_name可以为string类型或list类型
        self.task_list = []
        for config in config_list:
            if config.API_TYPE.lower() == "wind":
                lib_id = config.LIB_ID
                assert lib_id, "同步数据配置必须包含库名或表名，如：ASHAREEODPRICES"
                condition_dct = config.API_KWARGS
                assert "library_name" in condition_dct, "同步数据的条件必须包含库名或表名，如：WIND_ASHAREEODPRICES"
                if isinstance(table_name, str):
                    if lib_id.lower() == table_name.lower():
                        self.task_list.append(config)
                    else:
                        print(f"{lib_id} is not update by date or not in config.")
                elif isinstance(table_name, list):
                    for i in table_name:
                        if lib_id.lower() == i.lower():
                            self.task_list.append(config)
                        else:
                            print(f"{lib_id} is not update by date or not in config.")
                else:
                    self.task_list.append(config)
        if len(self.task_list) == 0:
            raise Exception("没有符合条件的wind的任务配置信息!")

        config = self.task_list[0]
        self.link_ids = config.LINK_IDS
        self.base_dir = config.TABLE_BASE_PATH

        self.link_message = LinkMessage(user_ids=self.link_ids)
        self.logger = logger_handler("SyncWindDataByDate", "sync-wind-data-bydate.log", self.base_dir)
        self.tfd = third_FD()
        self.fd = FactorData()
        # self.md = MetaData()
        self.today_date = check_cur_parse_date()

    # 运行前的校验，校验接口是否准备好了数据
    def check_wind_data_before_start(self):
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
            df_p = self.tfd.get_factor_value(**condition_dct)
            if df_p.empty and date_col_name in ['TRADE_DT']:
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
    def check_panel_wind_data(self):
        self.logger.info(f"运行完成检查开始:{self.today_date}")
        error_list = []
        month = self.today_date[:6]
        for config in self.task_list:
            TABLE_BASE_PATH = config.TABLE_BASE_PATH
            lib_id = config.LIB_ID

            table_path = os.path.join(TABLE_BASE_PATH, month)
            API_INDEX_COL = config.API_INDEX_COL
            date_col = ""
            for key, value in API_INDEX_COL.items():
                if value == "datetime":
                    date_col = key
            if not date_col:
                raise Exception(f"{lib_id} 未配置日期映射：API_INDEX_COL")
            if date_col in ['TRADE_DT']:
                date_col = 'datetime'
                file_path = os.path.join(table_path, f"{lib_id}.parquet")
                if not os.path.exists(file_path):
                    error_list.append("{}_{}".format(lib_id, self.today_date))
                else:
                    df = pd.read_parquet(file_path)
                    if df[df[date_col] == self.today_date].shape[0] == 0:
                        error_list.append("{}_{}".format(lib_id, self.today_date))
                    else:
                        # 每个表数据更新完成则增加标志位
                        self.gen_flag(parse_date=self.today_date, table_name=lib_id)
            else:
                # TODO
                continue
        self.logger.info(f"运行完成检查完成:{self.today_date}")

        return error_list

    # 每日更新数据
    def run_daily(self):
        # 更新前校验接口是否准备好了数据
        ready_flag = False
        s_checktime = datetime.datetime.now()
        # TODO：调试
        time_delta = datetime.timedelta(minutes=2)  # 没有数据时持续校验30分钟
        e_checktime = s_checktime + time_delta
        while not ready_flag and datetime.datetime.now() < e_checktime:
            error_list = self.check_wind_data_before_start()
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
        error_list = self.check_panel_wind_data()
        if error_list:
            error_log = ",".join(error_list[:5])
            error_log_all = ",".join(error_list)
            self.logger.info("SyncByDateStrategy存在未更新数据的表：{}".format(error_log_all))
            self.link_message.sendMessage("[交易室-Alpha研究框架][WindByDate]未更新数据的表：{} 等。".format(error_log))
        else:
            self.link_message.sendMessage("[交易室-Alpha研究框架][WindByDate]表更新成功")

    def __get_data(self, date_col_name, date, data_condition):
        # wind接口不稳定 需要多次访问获取数据,最大尝试次数为5次
        retry_time = 0
        flag = False
        df_p = pd.DataFrame()
        library_name = data_condition["library_name"]
        while retry_time < 5 and not flag:
            try:
                df_p = self.tfd.get_factor_value(**data_condition)
                flag = True
                self.logger.info(f"{library_name}-{date} get data num: {len(df_p)}")
            except Exception as e:
                self.logger.warning(
                    f"{library_name}-{date}-{date} 接口获取数据失败，自动重试{retry_time}！")
                if "50W" in str(e):
                    self.logger.info(f"{library_name}-{date}-{date}数据超过50W，获取数据失败请关注！")
                    df_p_list = []
                    dt_conds = [['<=20121231'], ['>=20130101', '<=20151231'], ['>=20160101', '<=20181231'],
                                ['>=20190101', '<=20211231'], ['>=20220101', '<=20241231'], ['>=20250101', '<=20250827'],
                                ['>=20250828', '<=20250829'], ['>=20250830']]
                    for dt_cond in dt_conds:
                        cond_str = "{'" + date_col_name + "': " + str(dt_cond) + "}"
                        cond = eval(cond_str)
                        try:
                            df = self.tfd.get_factor_value(library_name, OPDATE=[date], **cond)
                        except:
                            self.logger.info(f"{library_name}-{date}-{date}拆分后仍存在大于50W行的情况，手动处理！")
                            df = pd.DataFrame()
                        if len(df) > 0:
                            df_p_list.append(df)
                    if len(df_p_list) > 0:
                        df_p = pd.concat(df_p_list)
                    else:
                        df_p = pd.DataFrame()
                    # # TODO 是否需要补全SH SZ后缀，wind大部分表是有后缀的
                    # if "TRADINGCODE" in df_p.columns:
                    #     #
                    #     df_p['TRADINGCODE'] = df_p['TRADINGCODE'].apply(lambda x: self.ticker_match(x))
                    break
            finally:
                retry_time += 1
        return df_p

    def total_sync(self, init_date=None, end_date=None, cover=True):
        t = 0
        for config in self.task_list:
            API_INDEX_COL = config.API_INDEX_COL
            condition_dct = config.API_KWARGS
            library_name = condition_dct["library_name"]
            lib_id = config.LIB_ID
            # metadata = self.md.get_metadata(library_id=lib_id)
            # if len(metadata) > 0:
            #     # 已存在元数据则判断元数据库中的信息与正在落地的是否一致
            #     check_res = self.md.check_factor_metadata(metadata, [lib_id])
            #     assert check_res, f"当前同步的{lib_id}信息已存入元数据库，但是当前同步的因子与库中信息不一致！"
            # else:
            #     factor_info = {lib_id: "wind表"}
            #     self.md.save_metadata(library_id=lib_id, factor_freq="Daily", library_describe="wind源表",
            #                           factor_info=factor_info, category="table")

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
                                           date=self.today_date, data_condition=config.API_KWARGS)
                if df_today.shape[0] == 0:
                    continue
                # 有数据的话按年存储到一个字典里
                else:
                    func_save(df_data=df_today, date_col_name=date_col_name, out_path=TABLE_BASE_PATH,
                              lib_id=lib_id, cover=cover)
                    self.logger.info(f"{lib_id} update success {date_list[0]}-{date_list[-1]}")
            else:
                sync_date_field = ""
                for key, value in condition_dct.items():
                    if key != "library_name" and isinstance(value, list):
                        sync_date_field = key
                df_list = []
                for date in date_list:
                    # 按date_condition_str获取数据 按date_col_name存储 将一年的数据汇总成一个dataframe 然后打开文件更新
                    sdate, edate = date, date  # 不能删
                    if 'OPDATE' in condition_dct:
                        edate_time = dt.datetime.strptime(sdate, "%Y%m%d") + dt.timedelta(days=1)
                        edate = edate_time.strftime("%Y%m%d")
                        sdate = (dt.datetime.strptime(sdate, "%Y%m%d") - dt.timedelta(days=1)).strftime("%Y%m%d")
                    data_condition = {"library_name": library_name, sync_date_field: [f">={sdate}", f"<={edate}"]}
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
    swd = SyncWindDataByDate()
    # # 补所有历史数据
    # swd.total_sync(init_date="20180101", end_date="20250519", cover=True)
    swd.total_sync(init_date="20021201", end_date="20021231", cover=True)
    # 每日更新数据
    # swd.run_daily()

    # 补指定表名或多个表 指定日期区间的数据
    # WIND_AShareIncome  WIND_AShareCashFlow WIND_AShareTTMAndMRQ WIND_AShareTTMHis
#    table_list = ["WIND_ASHAREBLOCKTRADE","WIND_ASHAREEXRIGHTDIVIDENDRECORD","WIND_ASHAREAUCTION","WIND_ASHAREEQUITYPLEDGEINFO","WIND_ASHARESTOCKRATINGCONSUS","WIND_ASHAREFLOATHOLDER","WIND_ASHAREINSIDERTRADE","WIND_ASHAREPROSECUTION","WIND_ASHAREMJRHOLDERTRADE","WIND_ASAREPLANTRADE","WIND_ASHAREINSIDEHOLDER","WIND_ASHAREINCDESCRIPTION",]
#    table_list += ["WIND_ASHARESTAFF","WIND_ASHAREMANAGEMENTHOLDREWARD","WIND_ASHAREINCEXECQTYPRI","WIND_ASHAREESOPTRADINGINFO","WIND_ASHAREESOPDESCRIPTION","WIND_ASHAREMARGINGUARANTEE","WIND_ASHAREMARGINTRADE","WIND_ASHARESTIBINVESTMENTIENDING","WIND_ASHARESTOCKREPO","WIND_ASHAREHOLDERSMEETING","WIND_ASHAREMAJOREVENT","WIND_ASHAREOFFERFOROFFER",]
#    print(len(table_list))
#    for table_name_1 in ['WIND_HKOptionEODPrices']:
#        swd = SyncWindDataByDate(table_name=[table_name_1])
#        swd.total_sync(init_date="20250101", end_date="20250415", cover=True)
##        swd.total_sync(init_date="20220101", end_date="20221231", cover=True)
##        swd.total_sync(init_date="20230101", end_date="20231231", cover=True)
#        swd.total_sync(init_date="20240101", end_date="20240630", cover=True)
#        swd.total_sync(init_date="20240701", end_date="20241231", cover=True)
#        swd.total_sync(init_date="20210101", end_date="20211231", cover=True)
#        swd.total_sync(init_date="20200101", end_date="20201231", cover=True)
#        swd.total_sync(init_date="20180101", end_date="20191231", cover=True)
