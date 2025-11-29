// app/api/copilotkit/route.ts

import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  ExperimentalEmptyAdapter,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@ag-ui/langgraph";
import { NextRequest } from "next/server";

// 对齐后端 FastAPI：add_langgraph_fastapi_endpoint(app, agent, "/agent")
const agentUrl = process.env.AGENT_URL || "http://localhost:8001/agent";

// 单 agent 场景，用 EmptyAdapter 即可
const serviceAdapter = new ExperimentalEmptyAdapter();

// CopilotRuntime：注册一个名为 factor_agent 的 LangGraph 代理
const runtime = new CopilotRuntime({
  agents: {
    // 这里的 key 要和 <CopilotKit agent="factor_agent" />、后端 LangGraphAgent(name="factor_agent") 一致
    factor_agent: new LangGraphHttpAgent({
      url: agentUrl,
    }),
  },
});

// CopilotKit 会用 POST /api/copilotkit 做所有交互
export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  if (process.env.NODE_ENV !== "production") {
    console.log("[DBG] copilotkit POST", req.headers.get("content-type"));
  }

  return handleRequest(req);
};

// 可选：如果你想让 GET /api/copilotkit 也返回一点东西，可以解开这段
// export const GET = async () => Response.json({ status: "ok" });
