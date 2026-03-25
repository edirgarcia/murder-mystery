import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { buildWsUrl, getGameInfo } from "../api/http";
import { usePD, usePDActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import CountdownBar from "../components/CountdownBar";
import type { WSEvent } from "@shared/types/game";
import type { AccusationResult, PDPlayerInfo, RoundResult, TeamColor } from "../types/game";

function teamPanel(team: TeamColor) {
  return team === "red"
    ? "border-red-400/30 bg-red-500/10"
    : "border-blue-400/30 bg-blue-500/10";
}

function teamLabel(team: TeamColor) {
  return team === "red" ? "Red Team" : "Blue Team";
}

function phaseLabel(
  roundPhase: string | null,
  revealType: "round" | "accusation" | null,
  phase: string | null,
): { text: string; color: string } {
  if (phase === "lobby") return { text: "Waiting in Lobby", color: "text-mystery-300" };
  if (!roundPhase) return { text: "Starting...", color: "text-mystery-300" };
  if (roundPhase === "voting") return { text: "Voting Phase", color: "text-emerald-400" };
  if (roundPhase === "reveal" && revealType === "round")
    return { text: "Round Results", color: "text-amber-400" };
  if (roundPhase === "accusation") return { text: "Accusation Phase", color: "text-purple-400" };
  if (roundPhase === "reveal" && revealType === "accusation")
    return { text: "Accusation Results", color: "text-amber-400" };
  return { text: "In Progress", color: "text-mystery-300" };
}

export default function DashboardPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = usePD();
  const {
    addPlayer,
    accusationStarted,
    roundStarted,
    setAccusationResult,
    setGame,
    setPhase,
    setPlayers,
    setRoundResult,
    setTeamScores,
    setWinner,
    syncGameInfo,
  } = usePDActions();
  const [narrationText, setNarrationText] = useState<string | null>(null);
  const sendAckRef = useRef<() => void>(() => {});

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("pd_player_id");
    const storedCode = localStorage.getItem("pd_game_code");
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "Host", true);
    }
  }, [code, setGame, state.playerId]);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      syncGameInfo(info);
      if (info.phase === "finished") {
        navigate(`/result/${code}`, { replace: true });
      }
    });
  }, [code, navigate, syncGameInfo]);

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
          setPlayers(event.data.players as PDPlayerInfo[]);
          setTeamScores(event.data.team_scores as Record<TeamColor, number>);
          setNarrationText("");
          break;
        case "intro_narration": {
          setNarrationText(event.data.text as string);
          const sound = event.data.sound as string | undefined;
          if (sound) {
            const audio = new Audio(`/prisoners-dilemma/audio/${sound}`);
            audio.onended = () => sendAckRef.current();
            audio.onerror = () => sendAckRef.current();
            audio.play().catch(() => sendAckRef.current());
          }
          break;
        }
        case "intro_done":
          setNarrationText(null);
          break;
        case "round_started":
          roundStarted(
            event.data.round as number,
            event.data.total_rounds as number,
            (event.data.voting_ends_at as string) ?? null,
            event.data.players as PDPlayerInfo[],
            event.data.team_scores as Record<TeamColor, number>
          );
          break;
        case "round_result":
          setRoundResult(event.data as unknown as RoundResult);
          break;
        case "accusation_started":
          accusationStarted(
            (event.data.accusation_ends_at as string) ?? null,
            event.data.players as PDPlayerInfo[]
          );
          break;
        case "accusation_result":
          setAccusationResult(event.data as unknown as AccusationResult);
          break;
        case "game_over":
          setWinner(event.data as any);
          navigate(`/result/${code}`);
          break;
      }
    },
    [
      accusationStarted,
      addPlayer,
      code,
      navigate,
      roundStarted,
      setAccusationResult,
      setPhase,
      setPlayers,
      setRoundResult,
      setTeamScores,
      setWinner,
    ]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  const wsRef = useWebSocket(wsUrl, handleWSEvent);

  sendAckRef.current = () => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "narration_ack" }));
    }
  };

  const redPlayers = state.players.filter((player) => player.team === "red");
  const bluePlayers = state.players.filter((player) => player.team === "blue");

  return (
    <div className="min-h-screen px-4 py-6">
      {narrationText !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
          <p className="animate-pulse text-center text-3xl font-bold text-mystery-100 px-6 leading-relaxed md:text-5xl">
            {narrationText}
          </p>
        </div>
      )}
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-[32px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Host Dashboard</p>
              <h1 className="mt-2 text-4xl font-bold text-white">
                Round {state.currentRound || 1} / {state.totalRounds}
              </h1>
              {state.phase === "playing" && (
                <p className={`mt-2 text-lg font-semibold uppercase tracking-[0.2em] ${phaseLabel(state.roundPhase, state.revealType, state.phase).color}`}>
                  {phaseLabel(state.roundPhase, state.revealType, state.phase).text}
                </p>
              )}
            </div>
            <div className="flex gap-3">
              <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-5 py-3 text-red-100">
                <p className="text-xs uppercase tracking-[0.2em]">Red</p>
                <p className="text-3xl font-bold">{state.teamScores.red}</p>
              </div>
              <div className="rounded-2xl border border-blue-400/30 bg-blue-500/10 px-5 py-3 text-blue-100">
                <p className="text-xs uppercase tracking-[0.2em]">Blue</p>
                <p className="text-3xl font-bold">{state.teamScores.blue}</p>
              </div>
            </div>
          </div>
          {state.roundPhase === "voting" && state.votingEndsAt && (
            <div className="mt-6">
              <CountdownBar endsAt={state.votingEndsAt} totalSeconds={45} label="Voting closes in" />
            </div>
          )}
          {state.roundPhase === "accusation" && state.accusationEndsAt && (
            <div className="mt-6">
              <CountdownBar endsAt={state.accusationEndsAt} totalSeconds={20} label="Accusation closes in" />
            </div>
          )}
          {state.roundPhase === "reveal" && state.revealEndsAt && (
            <div className="mt-6">
              <CountdownBar endsAt={state.revealEndsAt} totalSeconds={25} label="Next phase in" />
            </div>
          )}
        </header>

        <section className="grid gap-6 lg:grid-cols-2">
          <div className={`rounded-[28px] border p-6 shadow-xl ${teamPanel("red")}`}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-white">{teamLabel("red")}</h2>
              <span className="text-sm text-red-100">{redPlayers.length} players</span>
            </div>
            <div className="space-y-3">
              {redPlayers.map((player) => (
                <div key={player.id} className="flex items-center justify-between rounded-2xl bg-mystery-900/60 px-4 py-3">
                  <span className="font-medium text-white">{player.name}</span>
                  {player.spy_exposed && (
                    <span className="rounded-full bg-amber-300/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-100">
                      Spy exposed
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className={`rounded-[28px] border p-6 shadow-xl ${teamPanel("blue")}`}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-white">{teamLabel("blue")}</h2>
              <span className="text-sm text-blue-100">{bluePlayers.length} players</span>
            </div>
            <div className="space-y-3">
              {bluePlayers.map((player) => (
                <div key={player.id} className="flex items-center justify-between rounded-2xl bg-mystery-900/60 px-4 py-3">
                  <span className="font-medium text-white">{player.name}</span>
                  {player.spy_exposed && (
                    <span className="rounded-full bg-amber-300/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-100">
                      Spy exposed
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        {state.latestRoundResult && (
          <section className="rounded-[32px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
            <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Round Resolution</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {(["red", "blue"] as TeamColor[]).map((team) => {
                const result = state.latestRoundResult!.teams[team];
                return (
                  <div key={team} className="rounded-2xl bg-mystery-900/70 p-5">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xl font-semibold text-white">{teamLabel(team)}</h3>
                      {result.tampered && (
                        <span className="rounded-full bg-amber-300/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-100">
                          Tampered
                        </span>
                      )}
                    </div>
                    <p className="mt-3 text-mystery-200">
                      Majority: <span className="font-semibold text-white">{result.majority_choice}</span>
                    </p>
                    <p className="mt-1 text-mystery-200">
                      Final: <span className="font-semibold text-white">{result.final_choice}</span>
                    </p>
                    <p className="mt-3 text-sm text-mystery-300">
                      Votes {result.trust_votes} trust / {result.betray_votes} betray / {result.team_size} total
                    </p>
                    <p className="mt-2 text-lg font-semibold text-white">
                      {result.score_delta > 0 ? "+" : ""}
                      {result.score_delta} points
                    </p>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {state.latestAccusationResult && (
          <section className="rounded-[32px] border border-white/10 bg-mystery-800/80 p-6 shadow-xl">
            <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Accusation Resolution</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {(["red", "blue"] as TeamColor[]).map((team) => {
                const result = state.latestAccusationResult!.teams[team];
                return (
                  <div key={team} className="rounded-2xl bg-mystery-900/70 p-5">
                    <h3 className="text-xl font-semibold text-white">{teamLabel(team)}</h3>
                    {!result.accusation_triggered && (
                      <p className="mt-3 text-mystery-200">No accusation landed this round.</p>
                    )}
                    {result.accusation_triggered && (
                      <>
                        <p className="mt-3 text-mystery-200">
                          Targeted: <span className="font-semibold text-white">{result.accused_player_name}</span>
                        </p>
                        <p className="mt-2 text-mystery-200">
                          {result.correct ? "Correct. Spy neutralized." : "Wrong. Team loses 1 point."}
                        </p>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
