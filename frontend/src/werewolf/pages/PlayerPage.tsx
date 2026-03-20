import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { WSEvent } from "@shared/types/game";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { buildWsUrl, getPlayerState, submitNightAction, submitVote } from "../api/http";
import { useWW, useWWActions } from "../context/GameContext";
import CountdownBar from "../components/CountdownBar";
import DayVote from "../components/DayVote";
import NightAction from "../components/NightAction";
import RoleCard from "../components/RoleCard";
import PlayerGrid from "../components/PlayerGrid";
import type { Role, WWPrivateState } from "../types/game";

function canActInNight(role: Role | null, nightSubPhase: string | null, alive: boolean): boolean {
  if (!alive) return false;
  if (!role || !nightSubPhase) return false;
  return (
    (nightSubPhase === "cupid" && role === "cupid") ||
    (nightSubPhase === "werewolves" && role === "werewolf") ||
    (nightSubPhase === "seer" && role === "seer") ||
    (nightSubPhase === "witch" && role === "witch")
  );
}

export default function PlayerPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useWW();
  const {
    setGame,
    setPhase,
    setPlayers,
    setPrivate,
    setPhaseDetail,
    setWinner,
    setLastDeaths,
    setSeerResult,
    setActionSubmitted,
    setHasVoted,
    setError,
  } = useWWActions();

  const [selected, setSelected] = useState("");
  const [selected2, setSelected2] = useState("");
  const [loading, setLoading] = useState(false);

  const isHunterRevengeAction = useMemo(
    () => state.role === "hunter" && !state.alive && state.daySubPhase === "hunter_revenge",
    [state.alive, state.daySubPhase, state.role]
  );

  const hydrateState = useCallback(
    (payload: WWPrivateState) => {
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
      if (payload.me) {
        setPrivate(payload.me.role, payload.me.alive, payload.me.lover_id);
      }
      if (payload.winner && payload.roles) {
        setWinner(payload.winner, payload.roles);
      }
    },
    [setLastDeaths, setPhase, setPhaseDetail, setPlayers, setPrivate, setWinner]
  );

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
    getPlayerState(code, state.playerId).then(hydrateState).catch((e) => {
      setError(e instanceof Error ? e.message : "Failed to load game state");
    });
  }, [code, hydrateState, setError, state.playerId]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      if (event.event === "game_started") {
        setPhase("playing");
      }
      if (event.event === "role_assigned") {
        setPrivate(
          event.data.role as Role,
          Boolean(event.data.alive ?? true),
          state.loverId
        );
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
        setSelected("");
        setSelected2("");
      }
      if (event.event === "seer_result") {
        setSeerResult(
          String(event.data.target_name ?? "Unknown"),
          Boolean(event.data.is_werewolf)
        );
      }
      if (event.event === "death_announcement" || event.event === "vote_result") {
        const players = event.data.players as WWPrivateState["players"] | undefined;
        if (players) setPlayers(players);
        const deaths = event.data.deaths as string[] | undefined;
        if (deaths) setLastDeaths(deaths);
      }
      if (event.event === "game_over") {
        const winner = event.data.winner as WWPrivateState["winner"];
        if (winner) {
          setWinner(
            winner,
            (event.data.roles as Record<string, Role>) ?? {}
          );
          navigate(`/result/${code}`);
        }
      }
    },
    [
      code,
      navigate,
      setLastDeaths,
      setPhase,
      setPhaseDetail,
      setPlayers,
      setPrivate,
      setSeerResult,
      setWinner,
      state.dayNumber,
      state.loverId,
      state.nightNumber,
    ]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleNightSubmit() {
    if (!code || !state.playerId || !state.role) return;
    let payload: { action: string; target?: string; target2?: string } | null = null;

    if (state.nightSubPhase === "cupid" && state.role === "cupid") {
      payload = { action: "cupid_link", target: selected, target2: selected2 };
    } else if (state.nightSubPhase === "werewolves" && state.role === "werewolf") {
      payload = { action: "werewolf_vote", target: selected };
    } else if (state.nightSubPhase === "seer" && state.role === "seer") {
      payload = { action: "seer_investigate", target: selected };
    } else if (state.nightSubPhase === "witch" && state.role === "witch") {
      payload = { action: "witch_kill", target: selected };
    } else if (isHunterRevengeAction) {
      payload = { action: "hunter_shoot", target: selected };
    }

    if (!payload) return;
    setLoading(true);
    try {
      await submitNightAction(code, state.playerId, payload);
      setActionSubmitted(true);
      setSelected("");
      setSelected2("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleVoteSubmit() {
    if (!code || !state.playerId || !selected) return;
    setLoading(true);
    try {
      await submitVote(code, state.playerId, selected);
      setHasVoted(true);
      setSelected("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Vote failed");
    } finally {
      setLoading(false);
    }
  }

  const canNightAct = canActInNight(state.role, state.nightSubPhase, state.alive) || isHunterRevengeAction;
  const canVote = state.daySubPhase === "voting" && state.alive;

  return (
    <div className="min-h-screen px-4 py-6">
      <div className="max-w-lg mx-auto space-y-4">
        <RoleCard role={state.role} alive={state.alive} />

        {(state.nightSubPhase || state.daySubPhase) && (
          <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700">
            <p className="text-sm uppercase tracking-wider text-mystery-400">
              {state.nightSubPhase
                ? `Night ${state.nightNumber}: ${state.nightSubPhase}`
                : `Day ${state.dayNumber}: ${state.daySubPhase}`}
            </p>
            <div className="mt-2">
              <CountdownBar endsAt={state.phaseEndsAt} fallbackSeconds={30} />
            </div>
          </div>
        )}

        {canNightAct && (
          <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700 space-y-3">
            <NightAction
              role={state.role}
              players={state.players}
              prompt={isHunterRevengeAction ? "Choose someone to shoot." : "Choose your target."}
              selected={selected}
              selected2={selected2}
              onSelect={setSelected}
              onSelect2={setSelected2}
              onSubmit={handleNightSubmit}
              disabled={loading || state.hasSubmittedAction}
            />
            {state.hasSubmittedAction && (
              <p className="text-mystery-300 text-sm">Action submitted. Waiting for the phase to end.</p>
            )}
          </div>
        )}

        {canVote && (
          <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700 space-y-3">
            <DayVote
              players={state.players}
              selected={selected}
              onSelect={setSelected}
              disabled={loading || state.hasVoted}
            />
            <button
              onClick={handleVoteSubmit}
              disabled={!selected || loading || state.hasVoted}
              className="w-full rounded-xl p-3 bg-red-600 hover:bg-red-500 disabled:opacity-40"
            >
              {state.hasVoted ? "Vote submitted" : "Submit Vote"}
            </button>
          </div>
        )}

        {state.seerResult && (
          <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700">
            <p className="text-mystery-300 text-sm">Seer Result</p>
            <p className="text-mystery-100">
              {state.seerResult.targetName} is{" "}
              <span className="font-semibold">
                {state.seerResult.isWerewolf ? "a Werewolf" : "not a Werewolf"}
              </span>
            </p>
          </div>
        )}

        <div className="bg-mystery-800 rounded-2xl p-4 border border-mystery-700 space-y-2">
          <p className="text-mystery-200 font-semibold">Players</p>
          <PlayerGrid players={state.players} />
        </div>

        {state.error && <p className="text-red-300 text-sm text-center">{state.error}</p>}
      </div>
    </div>
  );
}
