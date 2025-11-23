import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  LangGraphHttpAgent,
} from "@copilotkit/runtime";
import type { NextRequest } from "next/server";

const agentUrl =
  process.env.AGENT_URL || "http://localhost:8001/agent/factor_agent"; // 记得对齐后端

if (process.env.NODE_ENV !== "production") {
  console.log("[DBG] copilot runtime init agentUrl=", agentUrl);
}

const runtime = new CopilotRuntime({
  agents: {
    factor_agent: new LangGraphHttpAgent({ url: agentUrl }),
  },
});

const { handleRequest, GET: _GET, POST: _POST } =
  copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });

export async function GET(req: NextRequest) {
  if (process.env.NODE_ENV !== "production") {
    console.log("[DBG] copilotkit GET", req.headers.get("accept"));
  }
  return _GET(req);
}

export async function POST(req: NextRequest) {
  if (process.env.NODE_ENV !== "production") {
    console.log("[DBG] copilotkit POST", req.headers.get("content-type"));
  }
  return _POST(req);
}
