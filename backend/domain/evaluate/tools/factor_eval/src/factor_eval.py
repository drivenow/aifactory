import polars as pl
import numpy as np
from scipy.stats import pearsonr, spearmanr, kurtosis, skew
from sklearn.metrics import mutual_info_score
import ray
# from AutoMiningFrame.DataCaculation.entry.FactorManager import FactorProvider
import pandas as pd
import warnings
import pickle
import time
import os
warnings.filterwarnings('ignore', category=UserWarning, module='ray')
pd.set_option('display.max_colwidth', 0)
pd.set_option('display.width', 1000)
# fd = FactorProvider("019771")

class FactorEvaluatorBase:
    """ 基础函数 评价【单因子】 【单标的】 【单天】 """
    def __init__(self, df: pl.DataFrame, factor_col: str):
        # 这里 df 包含 多票多天
        self.df = df
        self.factor_col = factor_col
        self.eval_res = {}

    def check_data(self):
        # 检查是否有非NaN值
        non_na = self.df[self.factor_col].dropna()
        if len(non_na) <= 0.3*len(self.df):
            #print("因子数据异常：缺失")
            return "All_NONE" # 全是NaN，认为所有元素相同
        elif self.df[self.factor_col].std() == 0:
            #print("因子数据异常：全一致")
            return "ALL_SAME"
        return "PASS"
    
    def check_corr(self, label_col):
        if self.factor_col not in self.df.columns or label_col not in self.df.columns:
            raise KeyError("指定的列不存在于DataFrame中")
        # 提取因子值和标签值
        factor = self.df[self.factor_col]
        label = self.df[label_col]
        # print(factor.isna().any())
        
        pearson_corr, _ = pearsonr(factor.to_numpy(), label.to_numpy())
        spearman_corr, _ = spearmanr(factor.to_numpy(), label.to_numpy())

        return {
            'IC': round(pearson_corr,4),
            'RankIC': round(spearman_corr,4),
        }
        
    def check_layer_class(self, label_col, top_ratio= [0.01, 0.05, 0.1, 0.2, -0.2, -0.1,-0.05,-0.01]):
        results = {}
        total_rows = self.df.shape[0]
    
        for ratio in top_ratio:
            # 确保ratio在有效的范围内
            if ratio > 1 or ratio < -1:
                raise ValueError(f"top_ratio中的值必须在[-1, 1]之间，当前值为{ratio}")
            # 确定排序方向和分位点位置
            if ratio > 0:
                sorted_df = self.df.sort_values(self.factor_col, ascending=False)
                ratio_ = ratio
            else:
                sorted_df = self.df.sort_values(self.factor_col, ascending=True)
                ratio_ = abs(ratio)
    
            n = int(total_rows * ratio_)
    
            # 避免n超过数据范围
            if n <=0 or n > total_rows:
                raise ValueError(f"根据top_ratio={ratio}，计算得到的行数{n}超出有效范围[1, {total_rows}]")

            selected_label = sorted_df[label_col].head(n)
             # 计算平均收益（可以根据需求修改为其他统计量）
            avg_return = np.mean(selected_label)
            results[ratio] = round(avg_return,4)
    
        return results

    def check_delayed_correlation(self, label_col, lag_range=[-20, -10, -5, -2, 0, 2, 5, 10, 20]):
        # 前瞻性 = max(左移) - max(右移动)
        # lag 为负的时候绝对值更大则更好
        correlation_dict = {}
    
        for delay in lag_range:
            # 平移label列，与factor列对齐，删除包含NaN的行
            shifted_label = self.df[label_col].shift(delay)
            aligned_data = pd.concat([self.df[self.factor_col], shifted_label], axis=1).dropna()
    
            if len(aligned_data) == 0:
                correlation_dict[delay] = None  # 或者跳过该延迟值
                continue
    
            factor_series = aligned_data.iloc[:, 0]
            label_series = aligned_data.iloc[:, 1]
    
            # 计算皮尔逊相关系数
            correlation = factor_series.corr(label_series)
            correlation_dict[delay] = round(correlation,4)
    
        return correlation_dict

    def check_base_info(self, lag=5):
        if isinstance(self.df, pd.DataFrame):
            df = self.df.copy()
        else:
            df = self.df.to_pandas()

        # 检查列是否存在
        if self.factor_col not in df.columns:
            raise KeyError(f"列 '{self.factor_col}' 不存在于DataFrame中")
        series = df[self.factor_col]

        # 计算峰度偏度
        kurt = kurtosis(series)
        skew_val = skew(series)

        # 计算自相关系数（默认一阶）
        autocorr = series.autocorr(lag=5) if len(series) >= 2 else None

        # 计算夏普值
        mean_return = series.mean()
        std_deviation = series.std()
        sharpe_ratio = 0.0  if std_deviation == 0 else mean_return / std_deviation

        return {
            'kurtosis': round(kurt,4),
            'skewness': round(skew_val,4),
            'autocorrelation': round(autocorr,4),
            'sharpe_ratio': round(sharpe_ratio,4)
        }

    def check_all(self, label_col, top_ratio = [0.01, 0.05, 0.1, 0.2, -0.2, -0.1,-0.05,-0.01], 
                  lag_range=[-20, -10, -5, -2, 0, 2, 5, 10, 20]):
        flag = self.check_data()
        if flag == "PASS":
            self.eval_res["corr"]       = self.check_corr(label_col)
            self.eval_res["layerClass"] = self.check_layer_class(label_col, top_ratio)
            self.eval_res["baseInfo"]   = self.check_base_info(lag=5)
            self.eval_res["delayCorr"]  = self.check_delayed_correlation(label_col, lag_range)
            return self.eval_res
        else:
            self.eval_res["corr"]       = np.nan
            self.eval_res["layerClass"] = np.nan
            self.eval_res["baseInfo"]   = np.nan
            self.eval_res["delayCorr"]  = np.nan          
            return flag


