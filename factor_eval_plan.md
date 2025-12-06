# 因子评价模块落地计划（基于现有实现）

现有能力：`backend/graph/domain/factor_eval/src/factor_eval.py` 已包含完整的评价函数（`FactorEvaluatorBase`/`FactorEvaluatorMulti`、`evaluate_factor_multiday`、`evaluate_factor_multisymbol` 等），`README.md` 也给了数据/代码两种使用路径，且有 `factoreval.py`/`factorevaldata.py` 辅助脚本。目标是最小改造，把现成能力接入 LangGraph Agent，统一对外入口与状态读写，不额外设计复杂工具链。

## 1. 目录与接口梳理
- 继续使用现有目录：`backend/graph/domain/factor_eval/`，保留 `src/factor_eval.py` 作为核心实现。
- 补充一个轻量入口模块（如 `backend/graph/domain/factor_eval/__init__.py` 或 `runner.py`），封装两个出口：
  - `run_factor_eval(state)`：读取 `FactorAgentState` 中的 `factor_name、`factor_code`、 等，`symbols`、`dates`写死为固定的配置，调用 `evaluate_factor_multisymbol`/`FactorEvaluatorMulti.get_eval_info`，返回 `res_l2` 和 `res_l1`(`res_l3`数据量太大，不写入)，存入到FactorAgentState的eval_metrics。
  - `save_eval_result(result, save_path)`：薄封装现有的 `pickle`/`csv` 保存逻辑，路径可配置。
- 保留原脚本 `factoreval.py`/`factorevaldata.py` 供批量离线使用。

## 2. 接入 LangGraph 的最小改动
- 在 `backend/graph/domain/eval.py` 中，新增一个开关（如 `USE_NEW_EVAL=True`），默认走新入口 `factor_eval.run_factor_eval`，回填 `state.eval_metrics`：
  - `eval_metrics["l2"]`：因子-标的层结果（`res_l2`）。
  - `eval_metrics["l3"]`：因子-标的-日期明细（`res_l3`，可选）。
  - `eval_metrics["summary"]`：因子层汇总（`res_l1`）。
- 保留 `mock_evals` 作为兜底（例如当数据缺失或配置关闭时）。
- 不引入新的 LangChain Tool；仅将结果写回 state，方便前端展示/存档。

## 3. 兼容性与配置
- 参数来源：设置固定的 中读取 `symbols`、`dates`、；缺省时做合理默认或报错。
- 并发：不用额外实现，秩序调用现有的实现代码即可。
- 日志/错误：沿用现有打印，可在入口处包装 try/except，将错误写入 `state.error`。

## 4. 交付物
- 新的轻量入口文件（`__init__.py` 或 `runner.py`）+ `eval.py` 路由改造。
- 文档更新：在 `backend/graph/domain/factor_eval/README.md` 补充“在 Agent/Graph 中如何调用”的示例。
- 简单回归：准备一份小样本 parquet/csv，验证 `run_factor_eval` 能产出 `res_l1`/`res_l2` 并写回 state。

这样即可复用现有评价函数，快速接入 Agent 流程，无需额外的复杂工具提示或新设计。
