import type { Role, WolfPackMember, WWPlayerInfo } from "../types/game";

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
  wolfPreselections,
  packMembers,
  alphaWolfId,
  myId,
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
  wolfPreselections?: Record<string, string>;
  packMembers?: WolfPackMember[];
  alphaWolfId?: string | null;
  myId?: string | null;
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

      {role === "werewolf" && packMembers && wolfPreselections && (
        <div className="space-y-1 mt-3 pt-3 border-t border-mystery-700">
          <p className="text-xs uppercase tracking-wider text-mystery-400">Pack selections</p>
          {packMembers
            .filter((w) => w.id !== myId)
            .map((w) => {
              const preselectedTarget = wolfPreselections[w.id];
              const targetPlayer = preselectedTarget
                ? players.find((p) => p.id === preselectedTarget)
                : null;
              const isAlpha = w.id === alphaWolfId;
              return (
                <div key={w.id} className="flex items-center gap-2 text-sm text-mystery-300">
                  {isAlpha && <span title="Alpha Wolf">&#x1F451;</span>}
                  <span className="font-medium">{w.name}</span>
                  <span className="text-mystery-500">&rarr;</span>
                  <span className={targetPlayer ? "text-red-300" : "text-mystery-500 italic"}>
                    {targetPlayer ? targetPlayer.name : "undecided"}
                  </span>
                </div>
              );
            })}
        </div>
      )}

      <button onClick={onSubmit} disabled={!selected || disabled} className="w-full rounded-xl p-3 bg-red-600 disabled:opacity-40">
        Submit Action
      </button>
    </div>
  );
}
