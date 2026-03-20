import type { WWPlayerInfo } from "../types/game";

export default function PlayerGrid({ players }: { players: WWPlayerInfo[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {players.map((p) => (
        <div
          key={p.id}
          className={`rounded-xl px-3 py-2 text-sm border ${
            p.alive ? "bg-mystery-700 border-mystery-600 text-mystery-100" : "bg-mystery-900 border-mystery-800 text-mystery-400 line-through"
          }`}
        >
          {p.name}
        </div>
      ))}
    </div>
  );
}
