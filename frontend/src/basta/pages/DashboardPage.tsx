import { useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import type { WSEvent } from "@shared/types/game";
import { buildWsUrl, getGameInfo, nextRound, resetGame } from "../api/http";
import CountdownBar from "../components/CountdownBar";
import ReviewCategoryPanel from "../components/ReviewCategoryPanel";
import RoundResultTable from "../components/RoundResultTable";
import ScoreBoard from "../components/ScoreBoard";
import { useBasta, useBastaActions, useRestoreSession } from "../context/GameContext";
import type { RoundResult } from "../types/game";

export default function DashboardPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useBasta();
  const {
    setPhase,
    setPlayers,
    newRound,
    setSubmissions,
    setRoundTimer,
    setReviewCategory,
    setRoundResult,
    updateVeto,
    setWinner,
    setScores,
    setConfig,
    resetGame: resetGameState,
  } = useBastaActions();

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
      }
    });
  }, [code]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "new_round":
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
          setRoundResult(event.data as unknown as RoundResult);
          break;
        case "game_over":
          setWinner(
            event.data.winner_name as string,
            event.data.scores as Record<string, number>
          );
          break;
        case "game_reset":
          resetGameState();
          navigate(`/lobby/${code}`);
          break;
      }
    },
    [
      code,
      navigate,
      newRound,
      resetGameState,
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

  if (state.phase === "finished") {
    return (
      <div className="min-h-screen px-4 py-8">
        <div className="mx-auto max-w-3xl space-y-6">
          <section className="rounded-lg border border-mystery-700 bg-mystery-800 p-6 text-center shadow-xl">
            <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
              Winner
            </p>
            <h1 className="mt-2 text-5xl font-black text-amber-200">
              {state.winner}
            </h1>
          </section>
          <ScoreBoard scores={state.scores} />
          <button
            onClick={() => code && state.playerId && resetGame(code, state.playerId)}
            className="w-full rounded-lg bg-amber-300 px-4 py-4 text-lg font-black text-mystery-900 transition hover:bg-amber-200"
          >
            Play Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-6">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <main className="space-y-5">
          <header className="rounded-lg border border-mystery-700 bg-mystery-800 p-5 shadow-xl">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
                  Room {code}
                </p>
                <h1 className="mt-1 text-3xl font-black text-mystery-100">
                  Round {state.currentRound || 1} of {state.roundsToPlay}
                </h1>
              </div>
              {state.currentLetter && (
                <div className="text-right">
                  <p className="text-xs font-semibold uppercase tracking-wide text-mystery-400">
                    Letter
                  </p>
                  <p className="text-7xl font-black leading-none text-amber-200">
                    {state.currentLetter}
                  </p>
                </div>
              )}
            </div>
          </header>

          {state.roundPhase === "review" && state.reviewCategory ? (
            <>
              <ReviewCategoryPanel
                layout="dashboard"
                review={state.reviewCategory}
                currentPlayerId={null}
              />
              {state.hostPaced && (
                <button
                  onClick={() => code && state.playerId && nextRound(code, state.playerId)}
                  className="w-full rounded-lg bg-teal-300 px-4 py-4 text-lg font-black text-mystery-900 transition hover:bg-teal-200"
                >
                  {state.reviewCategory.category_index + 1 >=
                  state.reviewCategory.category_count
                    ? "Show Scores"
                    : "Next Category"}
                </button>
              )}
            </>
          ) : state.roundPhase === "reveal" && state.roundResult ? (
            <>
              <RoundResultTable result={state.roundResult} />
              {state.hostPaced && !state.winner && (
                <button
                  onClick={() => code && state.playerId && nextRound(code, state.playerId)}
                  className="w-full rounded-lg bg-teal-300 px-4 py-4 text-lg font-black text-mystery-900 transition hover:bg-teal-200"
                >
                  Next Round
                </button>
              )}
            </>
          ) : (
            <section className="rounded-lg border border-mystery-700 bg-mystery-800 p-5 shadow-xl">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
                    Submitted
                  </p>
                  <p className="text-4xl font-black text-teal-200">
                    {state.submissionsIn}/{state.players.length}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold uppercase tracking-wide text-mystery-400">
                    Categories
                  </p>
                  <p className="text-2xl font-black text-mystery-100">
                    {state.categories.length}
                  </p>
                </div>
              </div>
              {state.roundEndsAt ? (
                <CountdownBar endsAt={state.roundEndsAt} totalSeconds={state.roundSeconds} />
              ) : (
                <div className="rounded-lg border border-mystery-700 bg-mystery-900 p-4 text-center text-sm font-semibold text-mystery-300">
                  Waiting for first Basta
                </div>
              )}
              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                {state.categories.map((category) => (
                  <div
                    key={category}
                    className="rounded border border-mystery-700 bg-mystery-900 px-3 py-2 text-mystery-100"
                  >
                    {category}
                  </div>
                ))}
              </div>
            </section>
          )}
        </main>

        <aside>
          <ScoreBoard scores={state.scores} />
        </aside>
      </div>
    </div>
  );
}
