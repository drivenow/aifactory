import { CopilotRuntime, copilotRuntimeNextJSAppRouterEndpoint, LangGraphHttpAgent, ExperimentalEmptyAdapter } from "@copilotkit/runtime";
import type { NextRequest } from "next/server";

const agentUrl = process.env.AGENT_URL || "http://localhost:8002/agent";
console.log("[DBG] copilot runtime init agentUrl=", agentUrl);
const runtime = new CopilotRuntime({
  agents: {
    factor_agent: new LangGraphHttpAgent({ url: agentUrl }),
  },
});

const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({ runtime, serviceAdapter: new ExperimentalEmptyAdapter(), endpoint: "/api/copilotkit" });

export async function POST(req: NextRequest) {
  console.log("[DBG] copilotkit POST", req.headers.get("content-type"));
  return handleRequest(req);
}