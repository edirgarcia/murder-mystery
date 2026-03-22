import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useFQ, useFQActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { vote, getGameInfo, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";
import type { RoundResult } from "../types/game";
import QuestionCard from "../components/QuestionCard";
import VoteButtons from "../components/VoteButtons";
import CountdownBar from "../components/CountdownBar";
import ShameIndicator from "../components/ShameIndicator";

export default function VotePage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useFQ();
  const { setGame, setPhase, setPlayers, addPlayer, newQuestion, setVoted, setRoundResult, setWinner, setPointsToWin, setError } = useFQActions();
  const [selected, setSelected] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [narrationText, setNarrationText] = useState<string | null>(null);

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

  // Load game state from HTTP (catches missed WS events)
  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setPhase(info.phase);
      if (info.scores) {
        // scores come as name->score, pass through
      }
      if (info.current_question && info.round_phase === "voting" && !state.currentQuestion) {
        newQuestion(
          info.current_question,
          info.current_round,
          info.voting_ends_at ?? new Date().toISOString(),
          info.players,
        );
      }
    });
  }, [code]);

  // Redirect host to dashboard
  useEffect(() => {
    if (state.isHost && code) {
      navigate(`/dashboard/${code}`, { replace: true });
    }
  }, [state.isHost, code, navigate]);

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
          setNarrationText("");
          if (event.data.points_to_win) {
            setPointsToWin(event.data.points_to_win as number);
          }
          break;
        case "intro_narration":
          setNarrationText(event.data.text as string);
          break;
        case "intro_done":
          setNarrationText(null);
          break;
        case "new_question":
          setSelected(null);
          setSubmitting(false);
          newQuestion(
            event.data.question as string,
            event.data.round as number,
            event.data.voting_ends_at as string,
            (event.data.players as { id: string; name: string }[]),
          );
          break;
        case "round_result":
          setRoundResult(event.data as unknown as RoundResult);
          break;
        case "game_over":
          setWinner(event.data.winner_name as string);
          navigate(`/result/${code}`);
          break;
      }
    },
    [code, navigate, addPlayer, setPhase, newQuestion, setRoundResult, setWinner, setPointsToWin]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleVote() {
    if (!code || !state.playerId || !selected) return;
    setSubmitting(true);
    try {
      await vote(code, state.playerId, selected);
      setVoted();
    } catch (e: any) {
      setError(e.message);
      setSubmitting(false);
    }
  }

  // Intro narration overlay
  if (narrationText !== null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black/90 px-4">
        <p className="animate-pulse text-center text-3xl font-bold text-mystery-100 px-6 leading-relaxed md:text-5xl">
          {narrationText}
        </p>
      </div>
    );
  }

  // Waiting for first question
  if (!state.currentQuestion && state.roundPhase !== "reveal") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-md text-center space-y-4">
          <h2 className="text-3xl font-bold text-mystery-300">Get Ready!</h2>
          <p className="text-mystery-400">Waiting for the first question...</p>
        </div>
      </div>
    );
  }

  // Reveal phase — tell players to look at the dashboard
  if (state.roundPhase === "reveal") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-md text-center space-y-4">
          <p className="text-5xl">📺</p>
          <h2 className="text-2xl font-bold text-mystery-300">Look at the screen!</h2>
          <p className="text-mystery-400 animate-pulse">Next question coming up...</p>
        </div>
      </div>
    );
  }

  // Voting phase
  return (
    <div className="min-h-screen px-4 py-6">
      <div className="max-w-md mx-auto space-y-4">
        <QuestionCard question={state.currentQuestion!} round={state.currentRound} />

        {state.votingEndsAt && (
          <CountdownBar endsAt={state.votingEndsAt} totalSeconds={15} />
        )}

        {state.shameHolder && <ShameIndicator name={state.shameHolder} />}

        {state.hasVoted ? (
          <div className="bg-mystery-800 rounded-2xl p-6 text-center shadow-xl">
            <p className="text-mystery-300 font-semibold text-lg">Vote locked in!</p>
            <p className="text-mystery-400 text-sm mt-1">Waiting for others...</p>
          </div>
        ) : (
          <>
            <VoteButtons
              players={state.players}
              myId={state.playerId!}
              selected={selected}
              onSelect={setSelected}
              disabled={submitting}
            />
            <button
              onClick={handleVote}
              disabled={!selected || submitting}
              className="w-full py-3 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition disabled:opacity-40"
            >
              {submitting ? "..." : "Vote!"}
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
