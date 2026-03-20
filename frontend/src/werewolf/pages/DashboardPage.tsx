import { useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { WSEvent } from "@shared/types/game";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { buildWsUrl, getPlayerState } from "../api/http";
import { useWW, useWWActions } from "../context/GameContext";
import CountdownBar from "../components/CountdownBar";
import DeathAnnouncement from "../components/DeathAnnouncement";
import GameNarration from "../components/GameNarration";
import PlayerGrid from "../components/PlayerGrid";
import type { Role, WWPrivateState } from "../types/game";

export default function DashboardPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useWW();
  const {
    setGame,
    setPhase,
    setPlayers,
    setPhaseDetail,
    setWinner,
    setLastDeaths,
    addPlayer,
    setError,
  } = useWWActions();

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("ww_player_id");
    const storedCode = localStorage.getItem("ww_game_code");
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "Host", true);
    }
  }, [code, setGame, state.playerId]);

  useEffect(() => {
    if (!code || !state.playerId) return;
    getPlayerState(code, state.playerId)
      .then((payload: WWPrivateState) => {
        setPhase(payload.phase);
        setPlayers(payload.players);
        setPhaseDetail(
          payload.night_sub_phase,
          payload.day_sub_phase,
          payload.night_number,
          payload.day_number,
          payload.phase_ends_at
        );
        setLastDeaths(payload.last_deaths);
        if (payload.winner && payload.roles) {
          setWinner(payload.winner, payload.roles);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load state"));
  }, [code, setError, setLastDeaths, setPhase, setPhaseDetail, setPlayers, setWinner, state.playerId]);

  const handleWSEvent = useCallback((event: WSEvent) => {
    if (event.event === "player_joined") {
      addPlayer({
        id: event.data.player_id as string,
        name: event.data.player_name as string,
        alive: true,
      });
    }
    if (event.event === "phase_changed") {
      setPhase("playing");
      setPhaseDetail(
        (event.data.night_sub_phase as WWPrivateState["night_sub_phase"]) ?? null,
        (event.data.day_sub_phase as WWPrivateState["day_sub_phase"]) ?? null,
        Number(event.data.night_number ?? state.nightNumber),
        Number(event.data.day_number ?? state.dayNumber),
        (event.data.phase_ends_at as string | null) ?? null
      );
    }
    if (event.event === "death_announcement" || event.event === "vote_result") {
      const players = event.data.players as WWPrivateState["players"] | undefined;
      if (players) setPlayers(players);
      const deaths = event.data.deaths as string[] | undefined;
      if (deaths) setLastDeaths(deaths);
    }
    if (event.event === "game_over" && code) {
      const winner = event.data.winner as WWPrivateState["winner"];
      if (winner) {
        setWinner(
          winner,
          (event.data.roles as Record<string, Role>) ?? {}
        );
        navigate(`/result/${code}`);
      }
    }
  }, [addPlayer, code, navigate, setLastDeaths, setPhase, setPhaseDetail, setPlayers, setWinner, state.dayNumber, state.nightNumber]);

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  return (
    <div className="min-h-screen px-4 py-6">
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700">
          <p className="text-xs uppercase tracking-wider text-mystery-400">Host Dashboard</p>
          <h2 className="text-2xl text-mystery-100 font-semibold">Room {code}</h2>
          <GameNarration nightSubPhase={state.nightSubPhase} daySubPhase={state.daySubPhase} />
          <div className="mt-2">
            <CountdownBar endsAt={state.phaseEndsAt} fallbackSeconds={30} />
          </div>
        </div>

        <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700">
          <DeathAnnouncement deaths={state.lastDeaths} players={state.players} />
        </div>

        <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700 space-y-2">
          <p className="text-mystery-200 font-semibold">Players</p>
          <PlayerGrid players={state.players} />
        </div>

        {state.error && <p className="text-red-300 text-sm text-center">{state.error}</p>}
      </div>
    </div>
  );
}
