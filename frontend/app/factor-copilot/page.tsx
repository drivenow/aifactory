"use client";

import {
  CopilotKit,
  useCoAgent,
  useLangGraphInterrupt,
} from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

import StatusBadge from "../../components/StatusBadge";
import TracePane from "../../components/TracePane";
import CodeReviewPanel, {
  CodeReviewRequest,
} from "../../components/CodeReviewPanel";
import MetricsPanel from "../../components/MetricsPanel";

/**
 * 和后端 FactorAgentState 对齐一个前端类型，方便使用
 * 它只是“前端的 TS 类型声明”，而不是另一份独立的状态源。

好处是：

state?.route、state?.retry_count 有完整类型提示；

MetricsPanel / StatusBadge 这些组件也都能按这个类型来写 props。

这份类型只存在于前端编译期，不会制造一份“新状态”
 */
type FactorAgentState = {
  retry_count?: number;
  human_review_status?: string;
  eval_metrics?: any;
  db_write_status?: string;
  last_success_node?: string;
  route?: string;
};

export default function Page() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="factor_agent">
      <Inner />
    </CopilotKit>
  );
}

function Inner() {
  // 1) 同步 LangGraph 自定义 State（非中断）
  const { state, running, events } = useCoAgent<FactorAgentState>({
    name: "factor_agent",
    initialState: {
      retry_count: 0,
      human_review_status: "pending",
    },
  });

  const status =
    running
      ? "running"
      : state?.route === "finish"
        ? "done"
        : state?.db_write_status === "failed"
          ? "error"
          : "idle";

  // 2) 处理 LangGraph interrupt（HITL）
  useLangGraphInterrupt<CodeReviewRequest>({
    // 如果你以后有多 agent，可以在这里过滤 agent
    enabled: ({ agentMetadata }) =>
      !agentMetadata || agentMetadata.agentName === "factor_agent",

    // render 决定这次 interrupt 在前端长成什么 UI
    render: ({ event, resolve }) => {
      const req = event.value as CodeReviewRequest;

      if (!req || req.type !== "code_review") {
        // 非我们关心的中断类型，直接忽略
        return null;
      }

      return (
        <CodeReviewPanel
          request={req}
          onApprove={() =>
            resolve({
              type: "code_review",
              status: "approved",
            })
          }
          onReject={() =>
            resolve({
              type: "code_review",
              status: "rejected",
            })
          }
          onEdit={(code) =>
            resolve({
              type: "code_review",
              status: "edited",
              edited_code: code,
            })
          }
        />
      );
    },
  });

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16,
        padding: 16,
      }}
    >
      {/* 左侧：对话 + 状态 + 事件流 */}
      <div>
        <h1>量化因子</h1>
        <CopilotChat
          instructions="你是量化因子编码助手"
          labels={{ title: "Factor Agent" }}
        />
        <StatusBadge status={status} />
        <TracePane events={events || []} />
        <pre>
          {JSON.stringify(
            {
              node: state?.last_success_node,
              retries: state?.retry_count,
              human: state?.human_review_status,
              route: state?.route,
            },
            null,
            2
          )}
        </pre>
      </div>

      {/* 右侧：指标面板（从共享 state 里拿 eval_metrics） */}
      <div>
        <MetricsPanel state={state || {}} />
      </div>
    </div>
  );
}
