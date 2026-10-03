import type { Bundle, Resource } from "../types/game";
import { RESOURCE_META, bundleEntries } from "./resources";

interface Props {
  bundle: Bundle | null | undefined;
  empty?: string;
  size?: "sm" | "md" | "lg";
  // Resources to outline (e.g. what you need for upkeep).
  highlight?: Resource[];
}

const SIZES = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-4 py-2 text-xl",
};

export default function ResourceBundle({ bundle, empty = "—", size = "md", highlight = [] }: Props) {
  const entries = bundleEntries(bundle);
  if (!entries.length) return <span className="text-mystery-400">{empty}</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([r, n]) => (
        <span
          key={r}
          title={RESOURCE_META[r].label}
          className={`inline-flex items-center gap-1 rounded-full border font-semibold ${SIZES[size]} ${
            RESOURCE_META[r].chip
          } ${highlight.includes(r) ? "ring-2 ring-amber-300" : ""}`}
        >
          <span>{RESOURCE_META[r].icon}</span>
          <span>{n}</span>
          {size !== "sm" && <span className="font-normal opacity-80">{RESOURCE_META[r].label}</span>}
        </span>
      ))}
    </div>
  );
}
