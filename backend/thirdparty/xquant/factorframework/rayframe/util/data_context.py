from xquant.factordata import FactorData

s = FactorData()

factype_to_facname = {
    'alpha': ['alpha1', 'alpha2', 'alpha3', 'alpha4', 'alpha5', 'alpha6', 'alpha7', 'alpha8', 'alpha9', 'alpha10',
              'alpha11', 'alpha12', 'alpha13', 'alpha14', 'alpha15', 'alpha16', 'alpha17', 'alpha18', 'alpha19',
              'alpha20', 'alpha21', 'alpha22', 'alpha23', 'alpha24', 'alpha25', 'alpha26', 'alpha27', 'alpha28',
              'alpha29', 'alpha31', 'alpha32', 'alpha33', 'alpha34', 'alpha35', 'alpha36', 'alpha37',
              'alpha38', 'alpha39', 'alpha40', 'alpha41', 'alpha42', 'alpha43', 'alpha44', 'alpha45', 'alpha46',
              'alpha47', 'alpha48', 'alpha49', 'alpha50', 'alpha51', 'alpha52', 'alpha53', 'alpha54', 'alpha55',
              'alpha56', 'alpha57', 'alpha58', 'alpha59', 'alpha60', 'alpha61', 'alpha62', 'alpha63', 'alpha64',
              'alpha65', 'alpha66', 'alpha67', 'alpha68', 'alpha69', 'alpha70', 'alpha71', 'alpha72', 'alpha73',
              'alpha74', 'alpha75', 'alpha76', 'alpha77', 'alpha78', 'alpha79', 'alpha80', 'alpha81', 'alpha82',
              'alpha83', 'alpha84', 'alpha85', 'alpha86', 'alpha87', 'alpha88', 'alpha89', 'alpha90', 'alpha91',
              'alpha92', 'alpha93', 'alpha94', 'alpha95', 'alpha96', 'alpha97', 'alpha98', 'alpha99', 'alpha100',
              'alpha101', 'alpha102', 'alpha103', 'alpha104', 'alpha105', 'alpha106', 'alpha107', 'alpha108',
              'alpha109', 'alpha110', 'alpha111', 'alpha112', 'alpha113', 'alpha114', 'alpha115', 'alpha116',
              'alpha117', 'alpha118', 'alpha119', 'alpha120', 'alpha121', 'alpha122', 'alpha123', 'alpha124',
              'alpha125', 'alpha126', 'alpha127', 'alpha128', 'alpha129', 'alpha130', 'alpha131', 'alpha132',
              'alpha133', 'alpha134', 'alpha135', 'alpha136', 'alpha137', 'alpha138', 'alpha139', 'alpha140',
              'alpha141', 'alpha142', 'alpha143', 'alpha144', 'alpha145', 'alpha146', 'alpha147', 'alpha148',
              'alpha149', 'alpha150', 'alpha151', 'alpha152', 'alpha153', 'alpha154', 'alpha155', 'alpha156',
              'alpha157', 'alpha158', 'alpha159', 'alpha160', 'alpha161', 'alpha162', 'alpha163', 'alpha164',
              'alpha165', 'alpha166', 'alpha167', 'alpha168', 'alpha169', 'alpha170', 'alpha171', 'alpha172',
              'alpha173', 'alpha174', 'alpha175', 'alpha176', 'alpha177', 'alpha178', 'alpha179', 'alpha180',
              'alpha181', 'alpha182', 'alpha183', 'alpha184', 'alpha185', 'alpha186', 'alpha187', 'alpha188',
              'alpha189', 'alpha190', 'alpha191'],
    'barra_cne5': ['barra_cne5_beta', 'barra_cne5_bp', 'barra_cne5_earningsyield_cetop',
                   'barra_cne5_earningsyield_epibs', 'barra_cne5_earningsyield_etop', 'barra_cne5_growth_egibs',
                   'barra_cne5_growth_egibs_s', 'barra_cne5_growth_egro', 'barra_cne5_growth_sgro', 'barra_cne5_halpha',
                   'barra_cne5_leverage_blev', 'barra_cne5_leverage_dtoa', 'barra_cne5_leverage_mlev',
                   'barra_cne5_liquidity_stoa', 'barra_cne5_liquidity_stom', 'barra_cne5_liquidity_stoq',
                   'barra_cne5_residualvolatility_cmra', 'barra_cne5_residualvolatility_dastd',
                   'barra_cne5_residualvolatility_hsigma', 'barra_cne5_rstr', 'barra_cne5_size'],
    'emotion': ['cv_turn', 'relative_vol_updown'],
    'financialanalysis': ['apturn', 'apturndays', 'growth_cagr_netprofit_3y', 'growth_cagr_netprofit_5y',
                          'growth_cagr_tr_3y', 'growth_cagr_tr_5y', 'maintenance', 'netturndays',
                          'non_currentassetsturn', 'operatecapitalturn', 'yoycf', 'yoydebt', 'yoyprofit', 'yoy_assets',
                          'yoy_cash', 'yoy_fixedassets'],
    'momentum': ['halpha', 'relative_strength_12m', 'relative_strength_1m', 'relative_strength_2m',
                 'relative_strength_3m', 'relative_strength_6m', 'weighted_strength_12m', 'weighted_strength_2m',
                 'weighted_strength_3m'],
    'technicalanalysis': ['close1', 'close12', 'close2', 'close3', 'close6', 'coskew', 'ema_crossover',
                          'isabove_avg_mon', 'ln_close', 'long_bear', 'long_bull', 'mktcapfloat', 'negskew',
                          'price_vol_corr', 'short_bear', 'short_bull', 'std1', 'std12', 'std2', 'std3', 'std6', 'tr',
                          'tskew', 'turnover_m_ave1', 'turnover_m_ave12', 'turnover_m_ave2', 'turnover_m_ave3',
                          'turnover_m_ave6', 'turnover_m_ave_float1', 'turnover_m_ave_float12', 'turnover_m_ave_float2',
                          'turnover_m_ave_float3', 'turnover_m_ave_float6', 'turnover_w_ave', 'turnover_w_ave_float',
                          'vwap_close'],
    'valuationmetric': ['lncap_barra'],
    'barrarisk6': ['barra_cne6_beta', 'barra_cne6_booktoprice', 'barra_cne6_dividendyield',
                   'barra_cne6_earningsquality',
                   'barra_cne6_earningsvariability', 'barra_cne6_earningsyield', 'barra_cne6_growth',
                   'barra_cne6_inverstmentquality',
                   'barra_cne6_leverage', 'barra_cne6_liquidity', 'barra_cne6_longtermreversal', 'barra_cne6_midcap',
                   'barra_cne6_momentum',
                   'barra_cne6_profitability', 'barra_cne6_residualvolatility', 'barra_cne6_residualvolatility',
                   'barra_cne6_size',
                   'barra_cne6_beta', 'barra_cne6_booktoprice', 'barra_cne6_dividendyield',
                   'barra_cne6_earningsquality',
                   'barra_cne6_earningsvariability', 'barra_cne6_earningsyield', 'barra_cne6_growth',
                   'barra_cne6_inverstmentquality',
                   'barra_cne6_leverage', 'barra_cne6_liquidity', 'barra_cne6_longtermreversal', 'barra_cne6_midcap',
                   'barra_cne6_momentum',
                   'barra_cne6_profitability', 'barra_cne6_residualvolatility', 'barra_cne6_size', 'barra_cne6_beta',
                   'barra_cne6_booktoprice',
                   'barra_cne6_dividendyield', 'barra_cne6_earningsquality', 'barra_cne6_earningsvariability',
                   'barra_cne6_earningsyield',
                   'barra_cne6_growth', 'barra_cne6_investmentquality', 'barra_cne6_leverage', 'barra_cne6_liquidity',
                   'barra_cne6_longtermreversal',
                   'barra_cne6_midcap', 'barra_cne6_momentum', 'barra_cne6_profitability',
                   'barra_cne6_residualvolatility', 'barra_cne6_size']
}


