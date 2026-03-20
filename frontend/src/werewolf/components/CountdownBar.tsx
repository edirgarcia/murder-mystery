import { useEffect, useMemo, useState } from "react";

export default function CountdownBar({ endsAt, fallbackSeconds = 20 }: { endsAt: string | null; fallbackSeconds?: number }) {
  const endMs = useMemo(() => (endsAt ? new Date(endsAt).getTime() : Date.now() + fallbackSeconds * 1000), [endsAt, fallbackSeconds]);
  const total = fallbackSeconds * 1000;
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const remaining = Math.max(0, endMs - now);
  const pct = Math.max(0, Math.min(100, (remaining / total) * 100));

  return (
    <div className="space-y-1">
      <div className="h-2 rounded-full bg-mystery-700 overflow-hidden">
        <div className="h-full bg-red-400 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-mystery-400">{Math.ceil(remaining / 1000)}s</p>
    </div>
  );
}
