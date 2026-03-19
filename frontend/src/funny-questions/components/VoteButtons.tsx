import type { PlayerInfo } from "@shared/types/game";

interface Props {
  players: PlayerInfo[];
  myId: string;
  selected: string | null;
  onSelect: (id: string) => void;
  disabled: boolean;
}

export default function VoteButtons({ players, myId, selected, onSelect, disabled }: Props) {
  return (
    <div className="space-y-2">
      {players.map((p) => (
        <button
          key={p.id}
          onClick={() => onSelect(p.id)}
          disabled={disabled}
          className={`w-full p-3 rounded-xl text-left transition ${
            selected === p.id
              ? "bg-mystery-500 ring-2 ring-mystery-300"
              : "bg-mystery-800 hover:bg-mystery-700"
          } disabled:opacity-50`}
        >
          <span className="font-semibold">{p.name}</span>
          {p.id === myId && (
            <span className="text-mystery-400 text-sm ml-2">(you)</span>
          )}
        </button>
      ))}
    </div>
  );
}
