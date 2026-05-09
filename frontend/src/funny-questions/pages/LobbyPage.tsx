import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { useFQ, useFQActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getGameInfo, startGame, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";
import PlayerList from "@shared/components/PlayerList";

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useFQ();
  const { setGame, setPlayers, addPlayer, setPhase, setError, setPointsToWin } = useFQActions();
  const [maxSpice, setMaxSpice] = useState(2);
  const [pointsToWin, setLocalPointsToWin] = useState(20);
  const [hostPaced, setHostPaced] = useState(false);
  const [starting, setStarting] = useState(false);

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

  // Load game info
  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      if (info.phase === "playing") {
        setPhase("playing");
        if (state.isHost) {
          navigate(`/dashboard/${code}`);
        } else {
          navigate(`/vote/${code}`);
        }
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
          });
          break;
        case "game_started":
          setPhase("playing");
          if (event.data.points_to_win) {
            setPointsToWin(event.data.points_to_win as number);
          }
          if (state.isHost) {
            navigate(`/dashboard/${code}`);
          } else {
            navigate(`/vote/${code}`);
          }
          break;
      }
    },
    [code, navigate, addPlayer, setPhase, setPointsToWin, state.isHost]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    try {
      await startGame(code, state.playerId, {
        max_spice: maxSpice,
        points_to_win: pointsToWin,
        host_paced: hostPaced,
      });
    } catch (e: any) {
      setError(e.message);
      setStarting(false);
    }
  }

  const canStart = state.players.length >= 3 && !starting;

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center">
          <p className="text-mystery-400 text-sm uppercase tracking-wider">Game Code</p>
          <h2 className="text-7xl font-bold text-mystery-300 tracking-[0.3em] mt-1">{code}</h2>
          {state.isHost && (
            <div className="mt-4 inline-block rounded-xl bg-white p-3">
              <QRCodeSVG value={`${window.location.origin}/funny-questions/?join=${code}`} size={256} />
            </div>
          )}
          <p className="text-mystery-400 mt-3">
            {state.isHost ? "Scan to join or enter the code" : "Waiting for the host to start..."}
          </p>
        </div>

        <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl">
          <h3 className="text-mystery-300 font-semibold mb-3">
            Players ({state.players.length})
          </h3>
          <PlayerList players={state.players} />
          {state.players.length < 3 && (
            <p className="text-mystery-400 text-sm mt-3 text-center">
              Need at least 3 players to start
            </p>
          )}
        </div>

        {state.isHost && (
          <>
            <div className="bg-mystery-800 rounded-2xl p-4 shadow-xl">
              <h3 className="text-mystery-300 font-semibold mb-3 text-sm">Spice Level</h3>
              <div className="flex gap-2">
                {[1, 2, 3, 4].map((s) => (
                  <button
                    key={s}
                    onClick={() => setMaxSpice(s)}
                    disabled={starting}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                      maxSpice === s
                        ? "bg-mystery-500 text-white"
                        : "bg-mystery-700 text-mystery-400 hover:bg-mystery-600"
                    } disabled:opacity-40`}
                  >
                    {s === 1 ? "Mild" : s === 2 ? "Medium" : s === 3 ? "Spicy" : "Scorching"}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-mystery-800 rounded-2xl p-4 shadow-xl">
              <h3 className="text-mystery-300 font-semibold mb-3 text-sm">Points to Win</h3>
              <div className="flex gap-2">
                {[10, 15, 20, 30].map((p) => (
                  <button
                    key={p}
                    onClick={() => setLocalPointsToWin(p)}
                    disabled={starting}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                      pointsToWin === p
                        ? "bg-mystery-500 text-white"
                        : "bg-mystery-700 text-mystery-400 hover:bg-mystery-600"
                    } disabled:opacity-40`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-mystery-800 rounded-2xl p-4 shadow-xl">
              <button
                onClick={() => setHostPaced(!hostPaced)}
                disabled={starting}
                className="w-full flex items-center justify-between disabled:opacity-40"
              >
                <div className="text-left">
                  <h3 className="text-mystery-300 font-semibold text-sm">Host-Paced</h3>
                  <p className="text-mystery-500 text-xs mt-0.5">You control when the next question appears</p>
                </div>
                <div
                  className={`w-11 h-6 rounded-full transition-colors ${
                    hostPaced ? "bg-mystery-500" : "bg-mystery-700"
                  } relative`}
                >
                  <div
                    className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                      hostPaced ? "translate-x-5" : "translate-x-0.5"
                    }`}
                  />
                </div>
              </button>
            </div>

            <button
              onClick={handleStart}
              disabled={!canStart}
              className="w-full py-4 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition disabled:opacity-40"
            >
              {starting ? "Starting..." : "Start Game"}
            </button>
          </>
        )}

        {state.error && (
          <p className="text-red-400 text-sm text-center">{state.error}</p>
        )}
      </div>
    </div>
  );
}
