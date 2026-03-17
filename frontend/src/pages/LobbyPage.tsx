import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { getGameInfo, startGame } from "../api/http";
import type { WSEvent } from "../types/game";
import PlayerList from "../components/PlayerList";

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setPlayers, addPlayer, setPhase, setError } = useGameActions();
  const [starting, setStarting] = useState(false);

  // Load game info on mount
  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      if (info.phase === "playing") {
        setPhase("playing");
        navigate(`/game/${code}`);
      }
    });
  }, [code]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "player_joined":
          addPlayer({
            id: event.data.player_id as string,
            name: event.data.player_name as string,
            is_host: false,
          });
          break;
        case "game_starting":
          setPhase("generating");
          break;
        case "game_started":
          setPhase("playing");
          navigate(`/game/${code}`);
          break;
        case "generation_failed":
          setPhase("lobby");
          setError(event.data.error as string);
          setStarting(false);
          break;
      }
    },
    [code, navigate, addPlayer, setPhase, setError]
  );

  useWebSocket(code ?? null, state.playerId, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    try {
      await startGame(code, state.playerId);
    } catch (e: any) {
      setError(e.message);
      setStarting(false);
    }
  }

  const canStart =
    state.isHost && state.players.length >= 3 && !starting;

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <p className="text-mystery-400 text-sm uppercase tracking-wider">
            Game Code
          </p>
          <h2 className="text-5xl font-bold text-mystery-300 tracking-[0.3em] mt-1">
            {code}
          </h2>
          <p className="text-mystery-400 mt-2">
            Share this code with your friends
          </p>
        </div>

        <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl">
          <h3 className="text-mystery-300 font-semibold mb-3">
            Players ({state.players.length}/6)
          </h3>
          <PlayerList players={state.players} />

          {state.players.length < 3 && (
            <p className="text-mystery-400 text-sm mt-3 text-center">
              Need at least 3 players to start
            </p>
          )}
        </div>

        {state.isHost && (
          <button
            onClick={handleStart}
            disabled={!canStart}
            className="w-full py-4 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition disabled:opacity-40"
          >
            {starting
              ? state.phase === "generating"
                ? "Generating puzzle..."
                : "Starting..."
              : "Start Game"}
          </button>
        )}

        {!state.isHost && (
          <p className="text-center text-mystery-400">
            Waiting for the host to start the game...
          </p>
        )}

        {state.error && (
          <p className="text-red-400 text-sm text-center">{state.error}</p>
        )}
      </div>
    </div>
  );
}
