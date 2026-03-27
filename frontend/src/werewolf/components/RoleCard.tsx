import { useState, useMemo } from "react";
import type { Role } from "../types/game";

const ROLE_TEXT: Record<Role, { title: string; text: string }> = {
  villager: { title: "Villager", text: "Find and eliminate all werewolves." },
  werewolf: { title: "Werewolf", text: "Blend in by day and hunt by night." },
  seer: { title: "Seer", text: "Investigate one player each night." },
  witch: { title: "Witch", text: "Use one heal and one poison in the whole game." },
  hunter: { title: "Hunter", text: "If you die, you may shoot one player." },
  cupid: { title: "Cupid", text: "Link two lovers at game start." },
};

const ROLE_IMAGE: Record<Role, string | string[]> = {
  werewolf: "wolf.png",
  seer: "sorceress.png",
  witch: "witch.png",
  hunter: "hunter.png",
  cupid: "cupid.png",
  villager: Array.from({ length: 9 }, (_, i) => `villager${i}.png`),
};

function getRoleImage(role: Role, seed: string): string {
  const img = ROLE_IMAGE[role];
  if (typeof img === "string") return `/werewolf/images/${img}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  return `/werewolf/images/${img[Math.abs(hash) % img.length]}`;
}

export default function RoleCard({ role, alive, isAlpha, playerId }: { role: Role | null; alive: boolean; isAlpha?: boolean; playerId?: string }) {
  const [open, setOpen] = useState(false);
  if (!role) return null;
  const info = ROLE_TEXT[role];
  const imageSrc = useMemo(() => getRoleImage(role, playerId ?? ""), [role, playerId]);
  return (
    <div className="bg-mystery-800 rounded-2xl shadow-xl border border-mystery-700 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4"
      >
        <span className="text-xs uppercase tracking-wider text-mystery-400">
          Tap to {open ? "hide" : "reveal"} your role
        </span>
        <span className="text-mystery-400 text-lg">{open ? "\u25B2" : "\u25BC"}</span>
      </button>
      {open && (
        <>
          <img src={imageSrc} alt={info.title} className="w-full aspect-square object-cover" />
          <div className="p-5">
            <h2 className="text-2xl font-bold text-mystery-200">
              {info.title}
              {isAlpha && <span className="ml-2" title="Alpha Wolf">&#x1F451;</span>}
            </h2>
            <p className="text-mystery-300 mt-2 text-sm">{info.text}</p>
            <p className={`mt-3 text-sm font-semibold ${alive ? "text-emerald-300" : "text-red-300"}`}>
              {alive ? "Alive" : "Dead"}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
