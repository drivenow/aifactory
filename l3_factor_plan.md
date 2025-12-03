好，那我们现在来“重置版”设计一次，把前面踩过的坑都纳进去，做一份真正能一路演进的开发方案 👇

---

## 0. 目标 & 约束（统一一下）

**目标：**

* 支持两种代码生成模式：

  * `pandas`：现有 MVP 模板，主要是玩具/本地验证；
  * `l3_py`：真实 L3FactorFramework（`FactorBase` + `calculate`，依赖 nonfactor）。
* 在 `l3_py` 下：

  * 因子**优先依赖 nonfactor**（`FactorSecTradeAgg`、`FactorSecOrderBook`、`FactorSecOrderAgg` 等），而非直接操作逐笔；
  * Agent 能：

    1. 看 nonfactor 的结构化 metadata + 源码；
    2. 必要时查看历史因子实现；
    3. 写出合规的 `class FactorXxx(FactorBase)` 代码；
    4. 用工具自检（语法 + mock 运行）；
  * 外层仍由 LangGraph 负责重试 & human-in-loop。

**约束：**

* 不抽象统一模板层（暂时保持简单），不同模式在 `domain/code_gen.py` 内分发。
* 不侵入非因子实现文件，只用读取 + metadata 描述。
* 所有执行用 `exec` 的地方都在受限 stub 环境里，不接触真实 DB / 框架。

---

## 1. 核心数据结构设计

### 1.1 代码模式 & state 视图

```python
# 代码模式
class CodeMode(str, Enum):
    PANDAS = "pandas"
    L3_PY = "l3_py"
```

```python
# check_semantics 结果
class SemanticCheckResult(BaseModel):
    passed: bool = True                # 语义检查是否通过
    reason: List[str] = []             # 不通过的原因列表（用户可见）
    last_error: str = ""               # 上一轮 run_factor_dryrun/语义失败摘要（截断后的字符串）
```

```python
# run_factor_dryrun 结果（两种模式共用）
class DryrunResult(BaseModel):
    success: bool                      # 运行是否成功（语法+运行层面）
    traceback: Optional[str] = None    # 错误堆栈（截断前）
    result_preview: Optional[Any] = None  # 可选：比如 mock_run 的 _values/输出摘要
```

```python
# 视图（从 FactorAgentState 派生）
class CodeGenView(ViewBase):
    user_spec: str = ""
    factor_name: str = "factor"
    factor_code: str = ""              # 当前生成的代码全文
    code_mode: CodeMode = CodeMode.PANDAS
    dryrun_result: DryrunResult = DryrunResult(success=True)
    check_semantics: SemanticCheckResult = SemanticCheckResult()
```

> `FactorAgentState` 就继续用你现在的 dict 结构，只要保证这几个 key 被读写即可。

---

### 1.2 nonfactor 元信息（结构化 + 源码）

我们设计一个 metadata schema，让 Agent 不仅看源码，还看到结构化字段信息。

```json
NONFACTOR_META = {
    "FactorSecTradeAgg": {
        "desc": "1秒成交聚合",
        "fields": {
            "trade_buy_money_list": "过去每秒买成交金额，单位：...",
            "trade_sell_money_list": "...",
            "trade_buy_num_list": "...",
        },
    }
}
```

工具 `nonfactor_source` 的返回结构：

```json
{
  "ok": true,
  "source": "<源码字符串>",
  "meta": { ...上面这些结构化字段... }
}
```

---

### 1.3 L3 stub 运行场景（mock_run 用）

第一版我们可以只支持一个默认场景，先不对外暴露这个结构。

---

## 2. 模块划分与职责

### 2.1 tools 层

#### 2.1.1 `codebase_fs_tools.py`（文件系统工具）

**职责：**

* 提供受限的 repo 文件读取 & 目录列举；
* 被 `nonfactor_info` / Agent 直接调用。

**主要内容：**

* `SafeFileSystem`：

  * 字段：`project_root: Path`
  * 方法：

    * `_resolve_safe_path(file_path: str) -> Path`
    * `read_file_content(file_path: str) -> dict`
    * `list_directory_contents(dir_path: str) -> dict`
* LangChain tools：

  * `@tool("read_repo_file")`
  * `@tool("list_repo_dir")`

#### 2.1.2 `nonfactor_info.py`（nonfactor 信息工具）

**职责：**

* 维护 nonfactor 名称 → 文件路径 → metadata 映射；
* 提供 nonfactor 列表、源码+meta 给 Agent。

**主要内容：**

* 静态映射：

```python
NONFACTOR_PATHS = {
    "FactorSecOrderBook": "factors/l3/FactorSecOrderBook.py",
    "FactorSecTradeAgg": "factors/l3/FactorSecTradeAgg.py",
    "FactorSecOrderAgg": "factors/l3/FactorSecOrderAgg.py",
}
NONFACTOR_META = {
    "FactorSecTradeAgg": NonfactorMeta(...),
    ...
}
```