# 单因子 单标的 单天评价
def evaluate_factor_singleday(df, factor_col, label_col, symbol,date):
    print(date)
    group_df = df[df['MDDate'] == date]
    evaluator = FactorEvaluatorBase(group_df, factor_col)
    date_full = date.strftime('%Y%m%d')
    check_result = evaluator.check_all(label_col)
    file_path = f"/dfs/group/800657/025036/factor_eval_std/result/{factor_col}/{symbol}/{symbol}_{date_full}.pkl"
    os.makedirs(os.path.dirname(file_path),exist_ok = True)
    with open(file_path,'wb') as f:
        pickle.dump(check_result,f)
    return date,check_result

# 单因子 单标的 多天评价
def evaluate_factor_multiday(df, factor_col, label_col, symbol):
    # df仅包含单因子单标的 多天
    unique_dates = list(set(list(df['MDDate'])))
    daily_dict = {}
    tasks = []
    for date in unique_dates:
    #     remote_func = ray.remote(evaluate_factor_singleday)
    #     tasks.append(remote_func.remote(df, factor_col, label_col, symbol, date))
    # ray_res = ray.get(tasks)
    # for date, check_result in ray_res:
        group_df = df[df['MDDate'] == date]
        evaluator = FactorEvaluatorBase(group_df, factor_col)
        date_full = date.strftime('%Y%m%d')
        check_result = evaluator.check_all(label_col)
        file_path = f"/dfs/group/800657/025036/factor_eval_std/result/{factor_col}/{symbol}/{symbol}_{date_full}.pkl"
        os.makedirs(os.path.dirname(file_path),exist_ok = True)
        with open(file_path,'wb') as f:
            pickle.dump(check_result,f)
        if check_result not in ["All_NONE", "ALL_SAME"]:
            daily_dict[date] = check_result

    if daily_dict != {}:
        # 完成每日计算, 汇总指标
        res = {}
        
        # 计算IC 日维度
        ics = [d['corr']['IC'] for d in daily_dict.values()]
        stdIC = round(np.std(ics),4)
        res["avgIC"] = round(np.mean(ics),4)
        res["IR"]    = round(res["avgIC"] / stdIC,4)

        # 计算RankIC 日维度
        rankics = [d['corr']['RankIC'] for d in daily_dict.values()]
        stdRankIC = round(np.std(rankics),4)
        res["avgRankIC"] = round(np.mean(rankics),4)
        res["rankIR"]    = round(res["avgRankIC"] / stdRankIC  ,4) 

        res["layerClass"] = {k: round(sum(daily_dict[d]['layerClass'][k] for d in daily_dict) / len(daily_dict),4
                              ) for k in [0.01, 0.05, 0.1, 0.2, -0.2, -0.1, -0.05, -0.01]}

        res["baseInfo"] = {k: round(sum(daily_dict[d]['baseInfo'][k] for d in daily_dict) / len(daily_dict),4
                            ) for k in ["kurtosis", "skewness", "autocorrelation", "sharpe_ratio"]}

        res["delayCorr"] = {k: round(sum(daily_dict[d]['delayCorr'][k] for d in daily_dict) / len(daily_dict),4
                            ) for k in [-20, -10, -5, -2, 0, 2, 5, 10, 20]}
        res["calc_date"] = len(daily_dict)
    else:
        print(f"因子数据异常{symbol}-{check_result}")
        res = {}

    return res, symbol, daily_dict 

