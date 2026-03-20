import type { WWPlayerInfo } from "../types/game";

export default function DayVote({
  players,
  selected,
  onSelect,
  disabled,
}: {
  players: WWPlayerInfo[];
  selected: string;
  onSelect: (target: string) => void;
  disabled?: boolean;
}) {
  const alive = players.filter((p) => p.alive);

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {alive.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            disabled={disabled}
            className={`rounded-xl p-2 text-sm transition border ${
              selected === p.id
                ? "bg-red-600 border-red-400 text-white"
                : "bg-mystery-700 border-mystery-600 text-mystery-200 hover:bg-mystery-600"
            }`}
          >
            {p.name}
          </button>
        ))}
      </div>

      <button
        onClick={() => onSelect("skip")}
        disabled={disabled}
        className={`w-full rounded-xl p-2 text-sm transition border ${
          selected === "skip"
            ? "bg-mystery-500 border-mystery-300 text-white"
            : "bg-mystery-700 border-mystery-600 text-mystery-200 hover:bg-mystery-600"
        }`}
      >
        Skip Vote
      </button>
    </div>
  );
}