# 改造成从配置文件读取因子名
def get_fac_names(fac_type):
    """
    根据因子类获取因子名
    :param fac_type:
    :return:
    """
    all_type = list(factype_to_facname.keys())
    if isinstance(fac_type, str):
        if fac_type == 'all':
            fac_type = all_type
        else:
            fac_type = [fac_type]
    for i in fac_type:
        if i not in all_type and i != 'all':
            raise Exception('无此因子类,请重新输入')
    factor_names = []
    for i in fac_type:
        factor_names += factype_to_facname[i]

    return factor_names


def get_before_trade_days(day, bf_num):
    """
    获取交易日之前N个交易日
    :param day:
    :param bf_num:
    :return:
    """
    # from tquant.basic_data import BasicData
    # bd = BasicData()
    # trading_days = bd.get_trading_day(day, -bf_num)
    trading_days = s.tradingday(day, -bf_num)
    return trading_days


def get_before_trade_day(day, bf_num):
    """
    获取交易日之前N个交易日
    :param day:
    :param bf_num: 0 返回当天 1 返回前一个交易日 以此类推
    :return:
    """
    # from tquant.basic_data import BasicData
    # bd = BasicData()
    # trading_days = bd.get_trading_day(day, -(bf_num+1))
    trading_days = s.tradingday(day, -(bf_num + 1))
    return trading_days[0]


def get_trade_days(dt_from, dt_to):
    # from tquant.basic_data import BasicData
    # bd = BasicData()
    # return bd.get_trading_day(dt_from, dt_to)
    return s.tradingday(dt_from, dt_to)


