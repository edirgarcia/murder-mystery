import type { ReactNode } from "react";
import type { CityView, Resource } from "../types/game";
import BuiltProjects from "./BuiltProjects";
import ResourceBundle from "./ResourceBundle";

interface Props {
  city: CityView;
  highlight?: boolean;
  showEconomy?: boolean;
  children?: ReactNode;
}

/** Upkeep resources the city doesn't produce (its structural trade dependency). */
export function importNeeds(city: CityView): Resource[] {
  return (Object.keys(city.base_upkeep) as Resource[]).filter((r) => !city.base_production[r]);
}

export default function CityCard({ city, highlight, showEconomy = true, children }: Props) {
  return (
    <div
      className={`rounded-2xl border bg-mystery-800/80 p-4 ${
        highlight ? "border-amber-300/60 ring-1 ring-amber-300/40" : "border-white/10"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-widest text-mystery-400">{city.profile} city</p>
          <p className="text-lg font-semibold text-white">{city.name}</p>
          <p className="text-sm text-mystery-300">
            {city.is_ai ? "🤖 AI" : city.owner_name ? `👤 ${city.owner_name}` : "Unclaimed"}
          </p>
        </div>
        {showEconomy && (
          <div className="text-right text-sm">
            <p className="font-bold text-emerald-300">${city.cash}</p>
            <p className="text-amber-200">{city.vp} VP</p>
            {city.shortage > 0 && <p className="text-red-300">⚠ {city.shortage} shortage</p>}
          </div>
        )}
      </div>
      <div className="mt-3 space-y-2 text-sm">
        <div>
          <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">Produces / round</p>
          <ResourceBundle bundle={showEconomy ? city.production : city.base_production} size="sm" />
        </div>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">Upkeep / round</p>
          <ResourceBundle
            bundle={showEconomy ? city.upkeep : city.base_upkeep}
            size="sm"
            highlight={importNeeds(city)}
          />
        </div>
        {showEconomy && (
          <div>
            <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">Projects</p>
            <BuiltProjects city={city} />
          </div>
        )}
      </div>
      {children}
    </div>
  );
}
