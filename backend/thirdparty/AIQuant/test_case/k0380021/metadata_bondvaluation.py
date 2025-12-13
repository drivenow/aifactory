from AIQuant.utils import MetaData

md = MetaData()

factor_info = {'bond_d_valuation': {
    'accrueddays': {
        'factor_id': 'accrueddays',
        'factor_describe': '已计息天数',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '债券特色',
        'classify_level3': None,
        'unit': '天',
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '已计息天数为债券类资产特有估值指标，属债券特色数据',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'accruedinterest': {
        'factor_id': 'accruedinterest',
        'factor_describe': '应计利息',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '应计利息属于债券估值相关指标，归类于资讯下的估值分类',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'ptm': {
        'factor_id': 'ptm',
        'factor_describe': '剩余期限(年)',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '债券特色',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '剩余期限为可转债估值相关指标，属债券特色类数据',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'curyield': {
        'factor_id': 'curyield',
        'factor_describe': '当期收益率',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '当期收益率为可转债估值类指标，反映债券收益水平',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'ytm': {
        'factor_id': 'ytm',
        'factor_describe': '纯债到期收益率',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '债券特色',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '纯债到期收益率为可转债估值核心指标，属债券特色类',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'strbvalue': {
        'factor_id': 'strbvalue',
        'factor_describe': '纯债价值',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '债券特色',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '纯债价值为可转债估值核心指标，反映债券纯债部分价值，属债券特色类',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'strbpremium': {
        'factor_id': 'strbpremium',
        'factor_describe': '纯债溢价',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '纯债溢价为可转债估值类指标，反映转债相对于纯债的溢价水平',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'strbpremiumratio': {
        'factor_id': 'strbpremiumratio',
        'factor_describe': '纯债溢价率',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '纯债溢价率衡量可转债估值水平，属债券估值类指标',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'convprice': {
        'factor_id': 'convprice',
        'factor_describe': '转股价',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '转股价为可转债估值核心参数，属债券估值类指标',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'convratio': {
        'factor_id': 'convratio',
        'factor_describe': '转股比例',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '债券特色',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '转股比例为可转债特有估值指标，反映债券转股能力，属债券特色类',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'convvalue': {
        'factor_id': 'convvalue',
        'factor_describe': '转股价值',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '债券特色',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '转股价值属于可转债估值指标，反映债券转股后的价值，归类于债券特色',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'convpremium': {
        'factor_id': 'convpremium',
        'factor_describe': '转股溢价',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '转股溢价为可转债估值核心指标，反映转债价格与转股价值偏离度',
        'query_chain': 'xquant',
        'source': 'xquant'
    },
    'convpremiumratio': {
        'factor_id': 'convpremiumratio',
        'factor_describe': '转股溢价率',
        'factor_status': 'TRAIL',
        'classify_level1': '资讯',
        'classify_level2': '估值',
        'classify_level3': None,
        'unit': None,
        'support_scene': '查询',
        'support_market': '债券',
        'remark': '转股溢价率反映可转债估值水平，属债券估值类指标',
        'query_chain': 'xquant',
        'source': 'xquant'
    }
}
}

library_id = "bond_d_valuation"
library_describe = "可转债估值指标"
factor_freq = "日频"
category = "indicator"
md.save_metadata(library_id, factor_freq, category, library_describe, factor_info)
