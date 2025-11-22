import { useEffect, useMemo, useState } from "react";

export default function CodeReviewPanel({ state, onApprove, onReject, onEdit }: { state: any; onApprove: () => void; onReject: () => void; onEdit: (code: string) => void }) {
  const req = useMemo(() => state?.ui_request, [state]);
  const [code, setCode] = useState<string>("");
  useEffect(() => {
    if (req?.type === "code_review") setCode(req?.code || "");
  }, [req]);
  if (!req || req.type !== "code_review") return null;
  return (
    <div style={{ border: "1px solid #999", padding: 8, borderRadius: 8 }}>
      <div>Code Review</div>
      <textarea value={code} onChange={(e) => setCode(e.target.value)} rows={12} style={{ width: "100%" }} />
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onApprove}>Approve</button>
        <button onClick={onReject}>Reject</button>
        <button onClick={() => onEdit(code)}>Submit Edit</button>
      </div>
    </div>
  );
}