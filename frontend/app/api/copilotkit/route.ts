import { CopilotRuntime } from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/agents";

const runtime = new CopilotRuntime({
  agents: {
    factor_agent: new LangGraphHttpAgent({
      url: process.env.AGENT_URL || "http://localhost:8002/agent",
    }),
  },
});

export const POST = runtime.handler();