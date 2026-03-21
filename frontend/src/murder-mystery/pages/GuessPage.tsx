import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { makeGuess, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";

function WaitingTimer({ startedAt, durationSeconds }: { startedAt: string; durationSeconds: number }) {
  const [remaining, setRemaining] = useState(durationSeconds);

  useEffect(() => {
    const endTime = new Date(startedAt).getTime() + durationSeconds * 1000;
    const tick = () => {
      const left = Math.max(0, Math.floor((endTime - Date.now()) / 1000));
      setRemaining(left);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt, durationSeconds]);

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;

  return (
    <p className="text-3xl font-mono font-bold text-mystery-300">
      {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
    </p>
  );
}

export default function GuessPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setHasGuessed, setPhase, setRoundInfo } = useGameActions();
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Redirect back if somehow reached during round 1
  useEffect(() => {
    if (state.currentRound < 2 && state.currentRound > 0 && !state.hasGuessed) {
      navigate(`/game/${code}`, { replace: true });
    }
  }, [state.currentRound, state.hasGuessed, code, navigate]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      if (event.event === "game_over") {
        setPhase("finished");
        navigate(`/result/${code}`);
      }
      if (event.event === "round_advanced") {
        setRoundInfo(
          event.data.round as number,
          event.data.started_at as string,
          event.data.duration_seconds as number,
        );
      }
    },
    [code, navigate, setPhase, setRoundInfo]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleSubmit() {
    if (!code || !state.playerId || !selected) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await makeGuess(code, state.playerId, selected);
      setHasGuessed(result.guessed_at);
    } catch (e: unknown) {
      const message =
        e instanceof Error ? e.message : "Something went wrong";
      setError(message);
      setSubmitting(false);
    }
  }

  // Show locked-in state
  if (state.hasGuessed) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="bg-mystery-800 rounded-2xl p-8 shadow-xl">
            <h2 className="text-3xl font-bold text-mystery-300 mb-4">
              Guess Locked In!
            </h2>
            <p className="text-mystery-400 mb-6">
              Waiting for all players to finish or the timer to expire...
            </p>
            {state.roundStartedAt && state.roundDurations.length > 0 && state.currentRound > 0 && (
              <WaitingTimer
                startedAt={state.roundStartedAt}
                durationSeconds={state.roundDurations[state.currentRound - 1]}
              />
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-red-400">
            Make Your Accusation
          </h2>
          <p className="text-mystery-400 mt-2">
            Who committed the murder with the {state.murderWeapon ?? "mystery weapon"}?
          </p>
        </div>

        <div className="space-y-3">
          {state.characterNames.map((name) => (
            <button
              key={name}
              onClick={() => setSelected(name)}
              className={`w-full p-4 rounded-xl text-left transition ${
                selected === name
                  ? "bg-red-700 ring-2 ring-red-400"
                  : "bg-mystery-800 hover:bg-mystery-700"
              }`}
            >
              <p className="font-semibold text-lg">{name}</p>
              {name === state.card?.character_name && (
                <p className="text-mystery-400 text-sm">You</p>
              )}
            </button>
          ))}

          {state.characterNames.length === 0 && (
            <p className="text-mystery-400 text-center text-sm">
              No character list available. Type your suspect below.
            </p>
          )}
        </div>

        {error && <p className="text-red-400 text-sm text-center">{error}</p>}

        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/game/${code}`)}
            className="flex-1 py-3 rounded-xl bg-mystery-700 hover:bg-mystery-600 text-white font-semibold transition"
          >
            Back
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selected || submitting}
            className="flex-1 py-3 rounded-xl bg-red-700 hover:bg-red-600 text-white font-semibold transition disabled:opacity-40"
          >
            {submitting ? "..." : "Accuse!"}
          </button>
        </div>
      </div>
    </div>
  );
}
