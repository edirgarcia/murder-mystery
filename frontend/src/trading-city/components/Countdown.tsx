import { useEffect, useState } from "react";

interface Props {
  endsAt: string | null;
  // serverTime - clientTime (ms)
  clockOffset: number;
  className?: string;
  urgentBelow?: number;
}

export function useSecondsLeft(endsAt: string | null, clockOffset: number): number | null {
  const [left, setLeft] = useState<number | null>(null);
  useEffect(() => {
    if (!endsAt) {
      setLeft(null);
      return;
    }
    const end = new Date(endsAt).getTime();
    const tick = () => setLeft(Math.max(0, (end - (Date.now() + clockOffset)) / 1000));
    tick();
    const id = setInterval(tick, 100);
    return () => clearInterval(id);
  }, [endsAt, clockOffset]);
  return left;
}

export default function Countdown({ endsAt, clockOffset, className = "", urgentBelow = 5 }: Props) {
  const left = useSecondsLeft(endsAt, clockOffset);
  if (left === null) return null;
  return (
    <span
      className={`tabular-nums font-bold ${left <= urgentBelow ? "text-red-400" : "text-amber-200"} ${className}`}
    >
      {Math.ceil(left)}s
    </span>
  );
}
