import { useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useFQ, useFQActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getGameInfo, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";
import type { RoundResult } from "../types/game";
import QuestionCard from "../components/QuestionCard";
import CountdownBar from "../components/CountdownBar";
import ScoreBoard from "../components/ScoreBoard";
import RoundReveal from "../components/RoundReveal";

export default function DashboardPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useFQ();
  const { setGame, setPlayers, addPlayer, setPhase, newQuestion, setRoundResult, setWinner, setScores, setPointsToWin } = useFQActions();

  // Restore from localStorage
  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("fq_player_id");
    const storedCode = localStorage.getItem("fq_game_code");
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "Host", true);
    }
  }, [code, state.playerId, setGame]);

  // Load game info
  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setPhase(info.phase);
      if (info.scores) setScores(info.scores);
      if (info.points_to_win) setPointsToWin(info.points_to_win);
      if (info.current_question && info.round_phase === "voting") {
        newQuestion(
          info.current_question,
          info.current_round,
          info.voting_ends_at ?? new Date().toISOString(),
          info.players,
        );
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
          break;
        case "new_question":
          newQuestion(
            event.data.question as string,
            event.data.round as number,
            event.data.voting_ends_at as string,
            (event.data.players as { id: string; name: string }[]),
          );
          break;
        case "vote_cast":
          // Could show vote count, handled by state
          break;
        case "round_result":
          setRoundResult(event.data as unknown as RoundResult);
          break;
        case "game_over":
          setWinner(event.data.winner_name as string);
          break;
      }
    },
    [code, addPlayer, setPhase, newQuestion, setRoundResult, setWinner, setPointsToWin]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  // Finished
  if (state.phase === "finished" || state.winner) {
    return (
      <div className="min-h-screen px-4 py-8">
        <div className="max-w-lg mx-auto space-y-6">
          <div className="bg-mystery-800 rounded-2xl p-6 text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider">Winner</p>
            <h2 className="text-4xl font-bold text-mystery-300 mt-2">{state.winner}</h2>
          </div>
          <ScoreBoard scores={state.scores} shameHolder={state.shameHolder} pointsToWin={state.pointsToWin} />
          <button
            onClick={() => navigate("/")}
            className="w-full py-3 rounded-xl bg-mystery-700 hover:bg-mystery-600 text-white font-semibold text-lg transition"
          >
            Play Again
          </button>
        </div>
      </div>
    );
  }

  // Playing — show current question/reveal
  if (state.phase === "playing") {
    return (
      <div className="min-h-screen px-4 py-6">
        <div className="max-w-lg mx-auto space-y-6">
          <div className="text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider">Host Dashboard</p>
            <p className="text-mystery-300 text-lg mt-1">Room: {code}</p>
          </div>

          {state.roundPhase === "reveal" && state.roundResult ? (
            <RoundReveal result={state.roundResult} />
          ) : state.currentQuestion ? (
            <>
              <QuestionCard question={state.currentQuestion} round={state.currentRound} />
              {state.votingEndsAt && (
                <CountdownBar endsAt={state.votingEndsAt} totalSeconds={15} />
              )}
            </>
          ) : (
            <p className="text-center text-mystery-400 animate-pulse">Starting first round...</p>
          )}

          <ScoreBoard scores={state.scores} shameHolder={state.shameHolder} pointsToWin={state.pointsToWin} />
        </div>
      </div>
    );
  }

  // Lobby (shouldn't normally reach here, but just in case)
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <p className="text-mystery-400">Waiting for game to start...</p>
    </div>
  );
}
