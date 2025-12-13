import importlib.util
from FactorProvider.conf.TDubboConf import get_factorAttribute
from xquant.factorframework.rayframe.util.data_context import get_stocks_pool
from xquant.factorframework.rayframe.MetaFactor import MetaBaseFactor
import functools
import time, re, json, os
import datetime as dt
import importlib.util


factor_type_trans = {'行情': 'market',
                     '估值': 'valuation',
                     '风险': 'riskanalysis',
                     '财务分析': 'financialanalysis',
                     '财务报告': 'financialreport',
                     '分红指标': 'dividend',
                     '最新信息': 'newmsgindex',
                     '一致预期': 'consensus',
                     'Alpha指标': 'alpha',
                     'Barra指标': 'barra',
                     '技术面指标': 'technicalanalysis',
                     '动量指标': 'momentum',
                     '情绪指标': 'emotion',
                     'Barra因子CNE6': 'barrarisk6'}


def factor_time_info(func):
    @functools.wraps(func)
    def wrapper(cls, *args, **kwargs):
        "cls为func的第一个参数"
        # 运行前
        time1 = time.time()
        # 运行中
        log_info = None
        try:
            res = func(cls, *args, **kwargs)
        except Exception as e:
            cls.log.error(
                'factor func {} failed! error msg:\n {}'.format('frame' if cls.factor_name is None else cls.factor_name,
                                                                e))
            raise e
        finally:
            # 运行后
            cls.log.info(
                "{} func: {} success! use time {:.2f} s".format(cls.factor_name, func.__name__, time.time() - time1, ))
        return res

    return wrapper


def check_date(start_date, end_date):
    # start_date 单个日期，若end_date不为None则start_date 应小于end_date
    # date_type为日期类型 year,month,day,hour,minute,second
    if (not isinstance(start_date, str)) or (not isinstance(end_date, str)):
        raise Exception("请输入字符串形式的开始日期与结束日期")
    try:
        assert len(start_date) == 8
        assert len(end_date) == 8
        sdate = dt.datetime.strptime(start_date, '%Y%m%d')
        edate = dt.datetime.strptime(end_date, '%Y%m%d')
    except:
        raise Exception("日期-{0}-{1}的格式有误，请传入正确格式如'20200201'".format(start_date, end_date))
    if sdate > edate:
        raise Exception("开始日期{0}大于结束日期{1}，请检查后输入！".format(start_date, end_date))


def check_lag_date(day_lag, quarter_lag):
    if not isinstance(day_lag, int):
        raise Exception("[day_lag格式错误] 日频数据播放窗口需要传入一个整数， 不可为{} ".format(day_lag))
    elif day_lag < 0 or day_lag >= 251:
        raise ValueError("[quarter_lag数据范围错误] 日频数据播放窗口的范围为[0,250], 不可为{}".format(day_lag))
    if not isinstance(quarter_lag, int):
        raise Exception("[quarter_lag格式错误] 季频数据播放窗口需要传入一个整数, 不可为{} ".format(quarter_lag))
    elif quarter_lag <= 0 or quarter_lag >= 5:
        raise ValueError("[quarter_lag数据范围错误] 季频数据播放窗口的范围为[1,4], 不可为{}".format(quarter_lag))


def check_security_type(security_type):
    support_type_list = ['stock', 'fund']
    if not isinstance(security_type, str) and security_type is not None:
        raise Exception("目前仅支持{0}的标的类型,security_type为str类型".format(','.join(i for i in support_type_list)))
    if security_type and security_type.lower() not in support_type_list:
        raise Exception("目前仅支持{0}的标的类型,security_type为str类型".format(','.join(i for i in support_type_list)))


def check_factor_sample_consist(fac_list):
    """
    判断是否所有因子的采样时间间隔一致
    :param fac_list: list
    :param data_input_mode: list
    :return:
    """
    consist_interval = None
    for fac in fac_list:
        try:
            custom_params = getattr(fac, "custom_params")
        except:
            raise Exception(
                "sample_period缺失错误：在data_input_mode包含TICK_SAMPLE或者TRANSACTION_SAMPLE的情况下，"
                "因子{}未对类属性custom_params中的sample_period（采样时间间隔）赋值！".format(
                    fac.__name__))
        sample_period = custom_params.get("sample_period", None)
        #fac_logger.debug("{}, sample_period: {}".format(fac.__name__, sample_period))
        if not sample_period:
            raise Exception(
                "sample_period缺失错误：在data_input_mode包含TICK_SAMPLE或者TRANSACTION_SAMPLE的情况下，"
                "因子{}未对类属性custom_params中的sample_period（采样时间间隔）赋值！".format(
                    fac.__name__))
        if not consist_interval:
            consist_interval = sample_period
        else:
            assert sample_period == consist_interval, \
                "sample_period不一致错误：因子{0}的sample_period为{1}，和这批因子中其他因子的sample_period值{2}不一致！".format(
                    fac.__name__, sample_period, consist_interval)


