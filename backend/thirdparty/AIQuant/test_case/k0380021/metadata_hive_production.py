from AIQuant.utils import MetaData

md = MetaData()

lib_info = {'ZX_STKDEPTTRADINFO': {'library_describe': '个股上榜交易明细',
                                   'factor_describe': '个股上榜交易明细',
                                   'classify_level1': '资讯',
                                   'classify_level2': '龙虎榜',
                                   'classify_level3': None,
                                   'factor_id': 'ZX_STKDEPTTRADINFO',
                                   'support_market': '股票',
                                   'remark': '数据描述个股上榜交易明细，属于龙虎榜相关资讯',
                                   'query_chain': 'zx',
                                   'source': '资讯'},
            'ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY': {'library_describe': 'ETF成份股历史记录表',
                                                      'factor_describe': 'ETF成份股历史记录表',
                                                      'classify_level1': '资讯',
                                                      'classify_level2': '基本信息',
                                                      'classify_level3': None,
                                                      'factor_id': 'ETF_COMPONENT_PRODUCTINFO_EXT_HISTORY',
                                                      'support_market': '基金',
                                                      'remark': '记录ETF成份股历史变动信息，属于证券基本信息范畴',
                                                      'query_chain': 'productinfo',
                                                      'source': '资讯'},
            'INX_COMPONENTWEIGHT_ED': {'library_describe': '指数权重全量表',
                                       'factor_describe': '指数权重全量表',
                                       'classify_level1': '行情',
                                       'classify_level2': '公司属性',
                                       'classify_level3': '交易属性',
                                       'factor_id': 'INX_COMPONENTWEIGHT_ED',
                                       'support_market': '指数型',
                                       'remark': '指数权重由流通市值等交易属性决定，反映成分股在指数中的市场规则配置',
                                       'query_chain': 'productinfo',
                                       'source': '资讯'},
            'FND_FEERATECHANGE': {'library_describe': '基金费率变动',
                                  'factor_describe': '基金费率变动',
                                  'classify_level1': '资讯',
                                  'classify_level2': '基金特色',
                                  'classify_level3': '基金费率',
                                  'factor_id': 'FND_FEERATECHANGE',
                                  'support_market': '基金',
                                  'remark': '反映基金费率调整情况，属于基金特色类中的费率变动指标',
                                  'query_chain': 'productinfo',
                                  'source': '资讯'},
            'FND_INDUPORTFOLIO': {'library_describe': '基金投资行业组合',
                                  'factor_describe': '基金投资行业组合',
                                  'classify_level1': '资讯',
                                  'classify_level2': '投资组合',
                                  'classify_level3': None,
                                  'factor_id': 'FND_INDUPORTFOLIO',
                                  'support_market': '基金',
                                  'remark': '数据反映基金在各行业的投资分布，属资讯类下的投资组合信息',
                                  'query_chain': 'productinfo',
                                  'source': '资讯'},
            'STK_BLOCKTRADE': {'library_describe': '股票大宗交易',
                               'factor_describe': '股票大宗交易',
                               'classify_level1': '资讯',
                               'classify_level2': '重大事件',
                               'classify_level3': None,
                               'factor_id': 'STK_BLOCKTRADE',
                               'remark': '大宗交易属于公司重要交易行为，反映大额资金动向，归为重大事件类资讯',
                               'query_chain': 'hive',
                               'source': '资讯'},
            'STK_SHAREDETAILSCHANGE': {
                'library_describe': '龙虎榜_个股上榜信息_原因',
                'factor_describe': '龙虎榜_个股上榜信息_原因',
                'classify_level1': '资讯',
                'classify_level2': '龙虎榜',
                'classify_level3': None,
                'factor_id': 'STK_SHAREDETAILSCHANGE',
                'remark': '因子直接描述龙虎榜个股上榜原因，属龙虎榜专属数据，业务属性明确',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'COM_HOLDERSHARECHANGEPLAN': {
                'library_describe': '股东增减持计划表',
                'factor_describe': '股东增减持计划表',
                'classify_level1': '资讯',
                'classify_level2': '股本与股东',
                'classify_level3': '股东增减持',
                'factor_id': 'COM_HOLDERSHARECHANGEPLAN',
                'remark': '数据反映股东增减持计划，属股本与股东变动类信息',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'COM_HOLDERSHARECHANGE': {
                'library_describe': '股东增减持',
                'factor_describe': '股东增减持',
                'classify_level1': '资讯',
                'classify_level2': '股本与股东',
                'classify_level3': '股东增减持',
                'factor_id': 'COM_HOLDERSHARECHANGE',
                'remark': '数据反映股东持股变动情况，属股本与股东类下的股东增减持指标',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'STK_BUYBACKPRO': {
                'library_describe': '回购计划实施进度表',
                'factor_describe': '回购计划实施进度表',
                'classify_level1': '资讯',
                'classify_level2': '股本与股东',
                'classify_level3': '股份回购',
                'factor_id': 'STK_BUYBACKPRO',
                'remark': '数据反映公司股份回购实施进度，属股本变动相关信息披露',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'STK_ADDITIONALSHARE': {
                'library_describe': '股票增发',
                'factor_describe': '股票增发',
                'classify_level1': '资讯',
                'classify_level2': '增发配股',
                'classify_level3': None,
                'factor_id': 'STK_ADDITIONALSHARE',
                'remark': '因子描述为股票增发，属于公司资本运作信息，归类于增发配股',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'STK_ASHAREFREEFLOATCALENDAR': {
                'library_describe': '中国A股限售股流通日历',
                'factor_describe': '中国A股限售股流通日历',
                'classify_level1': '资讯',
                'classify_level2': '股本与股东',
                'classify_level3': '限售解禁',
                'factor_id': 'STK_ASHAREFREEFLOATCALENDAR',
                'remark': '数据反映A股限售股解禁日期安排，属股本变动类信息',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'STK_SEOWIND': {
                'library_describe': '中国A股增发',
                'factor_describe': '中国A股增发',
                'classify_level1': '资讯',
                'classify_level2': '增发配股',
                'classify_level3': None,
                'factor_id': 'STK_SEOWIND',
                'remark': '数据描述为A股增发，属于公司资本运作信息，归类于增发配股',
                'query_chain': 'hive',
                'source': '资讯'
            },
            'STK_ASHARESTOCKREPO': {
                'library_describe': '中国A股回购(万得)',
                'factor_describe': '中国A股回购(万得)',
                'classify_level1': '资讯',
                'classify_level2': '股本与股东',
                'classify_level3': '股份回购',
                'factor_id': 'STK_ASHARESTOCKREPO',
                'remark': '数据反映A股公司股份回购情况，属股本变动类信息',
                'query_chain': 'hive',
                'source': '资讯'
            }
            }
for lib_id in lib_info:
    library_id = lib_id
    library_describe = lib_info[lib_id]["library_describe"]
    category = "table"
    factor_freq = "日频"
    # factor_info为library_id下的所有因子信息
    support_market = lib_info[lib_id].get("support_market")
    factor_info = {lib_id: {"factor_describe": lib_info[lib_id]["factor_describe"],
                            "classify_level1": lib_info[lib_id]["classify_level1"],
                            "classify_level2": lib_info[lib_id]["classify_level2"],
                            "classify_level3": lib_info[lib_id]["classify_level3"],
                            "factor_id": lib_info[lib_id]["factor_id"],
                            "remark": lib_info[lib_id]["remark"],
                            "query_chain": lib_info[lib_id]["query_chain"],
                            "source": lib_info[lib_id]["source"],
                            },
                   }
    if support_market:
        factor_info[lib_id]["support_market"] = support_market
    # cover=True时，会先删除library_id对应的所有元数据信息，重新录入
    md.save_metadata(library_id, factor_freq, category, library_describe, factor_info, cover=True)
