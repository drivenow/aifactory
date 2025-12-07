# codegen 模块导航

本模块 (`backend/domain/codegen`) 提供了一套**自动化生成量化因子代码**的解决方案，支持从自然语言描述或已有代码转换为标准的 Python / C++ L3 因子实现。

## 1. 核心语义与设计意图

本模块主要服务于以下场景：
- **AI 辅助编程**：将自然语言需求转化为可执行的因子代码。
- **跨语言转写**：将 Python 因子原型转写为高性能 C++ 生产代码。
- **质量守护**：通过静态分析、Mock 运行和 Agent 自查，确保生成代码的语法正确性和逻辑合理性。

## 2. 目录结构与关键文件

### 2.1 核心流程
- **`generator.py`** (Entry Point):
  - 核心入口 `generate_factor_code_from_spec`。
  - 编排 "生成 -> 静态检查 -> Dryrun -> Agent 语义检查" 的完整闭环。
- **`view.py`** (Data Model):
  - 定义 `CodeGenView` 和 `FactorAgentState`，统一输入输出契约。
  - 管理 `code_mode` (L3_PY / L3_CPP / PANDAS) 和各阶段的检查结果。
- **`runner.py`** (Execution):
  - `run_factor`: 执行因子的 Mock 运行（Python）或返回环境提示（C++）。
  - 负责捕获 stdout/stderr 并截断过长输出，防止上下文溢出。
- **`semantic.py`** (Validation):
  - `check_semantics_static`: 快速静态检查（如是否继承 `FactorBase`、是否实现 `calculate`）。
  - `check_semantics_agent`: 调用 LLM 进行更深层的逻辑和异常分析。

### 2.2 Agent 与 Prompt
- **`agent_with_prompt/`**:
  - `agent_factor_l3_py.py`: Python L3 因子生成 Agent。
  - `agent_factor_l3_cpp.py`: C++ L3 因子生成 Agent。
  - `agent_semantic_check.py`: 语义校验 Agent。
  - **设计原则**：Prompt 作为“一等公民”管理，核心规则与 Few-Shot 样例分离。

### 2.3 基础设施 (Framework)
- **`framework/`**:
  - `factor_l3_py_standard.py` / `factor_l3_cpp_standard.py`: 定义标准 Prompt 模板、规则和 Demo。
  - `py_nonfactor/` & `cpp_nonfactor/`: 存放 NonFactor（基础数据聚合算子）的元数据和源码，供 Agent 参考以生成正确的依赖调用。
  - `factor_mock_tool.py`: 提供本地 Mock 运行环境和简单的 Pandas 模板渲染。

### 2.4 批处理工具 (Scripts)
- **`scripts/`**:
  - `batch_py_to_cpp.py`: 批量将 Python 因子转写为 C++。
  - `batch_json_to_py.py`: 批量从 JSON 描述生成 Python 因子。

---

## 3. 使用指南

### 3.1 Python L3 因子生成
适用于快速原型开发和验证。

```python
from domain.codegen.generator import generate_factor_code_from_spec
from domain.codegen.view import CodeMode

state = {
    "factor_name": "FactorBuyWillingByPrice",
    "user_spec": "用1秒成交聚合计算买卖意愿",
    "code_mode": CodeMode.L3_PY,
}

# 生成代码（包含自动修正流程）
code = generate_factor_code_from_spec(state)
print(code)
```
**预期输出**：继承 `FactorBase` 的 Python 类，自动注入 `FactorSecTradeAgg` 等 NonFactor 依赖。

### 3.2 C++ L3 因子生成
适用于生产环境部署。

```python
state = {
    "factor_name": "FactorBuyWillingByPrice",
    "user_spec": "用1秒成交聚合计算买卖意愿",
    # 可选：提供 Python 代码作为参考上下文
    "factor_code": python_code_str,
    "code_mode": CodeMode.L3_CPP,
}

code = generate_factor_code_from_spec(state)
```
**预期输出**：包含 `struct Param` 定义、继承 `Factor<Param>` 的 C++ 类，使用 `SlidingWindow` 和 `compute::` 算子。

### 3.3 批量转写脚本

**Python 转 C++**:
```bash
python -m backend.domain.codegen.scripts.batch_py_to_cpp \
  --src /path/to/py_factors \
  --out /path/to/output_cpp \
  --overwrite
```

**JSON 转 Python**:
```bash
python -m backend.domain.codegen.scripts.batch_json_to_py \
  --json /path/to/factors.json \
  --out /path/to/output_py
```

## 4. 扩展与维护

- **新增 NonFactor**:
  - 在 `framework/py_nonfactor` 或 `framework/cpp_nonfactor` 添加对应的元数据/源码文件。
  - 更新 `standard.py` 中的引用，使 Agent 能感知新能力。
- **调整 Prompt**:
  - 修改 `agent_with_prompt/` 下对应 Agent 的 System Prompt。
  - 遵循“开闭原则”：核心规则保持稳定，针对新场景通过 Few-Shot 或特定指令扩展。
