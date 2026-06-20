import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import type { WSEvent } from "@shared/types/game";
import {
  buildWsUrl,
  getGameInfo,
  saveDraft,
  submitAnswers,
  vetoAnswer,
} from "../api/http";
import CountdownBar from "../components/CountdownBar";
import ReviewCategoryPanel from "../components/ReviewCategoryPanel";
import ScoreBoard from "../components/ScoreBoard";
import { useBasta, useBastaActions, useRestoreSession } from "../context/GameContext";
import type { RoundResult } from "../types/game";

function normalizeAnswer(value: string) {
  return value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase();
}

export default function PlayPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useBasta();
  const {
    setPhase,
    setPlayers,
    newRound,
    setSubmitted,
    setSubmissions,
    setRoundTimer,
    setReviewCategory,
    setRoundResult,
    updateVeto,
    setWinner,
    setScores,
    setConfig,
    setError,
  } = useBastaActions();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [vetoedKeys, setVetoedKeys] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  useRestoreSession(code);

  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setPhase(info.phase);
      setScores(info.scores);
      setConfig(info.categories, info.rounds_to_play, info.round_seconds, info.host_paced);
      if (info.round_phase === "answering" && info.current_letter) {
        newRound(
          info.current_round,
          info.rounds_to_play,
          info.current_letter,
          info.categories,
          info.round_ends_at,
          info.players,
          info.scores
        );
        setSubmissions(info.submissions_in);
      }
      if (
        info.round_phase === "review" &&
        info.current_review_category &&
        info.current_review_index !== null
      ) {
        setReviewCategory({
          round: info.current_round,
          letter: info.current_letter,
          category_index: info.current_review_index,
          category_count: info.categories.length,
          category: info.current_review_category,
          review_seconds: info.review_seconds,
          vetoes_required: info.vetoes_required,
          answers: info.current_review_answers,
        });
      }
      if (info.round_phase === "reveal" && info.last_round_result) {
        setRoundResult(info.last_round_result);
      }
      if (info.phase === "finished" && info.winner) {
        setWinner(info.winner, info.scores);
        navigate(`/result/${code}`);
      }
    });
  }, [code]);

  useEffect(() => {
    if (state.isHost && code) {
      navigate(`/dashboard/${code}`, { replace: true });
    }
  }, [state.isHost, code, navigate]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "new_round":
          setAnswers({});
          setVetoedKeys(new Set());
          setSubmitting(false);
          newRound(
            event.data.round as number,
            event.data.rounds_to_play as number,
            event.data.letter as string,
            event.data.categories as string[],
            event.data.round_ends_at as string | null,
            event.data.players as { id: string; name: string }[],
            event.data.scores as Record<string, number>
          );
          break;
        case "basta_called":
          setRoundTimer(event.data.round_ends_at as string);
          break;
        case "answers_submitted":
          setSubmissions(event.data.submissions_in as number);
          break;
        case "review_category":
          setReviewCategory(event.data as any);
          break;
        case "veto_update":
          updateVeto(
            event.data.category as string,
            (event.data.affected_player_ids as string[] | undefined) ?? [
              event.data.target_player_id as string,
            ],
            event.data.veto_count as number
          );
          break;
        case "round_result":
          setSubmitting(false);
          setRoundResult(event.data as unknown as RoundResult);
          break;
        case "game_over":
          setWinner(
            event.data.winner_name as string,
            event.data.scores as Record<string, number>
          );
          navigate(`/result/${code}`);
          break;
        case "game_reset":
          navigate(`/lobby/${code}`);
          break;
      }
    },
    [
      code,
      navigate,
      newRound,
      setReviewCategory,
      setRoundResult,
      setRoundTimer,
      setSubmissions,
      setWinner,
      updateVeto,
    ]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleSubmit() {
    if (!code || !state.playerId) return;
    setSubmitting(true);
    try {
      await submitAnswers(code, state.playerId, answers);
      setSubmitted();
    } catch (e: any) {
      setError(e.message);
      setSubmitting(false);
    }
  }

  function updateAnswer(category: string, value: string) {
    const nextAnswers = { ...answers, [category]: value };
    setAnswers(nextAnswers);
    if (!code || !state.playerId || state.hasSubmitted || state.roundPhase !== "answering") {
      return;
    }
    saveDraft(code, state.playerId, nextAnswers).catch(() => {});
  }

  const handleAutoSubmit = useCallback(() => {
    if (!code || !state.playerId || state.hasSubmitted || submitting) return;
    setSubmitting(true);
    submitAnswers(code, state.playerId, answers, true)
      .then(() => setSubmitted())
      .catch(() => setSubmitting(false));
  }, [answers, code, setSubmitted, state.hasSubmitted, state.playerId, submitting]);

  async function handleVeto(targetPlayerId: string) {
    if (!code || !state.playerId || !state.reviewCategory) return;
    const vetoKey = `${state.reviewCategory.category}:${targetPlayerId}`;
    setVetoedKeys((current) => new Set(current).add(vetoKey));
    try {
      await vetoAnswer(code, state.playerId, state.reviewCategory.category, targetPlayerId);
    } catch (e: any) {
      setVetoedKeys((current) => {
        const next = new Set(current);
        next.delete(vetoKey);
        return next;
      });
      setError(e.message);
    }
  }

  const canCallBasta = state.categories.every((category) =>
    normalizeAnswer(answers[category] ?? "").startsWith(
      normalizeAnswer(state.currentLetter ?? "")
    )
  );

  if (state.phase === "finished") {
    navigate(`/result/${code}`, { replace: true });
  }

  if (state.roundPhase === "reveal" && state.roundResult) {
    return (
      <div className="min-h-screen px-4 py-6">
        <div className="mx-auto max-w-sm space-y-5">
          <section className="rounded-lg border border-mystery-700 bg-mystery-800 p-5 text-center shadow-xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
              Round {state.currentRound} complete
            </p>
            <h1 className="mt-2 text-3xl font-black text-mystery-100">
              Scores
            </h1>
          </section>
          <ScoreBoard scores={state.scores} />
        </div>
      </div>
    );
  }

  if (state.roundPhase === "review" && state.reviewCategory) {
    return (
      <div className="min-h-screen px-4 py-6">
        <div className="mx-auto max-w-sm space-y-5">
          <ReviewCategoryPanel
            layout="phone"
            review={state.reviewCategory}
            currentPlayerId={state.playerId}
            vetoedKeys={vetoedKeys}
            onVeto={handleVeto}
          />
          {state.error && <p className="text-center text-sm text-rose-200">{state.error}</p>}
        </div>
      </div>
    );
  }

  if (state.roundPhase !== "answering" || !state.currentLetter) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-6 text-center shadow-xl">
          <h1 className="text-3xl font-black text-mystery-100">Basta</h1>
          <p className="mt-2 text-mystery-300">Waiting for the next round</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-5">
      <div className="mx-auto max-w-2xl space-y-5">
        <header className="flex items-center justify-between rounded-lg border border-mystery-700 bg-mystery-800 p-4 shadow-xl">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-mystery-400">
              Round {state.currentRound} of {state.roundsToPlay}
            </p>
            <h1 className="text-6xl font-black leading-none text-amber-200">
              {state.currentLetter}
            </h1>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold text-mystery-300">
              {state.submissionsIn}/{state.players.length}
            </p>
            <p className="text-xs uppercase tracking-wide text-mystery-500">
              Submitted
            </p>
          </div>
        </header>

        {state.roundEndsAt ? (
          <CountdownBar
            endsAt={state.roundEndsAt}
            totalSeconds={state.roundSeconds}
            onComplete={handleAutoSubmit}
          />
        ) : (
          <div className="rounded-lg border border-mystery-700 bg-mystery-800 p-4 text-center text-sm font-semibold text-mystery-300">
            Waiting for first Basta
          </div>
        )}

        <div className="space-y-3">
          {state.categories.map((category) => (
            <label key={category} className="block space-y-1">
              <span className="text-sm font-semibold text-mystery-200">{category}</span>
              <input
                type="text"
                maxLength={80}
                disabled={state.hasSubmitted || submitting}
                value={answers[category] ?? ""}
                onChange={(e) => updateAnswer(category, e.target.value)}
                className="w-full rounded-lg border border-mystery-600 bg-mystery-900 px-4 py-3 text-lg text-white outline-none focus:border-amber-300 disabled:opacity-60"
              />
            </label>
          ))}
        </div>

        {state.hasSubmitted ? (
          <div className="rounded-lg border border-teal-300/40 bg-teal-950/40 p-5 text-center">
            <p className="font-bold text-teal-100">Submitted</p>
          </div>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting || !canCallBasta}
            className="w-full rounded-lg bg-amber-300 px-4 py-4 text-xl font-black text-mystery-900 transition hover:bg-amber-200 disabled:opacity-50"
          >
            {submitting ? "..." : "Basta"}
          </button>
        )}

        {state.error && <p className="text-center text-sm text-rose-200">{state.error}</p>}
      </div>
    </div>
  );
}
