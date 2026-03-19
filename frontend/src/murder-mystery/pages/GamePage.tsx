import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getCard, getGameInfo, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";
import CharacterCard from "../components/CharacterCard";
import ClueList from "../components/ClueList";

export default function GamePage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setCard, setPhase, setCharacterNames, setMurderWeapon, setTimerInfo } = useGameActions();
  const [loading, setLoading] = useState(true);

  // Redirect hosts to dashboard
  useEffect(() => {
    if (state.isHost && code) {
      navigate(`/dashboard/${code}`, { replace: true });
      return;
    }
  }, [state.isHost, code, navigate]);

  useEffect(() => {
    if (!code || !state.playerId || state.isHost) return;
    Promise.all([
      getCard(code, state.playerId),
      getGameInfo(code),
    ])
      .then(([card, info]) => {
        setCard(card);
        setCharacterNames(info.character_names);
        setMurderWeapon(info.murder_weapon);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [code, state.playerId, state.isHost]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "timer_started":
          if (event.data.started_at && event.data.duration_seconds) {
            setTimerInfo(
              event.data.started_at as string,
              event.data.duration_seconds as number,
            );
          }
          break;
        case "game_over":
          setPhase("finished");
          navigate(`/result/${code}`);
          break;
      }
    },
    [code, navigate, setPhase, setTimerInfo]
  );

  const wsUrl = code && state.playerId ? buildWsUrl(code, state.playerId) : null;
  useWebSocket(wsUrl, handleWSEvent);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-mystery-400 text-xl">Loading your card...</p>
      </div>
    );
  }

  if (!state.card) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-400">Could not load your card.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-6">
      <div className="max-w-md mx-auto space-y-6">
        <CharacterCard name={state.card.character_name} />

        <ClueList clues={state.card.clues} />

        <div className="bg-mystery-800/50 rounded-2xl p-4 text-center">
          <p className="text-mystery-400 text-sm mb-1">
            Talk to other players to share clues!
          </p>
          <p className="text-mystery-300 text-sm">
            Figure out who committed the murder with the {state.murderWeapon ?? "mystery weapon"}.
          </p>
        </div>

        <button
          onClick={() => navigate(`/guess/${code}`)}
          className="w-full py-4 rounded-xl bg-red-700 hover:bg-red-600 text-white font-semibold text-lg transition"
        >
          Make Accusation
        </button>
      </div>
    </div>
  );
}
