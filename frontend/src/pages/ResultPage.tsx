import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { getSolution } from "../api/http";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setSolution } = useGameActions();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!code || state.phase !== "finished") return;
    setLoading(true);
    getSolution(code)
      .then((sol) => {
        setSolution(sol);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [code, state.phase]);

  const result = state.guessResult;
  const solution = state.solution;

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-md mx-auto space-y-6">
        {result && (
          <div
            className={`rounded-2xl p-6 text-center ${
              result.correct ? "bg-green-900/50" : "bg-red-900/50"
            }`}
          >
            <h2 className="text-3xl font-bold mb-2">
              {result.correct ? "Correct!" : "Wrong!"}
            </h2>
            <p className="text-lg">
              You accused: <strong>{result.suspect}</strong>
            </p>
            {result.murderer && (
              <p className="text-mystery-300 mt-1">
                The murderer was: <strong>{result.murderer}</strong>
              </p>
            )}
          </div>
        )}

        {!result && state.phase !== "finished" && (
          <div className="text-center">
            <p className="text-mystery-400 text-xl">
              Waiting for all players to guess...
            </p>
          </div>
        )}

        {state.phase === "finished" && solution && (
          <div className="space-y-4">
            <div className="bg-mystery-800 rounded-2xl p-6 text-center">
              <p className="text-mystery-400 text-sm uppercase tracking-wider">
                The Murderer
              </p>
              <h3 className="text-3xl font-bold text-red-400 mt-1">
                {solution.murderer_name}
              </h3>
              <p className="text-mystery-300 mt-1">
                with the {solution.murder_weapon}
              </p>
            </div>

            <div className="bg-mystery-800 rounded-2xl p-6">
              <h4 className="text-mystery-300 font-semibold mb-3">
                Murder Clues
              </h4>
              {solution.murder_clues.map((clue, i) => (
                <p key={i} className="text-mystery-200 text-sm mb-1">
                  {clue.text}
                </p>
              ))}
            </div>

            <div className="bg-mystery-800 rounded-2xl p-6">
              <h4 className="text-mystery-300 font-semibold mb-3">
                Full Solution
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-mystery-400">
                      <th className="text-left py-1 pr-3">Category</th>
                      {Array.from(
                        {
                          length:
                            Object.values(solution.solution)[0]?.length ?? 0,
                        },
                        (_, i) => (
                          <th key={i} className="text-left py-1 px-2">
                            #{i + 1}
                          </th>
                        )
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(solution.solution).map(([cat, vals]) => (
                      <tr key={cat} className="border-t border-mystery-700">
                        <td className="py-1 pr-3 text-mystery-400 capitalize">
                          {cat.replace("_", " ")}
                        </td>
                        {vals.map((v, i) => (
                          <td key={i} className="py-1 px-2 text-mystery-200">
                            {v}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {loading && (
          <p className="text-center text-mystery-400">Loading solution...</p>
        )}

        <button
          onClick={() => {
            navigate("/");
            // Full reset would be needed
          }}
          className="w-full py-3 rounded-xl bg-mystery-700 hover:bg-mystery-600 text-white font-semibold text-lg transition"
        >
          Play Again
        </button>
      </div>
    </div>
  );
}