# 单因子 多标的 多天评价
def evaluate_factor_multisymbol(df, factor_col, label_col, njobs):
    # df = df[["M_HTSCSecurityID", "MDDate", factor_col, label_col]]
    # df_lis = df.groupby("M_HTSCSecurityID")
    df = df[[ "Symbol","MDDate", factor_col, label_col]]
    df_lis = df.groupby("Symbol")
    df_lis = [pair for pair in df_lis]
    # print(f"子df个数：{len(df_lis)}")
    factor_symbol_res = {} 
    factor_symbol_daily_res = {}
    if njobs : # 单线程模式, 遍历标的
        for symbol, tmp_df in df_lis:
            print(symbol, len(tmp_df))
            result, symbol, daily_dict = evaluate_factor_multiday(tmp_df, factor_col, label_col, symbol)

            factor_symbol_res[symbol] = result
            factor_symbol_daily_res[symbol] = daily_dict
    # else: 
    #     tasks = []
    #     remote_func = ray.remote(evaluate_factor_multiday)
    #     for symbol, tmp_df in df_lis:
    #         tasks.append(remote_func.remote(tmp_df, factor_col, label_col, symbol))
    #     ray_res = ray.get(tasks)
    #     for result, symbol, daily_dict in ray_res:
    #         factor_symbol_res[symbol] = result
    #         factor_symbol_daily_res[symbol] = daily_dict
    
    return factor_symbol_res, factor_symbol_daily_res


def evaluate_single_factor(df, factor_col, label_col, njobs):
    try:
        factor_symbol_res, factor_symbol_daily_res = evaluate_factor_multisymbol(df, factor_col, label_col, njobs)
        return factor_symbol_res, factor_symbol_daily_res
    except Exception as e:
        print(e)
        print(f"{factor_col}出现异常， 加入异常因子列表， 不在评价结果中出现")
        return {}, {}



