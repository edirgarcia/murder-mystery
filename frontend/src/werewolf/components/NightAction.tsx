import type { Role, WWPlayerInfo } from "../types/game";

export default function NightAction({
  role,
  players,
  prompt,
  selected,
  selected2,
  onSelect,
  onSelect2,
  onSubmit,
  disabled,
}: {
  role: Role | null;
  players: WWPlayerInfo[];
  prompt: string;
  selected: string;
  selected2: string;
  onSelect: (id: string) => void;
  onSelect2: (id: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}) {
  const alive = players.filter((p) => p.alive);

  if (!role) return null;

  if (role === "cupid") {
    return (
      <div className="space-y-2">
        <p className="text-sm text-mystery-300">Choose two lovers.</p>
        <select
          className="w-full rounded-xl bg-mystery-700 border border-mystery-600 p-2"
          value={selected}
          onChange={(e) => onSelect(e.target.value)}
        >
          <option value="">First lover</option>
          {alive.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          className="w-full rounded-xl bg-mystery-700 border border-mystery-600 p-2"
          value={selected2}
          onChange={(e) => onSelect2(e.target.value)}
        >
          <option value="">Second lover</option>
          {alive.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <button onClick={onSubmit} disabled={!selected || !selected2 || selected === selected2 || disabled} className="w-full rounded-xl p-3 bg-red-600 disabled:opacity-40">
          Confirm Lovers
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-mystery-300">{prompt}</p>
      <select
        className="w-full rounded-xl bg-mystery-700 border border-mystery-600 p-2"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
      >
        <option value="">Pick target</option>
        {alive.map((p) => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
      <button onClick={onSubmit} disabled={!selected || disabled} className="w-full rounded-xl p-3 bg-red-600 disabled:opacity-40">
        Submit Action
      </button>
    </div>
  );
}
