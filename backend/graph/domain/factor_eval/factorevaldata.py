from FactorEvaluate import Factor_with_data
from L3FactorFrame.FactorLibManager import FactorLib
import json
import time
from xquant.factordata import FactorData
import random

fl = FactorLib()
fa = FactorData()


factor_list = [f'cjy_{i}' for i in range(1,42)]

corr_path = "/dfs/group/800657/025036/factor_eval_std/result/corr_data.csv"
result_path = "/dfs/group/800657/025036/factor_eval_std/result/result_data.csv"
t1 = time.time()
data_path = "/dfs/group/800657/025036/cjy.parquet"
FWC = Factor_with_data(data_path,factor_list,10)
FWC.factor_eval_data()
t2 = time.time()
print(t2-t1)