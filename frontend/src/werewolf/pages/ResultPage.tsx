import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getPlayerState } from "../api/http";
import { useWW, useWWActions } from "../context/GameContext";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useWW();
  const { setGame, setPlayers, setWinner, setError } = useWWActions();

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("ww_player_id");
    const storedCode = localStorage.getItem("ww_game_code");
    const isHost = localStorage.getItem("ww_is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
    }
  }, [code, setGame, state.playerId]);

  useEffect(() => {
    if (!code || !state.playerId) return;
    if (state.winner && Object.keys(state.rolesReveal).length > 0) return;
    getPlayerState(code, state.playerId)
      .then((payload) => {
        setPlayers(payload.players);
        if (payload.winner && payload.roles) {
          setWinner(payload.winner, payload.roles);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load result"));
  }, [code, setError, setPlayers, setWinner, state.playerId, state.rolesReveal, state.winner]);

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-lg mx-auto space-y-4">
        <div className="bg-mystery-800 rounded-2xl p-5 border border-mystery-700 text-center">
          <p className="text-xs uppercase tracking-wider text-mystery-400">Winner</p>
          <h2 className="text-4xl font-bold text-mystery-100 mt-2">{state.winner ?? "Unknown"}</h2>
        </div>

        <div className="bg-mystery-800 rounded-2xl p-5 border border-mystery-700">
          <p className="text-mystery-200 font-semibold mb-2">Role Reveal</p>
          <div className="space-y-1">
            {state.players.map((p) => (
              <div key={p.id} className="flex justify-between text-sm">
                <span className={p.alive ? "text-mystery-100" : "text-mystery-400 line-through"}>{p.name}</span>
                <span className="text-mystery-300">{state.rolesReveal[p.id] ?? "?"}</span>
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={() => navigate("/")}
          className="w-full rounded-xl py-3 bg-mystery-700 hover:bg-mystery-600"
        >
          Play Again
        </button>

        {state.error && <p className="text-red-300 text-sm text-center">{state.error}</p>}
      </div>
    </div>
  );
}

