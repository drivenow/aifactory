# _*_ coding:utf-8 _*_
import os
import datetime
import traceback
import uuid
import time
import numpy as np
import pandas as pd
from FactorProvider.storage.db import DML_mysql, sql_connect
from FactorProvider.utils.utils import is_valid_date
from FactorProvider.factordata.xqfactor import tradingDay
import logging
import threading
import re
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
from pyarrow import fs
from retrying import retry
# logger = logging.getLogger("quant_info")

StorageConfig = {
    "T+0": {"catalog_type": 2, "remark": "T+0高频因子", "parent_id": 0, "status": 1},
    "Alpha": {"catalog_type": 1, "remark": "Alpha非高频因子", "parent_id": 0, "status": 1},
    "Source_table_daily": {"catalog_type": 3, "remark": "万得/朝阳永续等外部数据-日频", "parent_id": 0, "status": 1},
    "Source_table_fully": {"catalog_type": 3, "remark": "万得/朝阳永续等外部数据-全表", "parent_id": 0, "status": 1},
}


class FactorData():
    def __init__(self, base_save_path='/tmp/project_factor'):
        # 多个数据源
        self.dml_xquant = None
        if base_save_path:
            self.base_save_path = base_save_path
        else:
            self.base_save_path = '/tmp/project_factor'
        self.library_info = None
        self.library_info_new = None
        self.__sql_connect = None
        self.pa_types = {'double': pa.float64(), 'string': pa.string()}
        # self.__init_folder()

    def __init_folder(self):
        low_fre_path = os.path.join(self.base_save_path, 'low_fre')
        high_fre_path = os.path.join(self.base_save_path, 'high_fre')
        if not os.path.exists(low_fre_path):
            os.makedirs(low_fre_path)
        if not os.path.exists(high_fre_path):
            os.makedirs(high_fre_path)

    def __naming_specification(self, name):
        '''
        判断命名规范
        :return:
        '''
        try:
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
                return False
            else:
                return True
        except:
            return False

    def __set_library_info(self, refresh=False):
        if not self.library_info or refresh:
            self.library_info = self.__get_library_info()

    def __set_library_info_new(self, refresh=False):
        if not self.library_info_new or refresh:
            self.library_info_new = self.__get_library_info_new()

    def __get_library_info_new(self):
        # library_factors {'low_feq': {'库名1':[因子1，因子2], ...},'library_types':{'库名1':'low_feq'}}
        conn_name = str(int(time.time())) + str(threading.get_ident())
        sql = "select factor, library_name,factor_freq from personal_factors_new"
        self.__set_dml_xquant()
        result = self.dml_xquant.getAllByPandas(conn_name, sql)
        self.dml_xquant.close(conn_name)
        library_factors = {'low_fre': {},
                           'high_fre': {},
                           'library_types': {}}
        for i, row in result.iterrows():
            if row['factor'] in ['datetime', 'symbol']:
                continue
            if row['factor_freq'] not in library_factors:
                library_factors[row['factor_freq']] = {}
            if not library_factors[row['factor_freq']].get(row['library_name']):
                library_factors[row['factor_freq']][row['library_name']] = []
            library_factors[row['factor_freq']][row['library_name']].append(row['factor'])
            if not library_factors['library_types'].get(row['library_name']):
                library_factors['library_types'][row['library_name']] = row['factor_freq']
        return library_factors


    def __get_library_info(self):
        low_fre_libraries = {}
        high_fre_libraries = {}
        library_types = {}
        low_fre_path = os.path.join(self.base_save_path, 'low_fre')
        high_fre_path = os.path.join(self.base_save_path, 'high_fre')
        libraries = self.__get_all_factors()
        for lib in os.listdir(low_fre_path):
            if libraries.get(lib):
                low_fre_libraries[lib] = libraries[lib]
            else:
                low_fre_libraries[lib] = libraries.get(lib, {})
            library_types[lib] = 'low_fre'
        for lib in os.listdir(high_fre_path):
            if libraries.get(lib):
                high_fre_libraries[lib] = libraries[lib]
            else:
                #因子目录已清除，但mysql中仍有因子元数据
                high_fre_libraries[lib] = libraries.get(lib, {})
            library_types[lib] = 'high_fre'
        return {'low_fre': low_fre_libraries,
                'high_fre': high_fre_libraries,
                'library_types': library_types}

    def __set_dml_xquant(self):
        if not self.dml_xquant:
            self.dml_xquant = DML_mysql('xquant')

    def __set_sql_connect(self):
        if not self.__sql_connect or not self.__sql_connect.open:
            self.__sql_connect = sql_connect('xquant')

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def __add_lock_high_factor(self, owner, nas_folder_name, security):
        def __select_lock(lock_key):
            select_lock_sql = """
                select lock_key, owner, create_time, expire_seconds
                from lock_distributed
                where lock_key = "{}" 
            """.format(lock_key)
            result = pd.read_sql(select_lock_sql, self.__sql_connect)
            return result

        def __add_lock(cur, lock_key, owner):
            insert_lock_sql = """
                insert into lock_distributed (lock_key, owner, expire_seconds)
                value ("{}", "{}", 60*3)
            """.format(lock_key, owner)
            try:
                cur.execute(insert_lock_sql)
                self.__sql_connect.commit()
            except:
                self.__sql_connect.rollback()
                trace = traceback.print_exc()
                raise Exception('高频因子锁插入失败:{}'.format(trace))

        def __update_lock(cur, owner, lock_key):
            new_lock_key = '{}_{}'.format(lock_key, owner)
            update_lock_sql = """
                update lock_distributed
                set lock_key="{}", is_timeout=1, is_concurrent=1
                where lock_key = "{}"
            """.format(new_lock_key, lock_key)
            insert_lock_sql = """
                insert into lock_distributed (lock_key, owner, expire_seconds)
                value ("{}", "{}", 60*3)
            """.format(lock_key, owner)
            try:
                cur.execute(update_lock_sql)
                cur.execute(insert_lock_sql)
                self.__sql_connect.commit()
            except:
                self.__sql_connect.rollback()
                trace = traceback.print_exc()
                raise Exception('高频因子锁修改失败:{}'.format(trace))

        #logger.debug('{} __add_lock_high_factor {}'.format(owner, time.time()))
        self.__set_sql_connect()
        lock_key = '{}_{}'.format(nas_folder_name, security)
        cur = self.__sql_connect.cursor()
        while True:
            result = __select_lock(lock_key)
            if len(result) == 0:
                try:
                    __add_lock(cur, lock_key, owner)
                    break
                except Exception as e:
                    raise e
            else:
                lock = result.iloc[0]
                now = datetime.datetime.now()
                is_timeout = True if now > lock[
                    'create_time'] + datetime.timedelta(
                    seconds=int(lock['expire_seconds'])) else False
                if is_timeout:
                    try:
                        __update_lock(cur, owner, lock_key)
                        break
                    except Exception as e:
                        raise e
            time.sleep(10)
        cur.close()
        return True

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def __delete_lock_high_factor(self, owner, nas_folder_name, security,
                                  error=None):
        def __select_lock(owner):
            select_lock_sql = """
                select lock_key, owner, create_time, expire_seconds
                from lock_distributed
                where owner = "{}" 
            """.format(owner)
            result = pd.read_sql(select_lock_sql, self.__sql_connect)
            return result

        def __update_lock(cur, owner, lock_key, is_timeout=False,
                          is_exception=False, error=None):
            new_lock_key = '{}_{}'.format(lock_key, owner)
            update_lock_sql = """
                update lock_distributed
                set lock_key="{}", is_finished=1
            """.format(new_lock_key)
            if is_timeout:
                update_lock_sql += ', is_timeout=1'
            if is_exception:
                update_lock_sql += ', is_exception=1, exception="{}"'.format(
                    error)
            update_lock_sql += ' where owner = "{}"'.format(owner)
            try:
                cur.execute(update_lock_sql)
                self.__sql_connect.commit()
            except:
                self.__sql_connect.rollback()
                trace = traceback.print_exc()
                raise Exception('高频因子锁修改失败:{}'.format(trace))

        def __delete_lock(cur, owner):
            delete_lock_sql = """
                delete from lock_distributed 
                where owner = "{}" 
            """.format(owner)
            try:
                cur.execute(delete_lock_sql)
                self.__sql_connect.commit()
            except:
                self.__sql_connect.rollback()
                trace = traceback.print_exc()
                raise Exception('高频因子锁删除失败:{}'.format(trace))

        #logger.debug('{} __delete_lock_high_factor {}'.format(owner, time.time()))
        self.__set_sql_connect()
        lock_key = '{}_{}'.format(nas_folder_name, security)
        cur = self.__sql_connect.cursor()
        result = __select_lock(owner)
        if len(result) == 0:
            return
        lock = result.iloc[0]
        now = datetime.datetime.now()
        is_timeout = True if now > lock['create_time'] + datetime.timedelta(
            seconds=int(lock['expire_seconds'])) else False
        is_exception = True if error else False
        if is_exception or is_timeout:
            try:
                __update_lock(cur, owner, lock_key, is_timeout, is_exception,
                              error)
            except Exception as e:
                raise e
        else:
            try:
                __delete_lock(cur, owner)
            except Exception as e:
                raise e
        cur.close()
        return True

    def __get_all_factors(self):
        conn_name = str(int(time.time())) + str(threading.get_ident())
        sql = "select factor, library_name, col, factor_type from personal_factors"
        self.__set_dml_xquant()
        result = self.dml_xquant.getAllByPandas(conn_name, sql)
        self.dml_xquant.close(conn_name)
        library_factors = {}
        for i, row in result.iterrows():
            if row['factor'] in ['MDDate', 'Factor']:
                continue
            if not library_factors.get(row['library_name']):
                library_factors[row['library_name']] = {}
            library_factors[row['library_name']][row['factor']] = {'col': str(row['col']),
                                                                   'factor_type': row['factor_type']}
        return library_factors

    def create_factor_library(self, library_name, library_type):
        if not library_type in StorageConfig.keys():
            raise Exception("library_type 设置错误！请重新设置！目前只支持T+0和Alpha!")
        if not self.__naming_specification(library_name):
            raise Exception("library_name 命名不规范！请以字母开头且只能包含字母,数字和下划线！")
        # 得到所有库名
        self.__set_library_info()
        if library_type == 'Alpha':
            library_type = 'low_fre'
        else:
            library_type = 'high_fre'
        if library_name in self.library_info['library_types']:
            raise Exception("The library name already exists:该库名已存在！请重新输入！")
        # 创建文件夹
        lib_path = os.path.join(self.base_save_path, library_type)
        library_path = os.path.join(lib_path, library_name)
        if os.path.exists(library_path):
            raise Exception("因子库{}已存在！请重新输入！".format(library_path))
        os.makedirs(library_path)
        # 更新库信息
        self.library_info[library_type][library_name] = {}
        self.library_info['library_types'][library_name] = library_type
        return True

    def add_factor(self, library_name, factor_names):
        """
        向library_name的因子库中增加因子
        :param library_name: 库名
        :param factor_names: 因子名列表
        :return:

        """
        if not type(factor_names) == dict:
            raise Exception("factor_names 请传入字典！")
        for factor, _ in factor_names.items():
            if factor in ['MDTime', 'MDDate', 'HTSCSecurityID']:
                raise Exception('因子不允许以{}命名'.format(factor))
            if not self.__naming_specification(factor):
                raise Exception("%s因子命名不规范！" % str(factor))
        # 查找所有库名，判断用户输入的库名是否存在
        self.__set_library_info()
        library_type = self.library_info['library_types'].get(library_name)
        if not library_type:
            raise Exception(
                "library_name doesn't exists! %s不存在！" % str(library_name))
        # 得到该库所有因子名
        library_info = self.library_info[library_type].get(library_name)
        if library_info:
            factor_symbols = list(library_info.keys())
        else:
            # if self.__library_occupied(library_name):
            # 不区分用户
            #     raise Exception('没有访问因子库{}的权限'.format(library_name))
            factor_symbols = []
            self.library_info[library_type][library_name] = {}
        for factor_name in factor_names:
            if factor_name in factor_symbols:
                raise Exception(
                    "%s在%s库中已存在！" % (factor_name, library_name))
        for factor_name, factor_type in factor_names.items():
            if factor_type == 'float':
                factor_type = 'double'
            if factor_type not in ['string', 'double']:
                raise Exception('因子类型必须为string或double')
            result = self.__update_factor(factor_name, factor_type, library_name, library_type)
            # 更新权限文件
            self.library_info[library_type][library_name][factor_name] = {'col': result['col'],
                                                                          'factor_type': result['factor_type']}
        return True

    def del_factor(self, library_name, factor_names):
        if not isinstance(factor_names, list):
            raise Exception("factor_names 为list类型！")
        # 查找所有库名，判断用户输入的库名是否存在
        self.__set_library_info()
        library_type = self.library_info['library_types'].get(library_name)
        factor_names = list(set(factor_names))
        if not factor_names:
            raise Exception("factor_names 不能为空！")
        elif len(factor_names) == 1:
            factors = "(" + "'" + factor_names[0] + "'" + ")"
        else:
            factors = tuple(factor_names)
        conn_name = str(int(time.time())) + str(threading.get_ident())
        sql_use = "delete from personal_factors where library_name='{0}' and factor in {1}".format(library_name,
                                                                                                   factors)
        self.__set_dml_xquant()
        try:
            self.dml_xquant.delete(conn_name, sql_use)
            self.dml_xquant.commit(conn_name)
        except:
            self.dml_xquant.rollback(conn_name)
            raise Exception('删除因子失败！')
        finally:
            self.dml_xquant.close(conn_name)
        for fac in factor_names:
            try:
                del (self.library_info[library_type][library_name][fac])
            except:
                pass
        return True

    def __library_occupied(self, library_name):
        # 有别的用户在该库创建因子，则该用户无法创建新因子
        conn_name = str(int(time.time())) + str(threading.get_ident())
        self.__set_dml_xquant()
        sql = "select factor from personal_factors where library_name='{}'".format(library_name)
        result = self.dml_xquant.getAllByPandas(conn_name, sql)
        self.dml_xquant.close(conn_name)
        if not result.empty:
            return True
        return False

    def __update_factor(self, factor_name, factor_type, library_name, library_type):
        conn_name = str(int(time.time())) + str(threading.get_ident())
        self.__set_dml_xquant()
        sql = "select factor, col from personal_factors where library_name='{}'".format(
            library_name)
        result = self.dml_xquant.getAllByPandas(conn_name, sql)

        if len(result) == 0:
            max_col = 1
            add_col = 1
        else:
            if len(result[result['factor'] == factor_name]) != 0:
                #logger.debug('该因子库中已有{}'.format(factor_name))
                raise Exception("library_name: {0}中已存在factor_name:{1}".format(library_name, factor_name))
                # return True
            max_col = result['col'].max()
            add_col = max_col + 1
        if max_col >= 200 and library_type == 'high_fre':
            raise Exception("高频因子库最多存储200个因子，因子{}将超出总因子数！".format(factor_name))
        insert_sql = 'insert into personal_factors (factor, library_name, col, factor_type) values ("{}","{}",{},"{}")'.format(
            factor_name, library_name, add_col, factor_type)
        try:
            self.dml_xquant.execute(conn_name, insert_sql)
            self.dml_xquant.commit(conn_name)
        except:
            self.dml_xquant.rollback(conn_name)
            raise Exception('{}因子插入失败'.format(factor_name))
        finally:
            self.dml_xquant.close(conn_name)
        return {'factor': factor_name, 'library_name': library_name, 'col': str(add_col), 'factor_type': factor_type}

    def __get_factors(self, library_name):
        # 获取因子列表
        conn_name = str(int(time.time())) + str(threading.get_ident())
        self.__set_dml_xquant()
        sql = "select factor, col, factor_type from personal_factors where library_name='{}'".format(library_name)
        result = self.dml_xquant.getAllByPandas(conn_name, sql)
        self.dml_xquant.close(conn_name)
        factor_infos = {}
        for i, row in result.iterrows():
            if row['factor'] in ['MDDate', 'Factor']:
                continue
            factor_infos[row['factor']] = {'col': str(row['col']), 'factor_type': row['factor_type']}
        return factor_infos

    def get_library_info(self, refresh=False):
        """
        得到该用户所有的有权限访问的库信息和该库下面的所有因子信息
        :return:
        """
        self.__set_library_info(refresh)
        library_infos = {}
        for lib, lib_data in self.library_info['low_fre'].items():
            library_infos[lib] = [factor for factor, _ in lib_data.items()]
        for lib, lib_data in self.library_info['high_fre'].items():
            library_infos[lib] = [factor for factor, _ in lib_data.items()]

        return library_infos

    def get_library_securities(self):
        """
        得到该用户所有的有权限访问的库中的标的
        :return:
        """
        self.__set_library_info()
        library_infos = {}
        for lib, _ in self.library_info['high_fre'].items():
            library_path = os.path.join(self.base_save_path, 'high_fre', lib)
            file_list = os.listdir(library_path)
            library_infos[lib] = [file_name.split('=')[1] for file_name in file_list]
        return library_infos

    def update_factor_value_by_factor(self, library_name, factor_values, factor, check_olddata=False,
                                      allow_merge_olddata=True):
        # 查找所有库名，判断用户输入的库名是否存在
        self.__set_library_info()
        library_type = self.library_info['library_types'].get(library_name)
        if not library_type:
            raise Exception(
                "library_name doesn't exist: %s因子库不存在！" % library_name)
        if not library_type == 'low_fre':
            raise Exception('update_factor_value_by_factor方法仅支持低频因子数据更新！')
        library_info = self.library_info[library_type].get(library_name)
        if not library_info:
            raise Exception('因子库{} 暂未添加因子，请先添加因子！'.format(library_name))
        factor_info = library_info.get(factor)
        if not factor_info:
            raise Exception('因子库{}中没有因子{},请先添加因子'.format(library_name, factor))
        factor_type = factor_info['factor_type']

        for d in factor_values.index.get_level_values('MDDate').unique():
            if not is_valid_date(d, date_type='year_month_day'):
                raise Exception(
                    "【mddate_list】-{0}的格式不符合要求，日期类型为YYYYMMDD格式，如 '20200330'".format(
                        d))
        if list(factor_values.index.names) != ['MDDate', 'HTSCSecurityID']:
            raise Exception('请将MDDate与HTSCSecurityID设为multiindex')
        if len(factor_values.columns) != 1:
            raise Exception('请将列数设为一列')
        if 'Value' not in factor_values:
            col_name = list(factor_values.columns)[0]
            factor_values = factor_values.rename(columns={col_name: "Value"})
        if not factor_values.index.is_unique:
            raise Exception('索引不唯一')

        value_type = pa.Schema.from_pandas(factor_values).field('Value')
        if factor_type not in str(value_type.type):
            raise Exception(
                '因子类型应为{}, 实际为{}'.format(factor_type, str(value_type.type)))

        result_df = pd.DataFrame()
        low_fre_save_path = os.path.join(self.base_save_path, 'low_fre')
        library_path = os.path.join(low_fre_save_path, library_name)
        factor_name_path = os.path.join(library_path, 'Factor={}'.format(factor))
        # 是否检查旧数据
        if check_olddata:
            if os.path.exists(factor_name_path):
                dates = factor_values.index.get_level_values('MDDate').unique()
                schemas = pa.schema([("MDDate", pa.string()), ("HTSCSecurityID", pa.string()), value_type])
                result_df = self.__read_factor_data(library_path, factor, dates, schemas)
                if not allow_merge_olddata:
                    result_df_count = result_df.groupby('MDDate').count()
                    factor_values_count = factor_values.groupby('MDDate').count()
                    result_df_dates = result_df_count.index.tolist()
                    not_match_dates = []
                    for date in result_df_dates:
                        if result_df_count.loc[date]['Value'] != factor_values_count.loc[date]['Value']:
                            not_match_dates.append(date)
                    if not_match_dates:
                        raise Exception('以下日期:{} 新数据与原数据Security行数不一致'.format(not_match_dates))
        if result_df.empty:
            # 因子不存在，创建新dataframe
            result_df = pd.DataFrame(columns=['MDDate', 'HTSCSecurityID', 'Value'])

        factor_values_tmp = factor_values.reset_index(inplace=False)
        if result_df.empty:
            for col in result_df.columns:
                result_df[col] = result_df[col].astype(factor_values_tmp[col].dtype)
        result_df = pd.merge(result_df, factor_values_tmp, how='outer', on=['MDDate', 'HTSCSecurityID'], indicator=True)
        left_only = result_df[result_df['_merge'] == 'left_only']
        result_df.loc[left_only.index, 'Value_y'] = left_only['Value_x']
        result_df['Value'] = result_df['Value_y']
        result_df = result_df[['Value', 'MDDate', 'HTSCSecurityID']]
        result_df['Factor'] = factor
        table = pa.Table.from_pandas(result_df, preserve_index=False,
                                     nthreads=16)
        pq.write_to_dataset(table, library_path,
                            partition_cols=['Factor', 'MDDate'],
                            partition_filename_cb=lambda x: '-'.join(x) + '.parquet')
        return True

    def update_factor_value_by_security(self, library_name, factor_values, security, check_olddata=True):
        # 查找所有库名，判断用户输入的库名是否存在
        self.__set_library_info()
        owner = str(uuid.uuid4())
        library_type = self.library_info['library_types'].get(library_name)
        if not library_type:
            raise Exception(
                "library_name doesn't exist: %s因子库不存在！" % library_name)
        if not library_type == 'high_fre':
            raise Exception('update_factor_value_by_security方法仅支持高频因子数据更新！')
        factors = self.library_info[library_type].get(library_name)
        if not factors:
            raise Exception('因子库{} 暂未添加因子，请先添加因子！'.format(library_name))

        if 'MDDate' not in factor_values:
            raise Exception('factor_values中未包含MDDate字段')
        if 'MDTime' not in factor_values:
            raise Exception('factor_values中未包含MDTime字段')
        factor_values[['MDDate', 'MDTime']] = factor_values[['MDDate', 'MDTime']].astype('str')
        for d in factor_values.MDDate.unique():
            if not is_valid_date(d, date_type='year_month_day'):
                raise Exception(
                    "【mddate_list】-{0}的格式不符合要求，日期类型为YYYYMMDD格式，如 '20200330'".format(
                        d))
        if False in factor_values['MDTime'].map(lambda x: len(x) == 9).values:
            raise Exception('MDTime格式错误，请传入9位字符串，如092500000')

        df_factors = list(set(factor_values.columns.tolist()) - {'MDDate', 'MDTime'})

        factor_values_schema = pa.Schema.from_pandas(factor_values[df_factors])
        factor_cols = {}
        for factor_name in df_factors:
            factor_data = factors.get(factor_name)
            if not factor_data:
                raise Exception('因子库{}中没有因子{},请先添加因子'.format(library_name, factor_name))

            # 判断因子类型是否正确
            value_type = factor_values_schema.field(factor_name)
            if factor_data['factor_type'] not in str(value_type.type):
                value_type = factor_values_schema.field(factor_name)
                raise Exception('因子{}类型应为{}, 实际为{}'.format(factor_name,
                                                           factor_data[
                                                               'factor_type'],
                                                           str(
                                                               value_type.type)))
            factor_cols[factor_name] = str(factor_data['col'])

        high_fre_save_path = os.path.join(self.base_save_path, 'high_fre')
        library_path = os.path.join(high_fre_save_path, library_name)
        security_name_path = os.path.join(library_path, 'HTSCSecurityID={}'.format(security))

        # 是否存在旧数据
        result_df = pd.DataFrame()
        if os.path.exists(security_name_path):
            dates = factor_values.MDDate.unique()
            result_df = self.__read_security_data_by_concat(library_path, security, dates)
            # 是否检查旧数据
            if check_olddata and not result_df.empty:
                result_df_count = result_df.groupby('MDDate').count()
                factor_values_count = factor_values.groupby('MDDate').count()
                result_df_dates = result_df_count.index.tolist()
                not_match_dates = []
                for date in result_df_dates:
                    if result_df_count.loc[date]['MDTime'] != factor_values_count.loc[date]['MDTime']:
                        not_match_dates.append(date)
                if not_match_dates:
                    raise Exception('以下日期:{} 新数据与原数据MDTime行数不一致'.format(not_match_dates))

        if result_df.empty:
            result_df = pd.DataFrame(np.full((len(factor_values.index), 200), np.NAN),
                                     columns=[str(i + 1) for i in range(200)])
            result_df[["MDDate", "MDTime"]] = factor_values[["MDDate", "MDTime"]]

        factor_values_tmp = factor_values.set_index(['MDDate', 'MDTime'], drop=False, inplace=False)

        factor_values_tmp.rename(columns=factor_cols, inplace=True)
        result_df.set_index(['MDDate', 'MDTime'], drop=False, inplace=True)
        result_df.drop(factor_values_tmp.columns.tolist(), axis=1, inplace=True)
        result_df = pd.concat([result_df, factor_values_tmp], axis=1)
        result_df['HTSCSecurityID'] = security
        table = pa.Table.from_pandas(result_df, preserve_index=False, nthreads=16)

        try:
            self.__add_lock_high_factor(owner, library_name, security)
            error = None
            try:
                pq.write_to_dataset(table, library_path,
                                    partition_cols=['HTSCSecurityID',
                                                    'MDDate'],
                                    partition_filename_cb=lambda x: '-'.join(
                                        x) + '.parquet')
            except Exception as e:
                error = repr(e)
            self.__delete_lock_high_factor(owner, library_name, security,
                                           error)
        except Exception as e:
            raise e
        finally:
            try:
                self.__sql_connect.close()
            except Exception as e:
                raise e
        return True

    def get_factor_value(self, library_name, mddate_list, security_list=None, factor_list=None, sort=False,
                         in_dataframe=False):
        """
        查询指定因子库中的因子值
        :param library_name: 因子库名
        :param mddate_list: list, 必传，高频传入string（单个日期）
        :param security_list: list, 高频因子必传，低频选传，低频默认为因子库全部标的
        :param factor_list: list, 低频因子必传，高频选传，高频默认为因子库中全部因子
        :return:

        """
        # 查找所有库名，判断用户输入的库名是否存在
        self.__set_library_info()
        try:
            library_type = self.library_info['library_types'][library_name]
        except:
            raise Exception("base_save_path:{0},不存在library_name: {1}库，请检查因子数据入库的根目录！".format(self.base_save_path, library_name))
        library_info = self.library_info[library_type].get(library_name)
        if not library_info:
            raise Exception('该用户没有权限访问因子库{}'.format(library_name))
        if type(mddate_list) != list:
            raise Exception('mddate_list类型为list')
        if len(mddate_list) == 0:
            raise Exception('请传入mddate_list')
        mddate_list = list(set(mddate_list))
        for i in mddate_list:
            if not is_valid_date(i, date_type='year_month_day'):
                raise Exception(
                    "【mddate_list】-{0}的格式不符合要求，日期类型为YYYYMMDD格式，如 '20200330'".format(
                        i))
        if library_type == 'low_fre':
            # 非高频操作
            if not factor_list:
                raise Exception('低频因子按factor独立分区存储，必须传入factor_list')
            result_df = self.__get_low_frequency_factor_value(library_name, mddate_list, factor_list, security_list,
                                                              sort, in_dataframe)
        elif library_type == 'high_fre':
            #  高频操作
            if not security_list:
                raise Exception('高频因子按security独立分区存储，必须传入security_list参数')
            result_df = self.__get_high_frequency_factor_value(library_name, mddate_list, security_list,
                                                               factor_list, sort)
        else:
            raise Exception("仅支持低频和高频两类因子！")
        return result_df

    def __get_low_frequency_factor_value(self, library_name, mddate_list,
                                         factor_list, security_list=None,
                                         sort=False, in_dataframe=False):
        low_fre_path = os.path.join(self.base_save_path, 'low_fre')
        library_path = os.path.join(low_fre_path, library_name)
        self.__set_library_info()
        library_type = self.library_info['library_types'][library_name]
        library_info = self.library_info[library_type][library_name]
        factor_dict = {}
        for factor in factor_list:
            factor_type = library_info[factor]['factor_type']
            if factor_type not in self.pa_types:
                raise Exception(
                    '{}类型不在double,string'.format(factor_type))
            schemas = pa.schema(
                [("MDDate", pa.string()), ("HTSCSecurityID", pa.string()),
                 ('Value', self.pa_types[factor_type])])
            df = self.__read_factor_data(library_path, factor, mddate_list,
                                         schemas)
            df = df.reindex(columns=['MDDate', 'HTSCSecurityID', 'Value'])
            if security_list:
                df = df[df['HTSCSecurityID'].isin(security_list)]
            if sort:
                df.sort_values(['MDDate'], inplace=True)
            df.set_index(['MDDate', 'HTSCSecurityID'], inplace=True)
            if not in_dataframe:
                df = df['Value'].unstack(level='HTSCSecurityID')
                # del df.columns.name
                df.columns.name = None
            factor_dict[factor] = df

        if not in_dataframe:
            result = factor_dict
        else:
            # 以dataframe形式返回
            dfs = []
            for factor, df in factor_dict.items():
                df.rename({'Value': factor}, axis=1, inplace=True)
                dfs.append(df)
            result = pd.concat(dfs, axis=1)
        return result

    def __get_high_frequency_factor_value(self, library_name, mddate_list,
                                          security_list, factor_list=None,
                                          sort=False):
        high_fre_path = os.path.join(self.base_save_path, 'high_fre')
        library_path = os.path.join(high_fre_path, library_name)
        self.__set_library_info()
        library_type = self.library_info['library_types'][library_name]
        library_info = self.library_info[library_type][library_name]
        unset_columns = []
        factors = {}
        result_dict = {}

        if factor_list:
            for factor_name in factor_list:
                if factor_name in library_info:
                    factors[factor_name] = library_info[factor_name]
                else:
                    unset_columns.append(factor_name)
        else:
            factors = library_info

        if unset_columns:
            raise Exception('以下factor:{} 在因子库中不存在'.format(unset_columns))

        include_not_double = False
        factor_datas = {'cols': [], 'col_factors': {}, 'col_schemas': []}
        for factor_name, factor_data in factors.items():
            if factor_data['factor_type'] not in self.pa_types:
                raise Exception('{}类型不在double,string'.format(factor_data['factor_type']))
            factor_datas['cols'].append(factor_data['col'])
            factor_datas['col_factors'][factor_data['col']] = factor_name
            factor_datas['col_schemas'].append((factor_data['col'], self.pa_types[factor_data['factor_type']]))
            if factor_data['factor_type'] != 'double':
                include_not_double = True

        schemas = pa.schema(
            factor_datas['col_schemas'] + [("MDDate", pa.string()),
                                           ("MDTime", pa.string())])
        for security in security_list:
            if not include_not_double:
                df = self.__read_security_data(library_path, security, mddate_list,
                                               schemas)
            else:
                df = self.__read_security_data_by_concat(library_path, security,
                                                         mddate_list,
                                                         ['MDTime'] + factor_datas[
                                                             'cols'])
            if not df.empty:
                df = df.reindex(columns=['MDDate', 'MDTime'] + factor_datas[
                    'cols'])
                df.rename(columns=factor_datas['col_factors'], inplace=True)
                if sort:
                    df.sort_values(['MDDate', 'MDTime'], inplace=True)
            else:
                df = pd.DataFrame()
            result_dict[security] = df

        return result_dict

    @retry(stop_max_attempt_number=4, wait_fixed=2000)
    def __read_factor_data(self, library_path, factor, mddate_list, schemas):
        factor_path_list = []
        date_list = []
        factor_name_path = os.path.join(library_path,
                                        'Factor={}'.format(factor))
        for mddate in mddate_list:
            factor_mdate_path = os.path.join(factor_name_path,
                                             'MDDate={}'.format(mddate))
            factor_path = os.path.join(factor_mdate_path,
                                       '{}-{}.parquet'.format(factor, mddate))
            if not os.path.exists(factor_path):
                #logger.debug('{}路径不存在'.format(factor_path))
                continue
            factor_path_list.append(
                'MDDate={0}/{1}-{0}.parquet'.format(mddate, factor))
            date_list.append(mddate)
        if date_list:
            partitions = [ds.field("MDDate") == date for date in date_list]
            dataset = ds.FileSystemDataset.from_paths(factor_path_list,
                                                      schema=schemas,
                                                      format=ds.ParquetFileFormat(),
                                                      filesystem=fs.SubTreeFileSystem(
                                                          factor_name_path,
                                                          fs.LocalFileSystem()),
                                                      partitions=partitions)
            df = dataset.to_table().to_pandas()
        else:
            df = pd.DataFrame()
        return df

    @retry(stop_max_attempt_number=4, wait_fixed=2000)
    def __read_security_data(self, library_path, security, mddate_list, schemas):
        security_path_list = []
        date_list = []
        security_name_path = os.path.join(library_path,
                                          'HTSCSecurityID={}'.format(security))
        for mddate in mddate_list:
            security_mdate_path = os.path.join(security_name_path,
                                               'MDDate={}'.format(mddate))
            factor_path = os.path.join(security_mdate_path,
                                       '{}-{}.parquet'.format(security, mddate))
            if not os.path.exists(factor_path):
                #logger.debug('{}路径不存在'.format(factor_path))
                continue
            security_path_list.append(
                'MDDate={0}/{1}-{0}.parquet'.format(mddate, security))
            date_list.append(mddate)
        if date_list:
            partitions = [ds.field("MDDate") == date for date in date_list]
            dataset = ds.FileSystemDataset.from_paths(security_path_list,
                                                      schema=schemas,
                                                      format=ds.ParquetFileFormat(),
                                                      filesystem=fs.SubTreeFileSystem(
                                                          security_name_path,
                                                          fs.LocalFileSystem()),
                                                      partitions=partitions)
            df = dataset.to_table().to_pandas()
        else:
            df = pd.DataFrame()
        return df

    @retry(stop_max_attempt_number=4, wait_fixed=2000)
    def __read_security_data_by_concat(self, library_path, security,
                                       mddate_list, cols=None):
        security_df_list = []
        security_name_path = os.path.join(library_path,
                                          'HTSCSecurityID={}'.format(security))
        for mddate in mddate_list:
            security_mdate_path = os.path.join(security_name_path,
                                               'MDDate={}'.format(mddate))
            factor_path = os.path.join(security_mdate_path,
                                       '{}-{}.parquet'.format(security,
                                                              mddate))
            if not os.path.exists(factor_path):
                #logger.debug('{}路径不存在'.format(factor_path))
                continue
            if not cols:
                security_df = pq.read_table(factor_path).to_pandas()
            else:
                security_df = pq.read_table(factor_path,
                                            columns=cols).to_pandas()
            security_df['MDDate'] = mddate
            security_df_list.append(security_df)
        if security_df_list:
            df = pd.concat(security_df_list, ignore_index=True)
        else:
            df = pd.DataFrame()
        return df

    def search_by_stock_date(self, library_name, stock, mddate, factor_list):
        """
        指定因子库名、股票、日期，查询在指定因子列表中哪些因子有数据
        :param library_name: string:因子库名
        :param stock: string:股票
        :param mddate: string:日期
        :param factor_list: list:因子名列表
        :return:
        """
        self.__set_library_info()
        library_type = self.library_info['library_types'][library_name]
        if library_type != 'high_fre':
            raise Exception('该接口只在高频因子库使用')
        library_info = self.library_info[library_type].get(library_name)
        if not library_info:
            raise Exception('该用户没有权限访问因子库{}'.format(library_name))
        df = self.__get_high_frequency_factor_value(library_name, [mddate], [stock],
                                                    factor_list=factor_list)[stock]
        columns_na_dict = df.isna().all().to_dict()
        column_list = [col for col, is_na in columns_na_dict.items() if
                       not is_na]
        exist_factors = list(set(factor_list) & set(column_list))
        return exist_factors

    def search_by_stock_factor(self, library_name, stock, factor, mddate_list):
        """
        按因子库名、股票、因子查询指定日期列表中哪些日期有数据
        :param library_name: string:因子库名
        :param stock: string:股票
        :param factor: string:因子
        :param mddate_list: list:日期列表
        :return:
        """
        self.__set_library_info()
        library_type = self.library_info['library_types'][library_name]
        if library_type != 'high_fre':
            raise Exception('该接口只在高频因子库使用')
        library_info = self.library_info[library_type].get(library_name)
        if not library_info:
            raise Exception('该用户没有权限访问因子库{}'.format(library_name))
        df = self.__get_high_frequency_factor_value(library_name, mddate_list, [stock],
                                                    factor_list=[factor])[stock]
        df.set_index('MDDate', inplace=True)
        date_list = df[df[factor].notna()].index.tolist()
        exist_dates = list(set(date_list) & set(mddate_list))
        return exist_dates

    def search_by_stock(self, library_name, stock, mddate_list):
        """
        按因子库名、股票查询指定日期列表中哪些天有数据
        :param library_name: string:因子库名
        :param stock: string:股票
        :param mddate_list: list:日期列表
        :return:
        """
        self.__set_library_info()
        library_type = self.library_info['library_types'][library_name]
        if library_type != 'high_fre':
            raise Exception('该接口只在高频因子库使用')
        library_info = self.library_info[library_type].get(library_name)
        if not library_info:
            raise Exception('该用户没有权限访问因子库{}'.format(library_name))
        high_fre_path = os.path.join(self.base_save_path, 'high_fre')
        library_path = os.path.join(high_fre_path, library_name)
        security_name_path = os.path.join(library_path,
                                          'HTSCSecurityID={}'.format(stock))
        exist_date_list = []
        for mddate in mddate_list:
            security_mdate_path = os.path.join(security_name_path,
                                               'MDDate={}'.format(mddate))
            factor_path = os.path.join(security_mdate_path,
                                       '{}-{}.parquet'.format(stock,
                                                              mddate))
            if os.path.exists(factor_path):
                exist_date_list.append(mddate)
        return exist_date_list

    def search_by_date(self, library_name, mddate, stock_list):
        """
        按因子库名、日期查询指定股票列表中哪些股票有数据
        :param library_name: string:因子库名
        :param mddate: string:股票
        :param stock_list: list:股票列表
        :return:
        """
        self.__set_library_info()
        library_type = self.library_info['library_types'][library_name]
        if library_type != 'high_fre':
            raise Exception('该接口只在高频因子库使用')
        library_info = self.library_info[library_type].get(library_name)
        if not library_info:
            raise Exception('该用户没有权限访问因子库{}'.format(library_name))
        high_fre_path = os.path.join(self.base_save_path, 'high_fre')
        library_path = os.path.join(high_fre_path, library_name)
        exist_stock_list = []
        for stock in stock_list:
            security_name_path = os.path.join(library_path,
                                              'HTSCSecurityID={}'.format(
                                                  stock))
            security_mdate_path = os.path.join(security_name_path,
                                               'MDDate={}'.format(mddate))
            factor_path = os.path.join(security_mdate_path,
                                       '{}-{}.parquet'.format(stock, mddate))
            if os.path.exists(factor_path):
                exist_stock_list.append(stock)
        return exist_stock_list

    def save_metadata_overwrite(self, library_name, library_type, library_describe, factor_info):
        """
        存储因子元数据信息
        :param library_name: 因子库名，string类型
        :param  library_type: 因子库类型，目前只支持T+0和Alpha，T+0对应高频因子，Alpha对应非高频因子
        :param library_describe: 库描述，string类型，库信息描述
        :param factor_info: 因子信息，dict类型，key为因子名 value为因子描述 如：{'factor1':'个人因子1'}
        :return:
        """
        if not library_type in StorageConfig.keys():
            raise Exception("library_type 设置错误！请重新设置！目前只支持T+0和Alpha，Source_table_daily，Source_table_fully!")
        if not self.__naming_specification(library_name):
            raise Exception("library_name 命名不规范！请以字母开头且只能包含字母,数字和下划线！")
        # 查找所有库名，判断用户输入的库名是否存在
        self.__set_library_info_new()
        if library_type == "Source_table_daily":
            library_type = 'Daily'
        elif library_type == "Source_table_fully":
            library_type = 'Fully'
        elif library_type == 'Alpha':
            library_type = 'low_fre'
        else:
            library_type = 'high_fre'
        if not type(factor_info) == dict:
            raise Exception("factor_info 请传入字典！")
        for factor, _ in factor_info.items():
            if factor in ['datetime', 'symbol']:
                raise Exception('因子不允许以{}命名'.format(factor))
            if not self.__naming_specification(factor):
                raise Exception("%s因子命名不规范！" % str(factor))
        self.__delete_library_info(library_name, library_type)
        # 校验所存因子库中是否有同名
        if library_type in self.library_info_new:
            library_type_factors = []
            for lib in list(self.library_info_new[library_type].keys()):
                library_type_factors.extend(self.library_info_new[library_type][lib])
            exists_fac = []
            for i in factor_info:
                if i in library_type_factors:
                    exists_fac.append(i)
            if exists_fac:
                raise Exception(f"库类型library_type: {library_type}已存在因子名：{exists_fac},请检查后重新输入！")
        for factor_name, fac_describe in factor_info.items():
            self.__update_factor_new(library_name, library_describe, factor_name, fac_describe, library_type)
        factor_list = list(factor_info.keys())
        self.library_info_new[library_type][library_name] = factor_list
        self.library_info_new['library_types'][library_name] = library_type
        return True


    def __delete_library_info(self, library_name, library_type):
        conn_name = str(int(time.time())) + str(threading.get_ident())
        self.__set_dml_xquant()
        sql = "delete from personal_factors_new where library_name='{0}' and factor_freq='{1}'".format(library_name, library_type)

        try:
            self.dml_xquant.execute(conn_name, sql)
            self.dml_xquant.commit(conn_name)
            del self.library_info_new[library_type][library_name]
            del self.library_info_new['library_types'][library_name]
        except:
            self.dml_xquant.rollback(conn_name)
            raise Exception(f'library_type:{library_type}-library_name：{library_name}删除失败!')
        finally:
            self.dml_xquant.close(conn_name)


    def save_metadata(self, library_name, library_type, library_describe, factor_info):
        """
        存储因子元数据信息
        :param library_name: 因子库名，string类型
        :param  library_type: 因子库类型，目前只支持T+0和Alpha，T+0对应高频因子，Alpha对应非高频因子
        :param library_describe: 库描述，string类型，库信息描述
        :param factor_info: 因子信息，dict类型，key为因子名 value为因子描述 如：{'factor1':'个人因子1'}
        :return:
        """
        if not library_type in StorageConfig.keys():
            raise Exception("library_type 设置错误！请重新设置！目前只支持T+0和Alpha，Source_table_daily，Source_table_fully!")
        if not self.__naming_specification(library_name):
            raise Exception("library_name 命名不规范！请以字母开头且只能包含字母,数字和下划线！")
        # 得到所有库名
        self.__set_library_info_new()
        if library_type == "Source_table_daily":
            library_type = 'Daily'
        elif library_type == "Source_table_fully":
            library_type = 'Fully'
        elif library_type == 'Alpha':
            library_type = 'low_fre'
        else:
            library_type = 'high_fre'
        if library_name in self.library_info_new['library_types']:
            raise Exception("因子库{}已存在！请重新输入！".format(library_name))
        # 一个library_type下的因子不能有重复值
        if library_type in self.library_info_new:
            library_type_factors = []
            for lib in list(self.library_info_new[library_type].keys()):
                library_type_factors.extend(self.library_info_new[library_type][lib])
            exists_fac = []
            for i in factor_info:
                if i in library_type_factors:
                    exists_fac.append(i)
            if exists_fac:
                raise Exception(f"库类型library_type: {library_type}已存在因子名：{exists_fac},请检查后重新输入！")
        else:
            self.library_info_new[library_type] = {}

        if not type(factor_info) == dict:
            raise Exception("factor_info 请传入字典！")
        for factor, _ in factor_info.items():
            if factor in ['datetime', 'symbol']:
                raise Exception('因子不允许以{}命名'.format(factor))
            if not self.__naming_specification(factor):
                raise Exception("%s因子命名不规范！" % str(factor))

        # 得到该库所有因子名
        library_info = self.library_info_new[library_type].get(library_name)
        if library_info:
            raise Exception(f"library_name:{library_name} 元数据已存在该因子库及因子信息，禁止再新增过减少因子！")
        else:
            self.library_info_new[library_type][library_name] = []
        for factor_name, fac_describe in factor_info.items():
            if library_name.upper() =="ZX" and fac_describe == "datetime":
                library_type = "Daily"
            elif library_name.upper() =="ZX" and fac_describe == "":
                library_type = "Fully"
            self.__update_factor_new(library_name, library_describe, factor_name, fac_describe, library_type)
            self.library_info_new[library_type][library_name].append(factor_name)
        return True

    def __update_factor_new(self, library_name, library_describe, factor_name, fac_describe, library_type):
        conn_name = str(int(time.time())) + str(threading.get_ident())
        self.__set_dml_xquant()
        insert_sql = 'insert into personal_factors_new (factor,factor_describe,factor_freq,library_name,library_describe) values ("{}","{}","{}","{}","{}")'.format(
            factor_name,fac_describe,library_type,library_name,library_describe)
        try:
            self.dml_xquant.execute(conn_name, insert_sql)
            self.dml_xquant.commit(conn_name)
        except:
            self.dml_xquant.rollback(conn_name)
            raise Exception('{}因子插入失败'.format(factor_name))
        finally:
            self.dml_xquant.close(conn_name)

    def get_metadata(self, library_type, library_name=None, factor_name=None):
        """
        获取元数据信息
        :param library_type: 库类型，string类型，目前只支持T+0和Alpha，T+0对应高频因子，Alpha对应非高频因子
        :param library_name: 因子库名，string类型，默认None查询library_type下的所有库信息
        :param factor_name: string或listl类型，如'factor1'或['factor1','factor2']，默认None查询所有属于library_name的因子
        :return:
        """
        if not library_type in StorageConfig.keys():
            raise Exception("library_type 设置错误！请重新设置！目前只支持T+0和Alpha，Source_table_daily，Source_table_fully!")
        if library_type == "Source_table_daily":
            library_type = 'Daily'
        elif library_type == "Source_table_fully":
            library_type = 'Fully'
        elif library_type == 'Alpha':
            library_type = 'low_fre'
        else:
            library_type = 'high_fre'

        self.__set_library_info_new()
        if not self.library_info_new.get(library_type):
            raise Exception(f"没有库类型library_type：{library_type}的相关信息，请重新输入！")
        result = {}
        if library_name is None:
            if factor_name is None:
                for lib in self.library_info_new[library_type]:
                    library_path = f"{library_type}/{lib}"
                    result[library_path] = self.library_info_new[library_type][lib]
            else:
                if not isinstance(factor_name, str) and isinstance(factor_name, list):
                    raise Exception(f"factor_name:{factor_name}应为string或listl类型！")
                if isinstance(factor_name, str):
                    factor_name = [factor_name]
                for lib in self.library_info_new[library_type]:
                    library_path = f"{library_type}/{lib}"
                    factor_list = [i for i in self.library_info_new[library_type][lib] if i in factor_name]
                    if factor_list:
                        result[library_path] = factor_list
        else:
            assert isinstance(library_name, str), "library_name为string类型！"
            if factor_name is None:
                if library_name in self.library_info_new[library_type]:
                    library_path = f"{library_type}/{library_name}"
                    result[library_path] = self.library_info_new[library_type][library_name]
                else:
                    raise Exception(f"库类型library_type：{library_type}没有库{library_name}的相关信息，请重新输入！")
            else:
                if not isinstance(factor_name, str) and isinstance(factor_name, list):
                    raise Exception(f"factor_name:{factor_name}应为string或listl类型！")
                if isinstance(factor_name, str):
                    factor_name = [factor_name]
                if library_name in self.library_info_new[library_type]:
                    library_path = f"{library_type}/{library_name}"
                    factor_list = [i for i in self.library_info_new[library_type][library_name] if i in factor_name]
                    result[library_path] = factor_list
                else:
                    raise Exception(f"库类型library_type：{library_type}没有库{library_name}的相关信息，请重新输入！")
        return result


    def update_factor_value_daily(self, df_new, base_save_path, library_name, month):
        # 更新日频因子数据
        # 新元数据对应因子数据存储
        if not isinstance(df_new, pd.DataFrame) or df_new.empty:
            print("存储的数据不是pd.DataFrame格式或数据为空：",df_new)
            return False
        # self.__set_library_info_new()
        # library_type = self.library_info_new['library_types'].get(library_name)
        # if not library_type:
        #     raise Exception(
        #         "library_name doesn't exist: %s因子库不存在！" % library_name)
        # library_fac_list = self.library_info_new[library_type].get(library_name)
        # df_new = df_new.reindex(columns=['datetime', 'symbol'] + library_fac_list)

        save_path  = os.path.join(base_save_path, month)
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        file_path = os.path.join(save_path, f"{library_name}.parquet")
        if not os.path.exists(file_path):
            df_new.sort_values(by='datetime', inplace=True)
            df_new.to_parquet(file_path)
        else:
            df_his = pd.read_parquet(file_path, engine="pyarrow")
            df_his.reset_index(inplace=True, drop=True)
            df_new.reset_index(inplace=True, drop=True)
            df = pd.concat([df_his, df_new], ignore_index=True)
            df = df.drop_duplicates(subset=['datetime', 'symbol'], keep="last")
            df.sort_values(by='datetime', inplace=True)
            df.to_parquet(file_path)
        return True

    def get_factor_value_daily(self, start_date, end_date, base_save_path, library_name, factor_list=None):
        date_list = tradingDay(start_date, end_date)
        if not date_list:
            raise Exception("在日期{0}~{1}之间没有交易日".format(start_date, end_date))
        per_month_dates = {}
        for i in date_list:
            if i[:6] not in per_month_dates:
                per_month_dates[i[:6]] = [i]
            else:
                per_month_dates[i[:6]].append(i)
        df_list = []
        for month in per_month_dates:
            file_path = os.path.join(base_save_path, month, f"{library_name}.parquet")
            if os.path.exists(file_path):
                df_p = pd.read_parquet(file_path, engine="pyarrow")
                if factor_list:
                    df_p = df_p[factor_list]
                df_p = df_p[(df_p["datetime"]>=start_date) & (df_p["datetime"]<=end_date)]
                df_list.append(df_p)
            else:
                print(f"month:{month}-{library_name}暂未存储因子数据！")
        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            df = df.sort_values(by="datetime")
        else:
            df = pd.DataFrame()
        return df

    def save_factor_data(self, factor_data, base_save_path, library_name):
        if len(factor_data) == 0:
            print("因子数据为空！")
            return
        date_list = list(factor_data["datetime"].unique())
        per_month_dates = {}
        for i in date_list:
            if i[:6] not in per_month_dates:
                per_month_dates[i[:6]] = [i]
            else:
                per_month_dates[i[:6]].append(i)
        for month, dates in per_month_dates.items():
            df_new = factor_data[factor_data["datetime"].isin(dates)]
            save_path = os.path.join(base_save_path, library_name, month)
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, f"{library_name}.parquet")
            if not os.path.exists(file_path):
                df_new.sort_values(by='datetime', inplace=True)
                df_new.to_parquet(file_path)
            else:
                df_his = pd.read_parquet(file_path, engine="pyarrow")
                df_his.reset_index(inplace=True, drop=True)
                df_new.reset_index(inplace=True, drop=True)
                df = pd.concat([df_his, df_new], ignore_index=True)
                df = df.drop_duplicates(subset=['datetime', 'symbol'], keep="last")
                df.sort_values(by='datetime', inplace=True)
                df.to_parquet(file_path)
        return True


