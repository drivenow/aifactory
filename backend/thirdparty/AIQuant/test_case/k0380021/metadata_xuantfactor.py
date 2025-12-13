from collections import defaultdict
import pandas as pd
import numpy as np
from AIQuant.utils import MetaData

md = MetaData()

lib_info = defaultdict(dict)

df = pd.read_csv("./xquantfactor_info_1.csv")
df["category"] = df["category"].astype(str)
df = df.replace(np.nan, None)
# print(df)

# 获取已分类的库名及含义
df_lib = df[["library_id", "library_describe", "factor_freq"]]
df_lib = df_lib.drop_duplicates()
lib_msg = df_lib.to_dict(orient='records')
# print(lib_msg)
# lib_msg = [{'library_id': 'factor_d_marketindex', 'library_describe': 'A股行情指标', 'factor_freq': '日频'},
#            {'library_id': 'factor_d_moneyflow', 'library_describe': 'A股行情衍生指标', 'factor_freq': '日频'},
#            {'library_id': 'bond_d_marketindex', 'library_describe': '可转债行情指标', 'factor_freq': '日频'},
#            {'library_id': 'fund_d_marketindex', 'library_describe': '基金行情指标', 'factor_freq': '日频'},
#            {'library_id': 'index_d_marketindex', 'library_describe': '指数行情指标', 'factor_freq': '日频'},
#            {'library_id': 'factor_d_valuationmetricsindex', 'library_describe': 'A股估值指标', 'factor_freq': '日频'},
#            {'library_id': 'bond_d_valuation', 'library_describe': '可转债估值指标', 'factor_freq': '日频'},
#            {'library_id': 'factor_d_issuingdateindex', 'library_describe': '财务-披露日期表', 'factor_freq': '季频'},
#            {'library_id': 'factor_d_financialreportindex', 'library_describe': 'A股财务报表', 'factor_freq': '季频'},
#            {'library_id': 'factor_d_profitnotice', 'library_describe': 'A股财务业绩预告快报', 'factor_freq': '季频'}]

for lib_msg_p in lib_msg:
    library_id = lib_msg_p["library_id"]
    df_p = df[df["library_id"] == library_id]
    for _, row in df_p.iterrows():
        factor = row["factor"]
        factor_describe = row["factor_describe"]
        unit = row["unit"]
        support_scene = row["support_scene"]
        support_market = row["support_market"]
        remark = row["explanation"]
        category = row["category"]
        category_list = category.split("/")
        try:
            classify_level1 = category_list[0]
        except:
            classify_level1 = None
        try:
            classify_level2 = category_list[1]
        except:
            classify_level2 = None
        try:
            classify_level3 = category_list[2]
        except:
            classify_level3 = None
        lib_info[library_id][factor] = {
            "factor_id": factor,
            "factor_describe": factor_describe,
            'factor_status': 'TRAIL',
            "classify_level1": classify_level1,
            "classify_level2": classify_level2,
            "classify_level3": classify_level3,
            "unit": unit,
            "support_scene": support_scene,
            "support_market": support_market,
            "remark": remark,
            "query_chain": "xquant",
            "source": "xquant"}

# print(lib_info)

for lib_msg_p in lib_msg:
    library_id = lib_msg_p["library_id"]
    library_describe = lib_msg_p["library_describe"]
    factor_freq = lib_msg_p["factor_freq"]
    category = "indicator"
    factor_info = lib_info[library_id]
    md.save_metadata(library_id, factor_freq, category, library_describe, factor_info)