def check_data_input_mode_consist(fac_cls_list):
    consist_data_input_mode = []
    for fac in fac_cls_list:
        data_input_mode = getattr(fac, "data_input_mode")
        if not data_input_mode:
            raise Exception("data_input_mode缺失错误： 因子：{} 缺少属性data_input_mode".format(fac.__name__))
        elif len(set(data_input_mode) - set(
                ["TICK_RAW", "TICK_SAMPLE", "TRANSACTION_RAW", "TRANSACTION_SAMPLE", "ORDER_RAW", "KLINE1M_RAW",
                 "ORDER_SAMPLE"])) != 0:
            raise Exception("data_input_mode错误：因子{0}的data_input_mode赋值错误:{1}目前仅支持TICK_RAW,TICK_SAMPLE,TRANSACTION_RAW,"
                            "TRANSACTION_SAMPLE,ORDER_RAW, ORDER_SAMPLE, KLINE1M_RAW的行情数据类型".format(fac.__name__,
                                                                                                    data_input_mode))
        if not consist_data_input_mode:
            consist_data_input_mode = data_input_mode
        else:
            assert set(data_input_mode) == set(
                consist_data_input_mode), "data_input_mode不一致：因子{0}的data_input_mode属性为{1}与批计算其他因子的{2}不一致！".format(
                fac.__name__, data_input_mode, consist_data_input_mode)


def check_factor_type(factor_type):
    if factor_type is None:
        raise Exception("factor_type目前仅支持返回DAY(日频因子)，TICK(高频因子)两种情况")
    factor_type = factor_type.upper()
    if factor_type not in ['DAY', 'TICK']:
        raise Exception("factor_type目前仅支持返回DAY(日频因子)，TICK(高频因子)两种情况")
    return


def check_factor_name(factor_name):
    if type(factor_name) == str:
        factor_name = [factor_name]
    for factor in factor_name:
        if not isinstance(factor, str):
            raise Exception("因子名必须是字符串格式")
        factor = factor.replace("$", "")
        if re.search(r"\W", factor):
            raise Exception("因子名{0}不符合格式，必须为大小写字母、数字或下划线的组合, 仅可包含特殊字符$.".format(factor))


def check_security_list(security_list):
    # security_list 支持的格式包括，
    # ['601688.SH','000001.SZ']  无跨标的因子
    # [['601688.SH', '000001.SZ'],['000002.SZ', '000003.SZ']] 跨标的因子开发过程中，副标的仅使用tick数据
    # [('601688.SH', '000001.SZ'),('000002.SZ', '000003.SZ')] 跨标的因子开发过程中，副标的与主标的数据类型完全一致
    if security_list:
        if not isinstance(security_list, list):
            raise Exception("参数security_list应为list格式")
        # if not isinstance(security_list[0], (list, tuple, str)):
        #     raise Exception("security_list 中每个元素的类型应当在（str, list, tuple）三种类型中")
        # for i in range(1, len(security_list)):
        #     if not isinstance(security_list[i], (list, tuple, str)):
        #         raise Exception("security_list 中每个元素的类型应当在（str, list, tuple）三种类型中")
        #     if not isinstance(security_list[i], type(security_list[i - 1])):
        #         raise Exception("security_list 中每一个元素的类型应当是一致的")
        if not isinstance(security_list[0], str):
            raise Exception("暂不支持跨标的因子开发 security_list 中每个元素为str类型")
        for i in range(1, len(security_list)):
            if not isinstance(security_list[i], str):
                raise Exception("暂不支持跨标的因子开发 security_list 中每个元素为str类型")
            if not isinstance(security_list[i], type(security_list[i - 1])):
                raise Exception("security_list 中每一个元素的类型应当是一致的")
    return


def check_factor_list(factor_list, factor_freq):
    if not isinstance(factor_list, list):
        raise Exception("请保证factor_list是列表。")
        # 校验factor_list中的元素是否为str类型
    if (factor_freq == 'DAY') and (not all(isinstance(x, str) for x in factor_list)):
        raise Exception("请保持factor_list中元素是因子名（string类型）。")
    if (factor_freq == 'TICK') and (not all(isinstance(x, (str, type)) for x in factor_list)):
        raise Exception("factor_list中元素的只能是因子名（string类型）或者因子类（type类型）。")
    return


