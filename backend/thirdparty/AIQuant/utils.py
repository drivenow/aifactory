from xquant.factordata import FactorData
import datetime
import logging
import pandas as pd
import os
import traceback
from xquant.setXquantEnv import xquantEnv
import pymysql1


def logger_handler(task_type, logger_name, base_dir):
    now_date = datetime.datetime.now().strftime("%Y%m%d")
    log_dir = os.path.join(base_dir, "LOG")
    os.makedirs(log_dir, exist_ok=True)
    log_file_name = os.path.join(log_dir, now_date, task_type)
    if not os.path.exists(os.path.join(log_dir, now_date)):
        os.mkdir(os.path.join(log_dir, now_date))
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)  # 设置日志级别
    file_handler = logging.FileHandler(log_file_name)
    file_handler.setLevel(logging.DEBUG)  # 设置文件handler的日志级别

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)  # 设置控制台handler的日志级别

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def check_cur_parse_date():
    fd = FactorData()
    now_date = datetime.datetime.now().strftime("%Y%m%d")
    now_time = datetime.datetime.now().strftime("%H%M%S")
    if "00:00:00" <= now_time <= "18:00:00":
        # 获取前一个交易日
        date_list = fd.tradingday(now_date, -2)
        if now_date in date_list:
            parse_date = date_list[0]
        else:
            parse_date = date_list[-1]
    else:
        # 获取当天交易日
        date_list = fd.tradingday(now_date, -2)
        if now_date in date_list:
            parse_date = now_date
        else:
            parse_date = date_list[-1]
    return parse_date


def standardizeRawCode(raw_code: str) -> str:
    """
    '000600' -> '000600.SZ'
    '688001' -> '688001.SH'
    :param raw_code:
    :return:
    """

    if raw_code[0] == '6':
        return raw_code + '.SH'
    else:
        return raw_code + '.SZ'


