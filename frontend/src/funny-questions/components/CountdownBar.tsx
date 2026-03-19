import { useState, useEffect } from "react";

interface Props {
  endsAt: string;
  totalSeconds: number;
}

export default function CountdownBar({ endsAt, totalSeconds }: Props) {
  const [remaining, setRemaining] = useState(totalSeconds);

  useEffect(() => {
    const endTime = new Date(endsAt).getTime();
    const tick = () => {
      const left = Math.max(0, (endTime - Date.now()) / 1000);
      setRemaining(left);
    };
    tick();
    const id = setInterval(tick, 50);
    return () => clearInterval(id);
  }, [endsAt]);

  const fraction = Math.max(0, Math.min(1, remaining / totalSeconds));

  return (
    <div className="w-full">
      <div className="flex justify-between text-sm text-mystery-400 mb-1">
        <span>Time to vote</span>
        <span>{Math.ceil(remaining)}s</span>
      </div>
      <div className="h-2 bg-mystery-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-100 ${
            remaining <= 2 ? "bg-red-500" : "bg-mystery-500"
          }`}
          style={{ width: `${fraction * 100}%` }}
        />
      </div>
    </div>
  );
}
