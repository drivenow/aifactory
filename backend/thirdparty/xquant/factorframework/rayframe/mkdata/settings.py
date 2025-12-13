from xquant.setXquantEnv import xquantEnv
from FactorProvider.storage.db import DML_mysql
import threading
import time
import os

# 基础目录
base_dir = "/data/user/016869/REF/DB_FILE_CACHE"
# 公共数据目录
panel_min_base_dir = os.path.join(base_dir, "MINUTE_DATA")
panel_wind_base_dir = os.path.join(base_dir, "WIND_DATA")
panel_index_weight_base_dir = os.path.join(base_dir, "INDEX_WEIGHT")
panel_barra_base_dir = os.path.join(base_dir, "BARRA_DATA")
panel_msci_base_dir = os.path.join(base_dir, "MSCI_DATA")
ori_min_base_dir = os.path.join(base_dir, "ORI_MINUTE_DATA")

if xquantEnv == 1:
    base_dir_new_1 = "/app/taip/bigdata/xdata/SOURCE_TABLES"
    base_dir_new_2 = "/dfs/group/800657/library_alpha/quant_data/SOURCE_TABLES"
    l3_data_dir = "/dfs/group/800657/library/l3_data/"
    l3_minute_data_dir = "/dfs/group/800657/library_alpha/quant_data/L3_MINUTE_DATA"
    if os.path.exists(base_dir_new_1):
        base_dir_new = base_dir_new_1
    elif os.path.exists(base_dir_new_2):
        base_dir_new = base_dir_new_2
    else:
        raise Exception("外部数据的NAS挂载路径不存在！！！")
else:
    base_dir_new_1 = "/app/taip/bigdata/xdata/SOURCE_TABLES"
    base_dir_new_2 = "/data/user/quanttest007/library_alpha/quant_data/SOURCE_TABLES"
    l3_data_dir = "/data/user/quanttest007/K0321499/keep/dataset"
    l3_minute_data_dir = "/data/user/quanttest007/library_alpha/quant_data/L3_MINUTE_DATA"
    if os.path.exists(base_dir_new_1):
        base_dir_new = base_dir_new_1
    elif os.path.exists(base_dir_new_2):
        base_dir_new = base_dir_new_2
    else:
        raise Exception("外部数据的NAS挂载路径不存在！！！")


def get_data_save_format():
    c_name = str(int(time.time())) + str(threading.get_ident())
    dml =  DML_mysql('xquant')
    sql = "select library_name,factor,factor_describe,factor_freq from personal_factors_new where factor_freq in ('Daily', 'Fully')"
    df = dml.getAllByPandas(c_name, sql)
    dml.close(c_name)
    data_save_format = {}
    library_names = list(df["library_name"].unique())
    for library_name in library_names:
        key = library_name + "_DATA"
        if key not in data_save_format:
            data_save_format[key] = {}
        df_p = df[df["library_name"] == library_name]
        for idx, row in df_p.iterrows():
            data_save_format[key][row['factor']] = {'save_type': row["factor_freq"], 'date_column':row["factor_describe"]}
    return data_save_format

data_save_format = get_data_save_format()
# print(data_save_format)

