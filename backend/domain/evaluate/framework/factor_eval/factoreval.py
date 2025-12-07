#多因子多标的多天

from FactorEvaluate import Factor_with_code
from L3FactorFrame.FactorLibManager import FactorLib
import json
import time
from xquant.factordata import FactorData
import random

fl = FactorLib()
fa = FactorData()
factor_list = {
    "FactorOBIC":[{}],
    "FactorOrderOBIC":[{}],
    "FactorTradeOBIC":[{}],
    "FactorCancelOBIC":[{}],
    "FactorOBIS":[{}],
    "FactorOrderOBIS":[{}],
    "FactorTradeOBIS":[{}],
    "FactorCancelOBIS":[{}],
}
print(factor_list)
t1 = time.time()
base_path = "/dfs/group/800657/025036/scratch/"
corr_path = "/dfs/group/800657/025036/factor_eval_std/result/corr.csv"
result_path = "/dfs/group/800657/025036/factor_eval_std/result/result_modify.csv"
FWC = Factor_with_code(factor_list,base_path,20)
FWC.factor_data_generate()
FWC.calculate_correlation(corr_path)
FWC.factor_eval_code(corr_path,result_path)
t2 = time.time()
print(t2-t1)
