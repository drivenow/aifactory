"use client";

import React, { useEffect, useState } from "react";

export type CodeReviewRequest = {
  type: "code_review";
  title?: string;
  code?: string;
  actions?: string[];
  retry_count?: number;
};

type Mode = "idle" | "review" | "edit";

export default function CodeReviewPanel(props: {
  request: CodeReviewRequest;
  onApprove: () => void;
  onReject: () => void;
  onSubmitReview: (comment: string) => void;
  onSubmitEdit: (code: string) => void;
  onClear?: () => void; // 可选：提交后清空面板
}) {
  const { request, onApprove, onReject, onSubmitReview, onSubmitEdit, onClear } = props;

  const [mode, setMode] = useState<Mode>("idle");
  const [code, setCode] = useState("");
  const [reviewComment, setReviewComment] = useState("");

  // request 更新时重置面板
  useEffect(() => {
    setMode("idle");
    setCode(request.code ?? "");
    setReviewComment("");
  }, [request]);

  const canSubmit =
    (mode === "review" && reviewComment.trim().length > 0) ||
    mode === "edit";

  const handleSubmit = () => {
    if (!canSubmit) return;

    if (mode === "review") {
      onSubmitReview(reviewComment.trim());
      onClear?.();
      return;
    }
    if (mode === "edit") {
      onSubmitEdit(code);
      onClear?.();
      return;
    }
  };

  return (
    <div
      style={{
        border: "1px solid #999",
        borderRadius: 8,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {/* 标题 */}
      <div style={{ fontWeight: 700 }}>
        {request.title ?? "Review generated factor code"}
      </div>

      {/* 顶部按钮区 */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={onApprove}>Approve</button>
        <button onClick={onReject}>Reject</button>

        <button
          onClick={() => setMode("review")}
          style={{
            fontWeight: mode === "review" ? 700 : 400,
            background: mode === "review" ? "#eee" : undefined,
          }}
        >
          Review
        </button>

        <button
          onClick={() => setMode("edit")}
          style={{
            fontWeight: mode === "edit" ? 700 : 400,
            background: mode === "edit" ? "#eee" : undefined,
          }}
        >
          Edit
        </button>

        <button onClick={handleSubmit} disabled={!canSubmit}>
          Submit
        </button>
      </div>

      {/* 代码区 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ fontSize: 12, color: "#555" }}>
          Factor Code {mode === "review" ? "(read-only)" : mode === "edit" ? "(editable)" : ""}
        </div>
        <textarea
          rows={14}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          readOnly={mode === "review"} // review 模式不能改代码
          style={{
            width: "100%",
            fontFamily: "monospace",
            fontSize: 12,
            lineHeight: 1.4,
            borderRadius: 6,
            border: "1px solid #ccc",
            padding: 8,
            background: mode === "review" ? "#f7f7f7" : "white",
          }}
        />
      </div>

      {/* Review 意见区（仅 review 模式出现） */}
      {mode === "review" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 12, color: "#555" }}>审核意见（不可编辑代码）</div>
          <textarea
            rows={5}
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
            placeholder="请在这里写审核意见，点击 Submit 提交给后端"
            style={{
              width: "100%",
              fontSize: 13,
              lineHeight: 1.5,
              borderRadius: 6,
              border: "1px solid #ccc",
              padding: 8,
            }}
          />
        </div>
      )}

      {/* 轻提示 */}
      {mode === "idle" && (
        <div style={{ fontSize: 12, color: "#777" }}>
          请选择 Review（写意见）或 Edit（改代码）后再 Submit。
        </div>
      )}
    </div>
  );
}
