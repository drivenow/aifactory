import polars as pl
import pandas as pd
import time
import ray
import os,sys
import json
sys.path.insert(0, "/dfs/group/800657/025036/scratch/")
from L3FactorFrame.UpdateL3PyFactor import UpdateFlyingFactor
from xquant.factordata import FactorData
import shutil
from src.factor_eval import *
from L3FactorFrame.FactorLibManager import FactorLib
from pathlib import Path




mode = "code"                 ####"code" or "data"

####将因子和非因子拷贝到运行目录
def copy_factor_code(src_folder, tar_folder):
    for item in os.listdir(src_folder):
        src_path = os.path.join(src_folder,item)
        tar_path = os.path.join(tar_folder,item)
        if os.path.isfile(src_path):
            if not os.path.exists(tar_folder):
                shutil.copy2(src_path, tar_path)




####对一个因子的全部数据评测
def EvalFactor(symbol,dates,subset_list,label,factor_list,njobs,data):
        fl = FactorLib()
        factor_df = []
        for date in dates:
            try:
                if data:
                    file_path = f"/dfs/group/800657/library/l3_data/l3_factor/research/python/11S/factor/{symbol}/{symbol}_{date}.parquet"
                    daily_factor_df = pl.read_parquet(file_path)
                    daily_factor_df = daily_factor_df.with_columns(pl.col('DateTime').cast(pl.Datetime("ns")))
                else:
                    daily_factor_df     = fl.load_factor_data('/research/python/1S/factor',symbols = symbol,start_date = date,end_date = date)
                daily_label_df      = fl.load_factor_data('/research/cpp/1S/label',symbols = symbol,start_date = date,end_date = date)
                daily_df = daily_factor_df.join(daily_label_df,on='DateTime',how='inner')
                daily_df = daily_df.with_columns(pl.col("DateTime").dt.date().alias("MDDate"))
            except Exception as e:
                print(e)
                continue
            factor_df.append(daily_df)
        df = pl.concat(factor_df)
        df = df.drop_nulls(subset=subset_list)
        df = df.to_pandas()
        FEM = FactorEvaluatorMulti(label_col = label,
                                    factor_lis = factor_list,
                                    symbol_lis = symbol, 
                                    )
        FEM.get_eval_info(df, save_path= False, njobs = njobs)
        # FEM.get_eval_info(df, save_path= False, njobs=1)
        symbol_result = FEM.factor_summary(save_path= False,load_path=False)
        return symbol_result

        

###计算全体因子单日的相关系数
def calc_daily_corr(date,symbols,factor_list,old = True,data = True):
    fl = FactorLib()
    df = []
    for symbol in symbols:
        try:
            if data:
                factor_df = pl.read_parquet(f'/dfs/group/800657/library/l3_data/l3_factor/research/python/11S/factor/{symbol}/{symbol}_{date}.parquet')
                factor_df = factor_df.with_columns(pl.col('DateTime').cast(pl.Datetime("ns")))
            else:
                factor_df = fl.load_factor_data('/research/python/1S/factor',symbols = symbol,start_date = date,end_date = date)
            factor_df = factor_df.select(factor_list+['DateTime','Symbol'])
            if old:
               old_factor_list = json.load(open("/dfs/group/800657/025036/factor_eval_std/factor_list.json", "r"))
               old_factor_df = fl.load_factor_data('/release/cpp/1S/factor',symbols = symbol,start_date = date,end_date = date)
               old_factor_df = old_factor_df.select(old_factor_list+['DateTime','Symbol'])
               factor_df = factor_df.join(old_factor_df,on=['DateTime','Symbol'],how='inner')
            factor_df = factor_df.drop_nulls()
            df.append(factor_df)
        except Exception as e:
            print(e)
            continue
    df = pl.concat(df)
    df = df.drop(['DateTime','Symbol'])
    daily_corr = df.corr()
    daily_corr = daily_corr.to_pandas()
    return daily_corr



