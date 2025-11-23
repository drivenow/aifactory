import { useEffect, useState } from "react";

export type CodeReviewRequest = {
  type: string;         // "code_review"
  title?: string;
  code?: string;
  actions?: string[];
  retry_count?: number;
};

export default function CodeReviewPanel(props: {
  request: CodeReviewRequest | null;
  onApprove: () => void;
  onReject: () => void;
  onEdit: (code: string) => void;
}) {
  const { request, onApprove, onReject, onEdit } = props;

  const [code, setCode] = useState<string>("");

  useEffect(() => {
    if (request?.type === "code_review") {
      setCode(request.code ?? "");
    } else {
      setCode("");
    }
  }, [request]);

  if (!request || request.type !== "code_review") return null;

  return (
    <div style={{ border: "1px solid #999", padding: 8, borderRadius: 8 }}>
      <div style={{ marginBottom: 8, fontWeight: 600 }}>
        {request.title ?? "Code Review"}
      </div>

      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={12}
        style={{ width: "100%", fontFamily: "monospace" }}
      />

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={onApprove}>Approve</button>
        <button onClick={onReject}>Reject</button>
        <button onClick={() => onEdit(code)}>Submit Edit</button>
      </div>
    </div>
  );
}
