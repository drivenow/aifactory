export default function MetricsPanel({ state }: { state: any }) {
  // 打印 state 对象用于调试
  console.log("[MetricsPanel] received state:", state);
  const metrics = state?.eval_metrics;
  if (!metrics) return null;
  return (
    <div style={{ border: "1px solid #999", padding: 8, borderRadius: 8, marginTop: 12 }}>
      <div>Metrics</div>
      <pre style={{ margin: 0 }}>{JSON.stringify(metrics, null, 2)}</pre>
    </div>
  );
}