####在相关系数表中找到相关系数大的因子
def format_high_corr(corr_series: pd.Series, target: str, threshold = 0.85) -> str:
    high_corr = corr_series[(corr_series >= threshold) & (corr_series.index != target)]
    # 按相关性降序排列
    high_corr = high_corr.sort_values(ascending=False)
    parts = [f"{idx}:{val:.2f}" for idx, val in high_corr.items()]
    return ", ".join(parts)










#有python因子代码(code)
class Factor_with_code:
    def __init__(self, factor_list, base_path, num_cpus):
        fa = FactorData()
        self.factor_list = factor_list
        self.num_cpus = num_cpus
        self.dates = json.load(open("/dfs/group/800657/025036/factor_eval_std/dates.json","r")) 
        # self.dates = ["20250512","20241220"]
        self.symbols = json.load(open("/dfs/group/800657/025036/factor_eval_std/eval_list.json","r"))
        # self.symbols = ["688158.SH","000016.SZ","300394.SZ","300682.SZ"]
        
        self.base_path = base_path
        self.label = "Label_VC_3_2"
        
        

    def factor_data_generate(self):
        
        self.input_base_dir =  "/dfs/group/800657/library/l3_data/"  # 原始逐笔委托数据目录
        self.event_path = os.path.join(self.base_path, "L3FactorFrame/Events")                     # l3因子触发计算事件目录
        self.factor_path = os.path.join(self.base_path, "L3FactorFrame/Factors")                   # 因子计算目录
        self.nonfactor_path = os.path.join(self.base_path, "L3FactorFrame/NonFactors")             # 依赖因子触发目录
        self.mode = "SAMPLE_1S"
        
        copy_factor_code('./Factors', self.factor_path)
        copy_factor_code('./NonFactors', self.nonfactor_path)
        ####将因子，非因子代码保存到运行目录下

        save_mode = True                            # 是否保存因子。save_mode为False时，userID、library、cover参数无效
        userID="013150"                              # 用户
        library="research/python/1S/factor"     # 要保存的库
        cover= True 
        print("开始生成因子数据")
        ray.init(num_cpus=self.num_cpus, local_mode=False)
        remote_func = ray.remote(max_calls=1)(UpdateFlyingFactor)
        tasks = []
        for date in self.dates:
            for symbol in self.symbols:
                tasks.append(remote_func.remote(symbol, date, self.factor_list, self.factor_path, self.event_path, self.nonfactor_path,
                                            mode=self.mode, input_base_dir=self.input_base_dir,
                                            save_mode=save_mode, userID=userID, library=library, cover=cover))
        reses = ray.get(tasks)
        print("因子数据已生成完毕")
    

    

    def calculate_correlation(self,corr_path):
        # corr_matrix = pl.read_csv("/dfs/group/800657/025036/factor_eval_std/result/.csv",index_col=0)
        self.factor_list = list(self.factor_list.keys())
        corr_matrix = None
        tasks = []
        print("开始计算因子间相关性")
        ray.init(num_cpus = self.num_cpus, local_mode=False)
        remote_func = ray.remote(max_calls=1)(calc_daily_corr)
        for date in self.dates:
            tasks.append(remote_func.remote(date,self.symbols,self.factor_list,old = True,data = False))
        reses = ray.get(tasks)
        for daily_corr in reses:
            if corr_matrix is None:
                corr_matrix = daily_corr.copy()
            else:
                corr_matrix += daily_corr
        corr_matrix = corr_matrix / len(self.dates)
        # return corr_matrix
        print(corr_matrix)
        corr_matrix.to_csv(corr_path)


    
    def factor_eval_code(self,corr_path,result_path):
            self.factor_list = list(self.factor_list.keys())
            df_list = []
            last_col = []
            subset_list = [self.label]+self.factor_list
            print("开始评估因子")
            ray.init(num_cpus = self.num_cpus, local_mode=False)
            for symbol in self.symbols:
                    symbol_result = EvalFactor(symbol,self.dates,subset_list,self.label,self.factor_list,njobs=self.num_cpus,data = False)
                    df_list.append(symbol_result)
            result_df = pd.concat(df_list).groupby("Factor").mean()
            corr_mat = pd.read_csv(corr_path)
            corr_mat.index = corr_mat.columns[1:]
            for factor in self.factor_list:
                s = corr_mat[factor]
                formatted_str = format_high_corr(s,factor,0.85)
                high_corr = pd.DataFrame({"Factor":[factor],"high_corr":[formatted_str]})
                last_col.append(high_corr)
            last_col = pd.concat(last_col)
            result_df = result_df.merge(last_col,on = "Factor", how = "inner")
            result_df.to_csv(result_path)
            print(result_df)

    


            















