import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useFQ, useFQActions } from "../context/GameContext";
import { getScores } from "../api/http";
import ScoreBoard from "../components/ScoreBoard";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useFQ();
  const { setScores, setGame } = useFQActions();

  // Restore from localStorage
  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("fq_player_id");
    const storedCode = localStorage.getItem("fq_game_code");
    const isHost = localStorage.getItem("fq_is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
    }
  }, [code, state.playerId, setGame]);

  // Load scores if we don't have them
  useEffect(() => {
    if (!code || Object.keys(state.scores).length > 0) return;
    getScores(code).then((entries) => {
      const scores: Record<string, number> = {};
      for (const e of entries) {
        scores[e.player_name] = e.score;
      }
      setScores(scores);
    });
  }, [code]);

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-md mx-auto space-y-6">
        <div className="bg-mystery-800 rounded-2xl p-6 text-center">
          <p className="text-mystery-400 text-sm uppercase tracking-wider">Game Over</p>
          {state.winner && (
            <h2 className="text-4xl font-bold text-mystery-300 mt-2">
              {state.winner} wins!
            </h2>
          )}
        </div>

        <ScoreBoard scores={state.scores} shameHolder={state.shameHolder} pointsToWin={state.pointsToWin} />

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
