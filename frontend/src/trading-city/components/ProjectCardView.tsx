import type { ReactNode } from "react";
import type { ProjectCard, ProjectCategory } from "../types/game";
import ResourceBundle from "./ResourceBundle";

export const CATEGORY_STYLE: Record<ProjectCategory, { label: string; border: string; badge: string }> = {
  city: { label: "City", border: "border-emerald-400/30", badge: "bg-emerald-500/20 text-emerald-100" },
  market: { label: "Market", border: "border-sky-400/30", badge: "bg-sky-500/20 text-sky-100" },
  prestige: { label: "Prestige", border: "border-amber-300/40", badge: "bg-amber-400/20 text-amber-100" },
};

interface Props {
  card: ProjectCard | null;
  category: ProjectCategory;
  affordable?: boolean;
  compact?: boolean;
  action?: ReactNode;
}

export default function ProjectCardView({ card, category, affordable, compact, action }: Props) {
  const style = CATEGORY_STYLE[category];
  if (!card) {
    return (
      <div className={`rounded-2xl border border-dashed ${style.border} p-3 text-sm text-mystery-500`}>
        {style.label} slot — empty until next round
      </div>
    );
  }
  return (
    <div
      className={`rounded-2xl border ${style.border} bg-mystery-800/80 p-3 ${
        affordable ? "ring-2 ring-emerald-400/70" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider ${style.badge}`}>
            {style.label}
            {card.tier ? ` · ${card.tier}` : ""}
          </span>
          <p className={`mt-1 font-semibold text-white ${compact ? "text-sm" : "text-base"}`}>{card.name}</p>
        </div>
        {card.vp > 0 && (
          <span className="shrink-0 rounded-lg bg-amber-400/20 px-2 py-1 text-sm font-bold text-amber-200">
            {card.vp} VP
          </span>
        )}
      </div>
      {card.effect && <p className="mt-1 text-sm text-mystery-200">{card.effect}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <ResourceBundle bundle={card.cost} size="sm" />
        {card.cash_cost > 0 && (
          <span className="rounded-full border border-emerald-400/30 bg-emerald-500/15 px-2 py-0.5 text-xs font-semibold text-emerald-200">
            ${card.cash_cost}
          </span>
        )}
      </div>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
