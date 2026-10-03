import type { MarketLevel, PublicState } from "../types/game";
import { RESOURCES } from "../types/game";
import { RESOURCE_META } from "./resources";

const LEVEL_STYLE: Record<MarketLevel, string> = {
  up: "bg-emerald-500/25 text-emerald-200",
  neutral: "text-mystery-500",
  down: "bg-red-500/25 text-red-200",
};

const LEVEL_TEXT: Record<MarketLevel, string> = { up: "▲ Up", neutral: "—", down: "▼ Down" };

/** Global Supply / Demand state per resource (spec §31). */
export default function MarketBoard({ pub }: { pub: PublicState }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase tracking-wider text-mystery-400">
          <th className="py-1">Resource</th>
          <th className="py-1 text-center">Supply</th>
          <th className="py-1 text-center">Demand</th>
        </tr>
      </thead>
      <tbody>
        {RESOURCES.map((r) => {
          const m = pub.market[r];
          return (
            <tr key={r} className="border-t border-white/5">
              <td className="py-1.5">
                {RESOURCE_META[r].icon} {RESOURCE_META[r].label}
              </td>
              {(["supply", "demand"] as const).map((axis) => {
                const slot = m[axis];
                const pending = slot.pending_level !== slot.level;
                return (
                  <td key={axis} className="py-1 text-center">
                    <span
                      title={slot.card_name ?? undefined}
                      className={`rounded-md px-2 py-0.5 font-semibold ${LEVEL_STYLE[slot.level]}`}
                    >
                      {LEVEL_TEXT[slot.level]}
                    </span>
                    {pending && (
                      <span className="ml-1 text-xs text-amber-300">→ {LEVEL_TEXT[slot.pending_level]}</span>
                    )}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
