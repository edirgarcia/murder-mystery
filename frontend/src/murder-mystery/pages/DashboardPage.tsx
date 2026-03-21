import { useEffect, useCallback, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { useGame, useGameActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getGameInfo, startGame, beginGame, advanceRound, endGame, getResults, buildWsUrl } from "../api/http";
import type { Difficulty, LeaderboardEntry, ClueInfo } from "../types/game";
import type { WSEvent } from "@shared/types/game";
import PlayerList from "@shared/components/PlayerList";
import IntroSequence from "../components/IntroSequence";

function CountdownTimer({ startedAt, durationSeconds }: { startedAt: string; durationSeconds: number }) {
  const [remaining, setRemaining] = useState(durationSeconds);

  useEffect(() => {
    const endTime = new Date(startedAt).getTime() + durationSeconds * 1000;
    const tick = () => {
      const left = Math.max(0, Math.floor((endTime - Date.now()) / 1000));
      setRemaining(left);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt, durationSeconds]);

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;

  return (
    <div className="text-center">
      <p className="text-mystery-400 text-sm uppercase tracking-wider">Time Remaining</p>
      <p className={`text-7xl font-mono font-bold mt-2 ${remaining <= 60 ? "text-red-400" : "text-mystery-200"}`}>
        {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
      </p>
    </div>
  );
}

export default function DashboardPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setGame, setPlayers, addPlayer, setPhase, setError, setRoundInfo, setRoundDurations, setMurderWeapon } = useGameActions();
  const [starting, setStarting] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [roundMinutes, setRoundMinutes] = useState(5);
  const [guessesCount, setGuessesCount] = useState(0);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[] | null>(null);
  const [murderClues, setMurderClues] = useState<ClueInfo[] | null>(null);
  const [murdererName, setMurdererName] = useState<string | null>(null);
  const [murderWeaponLocal, setMurderWeaponLocal] = useState<string | null>(null);
  const [currentRound, setCurrentRound] = useState(0);
  const [roundStartedAt, setRoundStartedAt] = useState<string | null>(null);
  const [roundDurationSeconds, setRoundDurationSeconds] = useState<number | null>(null);
  const [showIntro, setShowIntro] = useState(false);
  const [introPlayerNames, setIntroPlayerNames] = useState<string[]>([]);
  const loadedRef = useRef(false);

  // Restore game state from localStorage (handles page refresh / HMR)
  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("player_id");
    const storedCode = localStorage.getItem("game_code");
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "Host", true);
    }
  }, [code, state.playerId, setGame]);

  // Load game info on mount
  useEffect(() => {
    if (!code || loadedRef.current) return;
    loadedRef.current = true;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      setPhase(info.phase);
      setMurderWeapon(info.murder_weapon);
      setMurderWeaponLocal(info.murder_weapon);
      setGuessesCount(info.guesses_count);
      if (info.round_durations.length > 0) {
        setRoundDurations(info.round_durations);
      }
      if (info.current_round > 0 && info.round_started_at) {
        setCurrentRound(info.current_round);
        setRoundStartedAt(info.round_started_at);
        setRoundDurationSeconds(info.round_durations[info.current_round - 1]);
        setRoundInfo(info.current_round, info.round_started_at, info.round_durations[info.current_round - 1]);
      }
      if (info.phase === "finished") {
        getResults(code).then((results) => {
          setLeaderboard(results.leaderboard);
          setMurderClues(results.murder_clues);
          setMurdererName(results.murderer_name);
          setMurderWeaponLocal(results.murder_weapon);
        });
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
        case "game_starting":
          setPhase("generating");
          break;
        case "game_started":
          setPhase("playing");
          if (event.data.murder_weapon) {
            setMurderWeapon(event.data.murder_weapon as string);
            setMurderWeaponLocal(event.data.murder_weapon as string);
          }
          if (event.data.player_names) {
            setIntroPlayerNames(event.data.player_names as string[]);
          }
          setShowIntro(true);
          break;
        case "round_started":
          setCurrentRound(event.data.round as number);
          setRoundStartedAt(event.data.started_at as string);
          setRoundDurationSeconds(event.data.duration_seconds as number);
          setRoundInfo(
            event.data.round as number,
            event.data.started_at as string,
            event.data.duration_seconds as number,
          );
          break;
        case "round_advanced":
          setCurrentRound(event.data.round as number);
          setRoundStartedAt(event.data.started_at as string);
          setRoundDurationSeconds(event.data.duration_seconds as number);
          setRoundInfo(
            event.data.round as number,
            event.data.started_at as string,
            event.data.duration_seconds as number,
          );
          break;
        case "generation_failed":
          setPhase("lobby");
          setError(event.data.error as string);
          setStarting(false);
          break;
        case "guess_made":
          setGuessesCount(event.data.guesses_count as number);
          break;
        case "game_over": {
          setPhase("finished");
          setMurdererName(event.data.murderer as string);
          const lb = event.data.leaderboard as LeaderboardEntry[] | undefined;
          if (lb) setLeaderboard(lb);
          if (code) {
            getResults(code).then((results) => {
              setMurderClues(results.murder_clues);
              setMurderWeaponLocal(results.murder_weapon);
              if (!lb) setLeaderboard(results.leaderboard);
            });
          }
          break;
        }
      }
    },
    [code, addPlayer, setPhase, setError, setRoundInfo, setMurderWeapon, setRoundDurations]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  async function handleStart() {
    if (!code || !state.playerId) return;
    setStarting(true);
    try {
      await startGame(code, state.playerId, difficulty, roundMinutes);
    } catch (e: any) {
      setError(e.message);
      setStarting(false);
    }
  }

  async function handleAdvanceRound() {
    if (!code || !state.playerId) return;
    try {
      await advanceRound(code, state.playerId);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleEndGame() {
    if (!code || !state.playerId) return;
    try {
      await endGame(code, state.playerId);
    } catch (e: any) {
      setError(e.message);
    }
  }

  const canStart = state.players.length >= 4 && !starting;
  const phase = state.phase ?? "lobby";

  // --- INTRO SEQUENCE ---
  if (showIntro && murderWeaponLocal && introPlayerNames.length > 0) {
    return (
      <IntroSequence
        playerNames={introPlayerNames}
        murderWeapon={murderWeaponLocal}
        onComplete={() => {
          setShowIntro(false);
          if (code && state.playerId) {
            beginGame(code, state.playerId).catch(() => {});
          }
        }}
      />
    );
  }

  // --- LOBBY PHASE ---
  if (phase === "lobby" || phase === "generating") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-lg space-y-6">
          <div className="text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider">
              Game Code
            </p>
            <h2 className="text-7xl font-bold text-mystery-300 tracking-[0.3em] mt-1">
              {code}
            </h2>
            <div className="mt-4 inline-block rounded-xl bg-white p-3">
              <QRCodeSVG
                value={`http://localhost:5173/?join=${code}`}
                size={180}
              />
            </div>
            <p className="text-mystery-400 mt-3">
              Scan to join or enter the code
            </p>
          </div>

          <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-mystery-300 font-semibold mb-3">
              Players ({state.players.length})
            </h3>
            <PlayerList players={state.players} />
            {state.players.length < 4 && (
              <p className="text-mystery-400 text-sm mt-3 text-center">
                Need at least 4 players to start
              </p>
            )}
          </div>

          <div className="bg-mystery-800 rounded-2xl p-4 shadow-xl">
            <h3 className="text-mystery-300 font-semibold mb-3 text-sm">
              Difficulty
            </h3>
            <div className="flex gap-2">
              {(["easy", "medium", "hard", "harder", "hardest"] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  disabled={starting}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                    difficulty === d
                      ? "bg-mystery-500 text-white"
                      : "bg-mystery-700 text-mystery-400 hover:bg-mystery-600"
                  } disabled:opacity-40`}
                >
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-mystery-800 rounded-2xl p-4 shadow-xl">
            <h3 className="text-mystery-300 font-semibold mb-3 text-sm">
              Round Duration (minutes per round)
            </h3>
            <div className="flex gap-2">
              {[3, 5, 7].map((m) => (
                <button
                  key={m}
                  onClick={() => setRoundMinutes(m)}
                  disabled={starting}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                    roundMinutes === m
                      ? "bg-mystery-500 text-white"
                      : "bg-mystery-700 text-mystery-400 hover:bg-mystery-600"
                  } disabled:opacity-40`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleStart}
            disabled={!canStart}
            className="w-full py-4 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition disabled:opacity-40"
          >
            {starting
              ? phase === "generating"
                ? "Generating puzzle..."
                : "Starting..."
              : "Start Game"}
          </button>

          {state.error && (
            <p className="text-red-400 text-sm text-center">{state.error}</p>
          )}
        </div>
      </div>
    );
  }

  // --- PLAYING PHASE ---
  if (phase === "playing") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-lg space-y-8">
          {murderWeaponLocal && (
            <div className="text-center">
              <p className="text-mystery-400 text-sm uppercase tracking-wider">
                Murder Weapon
              </p>
              <h2 className="text-4xl font-bold text-red-400 mt-1">
                {murderWeaponLocal}
              </h2>
            </div>
          )}

          <div className="text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider">Round</p>
            <p className="text-5xl font-bold text-mystery-200 mt-1">
              {currentRound} <span className="text-mystery-400 text-2xl">/ 3</span>
            </p>
          </div>

          {roundStartedAt && roundDurationSeconds && (
            <CountdownTimer startedAt={roundStartedAt} durationSeconds={roundDurationSeconds} />
          )}

          {currentRound < 2 && (
            <p className="text-center text-mystery-400 text-sm">
              Accusations locked until Round 2
            </p>
          )}

          <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider mb-2">
              Guesses
            </p>
            <p className="text-4xl font-bold text-mystery-200">
              {guessesCount} <span className="text-mystery-400 text-2xl">of</span> {state.players.length}
            </p>
            <p className="text-mystery-400 text-sm mt-1">players have guessed</p>
          </div>

          <div className="bg-mystery-800 rounded-2xl p-4 shadow-xl">
            <h3 className="text-mystery-300 font-semibold mb-3 text-sm">
              Players
            </h3>
            <PlayerList players={state.players} />
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleAdvanceRound}
              className="flex-1 py-3 rounded-xl bg-mystery-500 hover:bg-mystery-400 text-white font-semibold text-lg transition"
            >
              {currentRound < 3 ? "Next Round" : "End Game"}
            </button>
            <button
              onClick={handleEndGame}
              className="py-3 px-6 rounded-xl bg-red-700 hover:bg-red-600 text-white font-semibold transition"
            >
              End
            </button>
          </div>

          {state.error && (
            <p className="text-red-400 text-sm text-center">{state.error}</p>
          )}
        </div>
      </div>
    );
  }

  // --- FINISHED PHASE ---
  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-lg mx-auto space-y-6">
        {murdererName && (
          <div className="bg-mystery-800 rounded-2xl p-6 text-center">
            <p className="text-mystery-400 text-sm uppercase tracking-wider">
              The Murderer Was
            </p>
            <h2 className="text-4xl font-bold text-red-400 mt-2">
              {murdererName}
            </h2>
            {murderWeaponLocal && (
              <p className="text-mystery-300 mt-2 text-lg">
                with the <strong>{murderWeaponLocal}</strong>
              </p>
            )}
          </div>
        )}

        {leaderboard && leaderboard.length > 0 && (
          <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-mystery-300 font-semibold mb-4">Leaderboard</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-mystery-400 text-left">
                  <th className="py-1 pr-2">#</th>
                  <th className="py-1 pr-2">Player</th>
                  <th className="py-1 pr-2">Suspect</th>
                  <th className="py-1 pr-2">Result</th>
                  <th className="py-1">Time</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry) => (
                  <tr key={entry.rank} className="border-t border-mystery-700">
                    <td className="py-2 pr-2 text-mystery-400">{entry.rank}</td>
                    <td className="py-2 pr-2 text-mystery-200 font-medium">{entry.player_name}</td>
                    <td className="py-2 pr-2 text-mystery-300">{entry.suspect_guessed}</td>
                    <td className="py-2 pr-2">
                      <span className={entry.correct ? "text-green-400" : "text-red-400"}>
                        {entry.correct ? "Correct" : "Wrong"}
                      </span>
                    </td>
                    <td className="py-2 text-mystery-400">
                      {entry.time_taken_seconds != null
                        ? `${Math.floor(entry.time_taken_seconds)}s`
                        : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {murderClues && murderClues.length > 0 && (
          <div className="bg-mystery-800 rounded-2xl p-6 shadow-xl">
            <h3 className="text-mystery-300 font-semibold mb-3">Murder Clues</h3>
            {murderClues.map((clue, i) => (
              <p key={i} className="text-mystery-200 text-sm mb-1">
                {clue.text}
              </p>
            ))}
          </div>
        )}

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
