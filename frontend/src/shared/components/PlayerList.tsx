import type { PlayerInfo } from "../types/game";

interface Props {
  players: PlayerInfo[];
}

export default function PlayerList({ players }: Props) {
  return (
    <ul className="space-y-2">
      {players.map((p) => (
        <li
          key={p.id}
          className="flex items-center justify-between bg-mystery-700/50 rounded-xl px-4 py-3"
        >
          <span className="text-mystery-200 font-medium">{p.name}</span>
        </li>
      ))}
    </ul>
  );
}
