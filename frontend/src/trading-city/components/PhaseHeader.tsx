import type { PublicState, RoundPhase } from "../types/game";
import Countdown from "./Countdown";

export const PHASE_LABEL: Record<RoundPhase, string> = {
  city_selection: "Choose Your City",
  production: "Production",
  market_study: "Study the Market",
  lot_creation: "Surplus Lots",
  auction: "Auction",
  projects: "Projects",
  upkeep: "Upkeep",
  cleanup: "Cleanup",
  finished: "Game Over",
};

const STEPS: RoundPhase[] = ["production", "market_study", "lot_creation", "auction", "projects", "upkeep", "cleanup"];

export default function PhaseHeader({ pub, clockOffset }: { pub: PublicState; clockOffset: number }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-mystery-400">
          {pub.round > 0 ? `Round ${pub.round} / ${pub.total_rounds}` : "Setup"}
        </p>
        <p className="text-2xl font-bold text-white">{PHASE_LABEL[pub.phase]}</p>
      </div>
      <div className="flex items-center gap-3">
        {pub.round > 0 && (
          <div className="hidden gap-1 sm:flex">
            {STEPS.map((step) => (
              <span
                key={step}
                className={`h-1.5 w-6 rounded-full ${step === pub.phase ? "bg-amber-300" : "bg-mystery-700"}`}
              />
            ))}
          </div>
        )}
        <Countdown endsAt={pub.deadline} clockOffset={clockOffset} className="text-2xl" />
      </div>
    </div>
  );
}
