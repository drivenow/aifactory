# 1.1 数据存取类-DataManager
### 构建类实例的参数如下：
```python
API_TYPE: str = ''  # 查询上游源数据必传， API类型(数据类型wind-万得数据/zx-资讯泛化接口数据/PRODUCTINFO-私募基金数据/indicator-指标因子数据)
API_KWARGS: dict = {}  # 查询上游源数据必传， API传入的运行参数，传参可参考缓存数据的配置(通过library_config函数)
LIB_ID: str = ''  # 查询缓存数据必传，唯一数据名(区分大小写)，可以是表名或者因子库名 WIND_ASHAREEODPRICES、INDICATOR_PLATFORM_1
API_START: str = '' # 查询缓存数据必传，开始日期
API_END: str = ''   # 查询缓存数据必传，结束日期
LIB_TYPE: str = ""  # 查询缓存数据必传，区分是表还是因子库，table表/factor因子
LIB_ID_FEILD: list = []  # 查询缓存数据可选，LIB_ID下对应的列名（对表可以是列名，对因子库可以是因子名），默认为空取所有因子或列
API_INDEX_COL: dict = {}  # 缓存数据必传，业务日期、标的列映射
TABLE_BASE_PATH: str = '/dfs/group/800657/library_alpha/quant_data/table/' # 表数据存储根目录，默认不传
FACTOR_BASE_PATH: str = '/dfs/group/800657/library_alpha/quant_data/factor/ai_daily_factor/'  # 因子数据存储根目录，默认不传
EXTRA_KWARGS: dict = {}  # 个性化的其他字段，如init_date, start_date
LINK_IDS: list = ['013150', '022917', '011048', '016349'] # 缓存数据故障玲客通知账号，默认不传
```

# 1.2 获取缓存数据范例
```python
from AIQuant.datamanager import DataManager
# 查询indicator因子缓存数据，LIB_ID区分大小写
conf = DataManager(LIB_ID="INDICATOR_PLATFORM_1", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)

conf = DataManager(LIB_ID="FactorILLIQUIDITY", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)

conf = DataManager(LIB_ID="Factor_xunfen1", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)

```

# 1.3 获取上游源数据范例
```python
from AIQuant.datamanager import DataManager
# API_KWARGS为透传参数，传参规范与指标平台保持一致
conf = DataManager(API_TYPE="indicator",
                   API_KWARGS={'action': '27720',
                                'props': '10035|10049|10055|10041|10042|10043|10044|11|10036|10018|10086|40105|40031|40002|10014|10015|10008|70098|70391|40624|10016|10017|10020|79999',
                                'marketType': 'HSJASH',
                                'date': '20251114'
                               },
                   )
df = conf.get_data(conf)
print(df)
```

# 1.4 根据library_id获取缓存数据的配置信息
```python
from AIQuant import get_library_config

conf = get_library_config(library_id='INDICATOR_PLATFORM_1')
print(conf)

conf = get_library_config(library_id='WIND_ASHAREEODPRICES')
print(conf)

```
