import type { Bundle } from "../types/game";
import { RESOURCE_META, bundleEntries } from "./resources";

interface Props {
  available: Bundle;
  value: Bundle;
  onChange: (value: Bundle) => void;
  // Resources to flag as needed for upkeep so players don't sell them by accident.
  needed?: Bundle;
  // Arrives before that upkeep is paid (e.g. next round's production at Cleanup).
  // When given, each row also shows how many are spare.
  incoming?: Bundle;
}

/** Stepper per owned resource, bounded by what the player actually has. */
export default function BundlePicker({ available, value, onChange, needed = {}, incoming }: Props) {
  const entries = bundleEntries(available);
  if (!entries.length) return <p className="text-mystery-400">Your storehouse is empty.</p>;

  function set(r: keyof Bundle, n: number) {
    onChange({ ...value, [r]: Math.max(0, Math.min(n, available[r] ?? 0)) });
  }

  return (
    <ul className="space-y-2">
      {entries.map(([r, have]) => {
        const picked = value[r] ?? 0;
        const need = needed[r] ?? 0;
        const arriving = incoming?.[r] ?? 0;
        const spare = Math.max(0, have + arriving - need);
        const eatsUpkeep = need > 0 && have - picked + arriving < need;
        return (
          <li key={r} className="flex items-center gap-3 rounded-xl bg-mystery-900/60 px-3 py-2">
            <span className="text-2xl">{RESOURCE_META[r].icon}</span>
            <div className="flex-1">
              <p className="font-medium text-white">{RESOURCE_META[r].label}</p>
              <p className={`text-xs ${eatsUpkeep ? "text-amber-300" : "text-mystery-400"}`}>
                have {have}
                {incoming && arriving > 0 && ` · +${arriving} next round`}
                {need > 0 && ` · ${incoming ? "next " : ""}upkeep needs ${need}`}
                {eatsUpkeep && " — you'd fall short"}
              </p>
              {incoming && (
                <p className={`text-xs font-semibold ${spare > 0 ? "text-emerald-300" : "text-mystery-500"}`}>
                  {spare > 0 ? `spare ${spare} — safe to drop` : "keep all"}
                </p>
              )}
            </div>
            <button
              onClick={() => set(r, picked - 1)}
              disabled={picked === 0}
              className="h-10 w-10 rounded-lg bg-mystery-700 text-xl font-bold disabled:opacity-30"
            >
              −
            </button>
            <span className="w-6 text-center text-lg font-bold">{picked}</span>
            <button
              onClick={() => set(r, picked + 1)}
              disabled={picked >= have}
              className="h-10 w-10 rounded-lg bg-mystery-700 text-xl font-bold disabled:opacity-30"
            >
              +
            </button>
          </li>
        );
      })}
    </ul>
  );
}
