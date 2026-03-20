import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import type { WSEvent } from "@shared/types/game";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { buildWsUrl, getGameInfo, startGame } from "../api/http";
import { useWW, useWWActions } from "../context/GameContext";
import PlayerGrid from "../components/PlayerGrid";

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useWW();
  const { setGame, setPlayers, addPlayer, setPhase, setError } = useWWActions();

  const [discussionSeconds, setDiscussionSeconds] = useState(90);
  const [starting, setStarting] = useState(false);

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
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setPhase(info.phase);
      if (info.phase === "playing") {
        navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`, { replace: true });
      }
    });
  }, [code, navigate, setPhase, setPlayers, state.isHost]);

  const handleWSEvent = useCallback((event: WSEvent) => {
    if (event.event === "player_joined") {
      addPlayer({
        id: event.data.player_id as string,
        name: event.data.player_name as string,
        alive: true,
      });
    }
    if (event.event === "game_started" && code) {
      setPhase("playing");
      navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`);
    }
  }, [addPlayer, code, navigate, setPhase, state.isHost]);

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    try {
      await startGame(code, state.playerId, discussionSeconds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start game");
      setStarting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-lg space-y-5">
        <div className="text-center">
          <p className="text-xs uppercase tracking-wider text-mystery-400">Room Code</p>
          <h2 className="text-6xl tracking-[0.3em] text-mystery-100 font-bold">{code}</h2>
          {state.isHost && (
            <div className="mt-3 inline-block rounded-xl bg-white p-2">
              <QRCodeSVG value={`http://localhost:5173/werewolf/?join=${code}`} size={160} />
            </div>
          )}
        </div>

        <div className="bg-mystery-800 rounded-2xl p-5 border border-mystery-700 shadow-xl space-y-3">
          <p className="text-mystery-200 font-semibold">Players ({state.players.length})</p>
          <PlayerGrid players={state.players} />
          {state.players.length < 6 && <p className="text-sm text-mystery-400">Need at least 6 players to start.</p>}
        </div>

        {state.isHost && (
          <div className="bg-mystery-800 rounded-2xl p-5 border border-mystery-700 shadow-xl space-y-3">
            <label className="text-sm text-mystery-300">Discussion time (seconds)</label>
            <input
              type="number"
              min={30}
              max={300}
              value={discussionSeconds}
              onChange={(e) => setDiscussionSeconds(Number(e.target.value))}
              className="w-full rounded-xl bg-mystery-700 border border-mystery-600 p-3"
            />
            <button
              onClick={handleStart}
              disabled={state.players.length < 6 || starting}
              className="w-full rounded-xl py-3 bg-red-600 hover:bg-red-500 disabled:opacity-40"
            >
              {starting ? "Starting..." : "Start Game"}
            </button>
          </div>
        )}

        {state.error && <p className="text-red-300 text-sm text-center">{state.error}</p>}
      </div>
    </div>
  );
}
