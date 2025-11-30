# 因子编码助手（MVP）

本项目通过 LangGraph 构建量化研究领域的选股因子编码助手，并使用 CopilotKit 在前端进行事件流展示与人审（Human-in-the-loop, HIL）交互。后端提供符合 AG-UI 协议的 `/agent` SSE 端点，前端以 `CopilotKit Provider` 顶层包裹，`useCopilotAgent` 读取 `state/events/status`，并通过 `agent.humanFeedback(...)` 将人审结果回传以继续编排流程。

## 项目背景
- 目标：加速量化因子从“自然语言描述 → 模版代码 → 试运行与语义检查 → 人审 → 历史回填与评价 → 入库”的完整链路。
- 技术栈：
  - 后端：FastAPI + LangGraph（状态图、SSE 输出），AG-UI 兼容端点
  - 前端：Next.js + CopilotKit（runtime + react-ui），事件流追踪、指标面板、人审编辑面板
  - 评估：agenteval（接口预留，当前为 mock 指标）
- 核心流程：
  1) 读取用户描述，按因子模板生成代码
  2) 沙盒试运行失败或语义不符则触发最多 5 次 react 重试
  3) 超过重试阈值或进入人审门（human_review_gate）后，请求 UI 呈现 code review 面板
  4) 人审通过/编辑后，回填历史并计算评价指标，入库

## 架构总览
- 后端（FastAPI）：
  - `POST /agent`：接收请求并以 SSE 流输出 LangGraph 事件（RAW、STATE_SNAPSHOT、STEP_*）
  - `GET /agent/health`：健康检查
  - `POST /agent/feedback`：接收人审反馈（CopilotKit runtime 适配器调用）
- 前端（Next.js + CopilotKit）：
  - `CopilotRuntime` 在 `route.ts` 注册 `factor_agent`
  - `LangGraphHttpAgent({ url: process.env.AGENT_URL || "http://localhost:8001/agent" })`
  - 页面使用 `useCopilotAgent("factor_agent")` 获取 `state/events/status/agent`
  - 组件：TracePane（事件流）、CodeReviewPanel（人审）、MetricsPanel（指标）、StatusBadge（状态）

## 运行前置条件
- Python ≥ 3.10，建议使用虚拟环境
- Node.js ≥ 18（如需启动前端）
- 依赖（示例）：
  - 后端：`pip install fastapi uvicorn langgraph pydantic`
  - 前端：`npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime`
  - 注：仓库中存在本地模块引用 `ag_ui_langgraph`（已在 PYTHONPATH 内）。如在你的环境中为外部包，请自行安装或将路径加入 `sys.path`。

## 启动后端
后端默认在代码中支持两种方式启动：

1) 使用 uvicorn 直接指定端口为 8002（与前端默认配置对齐）：

```bash
cd /Users/fullmetal/Documents/agent_demo
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8001
```

2) 使用 `backend/app.py` 中的入口（默认端口 8001，可通过环境变量 `PORT` 覆盖）：

```bash
cd /Users/fullmetal/Documents/agent_demo
PORT=8001 python backend/app.py
```

健康检查：

```bash
curl -s http://localhost:8001/agent/health
# 返回示例：{"status":"ok","agent":{"name":"graphwrapper"}}
```

SSE 独立验证（后端单跑）：

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

## 启动前端（如已集成 Next.js 工程）
前端目录示例：`frontend/app/api/copilotkit/route.ts`、`frontend/app/factor-copilot/page.tsx`、`frontend/components/*`

1) 安装依赖并启动开发服务器：

```bash
cd /Users/fullmetal/Documents/agent_demo/frontend
npm install
npm run dev
```

2) 路由适配（`route.ts`）：

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

3) 页面使用：
打开浏览器页面（示例路径）：`/factor-copilot`
- Network 应出现：`POST /api/copilotkit`（runtime），随后它会向后端发起 `/agent` SSE 请求
- TracePane 出现按类型分组的事件（如 `RAW`、`STATE_SNAPSHOT`、`TEXT_MESSAGE_CHUNK`）
- 人审面板 CodeReviewPanel 在 `state.ui_request.type === "code_review"` 时出现
- MetricsPanel 在 `state.eval_metrics` 存在时出现

