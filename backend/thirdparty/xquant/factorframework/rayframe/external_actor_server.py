import ray
import os
import polars as pl
import time
import json
from filelock import FileLock
from collections import defaultdict
import subprocess
from xquant.factorframework.rayframe.mkdata.DFSDataLoader import get_ori_min_data_dfs
from xquant.factordata import FactorData


actor_local = None


def create_cache_actor(actor_name="ray_factor_framework", cache_file="/tmp/factor_framework_default", local_mode=False, **kwargs):
    """
    创建全局缓存对象，数据存放在Ray的共享内存中，可以跨进程通过get_cache_actor来访问
    :param cache_file:
    :return:
    """
    if local_mode:
        global actor_local
        actor_local = FrameWorkGlobalCache(**kwargs)
        actor_local.cache_ori_min_data(security_type="STOCK", local_path = None)
        return actor_local
    else:
        cache_file_lock = cache_file + "_lock"
        try:
            flock = FileLock(cache_file_lock, timeout=2)
            with flock:
                print("create_cache_actor entering...")
                # time.sleep(5)
                if not ray.is_initialized():
                    try:
                        # 链接一个已经存在的集群
                        ray.init("auto", ignore_reinit_error=True)
                    except Exception as e:
                        dill_dir = os.path.join("/dfs/user/", os.listdir("/dfs/user/")[0])
                        print("dill_dir: ", dill_dir, e)
                        ray.init(_system_config={"object_spilling_config": json.dumps(
                            {"type": "filesystem", "params": {"directory_path": dill_dir}, })}, ignore_reinit_error=True)

                # 创建actor
                # max_concurrency 最大允许8个并发执行Ray远程函数，不保证并发的顺序
                actor_calss = ray.remote(FrameWorkGlobalCache)
                actor = actor_calss.options(name=actor_name, namespace="global", lifetime="detached",
                                            max_concurrency=12).remote(**kwargs)
                flock.release()
                print("create_cache_actor finished!")
            return actor
        except Exception as e:
            # 有文件锁，其他进程调用时非阻塞会报错
            print("create_cache_actor waiting...", e)
            time.sleep(1)  # 等待create_cache_actor完成
            return None


def get_cache_actor(actor_name="ray_factor_framework"):
    """从当前ray集群中，按照名称获取全局行情actor对象

    通过以下代码远程获取行情：
    actor = get_cache_actor()
    # 从全局行情Actor获取行情，返回polars.DataFrame
    obj = actor.get_ori_min_data.remote(self, start_time, end_time, security_type)
    polars_df = ray.get(obj)
    """
    try:
        if not ray.is_initialized():
            ray.init("auto", ignore_reinit_error=True)
        actor = ray.get_actor(actor_name, namespace="global")
    except Exception as e:
        raise Exception("获取外挂行情失败，请在run_securities_days中设置use_external_data为True：", e)
    return actor


def global_get_ori_min_data(stock, start_time, end_time):
    if ray.is_initialized():
        actor = get_cache_actor()
        task = actor.get_ori_min_data.remote(stock, start_time, end_time)
        df = ray.get(task)
    else:
        global actor_local
        df = actor_local.get_ori_min_data(stock, start_time, end_time)
    return df


class FrameWorkGlobalCache:
    def __init__(self, global_start_date, global_end_date):
        self.cache_finish_flag = defaultdict(lambda: False)
        self.global_cache_data_source = defaultdict(None)
        # self.global_cache_data = defaultdict(lambda: pl.DataFrame())
        self.global_start_date = global_start_date
        self.global_end_date = global_end_date
        self.fa = FactorData()
        self.tradingdays = [str(i) for i in self.fa.tradingday(global_start_date, global_end_date)]

    def cache_ori_min_data(self, stocks=None, indicators=None, security_type="STOCK", local_path = None):
        if not self.cache_finish_flag.get("min"):
            if local_path:
                # file_name = local_path.split("/")[-1]
                # if not file_name.endswith(".parquet"):
                #     raise Exception("本地数据请传入分钟行情的parquet文件路径！")
                # df = pl.read_parquet(local_path)
                from xquant.marketdata import MarketData
                mdp = MarketData()
                df = mdp.get_data_by_time_frame("Kline1m4ZT", "000001.SZ", 
                                                f"{self.global_start_date} 093000000", 
                                                f"{self.global_end_date} 150000250",["3"], sort_by_receive_time=True)
                df["MDDate"] = df["MDDate"].astype(int)
                df = pl.from_pandas(df)
            else:
                self.base_dir = "/dfs/user/020259/NASDB/"
                self.ori_min_base_dir = os.path.join(self.base_dir, "ORI_MINUTE_DATA")
                df = get_ori_min_data_dfs(str(self.global_start_date), str(self.global_end_date), stocks, indicators, security_type)
            self.global_cache_data_source["min"] = df
            self.cache_finish_flag["min"] = True
            print("ori_min_data 数据缓存成功 ! 数据形状为: ", df.shape)


    def get_ori_min_data(self, stock, end_time, look_back_days = -1):
        """
        # 获取一段时间的行情数据
        end_time: 截止时间
        look_back_days: 回看前n天的数据
        """
        i = 0
        end_time = str(end_time)
        while not self.cache_finish_flag["min"]:
            # print("waiting cache_finish_flag: {}".format(unique_str))
            time.sleep(5)
            i += 1
            if i >= 20:
                raise Exception("min的数据未缓存！")
            else:
                continue
        if "min" not in self.global_cache_data_source:
            raise Exception("get_ori_min_data Error: min_data cache {0}-{1} failed!".format(end_time, look_back_days))
        cache_data = self.global_cache_data_source["min"]
        # 获取前n天的数据
        end_index = self.tradingdays.index(end_time)
        tradingdays = self.tradingdays[max(end_index+look_back_days+1, 0):end_index+1]
        df = cache_data.filter((pl.col('MDDate').is_in(tradingdays)) & (pl.col("HTSCSecurityID")==stock)).to_pandas()
        return df


    def delete_min_cache_data(self,):
        if "min" in self.cache_finish_flag:
            del self.cache_finish_flag["min"]
            del self.global_cache_data["min"]
            print("{0}-{1} 外挂存储数据删除成功！".format(self.global_start_date, self.global_end_date))


if __name__ == '__main__':
    from rayframe.calculation.helper import start_public_ray, stop_public_ray
    # 启动Ray集群主节点
    start_public_ray(cpu_nums=4, ray_memory=10)
    # 创建远程服务
    actor = create_cache_actor(global_start_date = '20250301', global_end_date = '20250325')
    # # 缓存数据
    task = actor.cache_ori_min_data.remote(security_type="STOCK", local_path="/tmp/pycharm_project_216/rayframe/data/202301.parquet")
    ray.get(task)
    # # ----------------------------------
    # 全局获取数据
    df = global_get_ori_min_data("000001.SZ", '20250301', '20250325')
    print(df)
    # # -----------------------------------------
    # # 删除外挂数据
    # # 获取远程服务
    # actor = get_cache_actor()
    # task = actor.delete_cache_data.remote('20250301', '20250325', security_type="STOCK")
    # ray.get(task)
    # # --------------------------------
    # # 停止Ray集群主节点
    stop_public_ray()

