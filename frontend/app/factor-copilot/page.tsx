"use client";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAgent } from "@copilotkit/react-core";
import StatusBadge from "../../components/StatusBadge";
import TracePane from "../../components/TracePane";
import CodeReviewPanel from "../../components/CodeReviewPanel";
import MetricsPanel from "../../components/MetricsPanel";

export default function Page() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <Inner />
    </CopilotKit>
  );
}

function Inner() {
  const { state, events, status, agent } = useCopilotAgent("factor_agent");
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: 16 }}>
      <div>
        <CopilotChat instructions="你是量化因子编码助手" labels={{ title: "Factor Agent" }} />
        <StatusBadge status={status || "idle"} />
        <TracePane events={events || []} />
      </div>
      <div>
        <CodeReviewPanel
          state={state || {}}
          onApprove={() => agent?.humanFeedback?.({ human_review_status: "approved" })}
          onReject={() => agent?.humanFeedback?.({ human_review_status: "rejected" })}
          onEdit={(code) => agent?.humanFeedback?.({ human_review_status: "edited", factor_code: code, human_edits: "edited in UI" })}
        />
        <MetricsPanel state={state || {}} />
      </div>
    </div>
  );
}