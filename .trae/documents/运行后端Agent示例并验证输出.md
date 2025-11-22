## 目标
- 启用 LangGraph 检查点记忆（按 thread_id 持久化），同线程可断点续跑。
- 当流程节点出错时，回退到上一个成功步骤的下一步，自动重入失败节点。
- 精简状态扩展：仅添加 `thread_id`（只读展示）、`run_id`（调用ID）、`last_success_node`（记录上次成功节点）。

## 技术改动
- `backend/graph/state.py`
  - 新增字段：`thread_id: Optional[str]`, `run_id: Optional[str]`, `last_success_node: Optional[str]`
- `backend/graph/graph.py`
  - 使用 `MemorySaver`（或 `SqliteSaver`）作为 `checkpointer`：`graph = build_graph().compile(checkpointer=MemorySaver())`
  - 在关键节点后插入错误路由：`error_resume_router` 判断异常，`resume_to_last` → `backtrack_dispatch`，`pass` → 原既有下一步
  - `backtrack_dispatch` 根据 `last_success_node` 返回下一步节点名（如 `collect_spec→gen_code_react`, `gen_code_react→dryrun`, `dryrun→semantic_check`, ...）
- `backend/graph/nodes.py`
  - 为关键节点（`collect_spec`, `gen_code_react`, `dryrun`, `semantic_check`, `human_review_gate`, `backfill_and_eval`, `write_db`）添加成功路径更新 `last_success_node`
  - 在 `dryrun` 检测 `factor_code` 中出现 `raise NotImplementedError` 时标记失败（不抛异常），以触发回退路由
  - 新增 `error_resume_router(state)`：根据 `dryrun_result.success` 等判断是否需要回退；新增 `backtrack_dispatch(state)`：根据 `last_success_node` 返回下一步节点
- `backend/app.py`
  - `/agent/run` 支持 `thread_id`（用于检查点）与生成 `run_id`（返回前端展示）
  - 调用：`graph.invoke(init_state, config={'configurable': {'thread_id': thread_id}})`，并把 `thread_id/run_id` 写入 `init_state`

## 验证
1. 启动服务，使用固定 `thread_id` 连续调用，观察状态是否续跑。
2. 使用未知因子描述触发 `dryrun` 失败，验证自动回退到上一个成功步骤并重入。
3. 正常因子描述（如“5日滚动均值因子”）应生成代码与 mock 指标，并返回 `db_write_status=success`。

## Implementation Checklist
1. 扩展 `FactorAgentState` 字段：`thread_id/run_id/last_success_node`
2. 在 `graph.py` 启用 `checkpointer` 并新增错误路由与回退派发
3. 在 `nodes.py` 更新各节点：成功写 `last_success_node`；`dryrun` 对未实现体设为失败
4. 在 `app.py` 接收传入/生成 `thread_id`，生成 `run_id`，并在 `invoke` 时传入 `configurable.thread_id`
5. 本地运行示例：成功路径与失败回退路径均验证通过