## 人审反馈（HIL）
- 前端按钮已绑定：
  - Approve：`agent.humanFeedback({ human_review_status: "approve" })`
  - Reject：`agent.humanFeedback({ human_review_status: "rejecte" })`
  - Submit Edit：`agent.humanFeedback({ human_review_status: "edit", factor_code: code, human_edits: "edit in UI" })`
- CopilotKit 适配器会调用后端的 `POST /agent/feedback` 并携带完整上下文 envelope，使图从中断点继续：`backfill_and_eval → write_db → finish`

后端手工验证（仅用于排查适配器与路径）：

```bash
curl -s -X POST http://localhost:8001/agent/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "threadId":"t-debug-001",
    "runId":"r-debug-002",
    "messages":[],
    "tools":[],
    "context":[],
    "forwardedProps":{},
    "state": { "human_review_status": "approve" }
  }'
```

注意：若你看到代码中有 `@app.post("/agent/human-feedback")`，这条路由不是 CopilotKit runtime 默认使用的路径；当前服务的 OpenAPI 显示活跃的人审反馈端点为 `/agent/feedback`。请以 `/agent/feedback` 为准进行适配与排查。

## 指标与入库（mock）
- `backfill_and_eval` 节点会写入 `state.eval_metrics`（如 `ic/turnover/group_perf`），UI 的 MetricsPanel 会显示这些指标
- `write_db` 节点模拟写入入库状态到 `state.db_write_status`
- 完成后 `StatusBadge` 状态为 `done`

## 调试 Checklist（最小闭环）
0) 前端 `route.ts` 使用 `LangGraphHttpAgent`，注册 `factor_agent` 并指向后端 `/agent`
1) 后端单独用 `curl -N ... Accept: text/event-stream` 验证 SSE 是否正常（非 422/500）
2) 前端 Network 检查：`POST /api/copilotkit` 后是否请求后端 `/agent`
3) 事件流是否进 TracePane：发送“生成一个 5 日均线因子”，分组事件应出现
4) Metrics 是否出现：流程跑到 `backfill_and_eval` 后，`state.eval_metrics` 存在时显示
5) 人审面板出现：`state.ui_request.type === "code_review"` 时显示，默认填入 `req.code`
6) 点击 Approve：应看到新的事件涌入，状态进入 `backfill_and_eval → write_db → finish`，`status` 变为 done，MetricsPanel 出现

调试增强（可选）：在 TracePane 旁显示关键状态字段，快速定位：

```tsx
<pre>{JSON.stringify({
  node: state?.last_success_node,
  retries: state?.retry_count,
  human: state?.human_review_status,
}, null, 2)}</pre>
```

## 常见问题与排查
- 只看到 `POST /api/copilotkit`，没有后端 `/agent` 请求：检查 `route.ts` 是否注册了 `factor_agent` 并正确配置 `url`
- 事件面板空：多半是 agent 未注册或后端未以 SSE 返回（确认 `Accept: text/event-stream` 与 CORS）
- Metrics 不显示：检查 TracePane 是否有 `STATE_SNAPSHOT/DELTA` 包含 `eval_metrics`，后端节点是否写入
- 点击 Approve 无反应：
  - Network 是否有 `POST /agent/feedback`
  - 若有但后端未继续：确认 `human_review_gate` 是否正确读取 `state.human_review_status`
- 端口不一致：前端默认使用 8002；如后端为 8001，请设置 `AGENT_URL=http://localhost:8001/agent`

## 主要文件与代码参考
- 后端入口与路由：`backend/app.py`
- LangGraph 图：`backend/graph/graph.py`
- 节点实现：`backend/graph/nodes.py`
- 状态类型：`backend/graph/state.py`
- 因子模板：`backend/graph/tools/factor_template.py`
- 沙盒执行：`backend/graph/tools/sandbox_runner.py`
- 前端 runtime 路由：`frontend/app/api/copilotkit/route.ts`
- 页面与组件：`frontend/app/factor-copilot/page.tsx`、`frontend/components/*`

## 运行小结
- 后端先启动并确认 `/agent/health` 为 ok；
- 前端启动并确认 `route.ts` 指向后端 `/agent`；
- 在页面中聊天触发生成 → 事件追踪 → 人审 → 指标展示；
- 若路径或端口不一致，通过环境变量 `AGENT_URL` 对齐；
- 人审反馈以 `/agent/feedback` 为准，确保图能继续至 `finish`。