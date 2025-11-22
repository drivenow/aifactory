export default function StatusBadge({ status }: { status: string }) {
  const color = status === "running" ? "orange" : status === "done" ? "green" : "gray";
  return <div style={{ padding: 8, background: color, color: "white", borderRadius: 8 }}>{status || "idle"}</div>;
}