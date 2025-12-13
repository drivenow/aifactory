import pandas as pd

def read_save(file='data_all.csv'):
    # 读取XLS文件
    df = pd.read_csv(file, encoding='utf-8')
    count=0  # 统计有多少个null
    factor_info = {}    #保存每个结果
    for i,row in df.iterrows():
        #print(f"第{i}行\n")
        factor_name=f"factor{i+1}"
        category = row['category']
        if isinstance(category, str):
            categorys=category.split('/')
            #print(categorys)
        else:
            count+=1
            categorys=[None,None,None]
        factor_info.update({row['factor']:
                            {"factor_describe": row['name'],
                             "factor_alias": "",
                             "classify_level1": "选股",
                             "classify_level2": categorys[1],
                             "classify_level3": categorys[2],
                             "unit": "",
                             "factor_id": row['factor'],
                             "factor_status": "TRAIL",
                             "depend_factor": "",
                             "evaluation_metric": "",
                             "support_scene": "选股",
                             "support_market": "股票",
                             "remark": row['description'],
                             "query_chain": "l3factor",
                             "source": "xquant",
                             "source_id": "",
                             "author": "xquant",
                             }
                            }
                           )

    print(f"此次调用中，有{count}个null")
    return factor_info



factor_info=read_save()
print(factor_info)

# 调用超哥接口保存
# 元数据录入示例
from AIQuant.utils import MetaData
md = MetaData()

library_id = "Factormin" # 资金流因子库
factor_freq = "分钟频"
category = "factor"
library_describe = "用于描述资金流因子"



md.save_metadata(library_id, factor_freq, category, library_describe,factor_info, cover=True)



