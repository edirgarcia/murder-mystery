import type { PublicState } from "../types/game";
import { merchantLabel, who } from "./labels";
import ResourceBundle from "./ResourceBundle";
import SellerTag from "./SellerTag";

/** Completed lots, newest first (spec §51). */
export default function AuctionHistory({
  pub,
  limit,
  viewerSlot,
}: {
  pub: PublicState;
  limit?: number;
  viewerSlot?: number;
}) {
  const name = (slot: number | null) => (slot === null ? "" : who(pub.cities[slot]));
  const records = [...pub.history].reverse().slice(0, limit);
  if (!records.length) return <p className="text-sm text-mystery-400">No lots auctioned yet.</p>;
  return (
    <ul className="space-y-2">
      {records.map((r) => (
        <li key={r.lot_id} className="rounded-xl bg-mystery-900/60 px-3 py-2 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-2 text-mystery-400">
              R{r.round}
              <SellerTag city={pub.cities[r.seller]} isYou={r.seller === viewerSlot} />
            </span>
            {r.winner === null ? (
              <span className="text-mystery-500">unsold</span>
            ) : (
              <span className="font-semibold text-emerald-300">
                Sold to {merchantLabel(pub.cities[r.winner])} for ${r.price}
              </span>
            )}
          </div>
          <div className="mt-1">
            <ResourceBundle bundle={r.contents} size="sm" />
          </div>
          {r.bids.length > 1 && (
            <p className="mt-1 text-xs text-mystery-400">
              {r.bids.map((b) => `${name(b.bidder)} $${b.amount}`).join(" → ")}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
