落地开发计划

元数据服务（路径确认：backend/thirdparty/AIQuant/）

新增 meta_service.py：定义 MetaFactor/MetaFactorService，从 backend/thirdparty/aiquant_factor_meta.xlsx 读取全部元数据字段，LIB_ID 为唯一键；加本地 LRU/TTL 缓存。
补充单元/烟囱测试：给定 LIB_ID 能取到 library_name/lib_type/freq/...，缓存命中逻辑可控。
Configs/执行参数规范

在 backend/thirdparty/AIQuant/configs.py 增补字段：FREQ、ALIGN_POLICY（默认低频→高频按规则；支持 override）。
重写 get_library_config 只按 LIB_ID 查（不再用 API_KWARGS["library_name"]/resource）；Factormin 配置标注衍生分钟因子。
文档备注：DataConfig 仅执行参数，不承载元语义。
SDK 数据读取 (backend/thirdparty/AIQuant/datamanager.py)

实现统一 get(conf: Configs)：先用 LIB_ID 调 meta_service 取 library_name/lib_type/freq/index_cols；按存储规范定位 parquet（缓存路径 /backend/thirdparty/daily_factor，分钟衍生因子同路径），按月分区拼接、datetime/symbol 去重排序。
标准化：列重命名、datetime 解析；裁剪 LIB_ID_FEILD 保留 datetime/symbol，支持 long/panel（默认 long）。
补读缓存优先（回源可留空），fail fast 缺元数据/缺必需列。
频率对齐工具 (backend/thirdparty/AIQuant/data_process.py)

提供 align(source_df, source_freq, target_freq, method)：day→min broadcast/ffill，min→day agg_last。
默认策略：低频对齐到高频；建议先将高频聚合为低频再做对齐的约束说明。
rayframe 适配层

在 rayframe 内新增独立适配模块（不改 depend_factor），在 BaseFactor/Factor 增加 aiquant_requirements + load_inputs(stocks, start, end)；内部逐个 sdk.get，按因子目标频率调用 align。
MIN_BASE (L3_MIN_DATA) 继续走原接口；Factormin 通过 SDK；新增接口在 calc 前预加载缓存并按 calc 时间窗口切片。
CodeGen 支持 Rayframe 模式

backend/domain/codegen/view.py：新增 CodeMode.RAYFRAME_PY。
semantic.py：新增 rayframe 语义检查（要求 aiquant_requirements、Configs(、calc 实现，黑名单直连数据源）。
generator.py/runner.py：分流 rayframe 模板与 dryrun（构造最小 datetime/symbol df 调 calc）；前端/状态机可传新 mode。
测试与示例

添加最小示例因子（DAY/MIN 各一），调用新取数/对齐流程。
针对 meta_service、SDK get、align、rayframe 适配写基础单测或脚本，确保路径/频率逻辑符合规范。
文档更新

更新 README.md 或新增 project_rules.md 补充：路径、默认对齐策略、MIN_BASE/Factormin 分工、LIB_ID 唯一入口、mock 数据放置规范。

---

当前已开发要点（2025-03）

- 元数据：新增 `backend/thirdparty/AIQuant/meta_service.py`，从 `aiquant_factor_meta.xlsx` 以 `LIB_ID` 读取，带 TTL 缓存。
- 数据 SDK：`datamanager.get(conf)` 统一走元数据定位 parquet，支持 `FREQ/ALIGN_POLICY/RETURN_FORMAT`；`get_library_config` 改为按 `LIB_ID`。
- 频率对齐：`backend/thirdparty/AIQuant/data_process.py` 提供 day→min（broadcast/ffill）、min→day（agg_last）。
- rayframe 适配：`rayframe/aiquant_adapter.py` + `BaseFactor.load_inputs/preload_aiquant_inputs` 读取 `aiquant_requirements`，不影响现有 `depend_factor`/MIN_BASE。
- 代码助手：新增 `CodeMode.RAYFRAME_PY`，静态检查必含 `aiquant_requirements`、Configs/DataManager、`calc`；dryrun 占位返回。

待补充

- 增加最小示例因子与单测脚本覆盖 meta_service/get/align/adapter。
- 文档：在 README 或 project_rules 记录默认路径、对齐策略、Factormin/MIN_BASE 分工。
