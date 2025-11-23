"use client";
import { CopilotKit, useCoAgent } from "@copilotkit/react-core";
import { useCopilotMessagesContext } from "@copilotkit/react-core";
import { useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import StatusBadge from "../../components/StatusBadge";
import TracePane from "../../components/TracePane";
import CodeReviewPanel from "../../components/CodeReviewPanel";
import MetricsPanel from "../../components/MetricsPanel";

export default function Page() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="factor_agent">
      <Inner />
    </CopilotKit>
  );
}

function Inner() {
  const coagent = useCoAgent<{ [key: string]: any }>({ name: "factor_agent", initialState: {} });
  const { messages } = useCopilotMessagesContext();
  const { appendMessage, runChatCompletion } = useCopilotChat();
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: 16 }}>
      <div>
        <CopilotChat instructions="你是量化因子编码助手" labels={{ title: "Factor Agent" }} />
        <StatusBadge status={coagent.running ? "running" : "idle"} />
        <TracePane events={(messages || []).map((m:any)=>({ type: "MESSAGE", message: m }))} />
        <pre>{JSON.stringify({ node: coagent.state?.last_success_node, retries: coagent.state?.retries_left, human: coagent.state?.human_review_status, route: coagent.state?.route }, null, 2)}</pre>
      </div>
      <div>
        <CodeReviewPanel
          state={coagent.state || {}}
          onApprove={async () => {
            await appendMessage({ role: "user", content: "approved" } as any);
            await coagent.run();
          }}
          onReject={async () => {
            await appendMessage({ role: "user", content: "rejected" } as any);
            await coagent.run();
          }}
          onEdit={async (code) => {
            await appendMessage({ role: "user", content: `code_review_response:${JSON.stringify({ status: "edited", edited_code: code || "" })}` } as any);
            await coagent.run();
          }}
        />
        <MetricsPanel state={coagent.state || {}} />
      </div>
    </div>
  );
}