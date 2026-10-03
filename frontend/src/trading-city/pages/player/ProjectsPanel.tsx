import { buildProject, passProject } from "../../api/http";
import ProjectCardView from "../../components/ProjectCardView";
import type { PrivateState, PublicState } from "../../types/game";
import { useAction } from "./useAction";

interface Props {
  code: string;
  playerId: string;
  pub: PublicState;
  priv: PrivateState | null;
  interactive: boolean;
}

/** The 8 visible projects plus the public priority order (spec §23, §26-§27). */
export default function ProjectsPanel({ code, playerId, pub, priv, interactive }: Props) {
  const { run, busy, error } = useAction();
  const myTurn = interactive && pub.phase === "projects" && pub.project_turn_player === playerId;
  const affordable = new Set(priv?.affordable_projects ?? []);

  return (
    <div className="space-y-3">
      <PriorityStrip pub={pub} playerId={playerId} />
      {myTurn && (
        <div className="rounded-xl border border-amber-300/40 bg-amber-400/10 p-3 text-amber-100">
          <p className="font-semibold">Your turn — build one project or pass.</p>
          <button
            disabled={busy}
            onClick={() => run(() => passProject(code, playerId))}
            className="mt-2 w-full rounded-xl bg-mystery-700 py-2 font-semibold text-mystery-100 disabled:opacity-40"
          >
            Pass
          </button>
        </div>
      )}
      {error && <p className="text-sm text-red-300">{error}</p>}
      <div className="grid gap-2 sm:grid-cols-2">
        {pub.project_slots.map((slot) => (
          <ProjectCardView
            key={slot.index}
            card={slot.card}
            category={slot.category}
            affordable={affordable.has(slot.index)}
            action={
              myTurn && slot.card && affordable.has(slot.index) ? (
                <button
                  disabled={busy}
                  onClick={() => run(() => buildProject(code, playerId, slot.index))}
                  className="w-full rounded-xl bg-emerald-600 py-2 font-semibold text-white disabled:opacity-40"
                >
                  Build
                </button>
              ) : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}

export function PriorityStrip({ pub, playerId }: { pub: PublicState; playerId?: string }) {
  return (
    <div>
      <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">Project priority this round</p>
      <ol className="flex flex-wrap gap-1.5 text-sm">
        {pub.priority.map((p, i) => {
          const acted = String(p.slot) in pub.project_actions;
          const current = pub.project_turn_slot === p.slot;
          return (
            <li
              key={p.slot}
              className={`rounded-full px-3 py-1 ${
                current
                  ? "bg-amber-500 text-white"
                  : acted
                    ? "bg-mystery-800 text-mystery-500 line-through"
                    : "bg-mystery-700 text-mystery-200"
              } ${p.player_id && p.player_id === playerId ? "font-bold" : ""}`}
            >
              {i + 1}. {p.is_ai ? "🤖 " : ""}
              {p.name}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
