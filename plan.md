# MVP 现状对齐与修订计划

## 当前实现（代码基线）
- **LangGraph 路由**：StateGraph + MemorySaver；入口 `collect_spec_from_messages → gen_code_react → dryrun → semantic_check → human_review_gate → backfill_and_eval → write_db → finish`。路由依赖 `route` 字段 + conditional edges，`finish→END` 静态边，HITL 节点用 `Command` 中断恢复。
- **重试/HITL**：`RETRY_MAX=3`；`_route_retry_or_hitl` 控制重试计数，`human_review_status=="edit"` 时失败直接回人审；`human_review_gate` 支持 `approve→backfill_and_eval`，`edit→dryrun`，`review→gen_code_react`，`reject→finish`，中断 payload 为 `{type:"code_review", actions: HumanReviewStatus}`。
- **State 形态**：`FactorAgentState` 为 TypedDict 聚合（非 MessagesState），含 `messages/route/retry_count/factor_code/dryrun_result/semantic_check/human_review_status/ui_request/ui_response/eval_metrics/db_write_status` 等；`should_interrupt` 默认 True 但未用于路由；无 artifacts/overwrite_fields/短摘要实现。
- **代码生成**：`generate_factor_code_from_spec` 仅在有 LLM 时调用 `create_react_agent`（工具：`render_factor`/`propose_body`/`dryrun_code`），输出通过正则提取代码块；无 LLM 时回落 `simple_factor_body_from_spec` + 模板渲染。模板 `load_data` 返回静态 DataFrame。
- **试跑/沙盒**：`run_code` 直接 `exec`，开放 `pandas/numpy/os/__builtins__`，无 AST 过滤、时间/资源/网络限制；`dryrun` 使用固定入参调用 `run_factor`。
- **语义检查**：`is_semantic_check_ok` 仅返回 `state.semantic_check`，默认通过，无实际校验。
- **评估/入库**：`backfill_and_eval` 调用 `mock_evals` 产出 ic/turnover/group_perf；`write_db` 调 `mock_evals.write_factor_and_metrics_mock`，未接入 agentevals 数据集或 CI 门槛。
- **协议/前端**：当前仅编译 graph；未接入 ag-ui-langgraph/FastAPI SSE，CopilotKit 侧未落地；HITL 事件未对齐 AG-UI 标准。
- **测试**：`backend/tests/test_codegen_agent.py` 验证模板/回落生成与 dryrun；`backend/tests/test_graph_flow.py` 走完 approve 流程，确保 dryrun 成功、产生 eval_metrics 和 db_write_status。

## 与原计划的差异/风险
- 沙盒安全、AST 白名单、禁网/禁写与资源配额缺失，`exec` 暴露 `os` 等高风险。
- 语义一致性检查缺位，retry 仅由 dryrun/异常驱动，难以捕捉逻辑偏差。
- AG-UI/ai-ui-langgraph、FastAPI SSE 暴露、CopilotKit 映射未集成，HITL 事件格式与标准协议未对齐。


## 修订后的行动计划（按优先级推进）
3) **模板与沙盒安全**：收紧 `sandbox_runner`（AST 白名单、禁网/禁写、时间/内存限制），丰富模板（数据约定、缩进修复），确保 dryrun 可复现又安全。
4) **语义检查与重试链路**：实现 `semantic_check`（LLM 或规则 diff），将失败纳入重试；若超过上限或人审编辑后失败，统一落入 HITL。
5) **HITL & AG-UI 集成**：为 `human_review_gate` 产出 AG-UI 兼容事件，接入 ag-ui-langgraph + FastAPI SSE；前端 CopilotKit 消费事件并支持 `ui_request/ui_response`。
8) **Prompt 与工具一致性**：更新 prompt 与工具说明以匹配当前模板/安全约束，确保 create_react_agent 工具链稳健；必要时增加 mock data loader 与 artifacts 输出。
