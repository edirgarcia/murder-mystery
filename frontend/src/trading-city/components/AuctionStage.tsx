import type { PublicState } from "../types/game";
import Countdown from "./Countdown";
import { merchantLabel, who } from "./labels";
import ResourceBundle from "./ResourceBundle";
import SellerTag from "./SellerTag";

interface Props {
  pub: PublicState;
  clockOffset: number;
  big?: boolean;
  // City slot of whoever is looking at this screen (players), so their own lot says "You".
  viewerSlot?: number;
}

/** The lot currently on the block — fully public (spec §21). */
export default function AuctionStage({ pub, clockOffset, big, viewerSlot }: Props) {
  const a = pub.auction;
  const name = (slot: number) => who(pub.cities[slot]);

  if (!a) {
    const last = pub.history[pub.history.length - 1];
    if (last && last.round === pub.round) {
      return (
        <div className="text-center">
          <p className="text-sm uppercase tracking-widest text-mystery-400">Lot closed</p>
          <div className="mt-3 flex justify-center">
            <SellerTag city={pub.cities[last.seller]} isYou={last.seller === viewerSlot} size={big ? "lg" : "sm"} />
          </div>
          <div className="my-3 flex justify-center">
            <ResourceBundle bundle={last.contents} size={big ? "lg" : "md"} />
          </div>
          <p className={`font-bold ${big ? "text-4xl" : "text-2xl"} ${last.winner === null ? "text-mystery-400" : "text-emerald-300"}`}>
            {last.winner === null ? "Unsold — returned to the seller" : `Sold to ${merchantLabel(pub.cities[last.winner])} for $${last.price}`}
          </p>
        </div>
      );
    }
    return <p className="text-center text-mystery-300">Shuffling lots…</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm uppercase tracking-widest text-mystery-400">
          Lot {a.number} of {a.total}
        </p>
        <Countdown
          endsAt={a.ends_at}
          clockOffset={clockOffset}
          urgentBelow={pub.rules.anti_snipe_window_seconds}
          className={big ? "text-5xl" : "text-3xl"}
        />
      </div>
      <div className="flex flex-col items-center gap-3 py-2">
        <SellerTag city={pub.cities[a.seller]} isYou={a.seller === viewerSlot} size={big ? "lg" : "sm"} />
        <ResourceBundle bundle={a.contents} size={big ? "lg" : "md"} />
      </div>
      <div className="text-center">
        {a.high_bid === null ? (
          <p className={`${big ? "text-4xl" : "text-2xl"} font-bold text-mystery-300`}>
            No bids — opens at ${a.min_next_bid}
          </p>
        ) : (
          <>
            <p className={`${big ? "text-7xl" : "text-5xl"} font-black text-emerald-300`}>${a.high_bid}</p>
            <p className={`${big ? "text-2xl" : "text-lg"} text-white`}>{name(a.high_bidder!)}</p>
          </>
        )}
      </div>
      {a.bids.length > 0 && (
        <p className="text-center text-sm text-mystery-400">
          {a.bids.map((b) => `${name(b.bidder)} $${b.amount}`).join(" → ")}
        </p>
      )}
      {a.passed.some((s) => !pub.cities[s]?.is_ai) && (
        <p className="text-center text-xs text-mystery-500">
          Out: {a.passed.filter((s) => !pub.cities[s]?.is_ai).map(name).join(", ")}
        </p>
      )}
      <p className="text-center text-xs text-mystery-500">
        Bids in the last {pub.rules.anti_snipe_window_seconds}s add {pub.rules.anti_snipe_extension_seconds}s
      </p>
    </div>
  );
}
