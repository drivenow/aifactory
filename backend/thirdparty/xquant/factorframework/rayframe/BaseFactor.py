# -*- coding: utf-8 -*-

"""Base Factor"""
import os
from typing import Dict, Optional

import pandas as pd
import ray
from tqdm import trange

from xquant.factorframework.rayframe.aiquant_adapter import AIQuantDataAdapter
from xquant.factorframework.rayframe.util.data_context import get_trade_days, get_stocks_pool
from xquant.factorframework.rayframe.util.util import get_factor_attr, parse_extra_data
# from xquant.factorframework.rayframe import get_custom_factor_class
from xquant.factorframework.rayframe.calculation.helper import set_ray_options, get_docker_memory
try:
    from xquant.factorframework.rayframe.FactorDebug import run_day_factor_value
except Exception:  # pragma: no cover - 调试工具缺依赖时置为 None
    run_day_factor_value = None
from xquant.factorframework.rayframe.MetaFactor import MetaBaseFactor
from xquant.factorframework.rayframe.util.event_trace import event_trace
try:
    from xquant.factorframework.rayframe.mkdata.DFSDataLoader import get_panel_min_data_dfs, get_daily_data_from_dfs, get_ori_min_data_dfs
except Exception:  # pragma: no cover - 缺依赖时提供空实现
    def get_panel_min_data_dfs(*args, **kwargs):
        return {}

    def get_daily_data_from_dfs(*args, **kwargs):
        return {}

    def get_ori_min_data_dfs(*args, **kwargs):
        return pd.DataFrame()

avaliable_shared_memory = get_docker_memory()


