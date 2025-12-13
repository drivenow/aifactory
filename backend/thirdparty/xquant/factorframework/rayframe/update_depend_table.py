
from xquant.factorframework.rayframe.psfactor import FactorData as xpsFactorData

xf = xpsFactorData()

tables = {'ASHAREINCEXERCISEPCT': {'save_type': 'Fully', 'date_column': ''},
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

                'ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY':{'save_type': 'Daily', 'date_column': 'datetime'},
                }

factor_info_daily = {}
factor_info_fully = {}
for table in tables:
    if tables[table]["save_type"] == "Daily":
        factor_info_daily[table] = "datetime"
    if tables[table]["save_type"] == "Fully":
        factor_info_fully[table] = ""

xf.save_metadata(library_name="ZX", library_type="Source_table_daily",
                 library_describe="万得/朝阳永续等外部数据-日频", factor_info=factor_info_daily)

xf.save_metadata(library_name="ZX", library_type="Source_table_fully",
                 library_describe="万得/朝阳永续等外部数据-全表", factor_info=factor_info_fully)

# print(len(factor_info_daily))
# print(len(factor_info_fully))

# res = xf.get_metadata('Source_table_fully', 'ZX')
# print(res)



