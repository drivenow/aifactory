"use client";

import React from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgent, useLangGraphInterrupt } from "@copilotkit/react-core";

import StatusBadge from "../../components/StatusBadge";
import TracePane from "../../components/TracePane";
import CodeReviewPanel, { CodeReviewRequest } from "../../components/CodeReviewPanel";
import MetricsPanel from "../../components/MetricsPanel";


/**
 * FactorAgentState 类型（与后端 state.py 对齐）
 * 如果你的后端 get_state_snapshot 返回的是 {values: {...}} 结构，
 * 把下面所有 state.xxx 改为 state.values?.xxx 即可。
 */
export type FactorAgentState = {
  messages?: any[];
  user_spec?: string;
  factor_code?: string;
  route?: string;
  retry_count?: number;
  should_interrupt?: boolean;

  human_review_status?: "pending" | "approve" | "edit" | "rejecte" | "review";
  review_comment?: string; // ✅ 新增字段（后端也有）

  eval_metrics?: any;
  db_write_status?: "pending" | "success" | "failed";

  last_success_node?: string;
  error?: any;
};

function statusFromState(state: FactorAgentState | null | undefined, running: boolean) {
  if (running) return "running";
  if (state?.db_write_status === "failed") return "error";
  if (state?.route === "finish") return "done";
  return "idle";
}

function Inner() {
  const { state, running, events } = useCoAgent<FactorAgentState>({
    name: "factor_agent",
    initialState: {
      retry_count: 0,
      human_review_status: "pending",
    },
  });

  // 固定右侧 HITL Panel 的事件/resolve
  const [hitlEvent, setHitlEvent] = React.useState<any | null>(null);
  const [hitlResolve, setHitlResolve] = React.useState<((value: any) => void) | null>(null);

  useLangGraphInterrupt<CodeReviewRequest>({
    enabled: ({ agentMetadata }) =>
      !agentMetadata || agentMetadata.agentName === "factor_agent",
    render: ({ event, resolve }) => {
      const req = event.value as CodeReviewRequest;
      if (!req || req.type !== "code_review") return null;

      // 捕获 event/resolve，交给右侧固定面板渲染
      if (hitlEvent !== event) {
        setHitlEvent(event);
        setHitlResolve(() => resolve);
      }
      return null;
    },
  });

  const status = statusFromState(state, running);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* 主内容区：左右两列 */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "2fr 1.5fr",
          gap: 16,
          padding: 16,
          minHeight: 0,
        }}
      >
        {/* 左侧：状态 / 指标 / trace */}
        <div style={{ overflow: "auto", minHeight: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h2 style={{ margin: 0 }}>因子编码助手</h2>
            <StatusBadge status={status} />
          </div>

          <div style={{ marginTop: 12 }}>
            <MetricsPanel state={state || {}} />
          </div>

          <div style={{ marginTop: 12 }}>
            <TracePane events={events || []} />
          </div>
        </div>

        {/* 右侧：固定 HITL Panel */}
        <div style={{ overflow: "auto", minHeight: 0 }}>
          {hitlEvent && hitlResolve ? (
            <CodeReviewPanel
              request={hitlEvent.value as CodeReviewRequest}

              /**
               * ✅ 新协议边界：
               * resolve({ type, action, payload })
               * action: approve | rejecte | review | edit
               * payload: { review_comment? , edited_code? }
               */

              onApprove={() =>
                hitlResolve({
                  type: "code_review",
                  action: "approve",
                })
              }

              onReject={() =>
                hitlResolve({
                  type: "code_review",
                  action: "rejecte",
                })
              }

              onSubmitReview={(comment) =>
                hitlResolve({
                  type: "code_review",
                  action: "review",
                  payload: {
                    review_comment: comment,
                  },
                })
              }

              onSubmitEdit={(code) =>
                hitlResolve({
                  type: "code_review",
                  action: "edit",
                  payload: {
                    edited_code: code,
                  },
                })
              }

              onClear={() => {
                // 用户提交后清空右侧面板（可选）
                setHitlEvent(null);
                setHitlResolve(null);
              }}
            />
          ) : (
            <div
              style={{
                border: "1px dashed #bbb",
                borderRadius: 8,
                padding: 12,
                color: "#666",
              }}
            >
              暂无人工审核任务。代码生成完成后，这里会出现审核面板。
            </div>
          )}
        </div>
      </div>

      {/* 底部唯一对话框（初次描述因子 / 后续自然语言讨论） */}
      <div
        style={{
          borderTop: "1px solid #e5e5e5",
          padding: 8,
          background: "#fafafa",
        }}
      >
        <CopilotChat
          labels={{ title: "Factor Agent" }}
          instructions="你是量化研究因子编码助手。用户在这里描述因子逻辑、问问题或继续讨论。"
        />
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="factor_agent">
      <Inner />
    </CopilotKit>
  );
}
