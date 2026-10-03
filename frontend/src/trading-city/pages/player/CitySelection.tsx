import { claimCity } from "../../api/http";
import CityCard from "../../components/CityCard";
import type { PublicState } from "../../types/game";
import { useAction } from "./useAction";

interface Props {
  pub: PublicState;
  code: string;
  playerId: string;
}

/** All cities shown at once; first valid claim wins (spec §6). */
export default function CitySelection({ pub, code, playerId }: Props) {
  const { run, busy, error } = useAction();
  const mine = pub.cities.find((c) => c.owner_id === playerId);

  return (
    <div className="space-y-3">
      <p className="text-sm text-mystery-300">
        {mine
          ? `You run ${mine.name}. Waiting for the other merchants…`
          : "Pick a city. Outlined upkeep is something your city never produces — you'll have to buy it."}
      </p>
      {error && <p className="text-sm text-red-300">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {pub.cities.map((city) => (
          <CityCard key={city.slot} city={city} showEconomy={false} highlight={city.owner_id === playerId}>
            {!mine && !city.owner_id && (
              <button
                disabled={busy}
                onClick={() => run(() => claimCity(code, playerId, city.slot))}
                className="mt-3 w-full rounded-xl bg-amber-600 py-2 font-semibold text-white disabled:opacity-40"
              >
                Claim {city.city_name}
              </button>
            )}
          </CityCard>
        ))}
      </div>
    </div>
  );
}
