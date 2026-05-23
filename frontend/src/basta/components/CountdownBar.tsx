import { useEffect, useRef, useState } from "react";

interface Props {
  endsAt: string;
  totalSeconds: number;
  onComplete?: () => void;
}

export default function CountdownBar({ endsAt, totalSeconds, onComplete }: Props) {
  const [remaining, setRemaining] = useState(totalSeconds);
  const completedRef = useRef(false);

  useEffect(() => {
    completedRef.current = false;

    function tick() {
      const ms = new Date(endsAt).getTime() - Date.now();
      const nextRemaining = Math.max(0, Math.ceil(ms / 1000));
      setRemaining(nextRemaining);
      if (nextRemaining === 0 && !completedRef.current) {
        completedRef.current = true;
        onComplete?.();
      }
    }

    tick();
    const id = setInterval(tick, 250);
    return () => clearInterval(id);
  }, [endsAt, onComplete]);

  const percent = Math.max(0, Math.min(100, (remaining / totalSeconds) * 100));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm text-mystery-200">
        <span>Time</span>
        <span className="font-semibold tabular-nums">{remaining}s</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-mystery-800">
        <div
          className="h-full rounded-full bg-amber-300 transition-[width]"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
