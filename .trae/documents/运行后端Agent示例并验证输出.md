## 风险与影响评估
- 安全风险：前端可控的 `thread_id` 可能导致会话串线或跨租户读取检查点；可预见性或被猜测引发会话劫持。
- 一致性风险：`state.thread_id` 与 `configurable.thread_id` 可能不一致，检查点读写发生错位，恢复到错误线程。
- 负载风险：把 `thread_id` 放入 `state_update` 会增加事件负载但一般可控；若状态体积过大需做精简。
- 并发风险：同一 `thread_id` 多客户端并发写导致检查点竞态；需要加锁或串行化。
- 可维护性风险：将 `thread_id` 参与业务分支可能导致逻辑耦合，应保持只读展示属性。

## 方案与约束
- 只读展示：将 `thread_id` 放入 `FactorAgentState` 仅用于前端展示与追踪，禁止参与任何分支判断。
- 权威标识：检查点与恢复仅使用 `configurable.thread_id`；每次 `invoke` 都以此为准来读写检查点。
- 校验与回填：请求处理阶段生成/校验 `thread_id`；若前端传入，需校验归属（鉴权）和存在；把该值写入 `init_state.thread_id` 供前端显示。
- 一致性守卫：调用前校验 `state.thread_id == configurable.thread_id`，不一致则以 `configurable.thread_id` 为准更新 `state.thread_id` 并记录告警。
- 持久化记忆：使用 `SqliteSaver(".cache/graph.sqlite")`（或 `MemorySaver` 开发态）作为 checkpointer，命名空间可加租户前缀避免冲突。
- 并发控制：对同一 `thread_id` 采用进程内锁或队列串行执行；至少在 FastAPI 层做互斥。
- 附加标识：为每次调用生成 `run_id`，以及 `checkpoint_seq` 或时间戳，帮助前端追踪调用时间线。

## 技术改动
1. `FactorAgentState` 增加只读元信息：`thread_id`, `run_id`, `checkpoint_seq`，并保留 `last_success_node`, `failed_node`, `node_error`。
2. `graph.compile(checkpointer=SqliteSaver(...))` 启用检查点。
3. `/agent/run` 接收或生成 `thread_id`，传入 `configurable.thread_id`；同时写入 `init_state.thread_id` 与 `run_id`。
4. 在节点成功时更新 `last_success_node`；失败写入 `node_error/failed_node`。
5. 新增 `error_resume_router` 与 `backtrack_dispatch`，在主链关键节点后添加条件边以实现回退到上一个成功节点。
6. 统一校验：在入口层或首节点，对 `state.thread_id` 与 `configurable.thread_id` 进行一致性校验与修复。
7. 并发与鉴权：为同 `thread_id` 加互斥；校验 `thread_id` 归属，拒绝跨用户使用。

## 示例与验证
- 启动服务后，使用固定 `thread_id` 连续两次调用，验证检查点记忆；
- 模拟节点抛错，观察是否自动回到 `last_success_node` 并继续运行；
- 前端通过 `state_update` 获取 `thread_id/run_id/checkpoint_seq` 展示会话与步骤时间线。
