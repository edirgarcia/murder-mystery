import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions, useRestoreSession } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getResults, buildWsUrl } from "../api/http";
import type { ResultsResponse } from "../types/game";
import type { WSEvent } from "@shared/types/game";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setPhase, resetGameState } = useGameActions();
  const [results, setResults] = useState<ResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore identity from localStorage so a refresh keeps the live connection
  useRestoreSession(code);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      if (event.event === "game_reset") {
        resetGameState();
        navigate(`/lobby/${code}`);
      }
    },
    [code, navigate, resetGameState]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  useEffect(() => {
    if (!code) return;
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
        {results.traitor_mode && (
          <div
            className={`rounded-2xl p-6 text-center border ${
              results.murderer_caught
                ? "bg-green-950/40 border-green-700/60"
                : "bg-red-950/40 border-red-700/60"
            }`}
          >
            <h2
              className={`text-3xl font-bold ${
                results.murderer_caught ? "text-green-300" : "text-red-300"
              }`}
            >
              {results.murderer_caught ? "⚖️ Caught!" : "🔪 The murderer got away!"}
            </h2>
            <p className="text-mystery-300 text-sm mt-2">
              {results.murderer_name} fooled {(results.detectives_total ?? 0) - (results.detectives_correct ?? 0)} of {results.detectives_total ?? 0} detectives.
            </p>
          </div>
        )}
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
                        : "\u2014"}
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

        <p className="text-mystery-400 text-sm text-center">
          Waiting for host to start a new game...
        </p>
      </div>
    </div>
  );
}
