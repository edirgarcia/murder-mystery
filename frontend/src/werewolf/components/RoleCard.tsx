import type { Role } from "../types/game";

const ROLE_TEXT: Record<Role, { title: string; text: string }> = {
  villager: { title: "Villager", text: "Find and eliminate all werewolves." },
  werewolf: { title: "Werewolf", text: "Blend in by day and hunt by night." },
  seer: { title: "Seer", text: "Investigate one player each night." },
  witch: { title: "Witch", text: "Use one heal and one poison in the whole game." },
  hunter: { title: "Hunter", text: "If you die, you may shoot one player." },
  cupid: { title: "Cupid", text: "Link two lovers at game start." },
};

export default function RoleCard({ role, alive }: { role: Role | null; alive: boolean }) {
  if (!role) return null;
  const info = ROLE_TEXT[role];
  return (
    <div className="bg-mystery-800 rounded-2xl p-5 shadow-xl border border-mystery-700">
      <p className="text-xs uppercase tracking-wider text-mystery-400">Your role</p>
      <h2 className="text-2xl font-bold text-mystery-200 mt-1">{info.title}</h2>
      <p className="text-mystery-300 mt-2 text-sm">{info.text}</p>
      <p className={`mt-3 text-sm font-semibold ${alive ? "text-emerald-300" : "text-red-300"}`}>
        {alive ? "Alive" : "Dead"}
      </p>
    </div>
  );
}
