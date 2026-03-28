import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useFQ, useFQActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getGameInfo, nextQuestion, resetGame, buildWsUrl } from "../api/http";
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
  const { setGame, setPlayers, addPlayer, setPhase, newQuestion, setRoundResult, setWinner, setScores, setPointsToWin, setHostPaced, resetGame: resetGameState } = useFQActions();
  const [narrationText, setNarrationText] = useState<string | null>(null);
  const sendAckRef = useRef<() => void>(() => {});

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
      if (info.host_paced) setHostPaced(info.host_paced);
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
          setNarrationText("");
          if (event.data.points_to_win) {
            setPointsToWin(event.data.points_to_win as number);
          }
          if (event.data.host_paced) {
            setHostPaced(event.data.host_paced as boolean);
          }
          break;
        case "intro_narration": {
          setNarrationText(event.data.text as string);
          const sound = event.data.sound as string | undefined;
          if (sound) {
            const audio = new Audio(`/funny-questions/audio/${sound}`);
            audio.onended = () => sendAckRef.current();
            audio.onerror = () => sendAckRef.current();
            audio.play().catch(() => sendAckRef.current());
          }
          break;
        }
        case "intro_done":
          setNarrationText(null);
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
        case "game_reset":
          resetGameState();
          setNarrationText(null);
          navigate(`/lobby/${code}`);
          break;
      }
    },
    [code, addPlayer, setPhase, newQuestion, setRoundResult, setWinner, setPointsToWin, setHostPaced, resetGameState]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  const wsRef = useWebSocket(wsUrl, handleWSEvent);

  sendAckRef.current = () => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "narration_ack" }));
    }
  };

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
            onClick={() => {
              if (code && state.playerId) {
                resetGame(code, state.playerId).catch(() => {});
              }
            }}
            className="w-full py-3 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition"
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
        {(narrationText !== null || !state.currentQuestion) && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
            <p className="animate-pulse text-center text-3xl font-bold text-mystery-100 px-6 leading-relaxed md:text-5xl">
              {narrationText || ""}
            </p>
          </div>
        )}
        <div className={`mx-auto space-y-6 ${state.roundPhase === "reveal" ? "max-w-4xl" : "max-w-lg"}`}>
          <div className="text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider">Host Dashboard</p>
            <p className="text-mystery-300 text-lg mt-1">Room: {code}</p>
          </div>

          {state.roundPhase === "reveal" && state.roundResult ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <RoundReveal result={state.roundResult} />
                <ScoreBoard scores={state.scores} shameHolder={state.shameHolder} pointsToWin={state.pointsToWin} />
              </div>
              {state.hostPaced && !state.winner && (
                <button
                  onClick={() => code && state.playerId && nextQuestion(code, state.playerId)}
                  className="w-full py-4 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition"
                >
                  Next Question
                </button>
              )}
            </>
          ) : (
            <>
              {state.currentQuestion ? (
                <>
                  <QuestionCard question={state.currentQuestion} round={state.currentRound} />
                  {state.votingEndsAt && (
                    <CountdownBar endsAt={state.votingEndsAt} totalSeconds={30} />
                  )}
                </>
              ) : (
                <p className="text-center text-mystery-400 animate-pulse">Starting first round...</p>
              )}
              <ScoreBoard scores={state.scores} shameHolder={state.shameHolder} pointsToWin={state.pointsToWin} />
            </>
          )}
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