class Factor(object):
    """因子基类
    所有因子的定义都应继承自本类，并重写 calc 方法
    类属性
    factor_type:   因子类型 ： 分日频(DAY)和高频  (MIN, TICK) 三种
    factor_name:   因子的名称。
    security_type: 因子适用的证券类型， 股票stock 基金fund 债券bond 期货future
    quarter_lag:   需要回溯的季度时间窗口长度，单位为季度，低频财务类因子专用
    day_lag  :     需要回溯的日频时间窗口，单位为天，低频因子专用
    security_pool: 股票池 string or list
    depend_factor: 低高频通用 因子依赖的公共因子或其他的个人因子 String : “因子库名.因子名”
    """

    def __new__(cls, *args, **kwargs):
        if not hasattr(Factor, 'instance_dict'):
            Factor.instance_dict = {}

        if str(cls) not in Factor.instance_dict.keys():
            instance = super().__new__(cls, *args, **kwargs)
            Factor.instance_dict[str(cls)] = instance
            instance.__initialized = False
        return Factor.instance_dict[str(cls)]

    factor_type = "DAY"  # 暂时分日频和高频（分钟） “DAY”（日频） “MIN”（分钟级）"TICK"(Tick级)
    factor_name = ''  # 因子名，因子类名，因子文件名 保持一致，否则报错
    security_type = 'stock'  # 证券类型 stock,future,fund,future,bond
    quarter_lag = 1  # 需要回溯的季度时间窗口长度，单位为季度，低频财务类因子专用
    day_lag = 0  # 需要回溯的日频时间窗口，单位为天，低频因子专用
    reform_window = 1  # 后置计算需要的窗口大小 默认是1 低频因子专用
    security_pool = None  # 股票池 string or list
    depend_factor = []  # 低高频通用 因子依赖的公共因子或其他的个人因子 String : “因子库名.因子名”
    aiquant_requirements: Dict[str, object] = {}  # 统一 AIQuant 取数声明
    custom_params = {}  # 用户在动态生成因子类的时候可以自由传入参数
    external_data_memory_id_dict = dict()  # 用户依赖的外部数据的共享内存的id，与路径一一对应
    used_shared_memory = 0
    data_source = 'finchina'  # 数据源
    use_cache = False
    _aiquant_adapter: Optional[AIQuantDataAdapter] = None
    _aiquant_inputs: Dict[str, pd.DataFrame] = {}
    _aiquant_loaded_window: Optional[tuple] = None

    def mapping_name_func(self, class_name, custom_params):
        name_suffix = []
        if custom_params:
            para_names = sorted(custom_params.keys())
            name_suffix = [para + str(custom_params[para]) for para in para_names]
        name_suffix.insert(0, class_name)
        return "_".join(name_suffix)

    def __init__(self, logger_path='/tmp/factor_data/logs'):
        if self.__initialized:
            return
        self.__initialized = True

    def _init_aiquant_adapter(self):
        if self._aiquant_adapter is None:
            self._aiquant_adapter = AIQuantDataAdapter()
        if self._aiquant_inputs is None:
            self._aiquant_inputs = {}
        if not hasattr(self, "_aiquant_loaded_window"):
            self._aiquant_loaded_window = None

    def _target_freq(self):
        return "1d" if str(self.factor_type).upper() == "DAY" else "1m"

    def preload_aiquant_inputs(self, stocks=None, start_date=None, end_date=None):
        """
        按 aiquant_requirements 声明一次性拉取所有输入数据。
        MIN_BASE 仍可通过现有 add_ori_min_data 获取，Factormin 等走 SDK。
        """
        self._init_aiquant_adapter()
        requirements = getattr(self, "aiquant_requirements", {}) or {}
        if not requirements:
            return {}
        target_freq = self._target_freq()
        self._aiquant_inputs = self._aiquant_adapter.load_all(
            requirements=requirements,
            target_freq=target_freq,
            start_date=start_date,
            end_date=end_date,
        )
        self._aiquant_loaded_window = (start_date, end_date)
        return self._aiquant_inputs

    def load_inputs(self, stocks=None, start_date=None, end_date=None, dt_to=None):
        """
        对外取数接口：优先使用已缓存的 aiquant_inputs，如为空则触发预加载。
        dt_to 存在时返回截止 dt_to 的数据切片（基于 datetime 列）。
        """
        if (not getattr(self, "_aiquant_inputs", None)) or (self._aiquant_loaded_window != (start_date, end_date)):
            self.preload_aiquant_inputs(stocks=stocks, start_date=start_date, end_date=end_date)
        if dt_to is None:
            return self._aiquant_inputs
        dt_to_ts = pd.to_datetime(dt_to)
        sliced = {}
        for alias, df in self._aiquant_inputs.items():
            if isinstance(df, pd.DataFrame) and "datetime" in df.columns:
                sliced[alias] = df[df["datetime"] <= dt_to_ts]
            else:
                sliced[alias] = df
        return sliced

    # 可在前置计算方法中调用的 加载外部数据文件的接口
    @classmethod
    def add_personal_data(cls, file_list):
        if isinstance(file_list, str):
            file_list = [file_list]
        if not isinstance(file_list, list):
            raise Exception("file_list的参数格式为list（多文件）或str（单文件）,不支持 {}".format(type(file_list)))
        external_base_path = '/app/mount/project_data'
        for file_path in file_list:
            data_name = file_path.split(".")[0]
            complete_file_path = os.path.join(external_base_path, file_path)
            if not os.path.exists(complete_file_path):
                raise Exception("未找到{}文件,请确认文件名，文件路径是否正确，以及保存在/app/mount/project_data路径下".format(complete_file_path))
            file_size = os.path.getsize(complete_file_path) / float(1024 * 1024)
            print("文件 {} 的大小为 {}.MB".format(file_path, file_size))
            file_type = file_path.split(".")[-1]
            df_external = parse_extra_data(complete_file_path, file_type)
            cls.put_external_shared_data(data_name, df_external, file_size)
        return

    @classmethod
    def __add_hive_data(cls, ds_name, sql_string):
        from htds.dataset.service.sdk import HTDSContext
        htdsc = HTDSContext()
        sql_execute = htdsc.get_public_datasource(ds_name)
        data_df = sql_execute.query(sql_string)
        return data_df

    # 可在前置计算方法中调用的 加载hive数据的接口
    @classmethod
    def add_hive_data(cls, data_name, ds_name, sql_string):
        """
        :param data_name:
        :param ds_name:
        :param sql_string:
        :return:
        """
        data_df = cls.__add_hive_data(ds_name, sql_string)
        df_size = data_df.memory_usage().sum()
        print('hive表中获取的数据文件大小为{}MB'.format(df_size / (1024 ** 2)))
        cls.put_external_shared_data(data_name, data_df, df_size)
        return

    @staticmethod
    @ray.remote
    def get_market_data_kline(idx, stock_code, start_datetime, end_datetime, k_type='Kline1M4ZT'):
        from tquant import StockData, BasicData
        sd = StockData()
        df = sd.get_stock_kline(stock_code, start_datetime, end_datetime, k_type=k_type)
        # print("ID:{0}   Stock:{1}  {2}---{3} Finish!".format(str(idx), stock_code, str(start_datetime), str(end_datetime)))
        return df

    @classmethod
    def get_market_data_by_tquant(cls, market_type='', stock_list=[], date_list=[]):
        """
        :param market_type: 'kline'
        :param stock_list: 股票列表
        :param date_list:  日期列表 或 日期
        :return:
        """
        if market_type == 'kline1m':
            if isinstance(date_list, list):
                date_list.sort()
                if len(date_list) == 1:
                    start_date = end_date = date_list[0]
                elif len(date_list) > 1:
                    start_date = date_list[0]
                    end_date = date_list[-1]
                else:
                    raise Exception("date_list参数不能为空！")
            elif isinstance(date_list, str):
                if len(date_list) != 8:
                    raise Exception("date_list参数为string类型时，应为8位日期的字符串，如20191104")
                start_date = end_date = date_list
            else:
                raise Exception("date_list参数为日期列表(list)或单个日期的字符串(str)!")
            start_datetime = start_date + " 080000000"
            end_datetime = end_date + " 235900000"
            if not ray.is_initialized():
                set_ray_options(num_cpus=None, object_store_memory=None, options=None)
            results = [cls.get_market_data_kline.remote(idx, stock_code,
                                                        start_datetime,
                                                        end_datetime) for idx, stock_code in enumerate(stock_list)]
            df_list = ray.get(results)
            df = pd.concat(df_list)
        else:
            df = pd.DataFrame()
        return df

    # 可在前置计算方法中调用，加载高频行情数据的接口
    @classmethod
    def add_market_data(cls, data_name, market_type='', stock_list=[], date_list=[]):
        """
        :param data_name:
        :param market_type:
        :param stock_list:
        :param date_list:
        :return:
        """
        if (not date_list) or (not isinstance(date_list, list)):
            raise Exception("add_market_data接口必须传入日期列表 : date_list")
        if not stock_list:
            date = sorted(date_list)[-1]
            stock_list = get_stocks_pool(day=date, security_type=cls.security_type, securities=cls.security_pool)
        print("行情数据开始加载，时间较长，请稍后........")
        data_df = cls.get_market_data_by_tquant(market_type=market_type, stock_list=stock_list, date_list=date_list)
        df_size = data_df.memory_usage().sum()
        print('行情数据文件大小为{}MB'.format(df_size / (1024 ** 2)))
        cls.put_external_shared_data(data_name, data_df, df_size)
        print("行情数据加完成.")
        return

    @classmethod
    def add_panel_min_data(cls, start_date,end_date, indicators=[], security_type="STOCK"):
        data_df_dict = get_panel_min_data_dfs(start_date, end_date, indicators, security_type=security_type)
        return data_df_dict

    @classmethod
    def add_ori_min_data(cls,start_date, end_date, indicators=None,security_type='STOCK'):
        stocks_pool = get_stocks_pool(day=end_date, security_type=cls.security_type, securities=cls.security_pool)
        price_df_polars = get_ori_min_data_dfs(start_time=start_date, end_time=end_date, indicators=indicators, stocks=stocks_pool, security_type=security_type)

        return price_df_polars

    @classmethod
    def add_dfs_lf_data(cls,start_date, end_date, stock_list,report_date_list):
        non_hf_depend_factors = [i for i in cls.depend_factor if i.split(".")[0] != 'PanelMinData']
        data_df_dict = get_daily_data_from_dfs(quarterlag_dt_list=report_date_list, start_date=start_date,
                                               end_date=end_date, securities_list=stock_list,
                                               non_hf_depend_factors=non_hf_depend_factors)

        return data_df_dict

    # 前置计算方法 计算任务开始时，调用该方法，可选择加载 行情数据，hive数据 和 外部数据文件，用户开发时需要重写该方法
    @classmethod
    def onRunDaysStart(cls, start_date, end_date):
        """
        :return:
        """
        # 加载外部数据文件，获取数据
        # self.add_external_data_file(['test.csv'])
        # 加载高频行情数据
        # self.add_market_data()
        # 加载hive 数据
        # self.add_hive_data(ds_name, sql_string)
        return

    # 核心计算方法 计算过程中，并行计算每日数据时会调用，用户开发时可根据需要选择性重写该方法
    def calc(self, factor_data, price_data, **custom_params):
        """
        计算因子
        factor_data： dict key: 因子名 value: DataFrame  (高低频的DataFrame的格式不同)
        调用需要保证返回一个 pandas.Series, 低频因子: index :标的名, value : 因子值
                                        高频因子：index :MDTime  value : 因子值
        """
        return pd.DataFrame()

    # 后置计算方法，对calc计算的结果进行后置加工，用户开发时可根据需要选择性重写该方法
    def onRunDaysEnd(self, factor_df):
        """

        :param factor_df: pd.DataFrame 该因子计算过程中的所有值
        :return:
        """
        return factor_df

    def get_factor_data(self, quarterlag_dt_list, start_date, end_date, securities_list):
        """
        获取依赖的因子数据
        低频必须传入depend_factor,高频可传可不传
        quarterlag_dt_list: 财务因子需要回溯的时间窗口列表 例如：['20180630','20180930','20190331']
        start_date ： 日频因子开始时间 形如“20201123”
        end_date   ： 截止时间 形如“20201123”
        securities_list : 标的列表

        return : dict key: 因子名 value: DataFrame  (高低频的DataFrame的格式不同)
        """

        from xquant.factordata import FactorData
        s = FactorData()
        if len(self.depend_factor) == 0:
            raise Exception("低频因子depend_factor不能为空")

        date_list = get_trade_days(start_date, end_date)
        # depend_factor_dict 依赖因子字典 形如： {"market":['open','close'],"alpha191":['alpha1','alpha12']}
        depend_factor_dict = {}
        non_hf_depend_factors = [i for i in self.depend_factor if not i.startswith("PanelMinData")]
        for depend_factor_describe in non_hf_depend_factors:
            if len(depend_factor_describe.split('.')) != 2:
                raise Exception("请按照 因子类型（因子库名）.因子名 的方式书写依赖因子！")
            depend_factor_type, depend_factor_name = depend_factor_describe.split('.')
            if depend_factor_type not in depend_factor_dict:
                depend_factor_dict[depend_factor_type] = [depend_factor_name]
            else:
                depend_factor_dict[depend_factor_type].append(depend_factor_name)

        loop_time = len(depend_factor_dict.keys())
        depend_factor_type_list = list(depend_factor_dict.keys())
        res_dict = {}
        for i in trange(loop_time, desc='loading depend factor data'):
            depend_factor_type = depend_factor_type_list[i]
            depend_factor_list = depend_factor_dict[depend_factor_type_list[i]]
            print("Loading Data: {}".format(depend_factor_dict[depend_factor_type_list[i]]))
            if depend_factor_type == "BasicFinancialFactor":
                temp_data = s.get_factor_value("Basic_factor", securities_list, quarterlag_dt_list, depend_factor_list,
                                               fill_na=True)
                for depend_factor_name in depend_factor_list:
                    new_depend_factor_describe = 'BasicFinancialFactor.' + depend_factor_name
                    if int(self.calc.__code__.co_argcount) == 4:
                        res_dict[new_depend_factor_describe] = temp_data[depend_factor_name]
                    else:
                        res_dict[new_depend_factor_describe] = temp_data[depend_factor_name].unstack()
            elif depend_factor_type == "BasicDayFactor":
                temp_data = s.get_factor_value("Basic_factor", securities_list, date_list, depend_factor_list,
                                               fill_na=True)
                for depend_factor_name in depend_factor_list:
                    new_depend_factor_describe = 'BasicDayFactor.' + depend_factor_name
                    if int(self.calc.__code__.co_argcount) == 4:
                        res_dict[new_depend_factor_describe] = temp_data[depend_factor_name]
                    else:
                        res_dict[new_depend_factor_describe] = temp_data[depend_factor_name].unstack()
            else:
                raise Exception("暂时只支持BasicFinancialFactor-财务类因子, BasicDayFactor-日频因子")

        return res_dict


    # 用户调用低频因子的调试方法，
    @event_trace
    def run_day_factor_value(self, start_date, end_date, codefile_path):
        dynamic_load_attr = False
        # 从数据库中读到因子的属性，然后进行动态派生 生成因子类
        if dynamic_load_attr:
            factor_cls_ori = self.__class__  # 获得因子类
            factor_name = factor_cls_ori.__name__  # 获得因子名
            factor_attr = get_factor_attr(factor_name, library_env='research')  # 获得因子名对应的因子属性

            fac_cls = MetaBaseFactor(factor_name, (factor_cls_ori,), factor_attr)  # 动态派生成完整的因子类
            # fac_cls = get_custom_factor_class(factor_cls_ori, factor_attr)  # 动态派生成完整的因子类
            res_df = run_day_factor_value(fac_cls, start_date=start_date, end_date=end_date, factor_path=codefile_path)  # 调用因子调试的方法
        else:
            res_df = run_day_factor_value(self.__class__, start_date=start_date, end_date=end_date, factor_path=codefile_path)
        return res_df

    # 清理内存
    def clead_shared_memory(self):
        pass

    # 获取存储在共享内存中的外部数据，返回一个字典，key为调用加载外部数据的接口时 传入的data_name,value为pd.DataFrame
    def get_external_shared_data(self):
        df_dict = dict()
        if self.external_data_memory_id_dict:
            for data_name, shared_id in self.external_data_memory_id_dict.items():
                df_dict[data_name] = ray.get(shared_id)
        else:
            print('未发现因子 {} 的外部数据数据，请检查因子文件是否重写了 onRunDaysStart 方法'.format(self.factor_name))
        return df_dict

    # 将外部数据存储在共享内存中
    @classmethod
    def put_external_shared_data(cls, data_name, data_df, df_size):
        global avaliable_shared_memory
        if not ray.is_initialized():
            set_ray_options(num_cpus=None, object_store_memory=None, options=None)
        ray_id = ray.put(data_df)
        cls.external_data_memory_id_dict[data_name] = ray_id
        cls.used_shared_memory += df_size
        if cls.used_shared_memory > avaliable_shared_memory:
            raise Exception("目前可使用的共享内存大小为：{}，您已使用：{}，已超出限额".format(avaliable_shared_memory, cls.used_shared_memory))
        return