def get_factor_module(factor_name, file_path):
    # 遍历文件夹下的所有.py文件
    file_path_list = []
    for root, dirs, files in os.walk(file_path):
        for file in files:
            # 获取文件名称
            if not file.endswith('.py'):
                continue
            file_name, file_tail = file.split('.')[:2]
            # 获取文件绝对路径
            file_abs_path = os.path.join(root, file)
            if file_name == factor_name and file_tail == 'py':
                file_path_list.append(file_abs_path)
    if len(file_path_list) == 0:
        raise Exception("无法加载因子类：文件夹'{}'下无与因子{}同名的因子文件，请指定正确的file_path因子文件目录！".format(
            file_path, factor_name))
        return
    elif len(file_path_list) > 1:
        raise Exception("匹配到多个因子文件:" + " ".join(
            i for i in file_path_list) + "，请指定正确的file_path因子文件目录！")
        return
    else:
        return file_path_list[0]
    return


# 根据因子名 去指定的路径下找到和因子名相同的因子文件 并加载其中的因子类
def get_fac_class(factor_name, file_path):
    file_path = file_path.strip()
    file_abs_path = get_factor_module(factor_name, file_path)
    module_spec = importlib.util.spec_from_file_location(factor_name, file_abs_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    try:
        cls = getattr(module, factor_name)
    except:
        raise Exception(f"ERROR: Please keep factor module name {module} same as factor class name {factor_name}!")
    return cls


def check_return_and_lib(return_mode, library_name):
    if return_mode == 'show':
        pass
    elif return_mode == 'save':
        if not isinstance(library_name, str):
            raise Exception("因子库名应为str的格式")
        # jurisdictionData_dict = get_jurisdictionData()
        # db_list = list(
        #     jurisdictionData_dict["因子信息"]["jurisdictionData"].keys())
        # if not library_name in db_list:
        #     raise Exception(
        #         "library_name doesn't exist: %s！" % library_name)
    else:
        raise Exception("返回模式只有save和show两种")


def get_fac_task_cls_list(factor_list, file_path='./'):
    fac_task_cls_list = []
    factor_name_dict = {}
    factor_type = None
    for fac_cls in factor_list:
        if type(fac_cls) == str:
            fac_cls = get_fac_class(fac_cls, file_path)
        # 因子名不需要与任务名一致, 但所有任务不能有重名因子
        for fac_name in fac_cls.output_factor_names:
            if not fac_name.startswith(fac_cls.__name__):
                raise Exception(f"因子任务{fac_cls.__name__}的输出因子output_factor_names中的因子名必须以{fac_cls.__name__}开头！")
            if not factor_name_dict.get(fac_name, None):
                factor_name_dict[fac_name] = fac_cls.__name__
            else:
                raise Exception(
                    f"因子任务{factor_name_dict[fac_name]}和{fac_cls.__name__}存在重名因子{fac_name}，请检查因子任务并重新定义不同的因子名！")
        # 校验factor_name
        check_factor_name(fac_cls.output_factor_names)
        if not factor_type:
            factor_type = fac_cls.factor_type.upper()
        else:
            assert factor_type == fac_cls.factor_type.upper(), f"所有因子任务的factor_type不一致！{fac_cls.__name__}的factor_type为{fac_cls.factor_type}!"
        # 校验factor_type
        check_factor_type(fac_cls.factor_type)
        fac_task_cls_list.append(fac_cls)
    return fac_task_cls_list


def get_factor_attr(factor_name, library_env=''):
    # 通过 dubbo 接口 获取指定因子的因子属性
    factor_attr_dict = get_factorAttribute(factor_name, env=library_env)
    code = factor_attr_dict['code']
    if code != 0:
        raise Exception("调用查询因子属性的dubbo接口失败")
    # 解析因子属性字典
    factor_dict = {}
    factor_info_dict = factor_attr_dict['factorInfo']
    if not factor_info_dict:
        raise Exception("查无此因子:{0}，请联系管理员。".format(factor_name))

    # 高低频因子公共属性 factor_name， factor_type， security_type， security_pool, external_data_memory_id_list
    factor_dict['factor_name'] = factor_info_dict['factorSymbol']  # 因子名
    factor_dict['factor_type'] = factor_info_dict['freq']  # 因子类型
    security_type_trans = {'1': 'stock', '2': 'fund', '3': 'future', '4': 'bond'}  # 标的类型 1 是 股票（stock） 2 是基金（fund）
    factor_dict['security_type'] = security_type_trans[str(factor_info_dict['securityType'])]
    factor_dict['external_data_memory_id_dict'] = dict()  # 存储外部数据在共享内存中的id列表
    # security_pool
    # 低频：股票池参数 alpha_universe, hs300.....
    # 高频: 标的列表 解析为 security=[(主标的，副标的1，副标的2),(主标的，副标的1，副标的2)]的格式
    factor_dict['security_pool'] = []
    if factor_info_dict.get('securityPool'):
        for item_dict in factor_info_dict['securityPool']:
            if item_dict['infoCode'] in ['alpha_universe', 'hs300', 'zz500', 'sz50', 'zz800', 'zz1000']:
                factor_dict['security_pool'] = item_dict['infoCode']
                break
            security_id = item_dict['infoCode']
            # 判断跨票计算是否有副票
            if not item_dict.get("ancillary"):
                factor_dict['security_pool'].append(security_id)
            else:
                extra_sec_list = [sec_dict["benchmark"] for sec_dict in item_dict["ancillary"]]
                factor_dict['security_pool'].append(tuple([security_id] + extra_sec_list))

    # 低频因子专属属性 day_lag quarter_lag depend_factor
    if factor_dict['factor_type'] == "DAY":
        factor_dict['day_lag'] = int(factor_info_dict['dayLag']) if factor_info_dict.get('dayLag') else 0  # day_lag
        factor_dict['quarter_lag'] = int(factor_info_dict['quarterLag']) if factor_info_dict.get(
            'quarterLag') else 1  # quarter_lag
        # 拼接依赖因子的列表 depend_factor
        factor_dict['depend_factor'] = []
        if factor_info_dict.get('dependFactor'):
            for item_dict in factor_info_dict['dependFactor']:
                depend_factor_name = item_dict['dependencySymbol']
                depend_factor_lib_id = item_dict['libraryId']
                depend_factor_type = item_dict['factorType']
                # library_id=1：低频公共因子 libirary_id>10 个人因子
                if depend_factor_lib_id == 1:
                    depend_factor_lib = factor_type_trans[depend_factor_type]
                elif depend_factor_lib_id == 3:
                    depend_factor_lib = 'SharedFactor'
                elif depend_factor_lib_id > 10:
                    depend_factor_lib = '_'.join([item_dict['ownerTableName'].split('_')[0], item_dict['freq']])
                depend_factor_describ = '.'.join([depend_factor_lib, depend_factor_name])
                factor_dict['depend_factor'].append(depend_factor_describ)

    # 高频因子专属属性 depend_factor, data_input_mode
    if factor_dict['factor_type'] == "TICK":
        factor_dict['depend_factor'] = []
        factor_dict['data_input_mode'] = []
        # data_input_mode 作为高频因子的公共因子 从depend_factor传入
        if factor_info_dict.get('dependFactor'):
            for item_dict in factor_info_dict['dependFactor']:
                depend_factor_name = item_dict['dependencySymbol']
                depend_factor_lib_id = item_dict['libraryId']
                # library_id=2：高频行情数据类型 libirary_id>10 个人因子
                if depend_factor_lib_id == 2:
                    factor_dict['data_input_mode'].append(depend_factor_name)
                elif depend_factor_lib_id > 10:
                    depend_factor_lib = '_'.join([item_dict['ownerTableName'].split('_')[0], item_dict['freq']])
                    factor_dict['depend_factor'].append('.'.join([depend_factor_lib, depend_factor_name]))
        if len(factor_dict['data_input_mode']) == 0:
            factor_dict['data_input_mode'] = ['TICK_RAW']
    print("Factor Attr Dict:\n", factor_dict)
    return factor_dict


def get_factor_ori_name(factor_name, library_env='research'):
    # 还原因子名
    factor_attr = get_factor_attr(factor_name, library_env=library_env)
    custom_params_dict = factor_attr['custom_params']
    delete_str = '_' + '_'.join(str(item[0]) + str(item[1]) for item in custom_params_dict.items())
    factor_name_ori = factor_name.replace(delete_str, '', 1)
    return factor_name_ori


def get_fac_to_sec_dict(factor_list, dynamic_load_attr, library_env, date, file_path='./'):
    fac_to_sec_dict = {}
    # True 需要读取库中的因子属性 然后结合计算逻辑派生。
    if dynamic_load_attr:
        for fac_cls in factor_list:
            if type(fac_cls) == str:
                # fac_name_ori = get_factor_ori_name(fac_cls, library_env=library_env)  # 根据所传的因子名 获取基类的因子名
                fac_cls_ori = get_fac_class(fac_cls, file_path)  # 根据基类的因子名 获取计算逻辑
                fac_attr = get_factor_attr(fac_cls, library_env=library_env)  # 根据因子名 加载因子属性
                fac_cls = MetaBaseFactor(fac_cls, (fac_cls_ori,), fac_attr)  # 动态派生成完整的因子类

                # fac_cls = get_custom_factor_class(fac_cls_ori, fac_attr)  # 根据因子属性 与 因子的计算逻辑 派生出子类
            assert fac_cls.__name__ == fac_cls.factor_name, "因子名称冲突：因子类名{}与因子名{}不一致！".format(fac_cls.__name__,
                                                                                             fac_cls.factor_name)
            # 校验factor_name
            check_factor_name(fac_cls.factor_name)
            # 校验factor_type
            check_factor_type(fac_cls.factor_type)
            cur_security_pool = get_stocks_pool(day=date, security_type=fac_cls.security_type,
                                                securities=fac_cls.security_pool)
            fac_to_sec_dict[fac_cls] = cur_security_pool
    else:
        for fac_cls in factor_list:
            if type(fac_cls) == str:
                fac_cls = get_fac_class(fac_cls, file_path)
            assert fac_cls.__name__ == fac_cls.factor_name, "因子名称冲突：因子类名{}与因子名{}不一致！".format(
                fac_cls.__name__, fac_cls.factor_name)
            # 校验factor_name
            check_factor_name(fac_cls.factor_name)
            # 校验factor_type
            check_factor_type(fac_cls.factor_type)
            cur_security_pool = get_stocks_pool(day=date, security_type=fac_cls.security_type,
                                                securities=fac_cls.security_pool)
            fac_to_sec_dict[fac_cls] = cur_security_pool
    return fac_to_sec_dict


def get_sec_to_fac_dict(fac_to_sec_dict):
    # 映射标的与因子的关系
    sec_to_fac_dict = {}
    for key, value in fac_to_sec_dict.items():
        for code in value:
            sec_to_fac_dict[code] = sec_to_fac_dict.get(code, [])
            sec_to_fac_dict[code].append(key)
    return sec_to_fac_dict


import pandas as pd


def parse_extra_data(file_path, file_type):
    if file_type == 'csv':
        df = pd.read_csv(file_path)
    elif file_type == 'parquet':
        df = pd.read_parquet(file_path)
    elif file_type == 'pkl':
        df = pd.read_pickle(file_path)
    elif file_type in ["xlsx", 'xls']:
        df = pd.read_excel(file_path)
    else:
        raise Exception("目前仅支持后缀为csv, parquet, pickle, xlsx, xls的外部数据文件格式")
    return df


def parse_date_list(date_list):
    date_list_per_month = []
    date_tmp_list = []
    date_list = sorted(date_list)
    day_nums = len(date_list)
    for i, date in enumerate(date_list):
        if len(date_tmp_list) == 0:
            year, month = date[:4], str(int(date[4:6]) + 1).zfill(2)  # 一次算两个月
        if date[:4] == year and date[4:6] <= month:
            date_tmp_list.append(date)
        else:
            date_list_per_month.append(date_tmp_list)
            year, month = date[:4], str(int(date[4:6]) + 1).zfill(2)
            date_tmp_list = [date]
        if date_tmp_list and i == day_nums - 1:
            date_list_per_month.append(date_tmp_list)
    return date_list_per_month


def check_run_end_df(factor_data, start_date, end_date):
    if not isinstance(factor_data, pd.DataFrame):
        raise Exception(
            "【onRunDaysEnd方法返回值错误】低频因子的onRunDaysEnd方法需要返回pd.DataFrame格式的数据！目前是：{}".format(type(factor_data)))
    if factor_data.columns[0][-2:] not in ["SZ", "SH"] and len(factor_data.index[0]) != 8:
        raise Exception(
            "【onRunDaysEnd方法返回值错误】低频因子的onRunDaysEnd方法返回的pd.DataFrame的列必须是标的名，索引为yyyymmdd的日期形式！目前是：{}".format(
                factor_data.columns[0][-2:],
                factor_data.index[0]))
    if factor_data.index[0] != start_date or factor_data.index[-1] != end_date:
        raise Exception(
            "【onRunDaysEnd方法返回值错误】低频因子的onRunDaysEnd方法返回的dataframe的数据区间为【start_date,end_date】,本次为{}-{}".format(
                start_date, end_date))

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"{func.__name__} excuted in {run_time:.3f} secs")

        return value

    return wrapper

if __name__ == '__main__':
    factor_dict = get_factor_attr('test11', library_env='research')
    print(factor_dict)
