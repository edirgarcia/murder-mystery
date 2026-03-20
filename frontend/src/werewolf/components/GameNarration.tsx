import type { DaySubPhase, NightSubPhase } from "../types/game";

export default function GameNarration({ nightSubPhase, daySubPhase }: { nightSubPhase: NightSubPhase | null; daySubPhase: DaySubPhase | null }) {
  const text = nightSubPhase
    ? `Night phase: ${nightSubPhase}`
    : daySubPhase
      ? `Day phase: ${daySubPhase}`
      : "Waiting for next phase";

  return <p className="text-mystery-300">{text}</p>;
}
