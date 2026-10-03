import type { Bundle, Resource } from "../types/game";
import { RESOURCES } from "../types/game";

export const RESOURCE_META: Record<Resource, { label: string; icon: string; chip: string }> = {
  grain: { label: "Grain", icon: "🌾", chip: "bg-yellow-500/15 text-yellow-100 border-yellow-400/30" },
  livestock: { label: "Livestock", icon: "🐄", chip: "bg-orange-500/15 text-orange-100 border-orange-400/30" },
  timber: { label: "Timber", icon: "🪵", chip: "bg-amber-700/25 text-amber-100 border-amber-600/40" },
  iron: { label: "Iron", icon: "🪨", chip: "bg-slate-400/15 text-slate-100 border-slate-300/30" },
  cloth: { label: "Cloth", icon: "🧵", chip: "bg-fuchsia-500/15 text-fuchsia-100 border-fuchsia-400/30" },
  tools: { label: "Tools", icon: "🛠️", chip: "bg-sky-500/15 text-sky-100 border-sky-400/30" },
  wine: { label: "Wine", icon: "🍷", chip: "bg-rose-600/20 text-rose-100 border-rose-500/30" },
  spices: { label: "Spices", icon: "🌶️", chip: "bg-red-500/15 text-red-100 border-red-400/30" },
};

export function bundleEntries(bundle: Bundle | null | undefined): [Resource, number][] {
  if (!bundle) return [];
  return RESOURCES.filter((r) => (bundle[r] ?? 0) > 0).map((r) => [r, bundle[r] as number]);
}

export function bundleSize(bundle: Bundle | null | undefined): number {
  return bundleEntries(bundle).reduce((sum, [, n]) => sum + n, 0);
}