# 支持两种模式：如果不传end_date,就返回开始日期前quarter_lag个报告期list
#               如果传 end_date, 就返回从开始日期前第quarter_lag个报告期到结束日期前一个报告期的list
def get_before_report_day(start_date, quarter_lag, end_date=None):
    date_list_complete = ['20000331', '20000630', '20000930', '20001231', '20010331', '20010630', '20010930',
                          '20011231',
                          '20020331', '20020630', '20020930', '20021231', '20030331', '20030630', '20030930',
                          '20031231',
                          '20040331', '20040630', '20040930', '20041231', '20050331', '20050630', '20050930',
                          '20051231',
                          '20060331', '20060630', '20060930', '20061231', '20070331', '20070630', '20070930',
                          '20071231',
                          '20080331', '20080630', '20080930', '20081231', '20090331', '20090630', '20090930',
                          '20091231',
                          '20100331', '20100630', '20100930', '20101231', '20110331', '20110630', '20110930',
                          '20111231',
                          '20120331', '20120630', '20120930', '20121231', '20130331', '20130630', '20130930',
                          '20131231',
                          '20140331', '20140630', '20140930', '20141231', '20150331', '20150630', '20150930',
                          '20151231',
                          '20160331', '20160630', '20160930', '20161231', '20170331', '20170630', '20170930',
                          '20171231',
                          '20180331', '20180630', '20180930', '20181231', '20190331', '20190630', '20190930',
                          '20191231',
                          '20200331', '20200630', '20200930', '20201231', '20210331', '20210630', '20210930',
                          '20211231',
                          '20220331', '20220630', '20220930', '20221231', '20230331', '20230630', '20230930',
                          '20231231',
                          '20240331', '20240630', '20240930', '20241231', '20250331', '20250630', '20250930',
                          '20251231',
                          '20260331', '20260630', '20260930', '20261231', '20270331', '20270630', '20270930',
                          '20271231',
                          '20280331', '20280630', '20280930', '20281231', '20290331', '20290630', '20290930',
                          '20291231',
                          '20300331', '20300630', '20300930', '20301231', '20310331', '20310630', '20310930',
                          '20311231']
    qtr_list = [str(i) for i in date_list_complete if i <= start_date][-1 * quarter_lag:]
    if end_date:
        qtr_tmp = []
        for i in date_list_complete:
            if i < start_date:
                continue
            elif start_date <= i <= end_date:
                qtr_tmp.append(i)
            else:
                break
        qtr_list += qtr_tmp
    return qtr_list


def get_factor(date_list, fac_names=None, stocks=None):
    """
    多因子多天多股票

    :param date_list:
    :param fac_names:
    :param stocks
    :return:
    """
    # from tquant.stock_data import StockData
    # sd = StockData()
    # df2_1 = sd.get_factor_price_daily(stocks, date_list, fac_names, fill_na=True)
    df2_1 = s.get_factor_value("Basic_factor", stocks, date_list, fac_names, fill_na=True)
    return df2_1


def get_stocks_pool(day, security_type, securities="alpha_universe"):
    """
    获取股票池
    :return:
    """
    # from tquant.index_data import IndexData
    # from tquant.stock_data import StockData
    day = get_before_trade_day(day, 0)
    if securities == "alpha_universe":
        securities = "ALLA_HIS"
    if isinstance(securities, str):
        # 目前支持 'ALLA', 'SHA', 'SZA', 'ALLA_HIS', 'HS300','ZZ500','SH50'
        securities = securities.upper()
        if security_type == 'stock' and securities in ['ALLA', 'SHA', 'SZA', 'ALLA_HIS']:
            # sd = StockData()
            # res = sd.get_plate_info('MARKET', day, securities)['stock'].tolist()
            res = s.hset('MARKET', day, securities)['stock'].tolist()

        elif security_type == 'stock' and securities.upper() in ['HS300', 'ZZ500', 'SH50', 'SZ50', 'ZZ800', 'ZZ1000']:
            # ind = IndexData()
            # res = ind.get_index_info(day, securities, 0)['stock'].tolist()
            res = s.hset('INDEX', day, securities, 0)['stock'].tolist()
        else:
            raise Exception(
                "证券类型{}, securities为string类型时暂只支持传入 ALLA,SHA,SZA,ALLA_HIS,HS300,ZZ500,SH50,SZ50,ZZ800,ZZ1000股票池参数!".format(
                    security_type))
        if not res:
            raise Exception("日期：{0} 中 证券类型为{1}的标的池为空".format(day, security_type))
        return res
    elif isinstance(securities, list):
        return securities
    else:
        raise Exception("暂不支持传入该类型的securities: {}!".format(securities))

# def get_factor_lib(factor_list):
#     from tquant.stock_data import StockData
#     sd = StockData()
#     factor_lib = sd.get_factor_lib(factor_list)
#     return factor_lib[0]
