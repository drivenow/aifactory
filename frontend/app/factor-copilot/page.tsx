"use client";
/*
输入因子描述 → 后端走 collect_spec → gen_code_react → dryrun → semantic_check → human_review_gate。
第一次到 human_review_gate 时触发中断，state.ui_request 带回前端 → CodeReviewPanel 打开。
你在右边面板点 Approve/Edit/Reject → setState 写入 ui_response → run()。
后端 human_review_gate 第二次执行，读到 ui_response，然后进入 backfill_and_eval → write_db → finish。
前端 statusBadge 变为 done，MetricsPanel 里能看到 mock 的指标。
*/
import { CopilotKit, useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import StatusBadge from "../../components/StatusBadge";
import TracePane from "../../components/TracePane";
import CodeReviewPanel from "../../components/CodeReviewPanel";
import MetricsPanel from "../../components/MetricsPanel";

type FactorAgentState = {
  retry_count?: number;
  human_review_status?: "pending" | "edited" | "approved" | "rejected";
  ui_request?: any;
  ui_response?: any;
  route?: string;
  last_success_node?: string;
  db_write_status?: "success" | "failed" | "unknown";
  events?: any[];
  // 其他后端 state 字段按需补充
  [key: string]: any;
};

export default function Page() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="factor_agent">
      <Inner />
    </CopilotKit>
  );
}

function Inner() {
  const { state, setState, run, running } = useCoAgent<FactorAgentState>({
    name: "factor_agent",
    initialState: {
      retry_count: 0,
      human_review_status: "pending",
      ui_request: null,
      ui_response: null,
    },
  });

  const events = state?.events ?? []; // 目前后端没提供就为空数组
  const status =
    running
      ? "running"
      : state?.db_write_status === "failed"
        ? "error"
        : state?.route === "finish"
          ? "done"
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
      {/* 左侧：聊天 + 状态 + Trace */}
      <div>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>量化因子</h1>
        <CopilotChat
          instructions="你是量化因子编码助手"
          labels={{ title: "Factor Agent" }}
        />
        <StatusBadge status={status} />
        <TracePane events={events} />
        <pre style={{ marginTop: 12 }}>
          {JSON.stringify(
            {
              node: state?.last_success_node,
              retries: state?.retry_count,
              human: state?.human_review_status,
              route: state?.route,
              db_write_status: state?.db_write_status,
            },
            null,
            2
          )}
        </pre>
      </div>

      {/* 右侧：人审面板 + 指标面板 */}
      <div>
        <CodeReviewPanel
          state={state || {}}
          onApprove={async () => {
            // 人审通过：写入 ui_response -> run() 让后端 human_review_gate 继续
            await setState((prev) => ({
              ...(prev || {}),
              ui_response: {
                type: "code_review",
                status: "approved",
              },
            }));
            await run();
          }}
          onReject={async () => {
            await setState((prev) => ({
              ...(prev || {}),
              ui_response: {
                type: "code_review",
                status: "rejected",
              },
            }));
            await run();
          }}
          onEdit={async (code) => {
            await setState((prev) => ({
              ...(prev || {}),
              ui_response: {
                type: "code_review",
                status: "edited",
                edited_code: code || "",
              },
            }));
            await run();
          }}
        />
        <MetricsPanel state={state || {}} />
      </div>
    </div>
  );
}