class MetaData:

    def __init__(self):
        self.library_df = None
        if xquantEnv == 0:
            sql_config = {"host": "168.64.54.128",
                          "port": 3306,
                          "user": "xquant_data",
                          "password": "gxmlTabkQZ8AahJJeoo5x4Gtkg9YYCAboeLI+ibLp5A=",
                          "db": "xquant_data",
                          "charset": "utf8",
                          "cursorclass": pymysql1.cursors.DictCursor
                          }
        else:
            sql_config = {"host": "168.11.34.94",
                          "port": 3308,
                          "user": "xquant_data",
                          "password": "ZNyoqzrmZ8DN40jcajG5k+fQdNzitAGO3V2B8nB1QZWcnZcmyQhPWC4DvgNnn8ya",
                          "db": "xquant_data",
                          "charset": "utf8",
                          "cursorclass": pymysql1.cursors.DictCursor
                          }
        self.conn = pymysql1.connect(**sql_config)
        self.cursor = self.conn.cursor()

    def query_data(self, sql_use):
        self.cursor.execute(sql_use)
        # "cursorclass": pymysql1.cursors.DictCursor
        # result返回的数据格式是一个列表，列表中的每个元素是一个字典，字典的键是列名，值是对应的数据
        result = self.cursor.fetchall()
        if isinstance(result, tuple):
            result = list(result)
        df = pd.DataFrame(result)
        return df

    def insert_data(self, sql, values):
        try:
            self.cursor.executemany(sql, values)
            self.conn.commit()
            print("insert successed !")
        except Exception as e:
            self.conn.rollback()
            raise Exception(traceback.print_exc())

    def update_sql(self, sql_use):
        try:
            self.cursor.execute(sql_use)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(traceback.print_exc())


    def __del__(self):
        try:
            self.cursor.close()
        except:
            pass
        try:
            self.conn.close()
        except:
            pass

    def __set_library_info(self, refresh=False):
        if self.library_df is None or refresh:
            self.library_df = self.__get_library_df()

    def __get_library_df(self):
        sql = "select factor_name,library_id from aiquant_factor_meta"
        df = self.query_data(sql)
        return df

    def __insert_metadata(self, **kwargs):
        filed_list = []
        value_list = []
        for key, value in kwargs.items():
            filed_list.append(key)
            value_list.append(value)
        fields_str = ",".join(filed_list)

        insert_sql = "insert into aiquant_factor_meta (" + fields_str + ") values (" + ("%s," * len(value_list))[:-1] + ")"

        self.insert_data(insert_sql, [value_list])

    def save_metadata(self, library_id, factor_freq, category, library_describe, factor_info, cover=False):
        """
        存储因子库因子元数据
        :param library_id: 库名
        :param factor_freq: 因子更新频率，季频、日频、分钟频、秒频、全量
        :param category: 分类，因子-factor，整表-table，现有指标-indicator
        :param library_describe: 库描述
        :param factor_info: 因子信息，有如下字段：
        factor_info = {"factor1": {"factor_describe": "（必填）表解释/因子中文名/AI生成的因子逻辑描述",
                               "factor_alias": "（默认为空字符串）因子别名",
                               "classify_level1": "（默认为选股）一级目录",
                               "classify_level2": "（必填）二级目录",
                               "classify_level3": "（必填）三级目录",
                               "unit": "（默认为空字符串）单位",
                               "factor_id": "（必填）和factor_info中的key一样，factor_id和factor_name填的内容默认一样",
                                "factor_status": "（默认TRAIL）TRAIL / RESEARCH / PUBLISH/ 试用/研究(有缓存功数据）/ 对外发布（有缓存有每日更新）",
                            "depend_factor": "（默认为空字符串）依赖因子",
                            "evaluation_metric": "（默认为空字符串）评价指标维度(多个维度用/分割)",
                            "support_scene": "（默认填选股）支持场景，例如查询   选股等，指标台账有",
                            "support_market": "（默认填股票）支持标的类型（股票/债券/基金/指数型/期货/期权）",
                            "remark": "（（必填，对应wiki上因子匹配的场景字段，填入因子解释，同factor_describe，注意跟support_scene字段的区别）对应指标平台台账里面的备注信息",
                            "query_chain": "（必填，按AIQuant的API_TYPE实际情况填, 为取数链路）查询链路类型(xquant/ hive/oracle)",
                            "source": "（必填，按实际情况填，source是资讯，可能对应多种AIQuant中的API_TYPE）因子来源（指标平台/资讯/TAIP/XQUANT）",
                            "source_id": "默认为空字符串，来源数据id，数据源内部的数据id，特指指标平台的data_id",
                            "author": "（默认同source）作者：因子的创建者或维护者"},
                            }
        :return:
        """
        self.__set_library_info(refresh=True)
        assert factor_freq in ["日频", "季频", "分钟频", "秒频", "全量"], "factor_freq根据库因子实际情况填写季频、日频、分钟频、秒频"
        if len(self.library_df[self.library_df['library_id'] == library_id]) > 0:
            print(f"{library_id} 元数据已存在该因子库及因子信息！")
            if cover:
                self.delete_library_info(library_id)
                self.save_metadata(library_id, factor_freq, category, library_describe, factor_info)
            else:
                return
        else:
            if not type(factor_info) == dict:
                raise Exception("factor_info 请传入字典！")
            print(f"category:{category}-library_id：{library_id}元数据开始入库")
            for factor, fac_info in factor_info.items():
                if factor in ['datetime', 'symbol']:
                    raise Exception('因子不允许以{}命名'.format(factor))
                assert isinstance(factor, str), "factor为string类型。"
                assert isinstance(fac_info, dict), "factor_info的value为dict类型。"
                need_fields = ['factor_describe', 'classify_level2',
                               'classify_level3', 'factor_id',
                               'remark', 'query_chain', 'source']
                pass_fields = list(fac_info.keys())
                lack_fields = list(set(need_fields) - set(pass_fields))
                if lack_fields:
                    raise Exception("因子信息缺失：{}".format(",".join(lack_fields)))
                factor_alias = fac_info.get("factor_alias") if fac_info.get("factor_alias") else None
                classify_level1 = fac_info.get("classify_level1") if fac_info.get("classify_level1") else "选股"
                unit = fac_info.get("unit") if fac_info.get("unit") else None
                factor_status = fac_info.get("factor_status") if fac_info.get("factor_status") else "TRAIL"
                support_scene = fac_info.get("support_scene") if fac_info.get("support_scene") else "选股"
                support_market = fac_info.get("support_market") if fac_info.get("support_market") else "股票"
                source_id = fac_info.get("source_id") if fac_info.get("source_id") else None
                depend_factor = fac_info.get("depend_factor") if fac_info.get("depend_factor") else None
                evaluation_metric = fac_info.get("evaluation_metric") if fac_info.get("evaluation_metric") else None
                self.__insert_metadata(library_id=library_id,
                                       factor_id=fac_info["factor_id"],
                                       factor_name=factor,
                                       factor_alias=factor_alias,
                                       classify_level1=classify_level1,
                                       classify_level2=fac_info["classify_level2"],
                                       classify_level3=fac_info["classify_level3"],
                                       factor_freq=factor_freq,
                                       unit=unit,
                                       factor_status=factor_status,
                                       category=category,
                                       library_describe=library_describe,
                                       factor_describe=fac_info["factor_describe"],
                                       support_scene=support_scene,
                                       support_market=support_market,
                                       remark=fac_info["remark"],
                                       query_chain=fac_info["query_chain"],
                                       source=fac_info["source"],
                                       source_id=source_id,
                                       author=fac_info.get("author", fac_info["source"]),
                                       depend_factor=depend_factor,
                                       evaluation_metric=evaluation_metric
                                       )
            print(f"category:{category}-library_id：{library_id}元数据入库完成")

    def delete_library_info(self, library_id):

        sql = "delete from aiquant_factor_meta where library_id='{0}'".format(library_id)
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            print(f'library_id：{library_id}已删除!')
        except:
            self.conn.rollback()
            raise Exception(f'library_id：{library_id}删除失败!')

    def get_metadata(self, library_id=None):
        self.__set_library_info()
        if library_id:
            assert isinstance(library_id, str), "library_id为string类型"
            metadata = self.library_df[self.library_df["library_id"] == library_id]
        else:
            metadata = self.library_df
        return metadata

    def check_factor_metadata(self, df_meta, sync_factors):
        assert isinstance(sync_factors, list), "同步因子为列表形式"
        meta_factors = df_meta["factor_name"].to_list()
        meta_factors.sort()
        sync_factors.sort()
        if sync_factors == meta_factors:
            return True
        else:
            return False