* tools：

  * `@tool("nonfactor_list") -> {factors: [ {name, desc, sample_rate}, ... ]}`
  * `@tool("nonfactor_source")(name: str) -> NonfactorSourceResult.dict()`

    * 内部：用 `SafeFileSystem.read_file_content(path)` 读源码，+ `NONFACTOR_META[name]`。

#### 2.1.3 `l3_factor_tool.py`（L3 语法 + stub 运行）

**职责：**

* 对 L3 因子代码做语法与结构检查；
* 在简化 stub 环境中执行 `calculate`，确认可运行。

**主要内容：**

* `_syntax_check(code: str) -> dict`：

  * `ast.parse`；
  * 检查至少有一个 `class Xxx(FactorBase)`；
  * 该类有 `def calculate(self)` 方法；
* `L3_FACTORBASE_STUB`：

  * 简单 FactorBase：

    * `__init__` 初始化 `_values`；
    * `addFactorValue` 追加；
    * 若需要可加空实现的 `getPrev*`。
* `_mock_run(code: str, scenario: Optional[L3MockScenario]) -> dict`：

  * 构造 ns；
  * `exec(L3_FACTORBASE_STUB, ns, ns)`；
  * 可注入 `nonfactor_stub`（简单对象，带几个 list 属性），以后再扩；
  * `exec(code, ns, ns)`；
  * 找 `FactorBase` 子类，实例化，`calculate()`；
  * 把 `_values` 作为 result 返回。
* tools：

  * `@tool("l3_syntax_check")(code: str) -> {"ok", "error"}`
  * `@tool("l3_mock_run")(code: str) -> {"ok", "error", "result"}`

> 注意：stub 内**不注入真实 L3 框架**，避免安全问题。

---

### 2.2 prompts 层

文件：`backend/graph/prompts/factor_l3_py.py`

**职责：** 提供 L3 因子 codegen 的 System Prompt。

**关键点：**

* 约束 FactorBase 规范（类名、继承、`__init__`、`calculate`、`addFactorValue`、禁 IO）。
* 强调：

  1. 必须先通过工具了解 nonfactor：

     * `nonfactor_list` 选候选；
     * `nonfactor_source` 获取 meta + 源码。

     Prompt 里明确说：字段名 / 语义以 meta 为准，源码只是辅助了解实现细节。
  2. 可以用：

     * `read_repo_file` / `list_repo_dir` 查阅历史因子样例；
  3. 写完后必须用：

     * 至少一个 `l3_syntax_check` 或 `l3_mock_run` 自检；
  4. 最终只输出完整 Python 代码（无 ```，无解释）。
  5. “如果 l3_mock_run 返回失败，就在 check_semantics.last_error 里写清错误，再走一轮 codegen”，
让模型在实践中“学会”必须用工具。
---

### 2.3 domain 层：`code_gen.py`

**职责：**

* 根据 state（spec + mode + check_semantics）调合适的 codegen 流程；
* 为 nodes 提供稳定 API。


#### 2.3.1 构建 L3 ReAct Agent

```python
_L3_AGENT = None

def _build_l3_codegen_agent():
    global _L3_AGENT
    if _L3_AGENT is not None:
        return _L3_AGENT

    llm = get_llm()
    if not llm:
        _L3_AGENT = None
        return None

    tools = [
        nonfactor_list,
        nonfactor_source,
        read_repo_file,
        list_repo_dir,
        l3_syntax_check,
        l3_mock_run,
    ]
    _L3_AGENT = create_react_agent(llm, tools=tools)
    return _L3_AGENT
```

#### 2.3.2 L3 代码生成逻辑

````python
def _generate_l3_factor_code(view: CodeGenView) -> str:
    agent = _build_l3_codegen_agent()
    if agent is None:
        return "# TODO: L3 codegen fallback (LLM unavailable)\n"

    last_error = _truncate(view.check_semantics.last_error)

    sys = SystemMessage(content=PROMPT_FACTOR_L3_PY)
    user_content = (
        f"因子类名: {view.factor_name}\n"
        f"因子需求描述: {view.user_spec}\n"
    )
    if last_error:
        user_content += f"\n[上一轮错误摘要]\n{last_error}\n"

    user = HumanMessage(content=user_content)
    result_state = agent.invoke({"messages": [sys, user]})
    # 提取最后的 assistant 内容，strip ```, 返回代码
````

#### 2.3.3 总入口：`generate_factor_code_from_spec`

```python
def generate_factor_code_from_spec(state: FactorAgentState) -> str:
    view = CodeGenView.from_state(state)

    if view.code_mode == CodeMode.L3_PY:
        code = _generate_l3_factor_code(view)
    else:
        # 保留原有 pandas 模板行为
        body = simple_factor_body_from_spec(view.user_spec)
        code = render_factor_code(view.factor_name, view.user_spec, body)

    return code
```

