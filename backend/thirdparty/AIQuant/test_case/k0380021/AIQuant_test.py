
from AIQuant.datamanager import DataManager

# 场景一：查询缓存数据
conf = DataManager(LIB_ID="ASHAREEODPRICES", API_START="19910101", API_END="19911205", LIB_TYPE="table")
dm = DataManager()
df = dm.get_data(conf)
print(df)


# 场景一：查询ZX缓存数据
conf = DataManager(LIB_ID="ZX_STKDEPTTRADINFO", API_START="20251101", API_END="20251114", LIB_TYPE="table")
df = conf.get_data(conf)
print(df)

# 场景一：查询productinfo缓存数据
conf = DataManager(LIB_ID="ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY", API_START="20251118",
                   API_END="20251118", LIB_TYPE="table")
df = conf.get_data(conf)
print(df)

# 查询indicator因子缓存数据
conf = DataManager(LIB_ID="INDICATOR_PLATFORM_1", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)

# 查询indicator_min因子缓存数据
conf = DataManager(LIB_ID="INDICATOR_PLATFORM_MINUTE_1", API_START="20251123", API_END="20251124", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)


conf = DataManager(LIB_ID="FactorILLIQUIDITY", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)

conf = DataManager(LIB_ID="Factor_xunfen1", API_START="20251111", API_END="20251114", LIB_TYPE="factor")
df = conf.get_data(conf)
print(df)



# 场景二：查询wind源表
conf = DataManager(API_TYPE='wind',
                   API_KWARGS={"library_name": "WIND_ASHAREEODPRICES", "OPDATE":[f">=20020724", f"<=20020725"]})
df = conf.get_data(conf)
print(df)


# 场景二：查询ZX源表
conf = DataManager(API_TYPE='zx',
                   API_KWARGS={"resource": "ZX_STKDEPTTRADINFO", "paramMaps": {"LISTDATE": "20251113"}, "rownum":10000})
df = conf.get_data(conf)
print(df)

# 场景二：查询productinfo源表
conf = DataManager(API_TYPE='productinfo',
                   API_KWARGS={"library_name": "PRODUCTINFO_ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY", "ARCHIVEDATE": "20250619"})
df = conf.get_data(conf)
print(df)

# 场景二：查询hive源表
conf = DataManager(API_TYPE='hive',
                   API_KWARGS={"library_name": "SRC_CENTER_ADMIN.stk_blocktrade", "tradingday": [">=2025-12-02 00:00:00","<=2025-12-03 23:59:59"]})
df = conf.get_data(conf)
print(df)

# 查询indicator源数据
conf = DataManager(API_TYPE="indicator",
                   API_KWARGS={'action': '27720',
                                'props': '10035|10049|10055|10041|10042|10043|10044|11|10036|10018|10086|40105|40031|40002|10014|10015|10008|70098|70391|40624|10016|10017|10020|79999',
                                'marketType': 'HSJASH',
                                'date': '20251114'
                               },
                   )
df = conf.get_data(conf)
print(df)

# 查询indicator源数据
conf = DataManager(API_TYPE="indicator_min",
                   API_KWARGS={'action': '27720',
                                'props': '10023',
                                'marketType': 'HSJASH',
                                'date': '20251114',
                               'codes': '600519|1_0',
                               },
                   )
df = conf.get_data(conf)
print(df)

# ---------------------------------------------------------------
# 缓存数据
# 1. 指标因子数据
from AIQuant.indicator.index_platform_sync import SyncIndicatorData
sid = SyncIndicatorData()
# 补历史
sid.total_sync(init_date="20251010", end_date="20251015")
# 每日更新数据
sid.run_daily()

# # 2. TODO wind数据同步
from AIQuant.xquant.wind_data_bydate_sync import SyncWindDataByDate
swd = SyncWindDataByDate(table_name="ASHAREEODPRICES")
# 补所有历史数据
swd.total_sync(init_date="20020101", end_date="20031231", cover=True)
# # 每日更新数据
# swd.run_daily()

# 3. TODO zx数据同步
from AIQuant.xquant.zx_data_sync import SyncZXDataByDate
swd = SyncZXDataByDate()
swd.total_sync(init_date='20251017', end_date='20251114', cover=True)
# # 每日更新数据
# swd.run_daily()

# 4. TODO  productinfo 数据同步
from AIQuant.xquant.productinfo_data_sync import SyncProductInfoDataByDate
swd = SyncProductInfoDataByDate()
# # 补所有历史数据
swd.total_sync(init_date="20250619", end_date="20250619", cover=True)
# 每日更新数据
# swd.run_daily()

# 5. TODO  HIve 数据同步
from AIQuant.xquant.hive_data_sync import SyncHiveDataByDate
swd = SyncHiveDataByDate(table_name=['STK_ASHAREFREEFLOATCALENDAR',
                                         'STK_SEOWIND',
                                         'STK_ASHARESTOCKREPO'])
# # 补所有历史数据
swd.total_sync_all(init_date="20241201", end_date="20251203", cover=True)
# 每日更新数据
swd.run_daily()

from AIQuant import get_library_config

conf = get_library_config(library_id='INDICATOR_PLATFORM_1')
print(conf)

conf = get_library_config(library_id='ASHAREEODPRICES')
print(conf)


