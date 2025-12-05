# codegen 模块导航

- `view.py`：把 `FactorAgentState` 规整成 `CodeGenView`，统一字段、默认值、容错。
- `generator.py`：按 `code_mode` 生成代码；Pandas 用模板渲染，L3 Python/C++ 调用各自 agent。
- Agent 现位于 `backend/graph/agent.py`，可被各 domain 复用；必要时可替换为自定义实现。
- `tools/`：L3 专用工具（语法检查、mock 运行、nonfactor 元数据）。
- `runner.py`：运行或 mock 运行因子，保证输出字段一致（C++ 模式仅提示暂不支持本地运行）。
- `validator.py`：语义检查/结果标准化，输出布尔 + detail。

调用顺序建议：collect_spec → generator.generate_factor_code_from_spec → runner.run_factor → validator.is_semantic_check_ok（失败态附带 reason/last_error）。替换某一环时，只要保持输入输出契约即可。

## 用法速览

- **Python L3 因子生成**
  - 设置 `CodeGenView.code_mode = CodeMode.L3_PY`，提供 `factor_name`、`user_spec`（可选 `factor_code` 作为修正上下文）。
  - 调用 `generator.generate_factor_code_from_spec(state)` 返回 Python L3 因子源码；内部注入 Python nonfactor 字段/源码提示，使用 LangChain Agent 生成。
  - 可用 `runner.run_factor(state)` 在 stub L3 环境 mock 运行；`validator.is_semantic_check_ok(state)` 做语义校验。
  - 示例输入：
    ```python
    state = {
        "factor_name": "FactorBuyWillingByPrice",
        "user_spec": "用1秒成交聚合计算买卖意愿",
        "code_mode": CodeMode.L3_PY,
    }
    code = generate_factor_code_from_spec(state)
    ```
    预期输出：返回一段继承 `FactorBase`、在 `calculate` 中读取 `FactorSecTradeAgg` 字段并 `addFactorValue` 的 Python 代码字符串。

- **C++ L3 因子生成**
  - 设置 `CodeGenView.code_mode = CodeMode.L3_CPP`，同样传入 `factor_name`、`user_spec`（或 `factor_code` 追加上下文）。
  - 调用 `generator.generate_factor_code_from_spec(state)` 返回 C++ 因子源码；提示词会注入 C++ nonfactor 字段/头文件摘要。
  - 本地 runner 暂不支持 C++ 编译运行，需在 SDK 环境落地测试。
  - 示例输入：
    ```python
    factor_code = "FactorBuyWillingByPrice的python代码"
    state = {
        "factor_name": "FactorBuyWillingByPrice",
        "user_spec": "用1秒成交聚合计算买卖意愿",
        "code_mode": CodeMode.L3_CPP,
        "factor_code": factor_code,
    }
    code = generate_factor_code_from_spec(state)
    ```
    预期输出：返回包含 `struct FactorBuyWillingByPriceParam`、`class FactorBuyWillingByPrice : public Factor<...>`，在 `on_init` 获取 `FactorSecTradeAgg`，`calculate` 中使用 `compute`/`SlidingWindow` 的 C++ 源码字符串。

- **Pandas 模式（演示）**
  - 设置 `code_mode = CodeMode.PANDAS`，调用 `generate_factor_code_from_spec`，使用模板+简单规则生成 Pandas 因子主体。
  - 示例输入：
    ```python
    state = {
        "factor_name": "DemoFactor",
        "user_spec": "5日均线",
        "code_mode": CodeMode.PANDAS,
    }
    code = generate_factor_code_from_spec(state)
    ```
    预期输出：返回一个带 `compute_factor` 的 Pandas 模板字符串，包含 rolling mean 逻辑。
