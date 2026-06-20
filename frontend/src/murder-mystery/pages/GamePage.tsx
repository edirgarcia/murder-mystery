import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGame, useGameActions, useRestoreSession } from "../context/GameContext";
import { useWebSocket } from "@shared/hooks/useWebSocket";
import { getCard, getGameInfo, buildWsUrl } from "../api/http";
import type { WSEvent } from "@shared/types/game";
import CharacterCard from "../components/CharacterCard";
import ClueList from "../components/ClueList";

export default function GamePage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { state } = useGame();
  const { setCard, setPhase, setCharacterNames, setMurderWeapon, setRoundInfo, setRoundDurations } = useGameActions();
  const [loading, setLoading] = useState(true);
  const [currentRound, setCurrentRound] = useState(0);
  const [notification, setNotification] = useState<string | null>(null);

  // Restore identity from localStorage so a mid-game refresh can reconnect
  useRestoreSession(code);

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
        if (info.current_round > 0) {
          setCurrentRound(info.current_round);
        }
        if (info.round_durations.length > 0) {
          setRoundDurations(info.round_durations);
        }
        if (info.current_round > 0 && info.round_started_at) {
          setRoundInfo(info.current_round, info.round_started_at, info.round_durations[info.current_round - 1]);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [code, state.playerId, state.isHost]);

  const handleWSEvent = useCallback(
    (event: WSEvent) => {
      switch (event.event) {
        case "round_started":
          setCurrentRound(event.data.round as number);
          setRoundInfo(
            event.data.round as number,
            event.data.started_at as string,
            event.data.duration_seconds as number,
          );
          break;
        case "round_advanced":
          setCurrentRound(event.data.round as number);
          setRoundInfo(
            event.data.round as number,
            event.data.started_at as string,
            event.data.duration_seconds as number,
          );
          setNotification(`Round ${event.data.round} — New clues available!`);
          // Re-fetch card to get newly available clues
          if (code && state.playerId) {
            getCard(code, state.playerId).then(setCard).catch(() => {});
          }
          break;
        case "game_over":
          setPhase("finished");
          navigate(`/result/${code}`);
          break;
      }
    },
    [code, navigate, state.playerId, setPhase, setRoundInfo, setCard]
  );

  // Auto-dismiss notification
  useEffect(() => {
    if (!notification) return;
    const id = setTimeout(() => setNotification(null), 4000);
    return () => clearTimeout(id);
  }, [notification]);

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

  const canAccuse = currentRound >= 2;
  const isMurderer = state.card.is_murderer === true;

  return (
    <div className="min-h-screen px-4 py-6">
      <div className="max-w-md mx-auto space-y-6">
        {isMurderer && (
          <div className="rounded-xl border border-red-800/60 bg-red-950/40 px-4 py-3 text-center">
            <p className="text-red-300 text-sm font-semibold">🔪 You are the murderer</p>
            <p className="text-red-200/70 text-xs mt-1">
              Only you can see this. Blend in, sow doubt, and don't get caught.
            </p>
          </div>
        )}
        {notification && (
          <div className="bg-mystery-500/80 text-white text-center py-3 px-4 rounded-xl text-sm font-medium animate-pulse">
            {notification}
          </div>
        )}

        {currentRound > 0 && (
          <div className="text-center">
            <p className="text-mystery-400 text-xs uppercase tracking-wider">
              Round {currentRound} / 3
            </p>
          </div>
        )}

        <CharacterCard name={state.card.character_name} />

        <ClueList clues={state.card.clues} currentRound={currentRound} />

        <div className="bg-mystery-800/50 rounded-2xl p-4 text-center">
          <p className="text-mystery-400 text-sm mb-1">
            Talk to other players to share clues!
          </p>
          <p className="text-mystery-300 text-sm">
            {isMurderer
              ? `Everyone is hunting for who used the ${state.murderWeapon ?? "mystery weapon"}. Keep them off your trail.`
              : `Figure out who committed the murder with the ${state.murderWeapon ?? "mystery weapon"}.`}
          </p>
        </div>

        {isMurderer ? (
          <div className="rounded-xl bg-red-950/40 border border-red-800/60 py-4 text-center">
            <p className="text-red-200 text-sm">
              You don't accuse — you survive. The others vote; if most of them
              miss you, you win.
            </p>
          </div>
        ) : canAccuse ? (
          <button
            onClick={() => navigate(`/guess/${code}`)}
            className="w-full py-4 rounded-xl bg-red-700 hover:bg-red-600 text-white font-semibold text-lg transition"
          >
            Make Accusation
          </button>
        ) : (
          <div className="text-center py-4">
            <p className="text-mystery-400 text-sm">
              Accusations unlock in Round 2
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
