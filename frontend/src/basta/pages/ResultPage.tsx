import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getGameInfo, resetGame } from "../api/http";
import ScoreBoard from "../components/ScoreBoard";
import { useBasta, useBastaActions, useRestoreSession } from "../context/GameContext";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useBasta();
  const { setPhase, setPlayers, setScores, setWinner } = useBastaActions();

  useRestoreSession(code);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPhase(info.phase);
      setPlayers(info.players);
      setScores(info.scores);
      if (info.winner) {
        setWinner(info.winner, info.scores);
      }
    });
  }, [code]);

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <section className="rounded-lg border border-mystery-700 bg-mystery-800 p-6 text-center shadow-xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
            Winner
          </p>
          <h1 className="mt-2 text-5xl font-black text-amber-200">
            {state.winner || "Final Scores"}
          </h1>
        </section>
        <ScoreBoard scores={state.scores} />
        {state.isHost ? (
          <button
            onClick={() => {
              if (!code || !state.playerId) return;
              resetGame(code, state.playerId).then(() => navigate(`/lobby/${code}`));
            }}
            className="w-full rounded-lg bg-amber-300 px-4 py-4 text-lg font-black text-mystery-900 transition hover:bg-amber-200"
          >
            Play Again
          </button>
        ) : (
          <button
            onClick={() => navigate(`/`)}
            className="w-full rounded-lg bg-mystery-700 px-4 py-4 text-lg font-black text-mystery-100 transition hover:bg-mystery-600"
          >
            Home
          </button>
        )}
      </div>
    </div>
  );
}
