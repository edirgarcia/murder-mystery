import { discard, markReady } from "../../api/http";
import BundlePicker from "../../components/BundlePicker";
import ResourceBundle from "../../components/ResourceBundle";
import { bundleSize } from "../../components/resources";
import type { Bundle, CityView, PrivateState, PublicState } from "../../types/game";
import { useState } from "react";
import { useAction } from "./useAction";

/** Summary screens move on once every player taps Continue (or the timer runs out). */
export function ContinueButton({ code, playerId, pub, city }: Props) {
  const { run, busy } = useAction();
  if (!pub.ready) return null;
  const humans = pub.cities.filter((c) => !c.is_ai).length;
  if (pub.ready.includes(city.slot)) {
    const waiting = humans - pub.ready.length;
    return (
      <p className="text-center text-sm text-mystery-400">
        {waiting > 0 ? `Waiting for ${waiting} other player${waiting > 1 ? "s" : ""}…` : "Moving on…"}
      </p>
    );
  }
  return (
    <button
      disabled={busy}
      onClick={() => run(() => markReady(code, playerId))}
      className="w-full rounded-xl bg-teal-600 py-3 font-semibold text-white disabled:opacity-40"
    >
      Continue
    </button>
  );
}

interface Props {
  code: string;
  playerId: string;
  pub: PublicState;
  city: CityView;
}

export function ProductionSummary({ code, playerId, pub, city }: Props) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-mystery-300">Income +${pub.cities[city.slot].income} and your city produced:</p>
      <ResourceBundle bundle={pub.last_production[city.slot]} empty="Nothing" />
      {city.shortage > 0 && (
        <p className="text-sm text-red-300">
          ⚠ {city.shortage} shortage cut your {city.primary_resource} output.
        </p>
      )}
      <ContinueButton code={code} playerId={playerId} pub={pub} city={city} />
    </div>
  );
}

export function UpkeepSummary({ priv, ...props }: Props & { priv: PrivateState }) {
  const u = priv.last_upkeep;
  if (!u) return null;
  return (
    <div className="space-y-3">
      <p className="text-sm text-mystery-300">Your city consumed:</p>
      <ResourceBundle bundle={u.paid} empty="Nothing" />
      {u.missing === 0 ? (
        <p className="font-semibold text-emerald-300">✓ Upkeep met — all shortages cleared.</p>
      ) : (
        <p className="font-semibold text-red-300">
          ✗ Missing {u.missing} unit{u.missing > 1 ? "s" : ""} — now at {u.shortage_after} shortage.
        </p>
      )}
      <ContinueButton {...props} />
    </div>
  );
}

export function DiscardPanel({ code, playerId, priv }: { code: string; playerId: string; priv: PrivateState }) {
  const [pick, setPick] = useState<Bundle>({});
  const { run, busy, error } = useAction();
  if (!priv.discard_required) {
    return bundleSize(priv.last_discards) > 0 ? (
      <div className="space-y-2">
        <p className="text-sm text-mystery-300">Discarded over storage:</p>
        <ResourceBundle bundle={priv.last_discards} />
      </div>
    ) : (
      <p className="text-mystery-300">Storage OK. Waiting for the next round…</p>
    );
  }
  const size = bundleSize(pick);
  return (
    <div className="space-y-3">
      <p className="text-amber-200">
        Over storage — discard {priv.discard_required}. (If time runs out, your largest stacks are trimmed.)
      </p>
      <div className="grid gap-2 rounded-xl bg-mystery-900/60 p-3 text-sm">
        <div>
          <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">Next round you'll produce</p>
          <ResourceBundle bundle={priv.next_production} size="sm" empty="Nothing" />
        </div>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">Next upkeep needs</p>
          <ResourceBundle bundle={priv.next_upkeep} size="sm" empty="Nothing" />
        </div>
      </div>
      <BundlePicker
        available={priv.inventory}
        value={pick}
        onChange={setPick}
        needed={priv.next_upkeep}
        incoming={priv.next_production}
      />
      {error && <p className="text-sm text-red-300">{error}</p>}
      <button
        disabled={busy || size !== priv.discard_required}
        onClick={() => run(() => discard(code, playerId, pick))}
        className="w-full rounded-xl bg-red-600 py-3 font-semibold text-white disabled:opacity-40"
      >
        Discard {size} / {priv.discard_required}
      </button>
    </div>
  );
}