---

### 2.4 nodes 层：`nodes.py`

#### 2.4.1 `run_factor_dryrun`

```python
def run_factor_dryrun(state: FactorAgentState) -> Dict[str, Any]:
    view = CodeGenView.from_state(state)

    if view.code_mode == CodeMode.L3_PY:
        # 直接用 l3_mock_run 做 stub 运行
        res = l3_mock_run.invoke({"code": view.factor_code})
        dry = DryrunResult(
            success=bool(res.get("ok")),
            traceback=res.get("error"),
            result_preview=res.get("result"),
        )
        state["dryrun_result"] = dry.dict()

        # 失败时更新 check_semantics.last_error（截断）
        semantic = view.check_semantics
        if not dry.success:
            semantic.last_error = _truncate(dry.traceback or "")
        state["check_semantics"] = semantic.dict()
        return dry.dict()

    # pandas 模式保持现有行为
    result = run_code(
        view.factor_code,
        entry="run_factor",
        args={"args": ["2020-01-01", "2020-01-10", ["A"]], "kwargs": {}},
    )
    state["dryrun_result"] = result
    # 可选：同步错误到 check_semantics.last_error
    return result
```

#### 2.4.2 `check_semantics` 节点

```python
def check_semantics(state: FactorAgentState) -> FactorAgentState:
    view = CodeGenView.from_state(state)
    code = view.factor_code
    semantic = view.check_semantics

    if view.code_mode == CodeMode.L3_PY:
        reasons = []

        if "FactorBase" not in code:
            reasons.append("未继承 FactorBase。")
        if "def calculate" not in code:
            reasons.append("未定义 calculate 方法。")
        if "addFactorValue" not in code:
            reasons.append("未调用 addFactorValue 写回因子值。")

        if reasons:
            semantic.passed = False
            semantic.reason = reasons
            if not semantic.last_error:
                semantic.last_error = "; ".join(reasons)
        else:
            semantic.passed = True
            semantic.reason = []
            # last_error 保留给下一轮（run_factor_dryrun）使用，或者清空均可

        state["check_semantics"] = semantic.dict()
        return state

    # pandas：默认通过 / 简单关键字检查
    semantic.passed = True
    semantic.reason = []
    state["check_semantics"] = semantic.dict()
    return state
```

外层 `_route_retry_or_human_review` 保持现状：只看 `check_semantics.passed` / `dryrun_result.success` 与 retry_count 决定走重试还是 HITL。

---

## 3. 实现路线图（可以一步一步来）

### Phase 1：基础 data structure & L3 tools（1 天）

1. 在 `domain/code_gen.py` 中引入 `CodeMode`、`CodeGenView`、`SemanticCheckResult`、`DryrunResult`。
2. 新建 `tools/codebase_fs_tools.py`，跑简单单测证明 `read_repo_file` 和 `list_repo_dir` 正常工作。
3. 新建 `tools/nonfactor_info.py`，填入 `NONFACTOR_PATHS` + 最简 `NONFACTOR_META`（先只写 3–5 个字段）。
4. 新建 `tools/l3_factor_tool.py`，实现 `_syntax_check` + `_mock_run` + `l3_syntax_check`/`l3_mock_run`。

### Phase 2：L3 Agent 接入（1 天）

1. 更新 `prompts/factor_l3_py.py`，加入 nonfactor 使用规范 + 工具使用 + 输出要求。
2. 在 `domain/code_gen.py` 中实现 `_build_l3_codegen_agent` + `_generate_l3_factor_code`。
3. 在 `generate_factor_code_from_spec` 中按 `code_mode` 分发。

### Phase 3：run_factor_dryrun & check_semantics 适配（0.5–1 天）

1. 更新 `nodes.run_factor_dryrun`，实现 L3 分支使用 `l3_mock_run`。
2. 更新 `nodes.check_semantics`，实现 L3 规则检查 & last_error 维护。
3. 保证 `_route_retry_or_human_review` 不需要改，只要 state 结构匹配即可。

### Phase 4：回归 & L3 smoke 测试（0.5 天）

1. 写一个 L3 测试 state：

   * `code_mode="l3_py"`
   * `factor_name="FactorBuyWillingByPriceV2"`
   * `user_spec` 描述“基于 FactorSecTradeAgg，计算买卖意愿”等。
2. 跑一遍完整 LangGraph 流程：

   * 期望：`factor_code` 非空、run_factor_dryrun success、check_semantics passed。
3. 再跑一遍 pandas 路径，验证兼容性。

### Phase 5（可选）：强化 nonfactor metadata & mock scenarios（1–2 天）

* 为每个 nonfactor 完善Json，标出关键字段含义、单位等；
* 给 `_mock_run` 增加一个简单 nonfactor stub，以便捕获字段名错误；
* 在 prompt 中明确要求字段名以 meta 为准。

---


