# 因子编码助手 (MVP)

本项目通过 LangGraph 构建量化研究领域的选股因子编码助手，并使用 CopilotKit 在前端进行事件流展示与人审 (Human-in-the-loop, HIL) 交互。后端提供符合 AG-UI 协议的 `/agent` SSE 端点，前端以 `CopilotKit Provider` 顶层包裹，`useCopilotAgent` 读取 `state/events/status`，并通过 `agent.humanFeedback(...)` 将人审结果回传以继续编排流程。

## 项目背景

*   **目标**：加速量化因子从“自然语言描述 → 模版代码 → 试运行与语义检查 → 人审 → 历史回填与评价 → 入库”的完整链路。
*   **技术栈**：
    *   **后端**：FastAPI + LangGraph (状态图、SSE 输出)，AG-UI 兼容端点
    *   **前端**：Next.js + CopilotKit (runtime + react-ui)，事件流追踪、指标面板、人审编辑面板
    *   **评估**：`compute_eval_metrics`（默认 mock，占位；`eval_type="l3"` 可调用高频因子评价，依赖 ray/polars/FactorLib）
*   **核心流程**：
    1.  读取用户描述，按因子模板生成代码 (`collect_spec_from_messages` -> `generate_factor_code`)
    2.  沙盒试运行 (`run_factor_dryrun`)，若失败或语义不符 (`check_semantics`) 则触发重试
    3.  超过重试阈值 (5次) 或进入人审门 (`human_review_gate`) 后，请求 UI 呈现 code review 面板
    4.  人审通过 (`approve`) / 编辑 (`edit`) / 仅评论 (`review`) 后，流程继续或回跳
    5.  回填历史并计算评价指标 (`backfill_and_eval`)，入库 (`write_db`)

## 架构总览

*   **后端 (FastAPI)**:
    *   `POST /agent`: 接收请求并以 SSE 流输出 LangGraph 事件 (RAW, STATE_SNAPSHOT, STEP_*)
    *   `GET /agent/health`: 健康检查
    *   `POST /agent/feedback`: 接收人审反馈 (CopilotKit runtime 适配器调用)
*   **前端 (Next.js + CopilotKit)**:
    *   `CopilotRuntime` 在 `route.ts` 注册 `factor_agent`
    *   `LangGraphHttpAgent({ url: process.env.AGENT_URL || "http://localhost:8001/agent" })`
    *   页面使用 `useCopilotAgent("factor_agent")` 获取 `state/events/status/agent`
    *   组件：TracePane (事件流)、CodeReviewPanel (人审)、MetricsPanel (指标)、StatusBadge (状态)

## 运行前置条件

*   Python ≥ 3.10，建议使用虚拟环境
*   Node.js ≥ 18 (如需启动前端)
*   依赖 (示例):
    *   后端: `pip install fastapi uvicorn langgraph pydantic`
    *   前端: `npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime`
    *   **注意**: 仓库中存在本地模块引用 `ag_ui_langgraph` (已在 PYTHONPATH 内)。如在你的环境中为外部包，请自行安装或将路径加入 `sys.path`。

## 启动后端

后端默认在代码中支持两种方式启动：

1.  **使用 uvicorn 直接指定端口为 8001 (推荐)**:

    ```bash
    cd /mnt/x/RPA-github/langgraph_source/aifactory
    python -m uvicorn backend.app:app --host 0.0.0.0 --port 8001
    ```

2.  **使用 `backend/app.py` 中的入口 (默认端口 8001，可通过环境变量 `PORT` 覆盖)**:

    ```bash
    cd /mnt/x/RPA-github/langgraph_source/aifactory
    PORT=8001 python backend/app.py
    ```

**健康检查**:

```bash
curl -s http://localhost:8001/agent/health
# 返回示例：{"status":"ok","agent":{"name":"factor_agent"}}
```

**SSE 独立验证 (后端单跑)**:

```bash
curl -N -X POST http://localhost:8001/agent \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId":"t-debug-001",
    "runId":"r-debug-001",
    "messages":[{"id":"msg-001","role":"user","content":"5日滚动均值因子","user":{"id":"u-001"}}],
    "tools":[],
    "context":[],
    "forwardedProps":{},
    "state":{"user_spec":"5日滚动均值因子","factor_name":"MA5"}
  }'
```

预期会看到 RAW/STATE_SNAPSHOT/STEP_* 等事件帧，并在试运行失败后进入 `human_review_gate` 输出 `ui_request`。

## 启动前端 (如已集成 Next.js 工程)

前端目录示例：`frontend/app/api/copilotkit/route.ts`、`frontend/app/factor-copilot/page.tsx`、`frontend/components/*`

1.  **安装依赖并启动开发服务器**:

    ```bash
    cd frontend
    npm install
    npm run dev
    ```

2.  **路由适配 (`route.ts`)**:

    ```ts
    // frontend/app/api/copilotkit/route.ts
    import { CopilotRuntime } from "@copilotkit/runtime";
    import { LangGraphHttpAgent } from "@copilotkit/runtime/agents";

    const runtime = new CopilotRuntime({
      agents: {
        factor_agent: new LangGraphHttpAgent({
          url: process.env.AGENT_URL || "http://localhost:8001/agent",
        }),
      },
    });

    export const POST = runtime.handler();
    ```

    若你的后端端口为 8001，请在前端启动时设置：

    ```bash
    AGENT_URL=http://localhost:8001/agent npm run dev
    ```

