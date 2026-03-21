import { useState } from "react";
import type { WitchPrompt } from "../types/game";

export default function WitchAction({
  prompt,
  onAction,
  disabled,
}: {
  prompt: WitchPrompt;
  onAction: (action: string, target?: string) => void;
  disabled?: boolean;
}) {
  const [phase, setPhase] = useState<"heal" | "kill">(
    prompt.healAvailable && prompt.werewolfVictim ? "heal" : "kill"
  );
  const [killTarget, setKillTarget] = useState("");

  const noPotions = !prompt.healAvailable && !prompt.killAvailable;

  return (
    <div className="space-y-4">
      {/* Potion indicators */}
      <div className="flex gap-3">
        <div className={`flex items-center gap-1.5 text-sm rounded-lg px-3 py-1.5 ${prompt.healAvailable ? "bg-emerald-900/50 text-emerald-300 border border-emerald-700" : "bg-mystery-700/50 text-mystery-500 border border-mystery-700 line-through"}`}>
          <span>{prompt.healAvailable ? "+" : "x"}</span>
          Heal Potion
        </div>
        <div className={`flex items-center gap-1.5 text-sm rounded-lg px-3 py-1.5 ${prompt.killAvailable ? "bg-red-900/50 text-red-300 border border-red-700" : "bg-mystery-700/50 text-mystery-500 border border-mystery-700 line-through"}`}>
          <span>{prompt.killAvailable ? "+" : "x"}</span>
          Kill Potion
        </div>
      </div>

      {noPotions ? (
        <div className="space-y-3">
          <p className="text-mystery-300 text-sm">You have no potions left.</p>
          <button
            onClick={() => onAction("witch_pass")}
            disabled={disabled}
            className="w-full rounded-xl p-3 bg-mystery-600 hover:bg-mystery-500 disabled:opacity-40"
          >
            Continue
          </button>
        </div>
      ) : phase === "heal" && prompt.healAvailable && prompt.werewolfVictim ? (
        <div className="space-y-3">
          <p className="text-mystery-100">
            <span className="font-semibold text-red-300">{prompt.victimName}</span>{" "}
            was attacked by the wolves.
          </p>
          <p className="text-mystery-300 text-sm">Do you want to use your heal potion to save them?</p>
          <div className="flex gap-2">
            <button
              onClick={() => onAction("witch_heal")}
              disabled={disabled}
              className="flex-1 rounded-xl p-3 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40"
            >
              Save them
            </button>
            <button
              onClick={() => {
                if (prompt.killAvailable) {
                  setPhase("kill");
                } else {
                  onAction("witch_pass");
                }
              }}
              disabled={disabled}
              className="flex-1 rounded-xl p-3 bg-mystery-600 hover:bg-mystery-500 disabled:opacity-40"
            >
              Let them die
            </button>
          </div>
        </div>
      ) : prompt.killAvailable ? (
        <div className="space-y-3">
          <p className="text-mystery-300 text-sm">Choose a player to eliminate, or skip.</p>
          <select
            className="w-full rounded-xl bg-mystery-700 border border-mystery-600 p-2"
            value={killTarget}
            onChange={(e) => setKillTarget(e.target.value)}
          >
            <option value="">Pick target</option>
            {prompt.targets.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={() => onAction("witch_kill", killTarget)}
              disabled={!killTarget || disabled}
              className="flex-1 rounded-xl p-3 bg-red-600 hover:bg-red-500 disabled:opacity-40"
            >
              Use Kill Potion
            </button>
            <button
              onClick={() => onAction("witch_pass")}
              disabled={disabled}
              className="flex-1 rounded-xl p-3 bg-mystery-600 hover:bg-mystery-500 disabled:opacity-40"
            >
              Skip
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-mystery-300 text-sm">No more actions available this night.</p>
          <button
            onClick={() => onAction("witch_pass")}
            disabled={disabled}
            className="w-full rounded-xl p-3 bg-mystery-600 hover:bg-mystery-500 disabled:opacity-40"
          >
            Continue
          </button>
        </div>
      )}
    </div>
  );
}