if __name__ == "__main__":
    fa = FactorData(base_save_path="/home/appadmin")

    # output_factor_names = ['big_order1_bid_amt_extra_large_hf1',
    #                        'big_order1_bid_amt_extra_large_hf2',
    #                        'big_order1_bid_amt_extra_large_hf3',
    #                        'big_order1_bid_amt_extra_large_hf4',
    #                        'big_order1_bid_amt_extra_large_hf5',
    #                        'big_order1_bid_amt_extra_large_hf6',
    #                        'big_order1_bid_amt_extra_large_hf7',
    #                        'big_order1_bid_amt_extra_large_hf8', 'big_order1_bid_amt_large_hf1',
    #                        'big_order1_bid_amt_large_hf2', 'big_order1_bid_amt_large_hf3',
    #                        'big_order1_bid_amt_large_hf4', 'big_order1_bid_amt_large_hf5',
    #                        'big_order1_bid_amt_large_hf6', 'big_order1_bid_amt_large_hf7',
    #                        'big_order1_bid_amt_large_hf8', 'big_order1_bid_amt_small_hf1',
    #                        'big_order1_bid_amt_small_hf2', 'big_order1_bid_amt_small_hf3',
    #                        'big_order1_bid_amt_small_hf4', 'big_order1_bid_amt_small_hf5',
    #                        'big_order1_bid_amt_small_hf6', 'big_order1_bid_amt_small_hf7',
    #                        'big_order1_bid_amt_small_hf8']
    # factor_info = {}
    # for fac in output_factor_names:
    #     factor_info[fac] = '新增因子'
    #
    # # 存储元数据
    # # fa.save_metadata_overwrite(library_name='test_bie',library_type='Alpha',library_describe='测试库',factor_info=factor_info)
    # # fa.save_metadata(library_name='test_bie',library_type='Alpha',library_describe='测试库',factor_info=factor_info)
    # # # # 查询元数据
    # # library_info = fa.get_metadata(library_type='Alpha',library_name='test_bie',factor_name='big_order1_bid_amt_extra_large_hf1')# library_name='test_bie',factor_name='big_order1_bid_amt_extra_large_hf1'
    # # print(library_info)
    #
    # df = fa.get_factor_value_daily("20241101", "20241105", '/tmp/pycharm_project_216/0_task_2025/rayframe_work_0513/quant_data', "test_bie")
    # print(df)
    # fa.create_factor_library("daily_factor", "Alpha")