3.  **页面使用**:
    打开浏览器页面 (示例路径)：`/factor-copilot`
    *   Network 应出现：`POST /api/copilotkit` (runtime)，随后它会向后端发起 `/agent` SSE 请求
    *   TracePane 出现按类型分组的事件 (如 `RAW`, `STATE_SNAPSHOT`, `TEXT_MESSAGE_CHUNK`)
    *   人审面板 CodeReviewPanel 在 `state.ui_request.type === "code_review"` 时出现
    *   MetricsPanel 在 `state.eval_metrics` 存在时出现

## 人审反馈 (HIL)

*   **前端按钮已绑定**:
    *   **Approve**: 通过 LangGraph 的 state update 机制，将 `{"human_review_status": "approve"}` 注入到 graph state 中。
    *   **Reject**: 注入 `{"human_review_status": "reject"}`。
    *   **Submit Edit**: 注入 `{"human_review_status": "edit", "factor_code": "..."}`。
    *   **Review Comment**: 注入 `{"human_review_status": "review", "ui_response": "..."}`。
*   **CopilotKit 适配器**:
    *   CopilotKit 的前端组件（如 `useLangGraphInterrupt`）会通过 `/agent` 接口与后端通信。
    *   当遇到 `interrupt` 时，前端展示 UI。
    *   用户操作后，前端将用户的反馈（作为新的 input）再次发送给 `/agent`，LangGraph 收到后恢复执行（resume）。
    *   **注意**: `ag-ui-langgraph` 库交互是通过标准的 LangGraph 状态更新和 resume 机制完成的，复用了 `/agent` 接口。

**后端手工验证 (仅用于排查适配器与路径)**:

```bash
curl -s -X GET http://localhost:8001/agent/health
```

**注意**: 请以 `/agent/feedback` 为准进行适配与排查。

## 指标与入库 (mock)

*   `backfill_and_eval` 节点会写入 `state.eval_metrics` (如 `ic/turnover/group_perf`)，UI 的 MetricsPanel 会显示这些指标
*   `write_db` 节点模拟写入入库状态到 `state.db_write_status`
*   完成后 `StatusBadge` 状态为 `done`

## 调试 Checklist (最小闭环)

0.  前端 `route.ts` 使用 `LangGraphHttpAgent`，注册 `factor_agent` 并指向后端 `/agent`
1.  后端单独用 `curl -N ... Accept: text/event-stream` 验证 SSE 是否正常 (非 422/500)
2.  前端 Network 检查：`POST /api/copilotkit` 后是否请求后端 `/agent`
3.  事件流是否进 TracePane：发送“生成一个 5 日均线因子”，分组事件应出现
4.  Metrics 是否出现：流程跑到 `backfill_and_eval` 后，`state.eval_metrics` 存在时显示
5.  人审面板出现：`state.ui_request.type === "code_review"` 时显示，默认填入 `req.code`
6.  点击 Approve：应看到新的事件涌入，状态进入 `backfill_and_eval → write_db → finish`，`status` 变为 done，MetricsPanel 出现

## 主要文件与代码参考

### Domain (业务领域层)
**目录**: `backend/domain/`
**功能**: 包含脱离 LangGraph 也能独立运行的核心业务逻辑，主要负责因子生成与评价。它封装了对底层因子框架 (FactorLib) 和评价框架的调用。
*   `codegen/` (因子代码生成):
    *   `runner.py`: 代码生成主入口，支持 Mock 和真实 L3 模式 (`CodeMode`)。
    *   `generator.py`: 基于 Prompt 和 LLM 生成因子代码。
    *   `validator.py`: 语义检查，确保代码符合预期的输入输出规范。
    *   `tools/factor_l3_py_tool.py`: 提供 L3 系统的语法检查与模拟运行工具。
*   `evaluate/` (因子评价):
    *   `runner.py`: 评价执行主入口。
    *   `tools/l3_factor_evals.py`: 调用 L3 评价系统计算 IC、换手率等指标。

### Graph (编排层)
**目录**: `backend/graph/`
**功能**: 基于 LangGraph 定义业务流程的状态机与节点流转逻辑。
*   `graph.py`: 定义 StateGraph 结构，配置节点 (`add_node`) 和边 (`add_edge`/`add_conditional_edges`)。
*   `nodes.py`: 实现具体的图节点函数 (如 `generate_factor_code`, `human_review_gate`)，负责调度 Domain 层的功能并更新 State。
*   `state.py` / `global_state.py`: 定义 `FactorAgentState` 数据结构，作为全图共享的上下文。

### Tools (工具层)
**目录**: `backend/global_tools/` (或分散在各 domain 的 `tools/` 下)
**功能**: 提供通用的基础设施工具。
*   `sandbox_runner.py`: 负责在隔离环境中执行生成的 Python 代码，捕获 stdout/stderr 和异常，确保安全运行。

### 其他重要文件
*   **后端入口**: `backend/app.py` - 集成 FastAPI 与 LangGraph，暴露 HTTP 接口。
*   **前端路由**: `frontend/app/api/copilotkit/route.ts` - CopilotKit Runtime 适配器。
*   **前端页面**: `frontend/app/factor-copilot/page.tsx` - 主交互界面。

## 运行小结

*   后端先启动并确认 `/agent/health` 为 ok；
*   前端启动并确认 `route.ts` 指向后端 `/agent`；
*   在页面中聊天触发生成 → 事件追踪 → 人审 → 指标展示；
*   若路径或端口不一致，通过环境变量 `AGENT_URL` 对齐；
*   人审反馈机制以 **LangGraph State Update** 为准，确保图能通过状态恢复继续至 `finish`。