# 数据存储模式
data_save_format_bak2 = {
    "ZX_DATA": {'ASHAREINCEXERCISEPCT': {'save_type': 'Fully', 'date_column': ''},
                'ASHAREINDUSTRIESCODE': {'save_type': 'Fully', 'date_column': ''},
                'ASHAREEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'AINDEXEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'AINDEXFINANCIALDERIVATIVE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'AINDEXINDUSTRIESEODCITICS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'AINDEXMEMBERS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'AINDEXVALUATION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREANNFINANCIALINDICATOR': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREAGENCY': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREBALANCESHEET': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREBLOCKTRADE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARECOCAPITALOPERATION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARECAPITALIZATION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARECASHFLOW': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARECOMPRESTRICTED': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARECONSEPTION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREDESCRIPTION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREDIVIDEND': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREEODDERIVATIVEINDICATOR': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREEQUITYDIVISION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREEQUITYPLEDGEINFO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREESOPDESCRIPTION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREESOPTRADINGINFO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREFINANCIALEXPENSE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREFINANCIALINDICATOR': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREFREEFLOAT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREFREEFLOATCALENDAR': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREHOLDERNUMBER': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREIPO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINCDESCRIPTION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINCEXECQTYPRI': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINCQUANTITYDETAILS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINCQUANTITYPRICE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINCOME': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINDUSTRIESCLASSCITICS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINSIDEHOLDER': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREINSIDERTRADE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREISSUECOMMAUDIT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREISSUINGDATEPREDICT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREL2INDICATORS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARELEADUNDERWRITER': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMAJOREVENT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMAJORHOLDERPLANHOLD': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMANAGEMENTHOLDREWARD': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMARGINSUBJECT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMARGINTRADE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMARGINTRADESUM': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMJRHOLDERTRADE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREMONEYFLOW': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREPLACEMENTDETAILS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREPLACEMENTINFO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREPLEDGEPROPORTION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREPROFITEXPRESS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREPROFITNOTICE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARERIGHTISSUE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREST': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARESTAFF': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARESTRANGETRADEDETAIL': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARESTYLECOEFFICIENT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARETTMHIS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARETRADINGSUSPENSION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREAGINGSTRUCTURE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHAREOTHERACCOUNTSRECEIVABLE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'ASHARESTOCKREPO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDFUTURESEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDFUTURESPOSITIONS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDISSUERRATING': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDRATING': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CCBONDCONVERSION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CCBONDVALUATION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CCOMMODITYFUTURESEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CCOMMODITYFUTURESPOSITIONS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CGBBENCHMARK': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CINDEXFUTURESEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CINDEXFUTURESPOSITIONS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CMFOTHERPORTFOLIO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDFCTD': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CBONDFSUBJECTCVF': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CHINAMUTUALFUNDSTOCKPORTFOLIO': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CHINAOPTIONDAILYSTATISTICS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CHINAOPTIONEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CHINAOPTIONINDEXEODPRICES': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CHINAOPTIONMEMBERSTATISTICS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CHINAOPTIONVALUATION': {'save_type': 'Daily', 'date_column': 'datetime'},
                'IECMEMBERLIST': {'save_type': 'Daily', 'date_column': 'datetime'},
                'IPOCOMPRFA': {'save_type': 'Daily', 'date_column': 'datetime'},
                'IPOINQUIRYDETAILS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'SHSCCHANNELHOLDINGS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'SHSCDAILYSTATISTICS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'SINDEXPERFORMANCE': {'save_type': 'Daily', 'date_column': 'datetime'},
                # -----------分割线，以下是GOGOAL的表------------------------
                'CON_FORECAST_C2_IDX': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CON_FORECAST_C3_IDX': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CON_FORECAST_IDX': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_FORECASTROLLRANK': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_FORECASTSECUDERIVED': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_RATINGADJNUM': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_RATINGSTRENGTHRANK': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_STKCONF': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_STKDIVER': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_STKFOCUS': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_STOCKEXCESSSTAT': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DWD_EXP_STOCKPROBNOTICE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'EXP_FORECASTADJNUM': {'save_type': 'Daily', 'date_column': 'datetime'},
                'EXP_FORECASTSCHEDULE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'EXP_FORECASTSECU': {'save_type': 'Daily', 'date_column': 'datetime'},
                'EXP_FORECASTSECUDERIVED': {'save_type': 'Daily', 'date_column': 'datetime'},
                'EXP_REPORTSCOREADJ': {'save_type': 'Daily', 'date_column': 'datetime'},
                'EXP_RESEARCHREPORTADJ': {'save_type': 'Daily', 'date_column': 'datetime'},
                'STK_REPORTNUM': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CON_FORECAST_C2_STK': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CON_FORECAST_C3_STK': {'save_type': 'Daily', 'date_column': 'datetime'},
                'CON_FORECAST_SCHEDULE': {'save_type': 'Daily', 'date_column': 'datetime'},
                'DER_EXCESS_STOCK': {'save_type': 'Daily', 'date_column': 'datetime'},
                # -----------分割线，以下是MSCI的表------------------------
                'CNLTS_ASSET_EXPOSURE': {'save_type': 'Daily', 'date_column': 'data_date'},
                'CHN_LOCALID_ASSET_ID': {'save_type': 'Fully'},
                # -----------分割线，以下是 的表------------------------
                },
}

data_save_format_bak = {
    "WIND_DATA": {"WIND_AShareEODDerivativeIndicator": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareEODPrices": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareANNFinancialIndicator": {"save_type": "Daily", "date_column": "REPORT_PERIOD"},
                  "WIND_AShareFinancialderivative": {"save_type": "Daily", "date_column": "ENDDATE"},
                  "WIND_AShareFinancialIndicator": {"save_type": "Daily", "date_column": "REPORT_PERIOD"},
                  "WIND_AShareConsensusData": {"save_type": "Daily", "date_column": "EST_DT"},
                  "WIND_AShareConsensusRollingData": {"save_type": "Daily", "date_column": "EST_DT"},
                  "WIND_AShareValuationIndicator": {"save_type": "Daily", "date_column": ""},
                  "WIND_AShareEVIndicator": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareBalanceSheet": {"save_type": "Daily", "date_column": "REPORT_PERIOD"},
                  "WIND_AShareMoneyFlow": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareEnergyindexADJ": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareintensitytrendADJ": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareswingReversetrendADJ": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AShareTechIndicators": {"save_type": "Daily", "date_column": "TRADE_DT"},
                  "WIND_AIndexMembers": {"save_type": "Fully", "date_column": ""},
                  "WIND_AIndexMembersCITICS": {"save_type": "Fully", "date_column": ""},
                  "WIND_AIndexWindIndustriesEOD": {"save_type": "Fully", "date_column": ""},
                  "WIND_WindCustomCode": {"save_type": "Fully", "date_column": ""},
                  "WIND_AShareSEO": {"save_type": "Fully", "date_column": ""},
                  },
    "MSCI_DATA": {"MSCI_cnlts_asset_exposure": {"save_type": "Daily", "date_column": "data_date"},
                  "MSCI_chn_localid_asset_id": {"save_type": "Fully"}
                  },
    "INDEX_WEIGHT": {"000016.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "000300.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "000688.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "000698.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "000852.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "000905.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "000906.SH": {"save_type": "Daily", "date_column": "TRADINGDAY"},
                     "ZZ2000": {"save_type": "Daily", "date_column": "TRADINGDAY"}
                     },
}
