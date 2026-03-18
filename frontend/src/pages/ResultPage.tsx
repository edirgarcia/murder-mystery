import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { getResults } from "../api/http";
import type { ResultsResponse } from "../types/game";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setPhase } = useGameActions();
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) return;
    // If we're not finished yet, set phase and try to fetch
    setPhase("finished");
    getResults(code)
      .then((r) => {
        setResults(r);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [code]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-mystery-400 text-xl">Loading results...</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-mystery-400 text-xl">Results not available yet.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-md mx-auto space-y-6">
        <div className="bg-mystery-800 rounded-2xl p-6 text-center">
          <p className="text-mystery-400 text-sm uppercase tracking-wider">
            The Murderer
          </p>
          <h3 className="text-3xl font-bold text-red-400 mt-1">
            {results.murderer_name}
          </h3>
          <p className="text-mystery-300 mt-1">
            with the {results.murder_weapon}
          </p>
        </div>

        <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl">
          <h4 className="text-mystery-300 font-semibold mb-4">Leaderboard</h4>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-mystery-400 text-left">
                <th className="py-1 pr-2">#</th>
                <th className="py-1 pr-2">Player</th>
                <th className="py-1 pr-2">Suspect</th>
                <th className="py-1 pr-2">Result</th>
                <th className="py-1">Time</th>
              </tr>
            </thead>
            <tbody>
              {results.leaderboard.map((entry) => {
                const isMe = entry.player_name === state.playerName;
                return (
                  <tr
                    key={entry.rank}
                    className={`border-t border-mystery-700 ${isMe ? "bg-mystery-700/30" : ""}`}
                  >
                    <td className="py-2 pr-2 text-mystery-400">{entry.rank}</td>
                    <td className="py-2 pr-2 text-mystery-200 font-medium">
                      {entry.player_name}
                      {isMe && <span className="text-mystery-400 text-xs ml-1">(you)</span>}
                    </td>
                    <td className="py-2 pr-2 text-mystery-300">{entry.suspect_guessed}</td>
                    <td className="py-2 pr-2">
                      <span className={entry.correct ? "text-green-400" : "text-red-400"}>
                        {entry.correct ? "Correct" : "Wrong"}
                      </span>
                    </td>
                    <td className="py-2 text-mystery-400">
                      {entry.time_taken_seconds != null
                        ? `${Math.floor(entry.time_taken_seconds)}s`
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {results.murder_clues.length > 0 && (
          <div className="bg-mystery-800 rounded-2xl p-6">
            <h4 className="text-mystery-300 font-semibold mb-3">
              Murder Clues
            </h4>
            {results.murder_clues.map((clue, i) => (
              <p key={i} className="text-mystery-200 text-sm mb-1">
                {clue.text}
              </p>
            ))}
          </div>
        )}

        <button
          onClick={() => navigate("/")}
          className="w-full py-3 rounded-xl bg-mystery-700 hover:bg-mystery-600 text-white font-semibold text-lg transition"
        >
          Play Again
        </button>
      </div>
    </div>
  );
}