####有因子数据(data)
class Factor_with_data:
    
    def __init__(self, data_path, factor_list,num_cpus):
        self.data_path = data_path
        self.factor_list = factor_list
        self.num_cpus = num_cpus
        self.dates = json.load(open("/dfs/group/800657/025036/factor_eval_std/dates.json","r"))
        self.dates = ["20250414","20250417","20250422","20250512","20250513","20250603","20250609","20250625","20250703","20250707","20250708","20250804","20250813","20250827","20250829","20250902","20250912","20250926","20251021","20251031"]
        # self.dates = ["20250414"]
        self.symbols = json.load(open("/dfs/group/800657/025036/factor_eval_std/eval_list.json","r"))
        self.symbols = os.listdir('/dfs/group/800657/library/l3_data/l3_factor/research/python/11S/factor')
        # self.symbols = ["603308.SH"]
        self.label = "Label_VC_3_2"




    def factor_data_generate(self):
        df = pl.read_parquet(self.data_path)
        print("开始数据转换")
        df_with_date = df.with_columns(pl.col('DateTime').dt.strftime("%Y%m%d").alias("date"))
        output_dir = Path('/dfs/group/800657/library/l3_data/l3_factor/research/python/11S/factor')
        for group_keys,group_df in df_with_date.group_by(['Symbol',"date"]):
            symbol,date = group_keys
            symbol_dir = output_dir/str(symbol)
            symbol_dir.mkdir(parents = True,exist_ok = True)
            file_path = symbol_dir/f"{symbol}_{date}.parquet"
            group_df.drop("date").write_parquet(file_path)
        print("done")
    

    def calculate_correlation(self,corr_path):
        self.factor_list = list(self.factor_list.keys())
        corr_matrix = None
        tasks = []
        print("开始计算因子间相关性")
        ray.init(num_cpus = self.num_cpus, local_mode=False)
        remote_func = ray.remote(max_calls=1)(calc_daily_corr)
        for date in self.dates:
            tasks.append(remote_func.remote(date,self.symbols,self.factor_list,old = True,data = True))
        reses = ray.get(tasks)
        for daily_corr in reses:
            if corr_matrix is None:
                corr_matrix = daily_corr.copy()
            else:
                corr_matrix += daily_corr
        corr_matrix = corr_matrix / len(self.dates)
        print(corr_matrix)
        corr_matrix.to_csv(corr_path)
   

    
        
    def factor_eval_data(self,corr_path,result_path):
        self.factor_list = list(self.factor_list.keys())
        df_list = []
        last_col = []
        subset_list = [self.label]+self.factor_list
        print("开始评估因子")
        ray.init(num_cpus = self.num_cpus, local_mode=False)
        for symbol in self.symbols:
                symbol_result = EvalFactor(symbol,self.dates,subset_list,self.label,self.factor_list,njobs=self.num_cpus,data = True)
                df_list.append(symbol_result)
        result_df = pd.concat(df_list).groupby("Factor").mean()
        corr_mat = pd.read_csv(corr_path)
        corr_mat.index = corr_mat.columns[1:]
        for factor in self.factor_list:
            s = corr_mat[factor]
            formatted_str = format_high_corr(s,factor,0.85)
            high_corr = pd.DataFrame({"Factor":[factor],"high_corr":[formatted_str]})
            last_col.append(high_corr)
        last_col = pd.concat(last_col)
        result_df = result_df.merge(last_col,on = "Factor", how = "inner")   
        result_df.to_csv(result_path)
        print(result_df)
