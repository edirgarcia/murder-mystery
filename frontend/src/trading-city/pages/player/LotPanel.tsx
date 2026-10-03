import { useState } from "react";
import { submitLot } from "../../api/http";
import BundlePicker from "../../components/BundlePicker";
import ResourceBundle from "../../components/ResourceBundle";
import { bundleSize } from "../../components/resources";
import type { Bundle, CityView, PrivateState } from "../../types/game";
import { useAction } from "./useAction";

interface Props {
  code: string;
  playerId: string;
  city: CityView;
  priv: PrivateState;
}

/** Secretly commit one surplus lot — locked once submitted (spec §13-§14). */
export default function LotPanel({ code, playerId, city, priv }: Props) {
  const [lot, setLot] = useState<Bundle>({});
  const { run, busy, error } = useAction();

  if (priv.lot_submitted) {
    return (
      <div className="space-y-2">
        <p className="font-semibold text-white">🔒 Locked in</p>
        <ResourceBundle bundle={priv.lot} empty="No lot this round" />
        <p className="text-sm text-mystery-400">Waiting for the other cities…</p>
      </div>
    );
  }

  const size = bundleSize(lot);
  return (
    <div className="space-y-3">
      <p className="text-sm text-mystery-300">
        Pick what to put up for auction. Contents stay hidden until the lot is revealed. You can't
        resell anything you buy this round.
      </p>
      <BundlePicker available={priv.inventory} value={lot} onChange={setLot} needed={city.upkeep} />
      {error && <p className="text-sm text-red-300">{error}</p>}
      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={() => run(() => submitLot(code, playerId, {}))}
          className="flex-1 rounded-xl bg-mystery-700 py-3 font-semibold text-mystery-100 disabled:opacity-40"
        >
          No lot
        </button>
        <button
          disabled={busy || size === 0}
          onClick={() => run(() => submitLot(code, playerId, lot))}
          className="flex-[2] rounded-xl bg-amber-600 py-3 font-semibold text-white disabled:opacity-40"
        >
          Lock lot ({size})
        </button>
      </div>
    </div>
  );
}
