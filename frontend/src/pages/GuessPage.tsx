import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { makeGuess } from "../api/http";

export default function GuessPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setGuessResult, setPhase } = useGameActions();
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!code || !state.playerId || !selected) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await makeGuess(code, state.playerId, selected);
      setGuessResult({
        correct: result.correct,
        suspect: result.suspect_name,
        murderer: result.actual_murderer ?? undefined,
      });
      if (result.correct || result.actual_murderer) {
        setPhase("finished");
      }
      navigate(`/result/${code}`);
    } catch (e: unknown) {
      const message =
        e instanceof Error ? e.message : "Something went wrong";
      setError(message);
      setSubmitting(false);
    }
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
