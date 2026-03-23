import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { buildWsUrl, getGameInfo, startGame } from "../api/http";
import { usePD, usePDActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import type { WSEvent } from "@shared/types/game";
import PlayerList from "@shared/components/PlayerList";

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = usePD();
  const { addPlayer, setGame, setPhase, setPlayers, setTeamScores, setError } = usePDActions();
  const [votingSeconds, setVotingSeconds] = useState(45);
  const [accusationSeconds, setAccusationSeconds] = useState(20);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("pd_player_id");
    const storedCode = localStorage.getItem("pd_game_code");
    const isHost = localStorage.getItem("pd_is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
    }
  }, [code, state.playerId, setGame]);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setPhase(info.phase);
      setTeamScores(info.team_scores);
      if (info.phase === "playing") {
        navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`, { replace: true });
      }
      if (info.phase === "finished") {
        navigate(`/result/${code}`, { replace: true });
      }
    });
  }, [code, navigate, setPhase, setPlayers, setTeamScores, state.isHost]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "player_joined":
          addPlayer({
            id: event.data.player_id as string,
            name: event.data.player_name as string,
            team: null,
            spy_exposed: false,
          });
          break;
        case "game_started":
          setPhase("playing");
          setPlayers(event.data.players as any);
          setTeamScores(event.data.team_scores as any);
          navigate(state.isHost ? `/dashboard/${code}` : `/play/${code}`);
          break;
      }
    },
    [addPlayer, code, navigate, setPhase, setPlayers, setTeamScores, state.isHost]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    try {
      await startGame(code, state.playerId, {
        voting_seconds: votingSeconds,
        accusation_seconds: accusationSeconds,
      });
    } catch (err: any) {
      setError(err.message);
      setStarting(false);
    }
  }

  const canStart = state.players.length >= 4 && !starting;

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
          <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Lobby Code</p>
              <h1 className="mt-2 text-6xl font-bold tracking-[0.35em] text-white">{code}</h1>
              <p className="mt-3 max-w-xl text-mystery-200">
                Players scan the QR code or enter the room code. Teams and spies are assigned
                randomly when the host starts the game.
              </p>
            </div>
            {state.isHost && (
              <div className="rounded-3xl bg-white p-4">
                <QRCodeSVG value={`${window.location.origin}/prisoners-dilemma/?join=${code}`} size={180} />
              </div>
            )}
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
          <div className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-white">Players</h2>
              <span className="rounded-full bg-mystery-700 px-3 py-1 text-sm text-mystery-200">
                {state.players.length} joined
              </span>
            </div>
            <PlayerList players={state.players} />
            {state.players.length < 4 && (
              <p className="mt-4 text-sm text-amber-200">At least 4 players are required to start.</p>
            )}
          </div>

          {state.isHost && (
            <div className="space-y-6">
              <div className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
                <h3 className="text-lg font-semibold text-white">Round Timing</h3>
                <p className="mt-2 text-sm text-mystery-200">Voting is team discussion plus a private phone vote. Accusation follows the reveal every round.</p>

                <div className="mt-5 space-y-4">
                  <div>
                    <p className="mb-2 text-sm uppercase tracking-[0.25em] text-mystery-300">Voting</p>
                    <div className="flex gap-2">
                      {[30, 45, 60].map((value) => (
                        <button
                          key={value}
                          onClick={() => setVotingSeconds(value)}
                          className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                            votingSeconds === value
                              ? "bg-blue-500 text-white"
                              : "bg-mystery-700 text-mystery-200 hover:bg-mystery-600"
                          }`}
                        >
                          {value}s
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 text-sm uppercase tracking-[0.25em] text-mystery-300">Accusation</p>
                    <div className="flex gap-2">
                      {[15, 20, 30].map((value) => (
                        <button
                          key={value}
                          onClick={() => setAccusationSeconds(value)}
                          className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                            accusationSeconds === value
                              ? "bg-red-500 text-white"
                              : "bg-mystery-700 text-mystery-200 hover:bg-mystery-600"
                          }`}
                        >
                          {value}s
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={handleStart}
                disabled={!canStart}
                className="w-full rounded-[28px] bg-gradient-to-r from-blue-500 to-red-500 px-6 py-4 text-lg font-semibold text-white shadow-xl transition hover:opacity-95 disabled:opacity-40"
              >
                {starting ? "Starting..." : "Start Prisoner's Dilemma"}
              </button>
            </div>
          )}
        </section>

        {state.error && <p className="text-center text-sm text-red-300">{state.error}</p>}
      </div>
    </div>
  );
}
