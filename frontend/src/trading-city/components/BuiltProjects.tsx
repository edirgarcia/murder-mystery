import type { CityView } from "../types/game";

/** Everything a city has built, with what each project does. */
export default function BuiltProjects({ city, empty = "No projects yet" }: { city: CityView; empty?: string }) {
  const items = [...city.projects, ...city.market_projects].sort((a, b) => a.round_built - b.round_built);
  if (!items.length) return <p className="text-sm text-mystery-500">{empty}</p>;
  return (
    <ul className="space-y-1">
      {items.map((p, i) => {
        const replaced = "active" in p && !p.active;
        return (
          <li key={`${p.id}-${i}`} className={`flex flex-wrap items-baseline gap-x-2 text-sm ${replaced ? "opacity-50" : ""}`}>
            <span className={`font-semibold text-white ${replaced ? "line-through" : ""}`}>{p.name}</span>
            {p.effect && <span className="text-mystery-300">— {p.effect}</span>}
            {p.vp > 0 && <span className="font-semibold text-amber-200">+{p.vp} VP</span>}
            {replaced && <span className="text-xs text-mystery-400">(replaced)</span>}
          </li>
        );
      })}
    </ul>
  );
}
