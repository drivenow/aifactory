下面给你一份**“数据结构/接口定义先行”**的标准落地方案与开发规范，严格按你澄清的职责边界来：

参考代码，后续都会引用到相关文件：
[文档1：rayframe框架](https://github.com/xquant/factorframework/tree/main/rayframe)只关注BaseFactor.py部分
[文档2：统一数据处理规范](https://github.com/xquant/factorframework/blob/main/rayframe/docs/数据存储规范.md)
[文档3：统一数据存取接口](/mnt/x/RPA-github/langgraph_source/aifactory/backend/thirdparty/AIQuant/configs.py)
[文档4：统一元数据标](https://github.com/xquant/factorframework/blob/main/rayframe/docs/数据存储规范.md)，通过library_id和数据进行关联

---

## 0. 目标与边界（统一共识）

### 目标

1. rayframe 因子框架的数据获取**统一走公司标准 SDK（Configs）**，并优先读缓存（月 parquet）。缓存规范：表/因子都统一 `datetime/symbol` 主键，因子库每月一个 parquet，写入后因子列集合固定。
2. **MIN_BASE = L3_MIN_DATA**（基础分钟行情）继续走 rayframe 现有接入；Factormin 只是衍生分钟缓存（例如大单数量），**不能代替 MIN_BASE**。rayframe BaseFactor 已有分钟行情接口（`add_ori_min_data` 调 `get_ori_min_data_dfs`）
3. **DataConfig/Configs 不承载更多元数据**：DataConfig 只存最小可执行配置（LIB_ID 等），元数据从 DB 查，通过 `LIB_ID` 关联。你们规范里也明确 “从元数据查询 library_name，再按存储规范读 parquet”。

### 边界（本期不做）

* 不做财务“报告期/披露日”口径治理（只做 1d/1m）。
* 不做无限数据源接入全覆盖，只做“接入能力”与“可扩展机制”。

---

## 1. 职责边界（必须写进开发规范，避免混淆）

### 1) DataConfig / Configs（轻配置）

* **只负责“怎么取数/怎么落缓存/怎么对齐”的执行参数**，不负责解释字段语义。
* 必须包含 `LIB_ID`（唯一数据名），其它参数可选：`API_TYPE/API_KWARGS/API_START/API_END/LIB_TYPE/LIB_ID_FEILD` 等（你们已经定义）。
* **禁止**在 Configs 里塞“字段含义、单位、复权口径”等元信息（这些归 DB 元数据管理）。

### 2) 元数据服务（DB）

* 输入：`LIB_ID`
* 输出：至少要能得到：

  * 缓存定位信息：`library_name`、库类型（表/因子库）、频率（1d/1m）、默认 index 列（或标准化规则 id）等
* 约束：元数据更新策略、唯一性（你们已在规范里定义“一次存储不能更新”等）。

### 3) Data SDK（统一取数入口）

* 输入：`Configs`
* 行为：命中缓存读 parquet；缺失则按 `API_TYPE` 回源（本期可先只做“缓存读”跑通），并且所有返回必须标准化为 `datetime/symbol`。

### 4) rayframe（计算框架）

* **只做计算与调度**：Factor 的 `calc()` 只处理输入 DataFrame/Series，不直接连接数据源。
* MIN_BASE（L3_MIN_DATA）维持现状（rayframe 已有 `add_ori_min_data`）。
* Factormin 作为“衍生分钟缓存”通过 SDK 作为普通输入源接入。

---

## 2. 数据结构与接口定义（先行）

下面是本期建议你们“定死”的最小接口集合（越少越稳，后续只增不改）。

### 2.1 Configs（在你们现有字段基础上，**只新增跨频所需字段**）

你们已有的 `Configs` 结构（API_TYPE/LIB_ID/API_START/API_END/API_KWARGS/LIB_TYPE/LIB_ID_FEILD/默认路径）保持不动。

**本期建议新增（仅 1d/1m）**：

* `FREQ: Literal["1m","1d"] | None`

  * 默认由元数据填充（Configs 可覆盖，默认规则为ffill，但一般不让用户写）
* `ALIGN_POLICY: Literal["broadcast","ffill","agg_last"] | None`

  * 仅当本输入频率与因子频率不一致时使用（见 2.3）
* `SYMBOL_NORMALIZER: str | None`

  * 指向“标的转换规则 id”（实际规则在 SDK 内置/或从元数据拿），LLM 只能选，不许发明

> 注意：这些依然属于“执行参数”，不算元数据语义。

### 2.2 元数据服务接口（DB）

#### 2.2.1 MetadataSchema定义

根据 [文档4：统一元数据标](https://github.com/xquant/factorframework/blob/main/rayframe/docs/数据存储规范.md)实现。
```python
class MetaData(BaseModel):
    lib_id: str
    library_name: str
    lib_type: Literal["table","factor"]
    freq: Literal["1m","1d"]
    # ... 根据
```

接口：

#### 2.2.2 MetadataService（DB 读取）

文件：/mnt/x/RPA-github/langgraph_source/aifactory/backend/thirdparty/AIQuant/meta_service.py

```python
class MetadataService(Protocol):
    def get_library_meta(self, lib_id: str) -> LibraryMeta: ...
    def list_libraries(self, **filters) -> list[LibraryMeta]: ...
```

- 输入：`lib_id`（唯一键）
- 输出：`LibraryMeta`（包含 library_name、freq、lib_type、symbol_normalizer_id、存储位置等）

#### 2.2.3 DataConfigRegistry（从 configs.py 构建）

```python
class DataConfigRegistry:
    def get(self, lib_id: str) -> DataManager | None: ...
```

- **必须以 `LIB_ID` 建索引**（而不是匹配 `API_KWARGS["library_name"]/["resource"]`）来替换当前 `get_library_config` 的实现缺陷。


### 2.3 Data SDK 统一接口（All-in-One 入口）

已有接口，位于[统一数据读取接口](backend/thirdparty/AIQuant/datamanager.py)

```python
def get(conf: Configs) -> pd.DataFrame:
    """
    1) 通过 conf.LIB_ID 查元数据得到 library_name/lib_type/freq/默认 index col/normalizer
    2) 命中缓存则按存储规范读 parquet（表：按年/或按月；因子库：按月 library_name.parquet）:contentReference[oaicite:7]{index=7}
    3) 按 conf.LIB_ID_FEILD 选列（datetime/symbol 永远保留）
    4) `RETURN_FORMAT: Literal["long","panel"] = "long"`（默认 long）
    """
```

### 2.4 rayframe 输入契约（对因子开发者/代码助手可见）

rayframe Factor 的核心契约是重写 `calc()`，框架负责调度。这部分已经实现。[rayframe计算实现](/mnt/x/RPA-github/langgraph_source/aifactory/backend/thirdparty/xquant/factorframework/rayframe/calculation/DataCalculation.py)

新增“数据需求声明”，替代/旁路 `depend_factor`（因为你们要接海量源表，不可能靠固定 BasicDayFactor 那套）。

建议在 Factor 子类里新增类属性，用于传入DataManager类的数据读取配置项。[文档3：统一数据存取接口](/mnt/x/RPA-github/langgraph_source/aifactory/backend/thirdparty/AIQuant/configs.py)


```python
data_requirements: dict[str, DataManager] = {
   "MIN_BASE": DataManager(LIB_ID="L3_MIN_DATA", FREQ="1m", ...),
   "DERIVED_MIN": DataManager(LIB_ID="Factormin", FREQ="1m", ...),
   "DAY_EOD": DataManager(LIB_ID="ASHAREEODPRICES", FREQ="1d", LIB_ID_FEILD=[...]),
}
```

rayframe 侧提供统一加载：

* `Factor.load_inputs(stocks, start_date, end_date) -> dict[str, pd.DataFrame]`

  * 内部逐个 `sdk.get(conf)`，并做跨频对齐（见 2.5）


* MIN_BASE / Factormin 的定位

    - `MIN_BASE (= L3_MIN_DATA)`：作为 **基础分钟行情**，进入元数据（freq=1m, lib_type=table），并在 DataConfigRegistry 有对应条目（可以复用 rayframe 原有接入，不要求立刻迁移）。
    - `Factormin`：作为 **分钟衍生因子库**（lib_type=factor, freq=1m），可作为 data_requirements 的一个输入（你 configs.py 里也有它作为 L3Factor/factor 的配置）。


### 2.5 频率对齐接口（仅 1m/1d）

统一做成 SDK/rayframe 的一个函数（不要让每个因子自己 merge）：

* `align(source_df, source_freq, target_freq, method) -> aligned_df`

method策略（本期只实现 3 个就够跑）：

1. `broadcast`：**日 → 分钟**，把日值铺到当日所有分钟（按 trade_date + symbol join）
2. `ffill`：**日 → 分钟**，在分钟时间轴上向前填充（适合“每个交易日一个值”的因子）
3. `agg_last`：**分钟 → 日**，按日聚合取最后一条（分钟 → 日最稳的 MVP）

---

## 3. 标准开发规范（Coding / 结构 / 治理）

### 3.1 模块分层规范（必须遵守）

1. `meta/`：元数据访问（DB client + cache），**只认 LIB_ID**
2. `sdk/`：Configs 解释、缓存读写、回源（可选）、标准化、对齐
3. `rayframe_adapter/`：把 `sdk.get()` 的结果注入到 rayframe 因子执行流程
4. `code_assistant/`：Prompt/静态检查/运行器适配（见第 5 节）

### 3.2 关键约束（写进 lint / 静态检查）

* 因子代码禁止直接访问第三方数据源；必须通过 `data_requirements -> sdk.get()`。
* `datetime/symbol` 必须存在且类型正确（datetime 为 pandas datetime64 / 或统一字符串规范）。
* 缺 Configs / 缺元数据：必须 fail fast（报“不可治理”，不要 silent fallback）。

### 3.3 命名与兼容规范

* 外部唯一键：`LIB_ID`（不要再让外部传 library_name/resource）
* `DataManager`/现有 config_list 继续保留，但用途改为“示例/默认回源参数模板”，不要再承担元数据职责。

你现在的 `configs.py` 里 `get_library_config()` 依赖 `API_KWARGS["library_name"]/["resource"]` 来匹配，这个会把职责搞混（也会逼着新增分支） ——规范里应该明确：**对外查询只用 LIB_ID，内部再由元数据决定 library_name。**

---

## 4. 详细功能点拆解（可一项一项实现的 Backlog）

我按“先能跑，再能扩”的顺序排，并给每项验收标准。

### Epic A：元数据关联（DB）

A1. `meta.get_by_lib_id(lib_id)`

* 验收：输入一个 LIB_ID，返回 library_name/lib_type/freq/index_cols/symbol_normalizer（字段可逐步补齐）。
  A2. 本地缓存（LRU/TTL）
* 验收：同一 lib_id 在 TTL 内不重复打 DB。

---

### Epic B：SDK 缓存读取（只读缓存先跑通）

B1. parquet 定位器（按规范拼路径）

* 表：按你们规范的 table_base_dir/table_name/年.parquet（或你们真实实现的月分区也行，接口不变）
* 因子库：factor_base_dir/月份/library_name.parquet 
* 验收：给 start/end 自动计算需要的分区文件列表。

B2. 跨分区拼接 + 去重排序

* 验收：跨月/跨年读取不漏不重；按 `(datetime,symbol)` 去重且排序。

B3. 标准化 pipeline

* rename（按元数据 default_index_cols）→ datetime parse → symbol normalize → 保留 datetime/symbol
* 验收：返回 DF 必含 `datetime/symbol`，且与存储规范一致。

B4. 字段裁剪（LIB_ID_FEILD）

* 验收：只返回指定列 + datetime/symbol；空则返回全量。

---

### Epic C：频率对齐（仅 1m/1d）

C1. `align_day_to_min(policy=broadcast/ffill)`

* 验收：分钟 DF 行数不变；日字段能正确注入到分钟轴。

C2. `align_min_to_day(policy=agg_last)`

* 验收：输出为日粒度；每个 (date,symbol) 一行；聚合结果与手工 groupby last 一致。

---

### Epic D：rayframe 适配（MIN_BASE 保持现有，新增“Configs 输入”）

D1. `Factor.load_inputs()`：读取 data_requirements

* 验收：因子无需手写取数；输入 dict key 与 data_requirements alias 一致。

D2. MIN_BASE / Factormin 区分

* MIN_BASE：仍走 rayframe 现有 `add_ori_min_data`（即 L3_MIN_DATA）
* Factormin：走 sdk.get(Configs(LIB_ID="Factormin"))（衍生分钟缓存）
* 验收：一个分钟因子可以同时拿到 MIN_BASE + Factormin，并在 calc 里做计算。

D3. 回退兼容（可选）：把旧 `depend_factor` 翻译成 Configs（仅 BasicDayFactor 类）

* 验收：旧因子不改代码也能跑，但新因子强制用 data_requirements。

---

### Epic E：因子代码助手接入（新增 rayframe code_mode）

你现在 codegen 的闭环入口是 `generate_factor_with_semantic_guard`（生成→静态检查→dryrun→agent语义检查），CodeMode 目前只有 pandas/l3_py/l3_cpp 。

E1. 新增 `CodeMode.RAYFRAME_PY = "rayframe_py"`

* 验收：前端/状态机能传入该 mode，后端能分流。

E2. rayframe 专用 Prompt / 模板

* 必须生成：

  * `class FactorXxx(Factor):`
  * `factor_type = "DAY"/"MIN"`
  * `data_requirements = {...Configs...}`
  * `def calc(self, factor_data, price_data, **custom_params): ...`
* 验收：生成代码可被 import，不包含直接取数。

E3. 静态语义检查（rayframe 版）

* 必须包含 `data_requirements` 与 `Configs(`；
* 必须实现 `calc`；
* 禁止出现直接数据源调用关键字（你们内部可列黑名单）。

> 你现在的静态检查只覆盖 L3_PY（FactorBase/def calculate/addFactorValue），rayframe 需要新增一套并行规则。

E4. dryrun（本地最小可运行）

* 方案：不跑真实数据，构造最小 df（含 datetime/symbol）调用一次 `calc`，确保逻辑可执行。
* 验收：dryrun_result 能返回 success/stdout/stderr（复用你现有 runner 输出结构）。

---

## 5. 你当前 configs.py 的“规范化改造”建议（与本方案一致）

你们现有 `config_list` 覆盖了大量库，并通过 `API_INDEX_COL` 把源字段映射到 `datetime/symbol`，这是好资产，应保留为“回源参数模板/本地开发默认配置”。

但必须修两点（写进规范）：

1. **get_library_config 的匹配方式要废弃**：现在按 `library_name/resource` 匹配，且写了 TODO 提醒会不断加分支。规范要求：对外只用 `LIB_ID`，内部依赖 DB 元数据决定 library_name/resource。
2. `Factormin` 的 `DataManager(API_TYPE='L3Factor', LIB_ID='Factormin', LIB_TYPE='factor', ...)` 应明确标注它是“衍生分钟缓存”，并在元数据里标 freq=1m、type=factor（Configs 不需要承载这类元语义）。

---

如果你愿意，我可以基于这份规范直接把 **“rayframe_py 静态语义检查规则（代码级）+ rayframe 因子模板”**也写出来（对应你们现有 `semantic.py/runner.py/view.py` 的接入点），让你们第一个任务就能在代码助手里“生成→静态过→dryrun 过”，然后再逐步把 SDK 真读缓存接上去。
