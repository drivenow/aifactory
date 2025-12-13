import datetime as dt
from .datamanager import DataManager
from .utils import check_cur_parse_date
NOWDATE = check_cur_parse_date()
NEXTDATE = dt.datetime.strptime(NOWDATE, "%Y%m%d") + dt.timedelta(days=1)
NEXTDATE = NEXTDATE.strftime("%Y%m%d")
NOWDATE_TIME = NOWDATE[:4]+"-"+NOWDATE[4:6]+"-"+NOWDATE[6:8]+" 00:00:00"
NEXTDATE_TIME = NEXTDATE[:4]+"-"+NEXTDATE[4:6]+"-"+NEXTDATE[6:8]+" 00:00:00"


config_list = [
    # 中国A股日行情
    DataManager(API_TYPE='wind', LIB_ID='ASHAREEODPRICES',
                API_KWARGS={"library_name": "WIND_ASHAREEODPRICES", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股指数日行情
    DataManager(API_TYPE='wind', LIB_ID='AINDEXEODPRICES',
                API_KWARGS={"library_name": "WIND_AINDEXEODPRICES", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股指数财务衍生指标
    DataManager(API_TYPE='wind', LIB_ID='AINDEXFINANCIALDERIVATIVE',
                API_KWARGS={"library_name": "WIND_AINDEXFINANCIALDERIVATIVE",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股中信行业指数日行情
    DataManager(API_TYPE='wind', LIB_ID='AINDEXINDUSTRIESEODCITICS',
                API_KWARGS={"library_name": "WIND_AINDEXINDUSTRIESEODCITICS",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股指数成份股
    DataManager(API_TYPE='wind', LIB_ID='AINDEXMEMBERS',
                API_KWARGS={"library_name": "WIND_AINDEXMEMBERS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_CON_INDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股指数估值数据
    DataManager(API_TYPE='wind', LIB_ID='AINDEXVALUATION',
                API_KWARGS={"library_name": "WIND_AINDEXVALUATION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股公布重要财务指标
    DataManager(API_TYPE='wind', LIB_ID='ASHAREANNFINANCIALINDICATOR',
                API_KWARGS={"library_name": "WIND_ASHAREANNFINANCIALINDICATOR",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股发行中介机构
    DataManager(API_TYPE='wind', LIB_ID='ASHAREAGENCY',
                API_KWARGS={"library_name": "WIND_ASHAREAGENCY", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股资产负债表
    DataManager(API_TYPE='wind', LIB_ID='ASHAREBALANCESHEET',
                API_KWARGS={"library_name": "WIND_ASHAREBALANCESHEET", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股大宗交易数据
    DataManager(API_TYPE='wind', LIB_ID='ASHAREBLOCKTRADE',
                API_KWARGS={"library_name": "WIND_ASHAREBLOCKTRADE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股公司资本运作
    DataManager(API_TYPE='wind', LIB_ID='ASHARECOCAPITALOPERATION',
                API_KWARGS={"library_name": "WIND_ASHARECOCAPITALOPERATION",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DATE': 'datetime', 'S_INFO_COMPCODE': 'symbol'}),
    # 中国A股股本
    DataManager(API_TYPE='wind', LIB_ID='ASHARECAPITALIZATION',
                API_KWARGS={"library_name": "WIND_ASHARECAPITALIZATION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股现金流量表
    DataManager(API_TYPE='wind', LIB_ID='ASHARECASHFLOW',
                API_KWARGS={"library_name": "WIND_ASHARECASHFLOW", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股限售股解禁公司明细
    DataManager(API_TYPE='wind', LIB_ID='ASHARECOMPRESTRICTED',
                API_KWARGS={"library_name": "WIND_ASHARECOMPRESTRICTED", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # # TODO 全量 中国A股Wind概念板块
    # DataManager(API_TYPE='wind', LIB_ID='ASHARECONSEPTION',
    #             API_KWARGS={"library_name": "WIND_ASHARECONSEPTION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
    #             API_INDEX_COL={'ENTRY_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # # TODO 全量 中国A股基本资料
    # DataManager(API_TYPE='wind', LIB_ID='ASHAREDESCRIPTION',
    #             API_KWARGS={"library_name": "WIND_ASHAREDESCRIPTION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
    #             API_INDEX_COL={'S_INFO_LISTDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股分红
    DataManager(API_TYPE='wind', LIB_ID='ASHAREDIVIDEND',
                API_KWARGS={"library_name": "WIND_ASHAREDIVIDEND", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股日行情估值指标
    DataManager(API_TYPE='wind', LIB_ID='ASHAREEODDERIVATIVEINDICATOR',
                API_KWARGS={"library_name": "WIND_ASHAREEODDERIVATIVEINDICATOR",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股权分置方案
    DataManager(API_TYPE='wind', LIB_ID='ASHAREEQUITYDIVISION',
                API_KWARGS={"library_name": "WIND_ASHAREEQUITYDIVISION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'WINDCODE': 'symbol'}),
    # 中国A股股权质押信息
    DataManager(API_TYPE='wind', LIB_ID='ASHAREEQUITYPLEDGEINFO',
                API_KWARGS={"library_name": "WIND_ASHAREEQUITYPLEDGEINFO", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股公司员工持股计划基本资料
    DataManager(API_TYPE='wind', LIB_ID='ASHAREESOPDESCRIPTION',
                API_KWARGS={"library_name": "WIND_ASHAREESOPDESCRIPTION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DATE_NEW': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股公司员工持股计划股票买卖情况
    DataManager(API_TYPE='wind', LIB_ID='ASHAREESOPTRADINGINFO',
                API_KWARGS={"library_name": "WIND_ASHAREESOPTRADINGINFO", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股财务费用明细
    DataManager(API_TYPE='wind', LIB_ID='ASHAREFINANCIALEXPENSE',
                API_KWARGS={"library_name": "WIND_ASHAREFINANCIALEXPENSE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股财务指标
    DataManager(API_TYPE='wind', LIB_ID='ASHAREFINANCIALINDICATOR',
                API_KWARGS={"library_name": "WIND_ASHAREFINANCIALINDICATOR",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股自由流通股本
    DataManager(API_TYPE='wind', LIB_ID='ASHAREFREEFLOAT',
                API_KWARGS={"library_name": "WIND_ASHAREFREEFLOAT", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股限售股流通日历
    DataManager(API_TYPE='wind', LIB_ID='ASHAREFREEFLOATCALENDAR',
                API_KWARGS={"library_name": "WIND_ASHAREFREEFLOATCALENDAR",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股东户数
    DataManager(API_TYPE='wind', LIB_ID='ASHAREHOLDERNUMBER',
                API_KWARGS={"library_name": "WIND_ASHAREHOLDERNUMBER", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股首次公开发行数据
    DataManager(API_TYPE='wind', LIB_ID='ASHAREIPO',
                API_KWARGS={"library_name": "WIND_ASHAREIPO", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股权激励基本资料
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINCDESCRIPTION',
                API_KWARGS={"library_name": "WIND_ASHAREINCDESCRIPTION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股权激励期权行权数量与价格
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINCEXECQTYPRI',
                API_KWARGS={"library_name": "WIND_ASHAREINCEXECQTYPRI", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_INC_EXECDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股权激励数量明细
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINCQUANTITYDETAILS',
                API_KWARGS={"library_name": "WIND_ASHAREINCQUANTITYDETAILS",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股权激励数量与价格
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINCQUANTITYPRICE',
                API_KWARGS={"library_name": "WIND_ASHAREINCQUANTITYPRICE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股利润表
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINCOME',
                API_KWARGS={"library_name": "WIND_ASHAREINCOME", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # TODO 全量 中国A股中信行业分类
    # DataManager(API_TYPE='wind', LIB_ID='ASHAREINDUSTRIESCLASSCITICS',
    #             API_KWARGS={"library_name": "WIND_ASHAREINDUSTRIESCLASSCITICS",
    #                         "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
    #             API_INDEX_COL={'ENTRY_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股前十大股东
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINSIDEHOLDER',
                API_KWARGS={"library_name": "WIND_ASHAREINSIDEHOLDER", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股内部人交易
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINSIDERTRADE',
                API_KWARGS={"library_name": "WIND_ASHAREINSIDERTRADE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股发行审核一览
    DataManager(API_TYPE='wind', LIB_ID='ASHAREISSUECOMMAUDIT',
                API_KWARGS={"library_name": "WIND_ASHAREISSUECOMMAUDIT", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_IC_DATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股定期报告披露日期
    DataManager(API_TYPE='wind', LIB_ID='ASHAREISSUINGDATEPREDICT',
                API_KWARGS={"library_name": "WIND_ASHAREISSUINGDATEPREDICT",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股Level2指标
    DataManager(API_TYPE='wind', LIB_ID='ASHAREL2INDICATORS',
                API_KWARGS={"library_name": "WIND_ASHAREL2INDICATORS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股发行主承销商
    DataManager(API_TYPE='wind', LIB_ID='ASHARELEADUNDERWRITER',
                API_KWARGS={"library_name": "WIND_ASHARELEADUNDERWRITER", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_LU_ANNISSUEDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股重大事件汇总
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMAJOREVENT',
                API_KWARGS={"library_name": "WIND_ASHAREMAJOREVENT", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_EVENT_ANNCEDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股东增持计划
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMAJORHOLDERPLANHOLD',
                API_KWARGS={"library_name": "WIND_ASHAREMAJORHOLDERPLANHOLD",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_PH_STARTDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股公司管理层持股及报酬
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMANAGEMENTHOLDREWARD',
                API_KWARGS={"library_name": "WIND_ASHAREMANAGEMENTHOLDREWARD",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股融资融券标的及担保物
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMARGINSUBJECT',
                API_KWARGS={"library_name": "WIND_ASHAREMARGINSUBJECT", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_MARGIN_EFFECTDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股融资融券交易明细
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMARGINTRADE',
                API_KWARGS={"library_name": "WIND_ASHAREMARGINTRADE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股融资融券交易汇总
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMARGINTRADESUM',
                API_KWARGS={"library_name": "WIND_ASHAREMARGINTRADESUM", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime'}),
    # 中国A股重要股东增减持
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMJRHOLDERTRADE',
                API_KWARGS={"library_name": "WIND_ASHAREMJRHOLDERTRADE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股资金流向数据
    DataManager(API_TYPE='wind', LIB_ID='ASHAREMONEYFLOW',
                API_KWARGS={"library_name": "WIND_ASHAREMONEYFLOW", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股网下配售机构获配明细
    DataManager(API_TYPE='wind', LIB_ID='ASHAREPLACEMENTDETAILS',
                API_KWARGS={"library_name": "WIND_ASHAREPLACEMENTDETAILS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股网下配售机构获配统计
    DataManager(API_TYPE='wind', LIB_ID='ASHAREPLACEMENTINFO',
                API_KWARGS={"library_name": "WIND_ASHAREPLACEMENTINFO", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股票质押比例
    DataManager(API_TYPE='wind', LIB_ID='ASHAREPLEDGEPROPORTION',
                API_KWARGS={"library_name": "WIND_ASHAREPLEDGEPROPORTION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_ENDDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股业绩快报
    DataManager(API_TYPE='wind', LIB_ID='ASHAREPROFITEXPRESS',
                API_KWARGS={"library_name": "WIND_ASHAREPROFITEXPRESS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股业绩预告
    DataManager(API_TYPE='wind', LIB_ID='ASHAREPROFITNOTICE',
                API_KWARGS={"library_name": "WIND_ASHAREPROFITNOTICE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_PROFITNOTICE_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股配股
    DataManager(API_TYPE='wind', LIB_ID='ASHARERIGHTISSUE',
                API_KWARGS={"library_name": "WIND_ASHARERIGHTISSUE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股特别处理
    DataManager(API_TYPE='wind', LIB_ID='ASHAREST',
                API_KWARGS={"library_name": "WIND_ASHAREST", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股员工人数变更
    DataManager(API_TYPE='wind', LIB_ID='ASHARESTAFF',
                API_KWARGS={"library_name": "WIND_ASHARESTAFF", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股交易异动
    DataManager(API_TYPE='wind', LIB_ID='ASHARESTRANGETRADEDETAIL',
                API_KWARGS={"library_name": "WIND_ASHARESTRANGETRADEDETAIL",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'START_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股股票风格系数
    DataManager(API_TYPE='wind', LIB_ID='ASHARESTYLECOEFFICIENT',
                API_KWARGS={"library_name": "WIND_ASHARESTYLECOEFFICIENT", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_CHANGE_DATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股TTM指标历史数据
    DataManager(API_TYPE='wind', LIB_ID='ASHARETTMHIS',
                API_KWARGS={"library_name": "WIND_ASHARETTMHIS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股停复牌信息
    DataManager(API_TYPE='wind', LIB_ID='ASHARETRADINGSUSPENSION',
                API_KWARGS={"library_name": "WIND_ASHARETRADINGSUSPENSION",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'S_DQ_SUSPENDDATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股应收账款账龄结构
    DataManager(API_TYPE='wind', LIB_ID='ASHAREAGINGSTRUCTURE',
                API_KWARGS={"library_name": "WIND_ASHAREAGINGSTRUCTURE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_COMPCODE': 'symbol'}),
    # 中国A股其它应收款帐龄结构
    DataManager(API_TYPE='wind', LIB_ID='ASHAREOTHERACCOUNTSRECEIVABLE',
                API_KWARGS={"library_name": "WIND_ASHAREOTHERACCOUNTSRECEIVABLE",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_COMPCODE': 'symbol'}),
    # 中国A股回购
    DataManager(API_TYPE='wind', LIB_ID='ASHARESTOCKREPO',
                API_KWARGS={"library_name": "WIND_ASHARESTOCKREPO", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国债券债券行情(沪深交易所)
    DataManager(API_TYPE='wind', LIB_ID='CBONDEODPRICES',
                API_KWARGS={"library_name": "WIND_CBONDEODPRICES", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国国债期货交易日行情
    DataManager(API_TYPE='wind', LIB_ID='CBONDFUTURESEODPRICES',
                API_KWARGS={"library_name": "WIND_CBONDFUTURESEODPRICES", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国国债期货成交及持仓
    DataManager(API_TYPE='wind', LIB_ID='CBONDFUTURESPOSITIONS',
                API_KWARGS={"library_name": "WIND_CBONDFUTURESPOSITIONS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国债券发行主体信用评级
    DataManager(API_TYPE='wind', LIB_ID='CBONDISSUERRATING',
                API_KWARGS={"library_name": "WIND_CBONDISSUERRATING", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_COMPCODE': 'symbol'}),
    # 中国债券信用评级
    DataManager(API_TYPE='wind', LIB_ID='CBONDRATING',
                API_KWARGS={"library_name": "WIND_CBONDRATING", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国可转债转股
    DataManager(API_TYPE='wind', LIB_ID='CCBONDCONVERSION',
                API_KWARGS={"library_name": "WIND_CCBONDCONVERSION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国可转债衍生指标
    DataManager(API_TYPE='wind', LIB_ID='CCBONDVALUATION',
                API_KWARGS={"library_name": "WIND_CCBONDVALUATION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国商品期货日行情
    DataManager(API_TYPE='wind', LIB_ID='CCOMMODITYFUTURESEODPRICES',
                API_KWARGS={"library_name": "WIND_CCOMMODITYFUTURESEODPRICES",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国商品期货成交及持仓
    DataManager(API_TYPE='wind', LIB_ID='CCOMMODITYFUTURESPOSITIONS',
                API_KWARGS={"library_name": "WIND_CCOMMODITYFUTURESPOSITIONS",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国国债基准收益率
    DataManager(API_TYPE='wind', LIB_ID='CGBBENCHMARK',
                API_KWARGS={"library_name": "WIND_CGBBENCHMARK", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国股指期货日行情
    DataManager(API_TYPE='wind', LIB_ID='CINDEXFUTURESEODPRICES',
                API_KWARGS={"library_name": "WIND_CINDEXFUTURESEODPRICES", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国股指期货成交及持仓
    DataManager(API_TYPE='wind', LIB_ID='CINDEXFUTURESPOSITIONS',
                API_KWARGS={"library_name": "WIND_CINDEXFUTURESPOSITIONS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国共同基金投资组合——其他证券
    DataManager(API_TYPE='wind', LIB_ID='CMFOTHERPORTFOLIO',
                API_KWARGS={"library_name": "WIND_CMFOTHERPORTFOLIO", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国国债期货最便宜可交割券
    DataManager(API_TYPE='wind', LIB_ID='CBONDFCTD',
                API_KWARGS={"library_name": "WIND_CBONDFCTD", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国国债期货标的券
    DataManager(API_TYPE='wind', LIB_ID='CBONDFSUBJECTCVF',
                API_KWARGS={"library_name": "WIND_CBONDFSUBJECTCVF", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国共同基金投资组合——持股明细
    DataManager(API_TYPE='wind', LIB_ID='CHINAMUTUALFUNDSTOCKPORTFOLIO',
                API_KWARGS={"library_name": "WIND_CHINAMUTUALFUNDSTOCKPORTFOLIO",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国期权日交易统计
    DataManager(API_TYPE='wind', LIB_ID='CHINAOPTIONDAILYSTATISTICS',
                API_KWARGS={"library_name": "WIND_CHINAOPTIONDAILYSTATISTICS",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国期权日行情
    DataManager(API_TYPE='wind', LIB_ID='CHINAOPTIONEODPRICES',
                API_KWARGS={"library_name": "WIND_CHINAOPTIONEODPRICES", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国期权指数日行情
    DataManager(API_TYPE='wind', LIB_ID='CHINAOPTIONINDEXEODPRICES',
                API_KWARGS={"library_name": "WIND_CHINAOPTIONINDEXEODPRICES",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国期权会员交易统计
    DataManager(API_TYPE='wind', LIB_ID='CHINAOPTIONMEMBERSTATISTICS',
                API_KWARGS={"library_name": "WIND_CHINAOPTIONMEMBERSTATISTICS",
                            "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_CODE': 'symbol'}),
    # 中国期权衍生指标
    DataManager(API_TYPE='wind', LIB_ID='CHINAOPTIONVALUATION',
                API_KWARGS={"library_name": "WIND_CHINAOPTIONVALUATION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # # TODO 全量 发审委员基本资料
    # DataManager(API_TYPE='wind', LIB_ID='IECMEMBERLIST',
    #             API_KWARGS={"library_name": "WIND_IECMEMBERLIST", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
    #             API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # IPO审核申报企业情况
    DataManager(API_TYPE='wind', LIB_ID='IPOCOMPRFA',
                API_KWARGS={"library_name": "WIND_IPOCOMPRFA", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ST_DATE': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # IPO初步询价明细
    DataManager(API_TYPE='wind', LIB_ID='IPOINQUIRYDETAILS',
                API_KWARGS={"library_name": "WIND_IPOINQUIRYDETAILS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'ANN_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 陆港通通道持股数量统计(中央结算系统)
    DataManager(API_TYPE='wind', LIB_ID='SHSCCHANNELHOLDINGS',
                API_KWARGS={"library_name": "WIND_SHSCCHANNELHOLDINGS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 陆港通日交易统计
    DataManager(API_TYPE='wind', LIB_ID='SHSCDAILYSTATISTICS',
                API_KWARGS={"library_name": "WIND_SHSCDAILYSTATISTICS", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime'}),
    # 中国A股指数行情衍生指标
    DataManager(API_TYPE='wind', LIB_ID='SINDEXPERFORMANCE',
                API_KWARGS={"library_name": "WIND_SINDEXPERFORMANCE", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国国债期货可交割券衍生指标
    DataManager(API_TYPE='wind', LIB_ID='CBONDFVALUATION',
                API_KWARGS={"library_name": "WIND_CBONDFVALUATION", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'TRADE_DT': 'datetime', 'S_INFO_WINDCODE': 'symbol'}),
    # 中国A股财务附注--所得税
    DataManager(API_TYPE='wind', LIB_ID='ASHAREINCOMETAX',
                API_KWARGS={"library_name": "WIND_ASHAREINCOMETAX", "OPDATE": [f">={NOWDATE}", f"<={NEXTDATE}"]},
                API_INDEX_COL={'REPORT_PERIOD': 'datetime', 'S_INFO_COMPCODE': 'symbol'}),
    # 个股上榜交易明细
    DataManager(API_TYPE='zx', LIB_ID='ZX_STKDEPTTRADINFO',
                API_KWARGS={"resource": "ZX_STKDEPTTRADINFO", "paramMaps": {"LISTDATE": f"{NOWDATE}"}, "rownum": 10000},
                API_INDEX_COL={'LISTDATE': 'datetime', 'TRADINGCODE': 'symbol'}),
    # ETF成份股历史记录表
    DataManager(API_TYPE='productinfo', LIB_ID='ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY',
                API_KWARGS={"library_name": "PRODUCTINFO_ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY",
                            "ArchiveDate": f"{NOWDATE}"},
                API_INDEX_COL={'ArchiveDate': 'datetime', 'ComponentExchangeSymbol': 'symbol'}),
    # 指数权重全量表
    DataManager(API_TYPE='productinfo', LIB_ID='INX_COMPONENTWEIGHT_ED',
                API_KWARGS={"library_name": "PRODUCTINFO_INX_COMPONENTWEIGHT_ED", "tradingday": f"{NOWDATE}"},
                API_INDEX_COL={'tradingday': 'datetime', 'secucode': 'symbol'}),
    # 基金费率变动
    DataManager(API_TYPE='productinfo', LIB_ID='FND_FEERATECHANGE',
                API_KWARGS={"library_name": "PRODUCTINFO_FND_FEERATECHANGE", "pubdate": f"{NOWDATE}"},
                API_INDEX_COL={'pubdate': 'datetime', 'secucode': 'symbol'}),
    # 基金投资行业组合
    DataManager(API_TYPE='productinfo', LIB_ID='FND_INDUPORTFOLIO',
                API_KWARGS={"library_name": "PRODUCTINFO_FND_INDUPORTFOLIO", "pubdate": f"{NOWDATE}"},
                API_INDEX_COL={'pubdate': 'datetime', 'secucode': 'symbol'}),
    # 指标因子
    DataManager(API_TYPE='indicator', LIB_ID='INDICATOR_PLATFORM_1',
                API_KWARGS={"date": f"{NOWDATE}",
                            "action": "27720",
                            "props": "10035|10049|10055|10041|10042|10043|10044|11|10036|10018|10086|40105|40031|40002|10014|10015|10008|70098|70391|40624|10016|10017|10020|79999",
                            "marketType": "HSJASH"},
                API_INDEX_COL={'TradeDate': 'datetime', 'SecurityId': 'symbol', 'Market': 'market'}),
    DataManager(API_TYPE='indicator_min', LIB_ID='INDICATOR_PLATFORM_MINUTE_1',
                API_KWARGS={"date": f"{NOWDATE}",
                            "action": "27720",
                            "props": "10023",
                            "marketType": "HSJASH",
                            "codes": "600519|1_0"},
                API_INDEX_COL={'TradeDate': 'datetime', 'SecurityId': 'symbol', 'Market': 'market'}),
    # hive数据
    # 股票大宗交易
    DataManager(API_TYPE='hive', LIB_ID='STK_BLOCKTRADE',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_BLOCKTRADE", "tradingday": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_blocktrade.tradingday': 'datetime', 'stk_blocktrade.tradingcode': 'symbol'}),
    # 龙虎榜_个股上榜信息_原因
    DataManager(API_TYPE='hive', LIB_ID='STK_SHAREDETAILSCHANGE',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_SHAREDETAILSCHANGE",
                            "listdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_sharedetailschange.listdate': 'datetime', 'stk_sharedetailschange.tradingcode': 'symbol'}),
    # 股东增减持计划表，根据 TRADEDIRECT 增持/减持判断
    DataManager(API_TYPE='hive', LIB_ID='COM_HOLDERSHARECHANGEPLAN',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.COM_HOLDERSHARECHANGEPLAN",
                            "pubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'com_holdersharechangeplan.pubdate': 'datetime', 'com_holdersharechangeplan.comcode': 'symbol'}),
    # 股东增减持，根据变动方向CHANGEDIRECTION 增持/减持判断
    DataManager(API_TYPE='hive', LIB_ID='COM_HOLDERSHARECHANGE',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.COM_HOLDERSHARECHANGE",
                            "pubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'com_holdersharechange.pubdate': 'datetime', 'com_holdersharechange.comcode': 'symbol'}),
    # 回购计划实施进度表
    DataManager(API_TYPE='hive', LIB_ID='STK_BUYBACKPRO',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_BUYBACKPRO",
                            "pubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_buybackpro.pubdate': 'datetime'}),
    # 股票增发
    DataManager(API_TYPE='hive', LIB_ID='STK_ADDITIONALSHARE',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_ADDITIONALSHARE",
                            "inipubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_additionalshare.inipubdate': 'datetime', 'stk_additionalshare.comcode': 'symbol'}),
    # 中国A股限售股流通日历
    DataManager(API_TYPE='hive', LIB_ID='STK_ASHAREFREEFLOATCALENDAR',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_ASHAREFREEFLOATCALENDAR",
                            "pubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_asharefreefloatcalendar.pubdate': 'datetime',
                               'stk_asharefreefloatcalendar.tradingcode': 'symbol'}),
    # 中国A股增发
    DataManager(API_TYPE='hive', LIB_ID='STK_SEOWIND',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_SEOWIND",
                            "pubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_seowind.pubdate': 'datetime',
                               'stk_seowind.tradingcode': 'symbol'}),
    # 中国A股回购(万得)
    DataManager(API_TYPE='hive', LIB_ID='STK_ASHARESTOCKREPO',
                API_KWARGS={"library_name": "SRC_CENTER_ADMIN.STK_ASHARESTOCKREPO",
                            "pubdate": [f">={NOWDATE_TIME}", f"<={NEXTDATE_TIME}"]},
                API_INDEX_COL={'stk_asharestockrepo.pubdate': 'datetime',
                               'stk_asharestockrepo.tradingcode': 'symbol'}),

    # 分钟频
    # 分钟衍生因子库（缓存），非 MIN_BASE 行情
    DataManager(API_TYPE='L3Factor', LIB_ID='Factormin', LIB_TYPE='factor',
                API_START='20240101',
                API_END='20240301',
                API_INDEX_COL={'datetime': 'datetime', 'symbol': 'symbol'}),

]




def get_library_config(library_id):
    for conf in config_list:
        if conf.LIB_ID == library_id:
            return conf
    return None
