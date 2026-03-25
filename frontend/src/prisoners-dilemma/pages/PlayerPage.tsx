import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { buildWsUrl, getGameInfo, getPrivateState, submitAccusation, submitVote } from "../api/http";
import { usePD, usePDActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import CountdownBar from "../components/CountdownBar";
import type { WSEvent } from "@shared/types/game";
import type { AccusationResult, Decision, PDPlayerInfo, PDPrivateState, RoundResult, TeamColor } from "../types/game";

function teamLabel(team: TeamColor) {
  return team === "red" ? "Red Team" : "Blue Team";
}

const themes = {
  red: {
    page: "bg-gradient-to-b from-red-950/40 to-mystery-950",
    section: "border-red-400/25 bg-red-950/30",
    badge: "border-red-400/30 bg-red-500/15 text-red-100",
    inner: "bg-red-950/40",
    btnPrimary: "bg-red-600 hover:bg-red-500 disabled:opacity-40",
    btnSelected: "border-red-300 bg-red-500/20",
    confirmed: "border-red-400/20 bg-red-500/10 text-red-100",
    accent: "text-red-300",
  },
  blue: {
    page: "bg-gradient-to-b from-blue-950/40 to-mystery-950",
    section: "border-blue-400/25 bg-blue-950/30",
    badge: "border-blue-400/30 bg-blue-500/15 text-blue-100",
    inner: "bg-blue-950/40",
    btnPrimary: "bg-blue-600 hover:bg-blue-500 disabled:opacity-40",
    btnSelected: "border-blue-300 bg-blue-500/20",
    confirmed: "border-blue-400/20 bg-blue-500/10 text-blue-100",
    accent: "text-blue-300",
  },
} as const;

export default function PlayerPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = usePD();
  const {
    addPlayer,
    accusationStarted,
    clearError,
    roundStarted,
    setAccusationResult,
    setAccused,
    setError,
    setGame,
    setPhase,
    setPlayers,
    setPrivateState,
    setRoundResult,
    setTeamScores,
    setVoted,
    setWinner,
    syncGameInfo,
  } = usePDActions();

  const [sabotage, setSabotage] = useState(false);
  const [accuseTarget, setAccuseTarget] = useState<string | null>(null);
  const [submittingVote, setSubmittingVote] = useState(false);
  const [submittingAccusation, setSubmittingAccusation] = useState(false);
  const [roleRevealed, setRoleRevealed] = useState(false);

  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("pd_player_id");
    const storedCode = localStorage.getItem("pd_game_code");
    const isHost = localStorage.getItem("pd_is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
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

  useEffect(() => {
    if (!code || !state.playerId || state.isHost) return;
    getPrivateState(code, state.playerId)
      .then((privateState) => setPrivateState(privateState))
      .catch(() => undefined);
  }, [code, setPrivateState, state.isHost, state.playerId]);

  useEffect(() => {
    if (state.isHost && code) {
      navigate(`/dashboard/${code}`, { replace: true });
    }
  }, [code, navigate, state.isHost]);

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
        case "role_assigned":
        case "private_state":
          setPrivateState(event.data as unknown as PDPrivateState);
          break;
        case "game_started":
          setPhase("playing");
          setPlayers(event.data.players as PDPlayerInfo[]);
          setTeamScores(event.data.team_scores as Record<TeamColor, number>);
          break;
        case "round_started":
          clearError();
          setSabotage(false);
          setAccuseTarget(null);
          setSubmittingVote(false);
          setSubmittingAccusation(false);
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
          setWinner(event.data as unknown as any);
          navigate(`/result/${code}`);
          break;
      }
    },
    [
      accusationStarted,
      addPlayer,
      clearError,
      code,
      navigate,
      roundStarted,
      setAccusationResult,
      setPhase,
      setPlayers,
      setPrivateState,
      setRoundResult,
      setTeamScores,
      setWinner,
    ]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  const myTeamMates = useMemo(
    () =>
      state.players.filter(
        (player) => player.team === state.privateState?.team && player.id !== state.playerId
      ),
    [state.playerId, state.players, state.privateState?.team]
  );

  async function handleAccusationSubmit() {
    if (!code || !state.playerId) return;
    setSubmittingAccusation(true);
    try {
      await submitAccusation(code, state.playerId, Boolean(accuseTarget), accuseTarget);
      setAccused();
    } catch (err: any) {
      setError(err.message);
      setSubmittingAccusation(false);
    }
  }

  if (!state.privateState) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-mystery-300">Waiting for private assignment...</p>
        </div>
      </div>
    );
  }

  const team = state.privateState.team;
  // Spies display the opposite team color so onlookers can't identify them
  const displayTeam: TeamColor = state.privateState.is_spy
    ? (team === "red" ? "blue" : "red")
    : team;
  const t = themes[displayTeam];
  const roundTeam = state.latestRoundResult?.teams[team];
  const accusationTeam = state.latestAccusationResult?.teams[team];

  return (
    <div className={`min-h-screen px-4 py-6 ${t.page}`}>
      <div className="mx-auto max-w-md space-y-4">
        <section className={`rounded-[28px] border p-5 shadow-xl ${t.section}`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-white">
                {state.privateState.player_name}
              </h1>
              <p className={`mt-1 text-sm ${t.accent}`}>
                Round {state.currentRound || 1} / {state.totalRounds}
              </p>
            </div>
            <div className={`rounded-2xl border px-4 py-2 text-sm font-semibold ${t.badge}`}>
              {teamLabel(displayTeam)}
            </div>
          </div>

          <button
            onClick={() => setRoleRevealed((prev) => !prev)}
            className={`mt-4 w-full rounded-2xl border border-white/10 p-4 text-left transition hover:brightness-125 ${t.inner}`}
          >
            {roleRevealed ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-mystery-400">Secret Role</p>
                  <p className="mt-2 text-lg font-semibold text-white">
                    {state.privateState.is_spy ? "Spy" : "Operative"}
                  </p>
                  <p className="mt-1 text-sm text-mystery-200">
                    {state.privateState.is_spy
                      ? state.privateState.spy_active
                        ? `Your screen shows ${teamLabel(displayTeam)}, but you're actually ${teamLabel(team)}.`
                        : "You were exposed and can no longer sabotage."
                      : "Vote with your team and help identify your spy."}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-mystery-400">Team Score</p>
                  <p className="mt-2 text-lg font-semibold text-white">{state.teamScores[team]}</p>
                  <p className="mt-1 text-sm text-mystery-200">
                    {state.privateState.is_spy ? `${state.privateState.sabotage_charges} sabotage charges left` : "Stay aligned if you want trust to stick."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-2 py-3 text-mystery-300">
                <span className="text-sm uppercase tracking-[0.25em]">Tap to reveal your role</span>
              </div>
            )}
          </button>
        </section>

        {state.roundPhase === "voting" && (
          <section className={`rounded-[28px] border p-5 shadow-xl ${t.section}`}>
            <div className="space-y-4">
              <div>
                <p className={`text-sm uppercase tracking-[0.25em] ${t.accent}`}>Private Vote</p>
                <h2 className="mt-1 text-2xl font-semibold text-white">Trust or Betray</h2>
                <p className="mt-2 text-sm text-mystery-200">
                  Discuss in person, then lock your personal vote here. Ties resolve to
                  betrayal, and a spy sabotage flips the team decision entirely.
                </p>
              </div>

              {state.votingEndsAt && (
                <CountdownBar
                  endsAt={state.votingEndsAt}
                  totalSeconds={45}
                  label="Voting closes in"
                />
              )}

              {state.hasVoted ? (
                <div className={`rounded-2xl border p-4 text-center ${t.confirmed}`}>
                  Vote locked in. Wait for the round reveal.
                </div>
              ) : (
                <>
                  {state.privateState.is_spy && state.privateState.spy_active && state.privateState.sabotage_charges > 0 && (
                    <label className="flex items-start gap-3 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">
                      <input
                        type="checkbox"
                        checked={sabotage}
                        onChange={(event) => setSabotage(event.target.checked)}
                        className="mt-1"
                      />
                      <span>
                        Sabotage this vote to flip its outcome.
                      </span>
                    </label>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    {(["trust", "betray"] as Decision[]).map((value) => (
                      <button
                        key={value}
                        disabled={submittingVote}
                        onClick={() => {
                          if (!code || !state.playerId) return;
                          setSubmittingVote(true);
                          submitVote(code, state.playerId, value, sabotage)
                            .then(() => setVoted())
                            .catch((err: any) => {
                              setError(err.message);
                              setSubmittingVote(false);
                            });
                        }}
                        className={`rounded-2xl border px-4 py-5 text-left transition disabled:opacity-40 ${
                          `border-white/10 ${t.inner} hover:brightness-125`
                        }`}
                      >
                        <p className="text-2xl font-bold uppercase tracking-[0.15em] text-white">
                          {value}
                        </p>
                        <p className={`mt-1 text-sm ${t.accent}`}>
                          {value === "trust" ? "Play nice" : "Play dirty"}
                        </p>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </section>
        )}

        {state.roundPhase === "accusation" && (
          <section className={`rounded-[28px] border p-5 shadow-xl ${t.section}`}>
            <div className="space-y-4">
              <div>
                <p className={`text-sm uppercase tracking-[0.25em] ${t.accent}`}>Accusation</p>
                <h2 className="mt-1 text-2xl font-semibold text-white">Do you call out a spy?</h2>
                <p className="mt-2 text-sm text-mystery-200">
                  Majority yes is required. Wrong accusations cost your team 1 point.
                </p>
              </div>

              {state.accusationEndsAt && (
                <CountdownBar
                  endsAt={state.accusationEndsAt}
                  totalSeconds={20}
                  label="Accusation closes in"
                />
              )}

              {state.hasAccused ? (
                <div className={`rounded-2xl border p-4 text-center ${t.confirmed}`}>
                  Accusation submitted. Wait for the team result.
                </div>
              ) : (
                <>
                  <button
                    onClick={() => setAccuseTarget(null)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      accuseTarget === null
                        ? t.btnSelected
                        : `border-white/10 ${t.inner} hover:brightness-125`
                    }`}
                  >
                    <p className="font-semibold text-white">No accusation</p>
                    <p className="mt-1 text-sm text-mystery-200">Stay quiet this round.</p>
                  </button>

                  <div className="space-y-3">
                    {myTeamMates.map((player) => (
                      <button
                        key={player.id}
                        onClick={() => setAccuseTarget(player.id)}
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                          accuseTarget === player.id
                            ? "border-amber-200 bg-amber-300/10"
                            : `border-white/10 ${t.inner} hover:brightness-125`
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <p className="font-semibold text-white">{player.name}</p>
                          {player.spy_exposed && (
                            <span className="rounded-full bg-green-500/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-green-100">
                              Exposed
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={handleAccusationSubmit}
                    disabled={submittingAccusation}
                    className={`w-full rounded-2xl px-5 py-4 text-lg font-semibold text-white transition ${t.btnPrimary}`}
                  >
                    {submittingAccusation ? "Submitting..." : "Submit Accusation Vote"}
                  </button>
                </>
              )}
            </div>
          </section>
        )}

        {state.roundPhase === "reveal" && (
          <section className={`rounded-[28px] border p-5 shadow-xl ${t.section}`}>
            <div className="space-y-4">
              <div>
                <p className={`text-sm uppercase tracking-[0.25em] ${t.accent}`}>Reveal</p>
                <h2 className="mt-1 text-2xl font-semibold text-white">Look up at the host screen</h2>
              </div>

              {roundTeam && (
                <div className={`rounded-2xl p-4 ${t.inner}`}>
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-white">Your team played {roundTeam.final_choice}</p>
                    {roundTeam.tampered && (
                      <span className="rounded-full bg-amber-300/15 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-100">
                        Tampered
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-sm text-mystery-200">
                    Team votes: {roundTeam.trust_votes} trust / {roundTeam.betray_votes} betray
                    {" · "}
                    score {roundTeam.score_delta > 0 ? "+" : ""}
                    {roundTeam.score_delta}
                  </p>
                </div>
              )}

              {accusationTeam && accusationTeam.accusation_triggered && (
                <div className={`rounded-2xl p-4 ${t.inner}`}>
                  <p className="font-semibold text-white">
                    {accusationTeam.correct
                      ? `${accusationTeam.accused_player_name} was the spy.`
                      : `${accusationTeam.accused_player_name} was not the spy.`}
                  </p>
                  <p className="mt-2 text-sm text-mystery-200">
                    {accusationTeam.correct
                      ? "That spy is neutralized for the rest of the game."
                      : "Wrong accusation: your team lost 1 point."}
                  </p>
                </div>
              )}

              {accusationTeam && !accusationTeam.accusation_triggered && (
                <div className={`rounded-2xl p-4 text-sm text-mystery-200 ${t.inner}`}>
                  No accusation landed for your team this round.
                </div>
              )}
            </div>
          </section>
        )}

        {state.error && <p className="text-center text-sm text-red-300">{state.error}</p>}
      </div>
    </div>
  );
}
