# evaluate 模块导航

本模块负责对生成的因子进行性能评估，支持多种评价后端（Mock, L3 Factor Eval 等）。

## 目录结构

- `runner.py`：模块统一入口。
  - `compute_eval_metrics(state)`：根据 `eval_type` ("l3", "mock", "alpha") 路由到不同的评价工具。
  - `write_factor_and_metrics(state)`：负责将评价结果持久化（当前仅支持 mock 写入）。
- `view.py`：定义数据视图 `EvalView`，用于解析 `FactorAgentState`。
- `tools/`：具体的评价工具集。
  - `l3_factor_evals.py`：L3 因子评价工具适配器。封装了 `run_factor_eval` 和 `l3_factor_eval_tool`，对接 `factor_eval` 核心逻辑。
  - `mock_evals.py`：模拟评价工具。提供 IC、换手率等指标的伪造数据，用于测试和兜底。
  - `factor_eval/`：**L3 因子评价核心逻辑实现目录**。
    - `FactorEvaluate.py`：包含 `Factor_with_code` 和 `Factor_with_data` 类，负责实际的计算逻辑（依赖 `polars`, `ray`, `FactorLib` 等）。

## 模块职责说明

- **输入**：`FactorAgentState`，包含因子名称、类型、代码或数据路径、评价配置等信息。
- **输出**：`eval_metrics`，包含评价报告路径、关键指标（IC, Turnover 等）。
- **扩展性**：通过 `eval_type` 字段支持多种评价后端：
  - `"mock"` (默认): 返回模拟数据，无需真实环境。
  - `"l3"`: 调用 L3 平台的真实评价流程（支持代码生成数据或直接使用数据）。
  - `"alpha"`: (预留) Alpha 因子评价，目前回退到 mock。

## 用法示例

### 1. Mock 评价（默认）

当 `eval_type` 未指定、为 "mock" 或为 "alpha" (暂未实现) 时，返回模拟数据。

```python
from domain.evaluate.runner import compute_eval_metrics

state = {
    "factor_name": "TestFactor",
    "eval_type": "mock"  # 或 "alpha"
}
metrics = compute_eval_metrics(state)
# metrics -> {"ic": {...}, "turnover": {...}, "group_perf": [...]}
```

### 2. L3 因子评价

设置 `eval_type="l3"`，并提供必要的配置（如 `factor_list`, `eval_mode`）。

**Code Mode (运行因子代码生成数据):**

```python
state = {
    "factor_name": "FactorOBIC",
    "eval_type": "l3",
    "eval_mode": "code",
    "num_cpus": 20,
    # 可选配置
    # "base_path": "...",
    # "factor_list": {...}
}
metrics = compute_eval_metrics(state)
# metrics -> {"result_path": "...", "corr_path": "..."}
```

**Data Mode (使用已有数据):**

```python
state = {
    "eval_type": "l3",
    "eval_mode": "data",
    "data_path": "/path/to/factor/data.parquet",
    "num_cpus": 20
}
metrics = compute_eval_metrics(state)
```

### 3. 工具调用

可以直接作为 LangChain 工具使用 `l3_factor_eval_tool`：

```python
from domain.evaluate.tools.l3_factor_evals import l3_factor_eval_tool

result = l3_factor_eval_tool(
    factor_list={"FactorOBIC": [{}]},
    eval_mode="code"
)
```
