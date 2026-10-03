import { useState } from "react";
import { passAuction, placeBid } from "../../api/http";
import AuctionStage from "../../components/AuctionStage";
import type { CityView, PublicState } from "../../types/game";
import { useAction } from "./useAction";

interface Props {
  code: string;
  playerId: string;
  pub: PublicState;
  city: CityView;
  clockOffset: number;
}

export default function BidPanel({ code, playerId, pub, city, clockOffset }: Props) {
  const { run, busy, error } = useAction();
  const [custom, setCustom] = useState("");
  const a = pub.auction;

  let blocked: string | null = null;
  if (a) {
    if (a.seller === city.slot) blocked = "This is your lot — you can't bid on it.";
    else if (a.high_bidder === city.slot) blocked = "You're the high bidder.";
    else if (a.passed.includes(city.slot)) blocked = "You passed on this lot.";
    else if (city.cash < a.min_next_bid) blocked = `You can't cover $${a.min_next_bid}.`;
  }

  const bid = (amount: number) => run(() => placeBid(code, playerId, amount));
  const quick = a ? [...new Set([a.min_next_bid, a.min_next_bid + 1, a.min_next_bid + 4])].filter((n) => n <= city.cash) : [];

  return (
    <div className="space-y-4">
      <AuctionStage pub={pub} clockOffset={clockOffset} viewerSlot={city.slot} />
      {a && (
        <div className="space-y-2 border-t border-white/10 pt-3">
          <p className="text-center text-sm text-mystery-300">Your cash: ${city.cash}</p>
          {blocked ? (
            <p className="text-center text-mystery-300">{blocked}</p>
          ) : (
            <>
              <div className="flex gap-2">
                {quick.map((amount) => (
                  <button
                    key={amount}
                    disabled={busy}
                    onClick={() => bid(amount)}
                    className="flex-1 rounded-xl bg-emerald-600 py-3 text-lg font-bold text-white disabled:opacity-40"
                  >
                    ${amount}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  inputMode="numeric"
                  min={a.min_next_bid}
                  max={city.cash}
                  placeholder={`$${a.min_next_bid}–${city.cash}`}
                  value={custom}
                  onChange={(e) => setCustom(e.target.value)}
                  className="w-full flex-1 rounded-xl border border-white/10 bg-mystery-900 px-3 py-2 text-white"
                />
                <button
                  disabled={busy || !custom}
                  onClick={() => {
                    bid(Number(custom));
                    setCustom("");
                  }}
                  className="rounded-xl bg-emerald-700 px-4 font-semibold text-white disabled:opacity-40"
                >
                  Bid
                </button>
                <button
                  disabled={busy}
                  onClick={() => run(() => passAuction(code, playerId))}
                  className="rounded-xl bg-mystery-700 px-4 font-semibold text-mystery-100 disabled:opacity-40"
                >
                  I'm out
                </button>
              </div>
            </>
          )}
          {error && <p className="text-center text-sm text-red-300">{error}</p>}
        </div>
      )}
    </div>
  );
}
