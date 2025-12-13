from AIQuant.utils import MetaData

md = MetaData()

lib_msg = [{'library_id': 'factor_d_issuingdateindex', 'library_describe': '财务-披露日期表', 'factor_freq': '季频'},
           {'library_id': 'factor_d_profitnotice', 'library_describe': 'A股财务业绩预告快报', 'factor_freq': '季频'}]

lib_info = {'factor_d_issuingdateindex': {
    'stm_issuingdate': {
        'factor_id': 'stm_issuingdate',
        'factor_describe': '定期报告实际披露日期',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '上市与发行',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '股票',
        'remark': '反映定期报告实际披露日期，属于公司信息披露范畴',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'stm_predict_issuingdate': {
        'factor_id': 'stm_predict_issuingdate',
        'factor_describe': '定期报告预计披露日期',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '上市与发行',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '股票',
        'remark': '反映定期报告预计披露日期，属于公司信息披露范畴',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    's_div_preanndt': {
        'factor_id': 's_div_preanndt',
        'factor_describe': '预案预披露公告日(股东提议的公告日期)',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '上市与发行',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '股票',
        'remark': '该因子表示股东提议的预案公告日，属于信息披露中的发行相关事件',
        'query_chain': 'xquant',
        'source': 'xquant'
    }
},
    'factor_d_profitnotice': {
        'profitnotice_date': {
            'factor_id': 'profitnotice_date',
            'factor_describe': '公告日期（业绩预告）',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '业绩与绩效评估',
            'classify_level3': None,
            'unit': None,
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '业绩预告公告日期属于公司业绩披露信息，归类于业绩与绩效评估',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'profitnotice_netprofitmin': {
            'factor_id': 'profitnotice_netprofitmin',
            'factor_describe': '预告净利润下限（万元）',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '业绩与绩效评估',
            'classify_level3': None,
            'unit': '万元',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '预告净利润下限反映公司业绩预期，属业绩与绩效评估类指标',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'profitnotice_netprofitmax': {
            'factor_id': 'profitnotice_netprofitmax',
            'factor_describe': '预告净利润上限（万元）',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '业绩与绩效评估',
            'classify_level3': None,
            'unit': '万元',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '预告净利润上限反映公司业绩预期，属业绩与绩效评估类指标',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'profitnotice_changemin': {
            'factor_id': 'profitnotice_changemin',
            'factor_describe': '预告净利润变动幅度下限（%）',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '业绩与绩效评估',
            'classify_level3': None,
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '反映公司预告净利润变动下限，属业绩预告类指标，用于绩效评估',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'profitnotice_changemax': {
            'factor_id': 'profitnotice_changemax',
            'factor_describe': '预告净利润变动幅度上限（%）',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '业绩与绩效评估',
            'classify_level3': None,
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '反映公司业绩预告中净利润变动上限，属业绩类指标',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'ann_dt_kb': {
            'factor_id': 'ann_dt_kb',
            'factor_describe': '公告日期（业绩快报）',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '业绩与绩效评估',
            'classify_level3': None,
            'unit': None,
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '公告日期关联业绩快报，属财务信息披露，归类于业绩与绩效评估',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'yoysales_kb': {
            'factor_id': 'yoysales_kb',
            'factor_describe': '同比增长率:营业收入',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '财务数据',
            'classify_level3': '利润',
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '营业收入同比增长率源自利润表，反映主营业务增长，属利润类财务指标的核心组成部分',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'yoyop_kb': {
            'factor_id': 'yoyop_kb',
            'factor_describe': '同比增长率:营业利润',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '财务数据',
            'classify_level3': '利润',
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '营业利润同比增长率属于财务数据中的利润类指标，反映公司盈利能力',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'yoyebt_kb': {
            'factor_id': 'yoyebt_kb',
            'factor_describe': '同比增长率:利润总额',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '财务数据',
            'classify_level3': '利润',
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '数据为利润总额同比增长率，来源于财务业绩预告，属财务数据中利润类指标',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'yoynetprofit_deducted_kb': {
            'factor_id': 'yoynetprofit_deducted_kb',
            'factor_describe': '同比增长率:归属母公司股东的净利润',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '财务数据',
            'classify_level3': '利润',
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '归属母公司净利润同比增长率，反映公司盈利能力，属财务数据中利润类指标',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'yoyeps_basic_kb': {
            'factor_id': 'yoyeps_basic_kb',
            'factor_describe': '同比增长率:基本每股收益',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '财务数据',
            'classify_level3': '利润',
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': '基本每股收益同比增长率反映公司盈利增长，属财务数据中利润类指标',
            'query_chain': 'xquant',
            'source': 'xquant'
        },
        'roe_yearly_kb': {
            'factor_id': 'roe_yearly_kb',
            'factor_describe': '同比增减:加权平均净资产收益率',
            'factor_status': 'TRAIL',
            'classify_level1': '资讯',
            'classify_level2': '财务数据',
            'classify_level3': '利润',
            'unit': '%',
            'support_scene': '选股',
            'support_market': '股票',
            'remark': 'ROE为盈利能力指标，基于财务数据中的利润信息计算，属利润类',
            'query_chain': 'xquant',
            'source': 'xquant'
        }
    }
}

for lib_msg_p in lib_msg:
    library_id = lib_msg_p["library_id"]
    library_describe = lib_msg_p["library_describe"]
    factor_freq = lib_msg_p["factor_freq"]
    category = "indicator"
    factor_info = lib_info[library_id]
    md.save_metadata(library_id, factor_freq, category, library_describe, factor_info)