class FactorEvaluatorMulti:
    def __init__(self, label_col, factor_lis, symbol_lis):
        # 这里 df 包含 多票多天
        self.label_col = label_col
        self.res_l3 = {} # 因子-标的-日期层面信息
        self.res_l2 = {} # 因子-标的层面信息
        self.res_l1 = {} # 因子层面信息
        self.error_factor = []
        self.factor_lis = factor_lis
        self.symbol = symbol_lis
        
    def get_eval_info(self, df, save_path=False, njobs=24):
        """ 获取[因子-标的-日期]和[因子-标的]层面信息
        Params:
            df:        因子和标签按timestamp join好的df， 需要有"timestamp", "M_HTSCSecurityID", "MDDate" 三列
            save_path: 默认为False不保存，或传入路径，结果默认为[_res_l3.xlsx, _res_l2.xlsx]
            njobs:     默认24， 为ray并发的数量
        """
        # 从df中选择评价所需列
        # try:
            # df = df[["timestamp", "M_HTSCSecurityID", "MDDate"] + self.factor_lis + [self.label_col]]
            # self.df = df[df["M_HTSCSecurityID"].isin(self.symbol_lis)]
        self.df = df[["Symbol","MDDate"] + self.factor_lis + [self.label_col]]
        
        # self.df = df[df["Symbol"].isin(self.symbol_lis)]
        print(f"df加载完毕，长度: {len(df)}")
        # except Exception as e:
        #     print(f"df异常， 除了要有factor, label 之外应具备timestamp, M_HTSCSecurityID， MDDate三列")
        #     print(e)
        # 遍历因子评价
        cnt = 0
        tasks = []
        remote_func = ray.remote(evaluate_single_factor)
        for factor_col in self.factor_lis: 
            cnt += 1
            print(f"\n第{cnt}/{len(self.factor_lis)}个因子:{factor_col}")
            tasks.append(remote_func.remote(df, factor_col, self.label_col, njobs))
        result = ray.get(tasks)
        for factor_col, (factor_symbol_res, factor_symbol_daily_res) in zip(self.factor_lis, result):
            self.res_l2[factor_col] = factor_symbol_res
            self.res_l3[factor_col] = factor_symbol_daily_res
            # try:
            #     factor_symbol_res, factor_symbol_daily_res = evaluate_factor_multisymbol(df, factor_col, self.label_col, njobs)
            #     self.res_l2[factor_col] = factor_symbol_res
            #     self.res_l3[factor_col] = factor_symbol_daily_res
            # except Exception as e:
            #    self.error_factor.append(factor_col)
            #    print(e)
            #    print(f"{factor_col}出现异常， 加入异常因子列表， 不在评价结果中出现")
        # 保存
        if save_path != False:
            print(f"评价完成，保存数据至{save_path}")
            with open(save_path + "_res_l3.pkl", "wb") as f1:
                pickle.dump(self.res_l3, f1) # 因子-标的-日期层面信息
            with open(save_path + "_res_l2.pkl", "wb") as f2:
                pickle.dump(self.res_l2, f2) # 因子-标的层面信息

    def factor_summary(self, save_path=False, load_path=False):
        # 计算最终因子层面评价
        if load_path == False:
            res_l2 = self.res_l2
            print("--load_path = False， 默认使用类内评价结果")
        else:
            with open(f'{load_path}_res_l2.pkl', 'rb') as file:
                res_l2 = pickle.load(file)
                file.close()
            print(f"--load eval res from {load_path}_res_l2.pkl")

        rows = []
        cnt = 0
        for factor, symbols in res_l2.items():
            cnt += 1
            for symbol, eval_info in symbols.items():
                try:
                    row = {'factor': factor, 'symbol': symbol,
                           'avgIC': eval_info["avgIC"], 
                           'avgRankIC': eval_info["avgRankIC"],
                           'IR': eval_info["IR"],
                           'rankIR': eval_info["rankIR"], 
                           #'layerClass': eval_info["layerClass"], 
                           'abs(top1%)':  abs(eval_info["layerClass"][0.01]),
                           'abs(top5%)':  abs(eval_info["layerClass"][0.05]),
                           'abs(top20%)': abs(eval_info["layerClass"][0.2]),
                           #'delayCorr': eval_info["delayCorr"],
                           'shift_2d':  abs(eval_info["delayCorr"][-2]) - abs(eval_info["delayCorr"][2]),
                           'shift_5d':  abs(eval_info["delayCorr"][-5]) - abs(eval_info["delayCorr"][5]),
                           'shift_10d': abs(eval_info["delayCorr"][-10]) - abs(eval_info["delayCorr"][10]),
                           'kurt': eval_info["baseInfo"]["kurtosis"], 
                           'skew': eval_info["baseInfo"]["skewness"], 
                           'autocorr': eval_info["baseInfo"]["autocorrelation"], 
                           'sharpe': eval_info["baseInfo"]["sharpe_ratio"],   
                          }
                    rows.append(row)
                except Exception as e:
                    print(cnt, factor, symbol, eval_info)
                    print(e)
                
        if len(rows) >= 1:
            # self.res_l2_df = pd.DataFrame(rows)
            # self.res_l1 = self.res_l2_df.groupby("factor").mean()
            # self.res_l1 =  self.res_l1.sort_values(by="abs(top5%)", ascending=False)
            # print("----- 因子评价完成  ----")
            # print(self.res_l1)
            # if save_path != False:
            #     self.res_l1.to_csv(f"{save_path}_res_l1.csv") 
            self.res_l2_df = pd.DataFrame(rows)
            # print(self.res_l2_df)
            
            # self.res_l1 = self.res_l2_df.groupby("factor").drop(columns='symbol').mean()
            self.res_l1 = self.res_l2_df.groupby("factor")
            df_list = []
            for factor, factor_df in self.res_l1:
                # factor_df = factor_df[:,~factor_df.columns.isin(['factor','symbol'])]
                factor_df =  factor_df.sort_values(by="abs(top5%)", ascending=False)
                factor_df =  factor_df.drop(columns = 'symbol')
                factor_df =  factor_df.mean(numeric_only = True)
                factor_df['Factor'] = factor 
                print("-----------------------")
                # print(factor_df)
                df_list.append(factor_df)
                
                # print(factor_df)
            # # self.res_l1 = self.res_l1.loc[:,~self.res_l1.columns.isin(['factor','symbol'])]
            # self.res_l1 =  self.res_l1.sort_values(by="abs(top5%)", ascending=False)
            self.res_l1 = pd.concat(df_list,axis = 1,ignore_index = False).T
            print("----- 因子评价完成  ----")
            # print(self.res_l1)
            if save_path != False:
                self.res_l1.to_csv(f"{save_path}/res_l1.csv") 
                print('评价结果保存成功')
            return self.res_l1
        else:
            print("评价结果为空")

