import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getGameInfo, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";
import PlayerList from "@shared/components/PlayerList";
import IntroSequence from "../components/IntroSequence";

export default function LobbyPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setGame, setPlayers, addPlayer, setPhase, setError, setRoundInfo } = useGameActions();
  const [showIntro, setShowIntro] = useState(false);
  const [introPlayerNames, setIntroPlayerNames] = useState<string[]>([]);
  const [introWeapon, setIntroWeapon] = useState<string | null>(null);

  // Restore game state from localStorage (handles page refresh / HMR)
  useEffect(() => {
    if (state.playerId || !code) return;
    const storedId = localStorage.getItem("player_id");
    const storedCode = localStorage.getItem("game_code");
    const isHost = localStorage.getItem("is_host") === "true";
    if (storedId && storedCode?.toUpperCase() === code.toUpperCase()) {
      setGame(code, storedId, "", isHost);
    }
  }, [code, state.playerId, setGame]);

  // Redirect hosts to dashboard
  useEffect(() => {
    if (state.isHost && code) {
      navigate(`/dashboard/${code}`, { replace: true });
    }
  }, [state.isHost, code, navigate]);

  // Load game info on mount
  useEffect(() => {
    if (!code) return;
    getGameInfo(code).then((info) => {
      setPlayers(info.players);
      if (info.phase === "playing") {
        setPhase("playing");
        if (info.current_round && info.round_started_at) {
          const duration = info.round_durations[info.current_round - 1] ?? 0;
          setRoundInfo(info.current_round, info.round_started_at, duration);
        }
        navigate(`/game/${code}`);
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
          if (event.data.murder_weapon && event.data.player_names) {
            setIntroWeapon(event.data.murder_weapon as string);
            setIntroPlayerNames(event.data.player_names as string[]);
            setShowIntro(true);
          } else {
            navigate(`/game/${code}`);
          }
          break;
        case "generation_failed":
          setPhase("lobby");
          setError(event.data.error as string);
          break;
      }
    },
    [code, navigate, addPlayer, setPhase, setError, setRoundInfo]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  if (showIntro && introWeapon && introPlayerNames.length > 0) {
    return (
      <IntroSequence
        playerNames={introPlayerNames}
        murderWeapon={introWeapon}
        onComplete={() => navigate(`/game/${code}`)}
      />
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <p className="text-mystery-400 text-sm uppercase tracking-wider">
            Game Code
          </p>
          <h2 className="text-5xl font-bold text-mystery-300 tracking-[0.3em] mt-1">
            {code}
          </h2>
          <p className="text-mystery-400 mt-2">
            Share this code with your friends
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

        <p className="text-center text-mystery-400">
          Waiting for the host to start the game...
        </p>

        {state.phase === "generating" && (
          <p className="text-center text-mystery-300 animate-pulse">
            Generating puzzle...
          </p>
        )}

        {state.error && (
          <p className="text-red-400 text-sm text-center">{state.error}</p>
        )}
      </div>
    </div>
  );
}
