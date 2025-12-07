# codegen 模块导航

- `view.py`：把 `FactorAgentState` 规整成 `CodeGenView`，统一字段、默认值、容错（含 `code_mode`）。
- `generator.py`：按 `code_mode` 生成代码；Pandas 用模板渲染，L3 Python/C++ 调用各自 agent。
- `agent.py`：L3 因子代码生成 agent，Python/C++ 共用；注入对应 nonfactor 提示。
- `tools/`：L3 专用工具（语法检查、mock 运行、nonfactor 元数据），含 py/cpp nonfactor 描述与源码聚合。
- `runner.py`：运行或 mock 运行因子，保证输出字段一致（C++ 模式仅提示暂不支持本地运行）。
- `validator.py`：语义检查/结果标准化，输出布尔 + detail。
- `scripts/`：批量脚本，如 `batch_py_to_cpp.py`（遍历因子代码转 C++）、`batch_json_to_py.py`（JSON 描述批量生 Python 因子）。

调用顺序建议：collect_spec → generator.generate_factor_code_from_spec → runner.run_factor → validator.check_semantics_static（失败态附带 reason/last_error）。替换某一环时，只要保持输入输出契约即可。

## 用法速览

- **Python L3 因子生成**
  - 设置 `CodeGenView.code_mode = CodeMode.L3_PY`，提供 `factor_name`、`user_spec`（可选 `factor_code` 作为修正上下文）。
  - 调用 `generator.generate_factor_code_from_spec(state)` 返回 Python L3 因子源码；内部注入 Python nonfactor 字段/源码提示，使用 LangChain Agent 生成。
  - 可用 `runner.run_factor(state)` 在 stub L3 环境 mock 运行；`validator.check_semantics_static(state)` 做语义校验。
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

- **Pandas 模式（MOCK）**
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

- **批量 Python→C++ 转换脚本**
  - 位置：`backend/domain/codegen/scripts/batch_py_to_cpp.py`
  - 用途：遍历指定目录下的 `.py` 因子文件，推断类名（`class Xxx(FactorBase)`），将代码作为上下文交给 C++ agent 生成对应 C++ 源码，并写入输出目录。
  - 使用示例：
    ```bash
    python -m backend.graph.domain.codegen.scripts.batch_py_to_cpp \
      --src /path/to/py_factors \
      --out /path/to/output_cpp \
      --overwrite  # 可选，存在同名文件时覆盖
    ```
  - 输出：按因子名生成 `FactorName.cpp` 文件；若 agent 未配置会返回占位 C++ 代码，需在 SDK 环境验证。

- **批量 JSON → Python 因子生成脚本**
  - 位置：`backend/domain/codegen/scripts/batch_json_to_py.py`
  - 用途：读取 JSON 中的因子描述，批量生成 Python L3 因子代码。
  - JSON 格式示例（数组或包含 `items` 数组）：
    ```json
    [
      {"factor_name": "FactorAlpha1", "user_spec": "买卖金额差/和归一化"},
      {"name": "FactorAlpha2", "desc": "5秒内涨幅均值", "factor_code": ""}  // 可选附带已有代码
    ]
    ```
  - 使用示例：
    ```bash
    python -m backend.graph.domain.codegen.scripts.batch_json_to_py \
      --json /path/to/factors.json \
      --out /path/to/output_py \
      --overwrite  # 可选，存在同名文件时覆盖
    ```
  - 输出：按因子名生成 `FactorName.py` 文件（继承 `FactorBase` 的 L3 因子），可配合 `runner.run_factor` 做 stub mock 运行。
