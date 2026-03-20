import { useEffect, useState } from "react";

interface Props {
  endsAt: string;
  totalSeconds: number;
  label: string;
}

export default function CountdownBar({ endsAt, totalSeconds, label }: Props) {
  const [remaining, setRemaining] = useState(totalSeconds);

  useEffect(() => {
    const endTime = new Date(endsAt).getTime();
    const tick = () => {
      const left = Math.max(0, (endTime - Date.now()) / 1000);
      setRemaining(left);
    };
    tick();
    const id = setInterval(tick, 100);
    return () => clearInterval(id);
  }, [endsAt]);

  const fraction = Math.max(0, Math.min(1, remaining / totalSeconds));

  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-sm text-mystery-300">
        <span>{label}</span>
        <span>{Math.ceil(remaining)}s</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-mystery-800">
        <div
          className={`h-full rounded-full transition-all duration-100 ${
            remaining <= 5 ? "bg-red-500" : "bg-mystery-500"
          }`}
          style={{ width: `${fraction * 100}%` }}
        />
      </div>
    </div>
  );
}
