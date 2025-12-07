# 1.结构

```
factor_eval/
└── result/
│   ├── Factor1/
│   │   ├── Symbol1/
│   │   │   ├── Day1
│   │   │   ├── Day2
│   │   │   └── ...
│   │   ├── Symbol2/
│   │   │   ├── Day1
│   │   │   ├── Day2
│   │   │   └── ...
│   │   └── ...
│   ├── Factor2/
│   │   ├── Symbol1/
│   │   │   ├── Day1
│   │   │   ├── Day2
│   │   │   └── ...
│   │   └── ...
│   ├── Corr.csv      # 存放相关系数矩阵
│   └── Result.csv    # 存放最终评估结果矩阵
├── src/
│     ├──factor_eval.py
├── factoreval.py
├── FactorEvaluate.py
├── dates.json        #评估日期
├── eval_list.json    #评估因子列表
│
│ 
```

# 2.基本评价函数

## 2.1拷贝因子和非因子代码

```python
def copy_factor_code(src_folder, tar_folder):
   for item in os.listdir(src_folder):
       src_path = os.path.join(src_folder,item)
       tar_path = os.path.join(tar_folder,item)
       if os.path.isfile(src_path):
          if not os.path.exists(tar_folder):
             shutil.copy2(src_path, tar_path)
```

## 2.2对一个因子的全部数据评测

```python
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
                daily_factor_df = fl.load_factor_data('/research/python/1S/factor',symbols = symbol,start_date = date,end_date = date)
            daily_label_df = fl.load_factor_data('/research/cpp/1S/label',symbols = symbol,start_date = date,end_date = date)
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
```

## 2.3计算全体因子单日的相关系数

```python
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
```

## 2.4在相关系数表中找到相关系数大的因子

```python
def format_high_corr(corr_series: pd.Series, target: str, threshold = 0.85) -> str:
    high_corr = corr_series[(corr_series >= threshold) & (corr_series.index != target)]
    # 按相关性降序排列
    high_corr = high_corr.sort_values(ascending=False)
    parts = [f"{idx}:{val:.2f}" for idx, val in high_corr.items()]
    return ", ".join(parts)
```

# 3.评价过程

## 3.1有因子代码

在子目录有Factors和NonFactors的目录下，运行factoreval.py

其中base_path目录下应该有L3FactorFrame

需要输入的参数有

**factor_list** (评价的因子及其参数)

**base_path**（基本目录）

**num_cpus**（并发数）<span style="color:#e74c3c">⚠️ 在计算相关系数时最好njobs<=10，保证每个cpu有足够内存</span>

**corr_path**（保存相关系数的地址）

**result_path**（保存最后结果的地址）

```python
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
t1 = time.time()
base_path = "/dfs/group/800657/025036/scratch/"
FWC = Factor_with_code(factor_list,base_path,num_cpus = 20)
FWC.factor_data_generate()
FWC.calculate_correlation(corr_path)
FWC.factor_eval_code(corr_path,result_path)
t2 = time.time()
print(t2-t1)
```

首先运行FWC.factor_data_generate()，生成因子数据，数据会保存在/dfs/group/800657/library/l3_data/l3_factor/research/python/1S/factor

然后运行FWC.calculate_correlation(corr_path)，生成因子之间相关系数矩阵

最后运行FWC.factor_eval_code(corr_path,result_path)生成因子每天的评价指标和平均指标

## 3.2有因子数据

直接运行factorevaldata.py

需要输入的参数有

**factor_list** （list）

**data_path**（因子数据地址）

因子数据是满足一下要求的parquet文件

| DateTime | Symbol | Factor1 | Factor2 | Factor3 | Factor4 | Factor5 |
| -------- | ------ | ------- | ------- | ------- | ------- | ------- |

必须含有DateTime个Symbol这两列，一列表示时间，一列表示标的名

**num_cpus**（并发数）<span style="color:#e74c3c">⚠️ 在计算相关系数时最好njobs<=10，保证每个cpu有足够内存</span>

**corr_path**（保存相关系数的地址）

**result_path**（保存最后结果的地址）

```python
factor_list = []
t1 = time.time()
base_path = "/dfs/group/800657/025036/scratch/"
FWC = Factor_with_data(data_path,factor_list, num_cpus = 20)
FWC.factor_data_generate()
FWC.calculate_correlation(corr_path)
FWC.factor_eval_code(corr_path,result_path)
t2 = time.time()
print(t2-t1)
```

## 4. 在 Agent/Graph 中调用（最小封装）
- 新增入口 `backend/domain/factor_eval/runner.py` 提供 `run_factor_eval(state, include_l3=False)`。
- 默认：`factor_name` 作为单因子，`label_col="Label_VC_3_2"`，`symbols/dates` 取本目录 `eval_list.json`/`dates.json`，`data_path` 缺省使用 FactorLib 读取。
- 可选：在 `state` 中传入 `factor_list`、`label_col`、`symbols`、`dates`、`data_path` 或直接传入 `factor_eval_df`（pandas DataFrame，包含 `Symbol/MDDate/{factors}/{label}` 列）。
- 结果写回 `state.eval_metrics = {"summary": [...], "l2": {...}}`，默认不写入体积大的 `l3`。

运行方式同有因子代码时的步骤
