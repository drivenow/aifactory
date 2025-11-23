"use client";
import { CopilotKit, useCoAgent } from "@copilotkit/react-core";
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
  const coagent = useCoAgent<{ [key: string]: any }>({
    name: "factor_agent",
    initialState: {
      retry_count: 0,
      human_review_status: "pending",
      ui_request: null,
    },
  });

  const events = coagent.state?.events ?? []; // 后端需要提供
  const status =
    coagent.running
      ? "running"
      : coagent.state?.route === "finish"
        ? "done"
        : coagent.state?.db_write_status === "failed"
          ? "error"
          : "idle";

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16,
        padding: 16,
      }}
    >
      <div>
        <CopilotChat
          instructions="你是量化因子编码助手"
          labels={{ title: "Factor Agent" }}
        />
        <StatusBadge status={status} />
        <TracePane events={events} />
        <pre>
          {JSON.stringify(
            {
              node: coagent.state?.last_success_node,
              retries: coagent.state?.retries_left,
              human: coagent.state?.human_review_status,
              route: coagent.state?.route,
            },
            null,
            2
          )}
        </pre>
      </div>

      <div>
        <CodeReviewPanel
          state={coagent.state || {}}
          onApprove={async () => {
            // ✅ 方案A：结构化 ui_response 回传
            await coagent.run({
              input: {
                ui_response: {
                  type: "code_review",
                  status: "approved",
                },
              },
            });
          }}
          onReject={async () => {
            await coagent.run({
              input: {
                ui_response: {
                  type: "code_review",
                  status: "rejected",
                },
              },
            });
          }}
          onEdit={async (code) => {
            await coagent.run({
              input: {
                ui_response: {
                  type: "code_review",
                  status: "edited",
                  edited_code: code || "",
                },
              },
            });
          }}
        />
        <MetricsPanel state={coagent.state || {}} />
      </div>
    </div>
  );
}
