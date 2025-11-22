import { useMemo, useState } from "react";

export default function TracePane({ events }: { events: any[] }) {
  const groups = useMemo(() => {
    const g: Record<string, any[]> = {};
    for (const e of events || []) {
      const k = e?.type || e?.event?.event || "UNKNOWN";
      if (!g[k]) g[k] = [];
      g[k].push(e);
    }
    return g;
  }, [events]);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  return (
    <div style={{ marginTop: 12 }}>
      <div>Events</div>
      <div style={{ maxHeight: 240, overflow: "auto", border: "1px solid #ccc", padding: 8 }}>
        {Object.keys(groups).map((k) => (
          <div key={k}>
            <button onClick={() => setOpen((o) => ({ ...o, [k]: !o[k] }))}>{open[k] ? "-" : "+"} {k}</button>
            {open[k] && groups[k].map((e, i) => (
              <pre key={k + i} style={{ margin: 0 }}>{JSON.stringify(e)}</pre>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}