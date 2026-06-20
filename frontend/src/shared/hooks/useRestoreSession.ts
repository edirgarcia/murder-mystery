import { useEffect } from "react";
import { loadSession } from "../session";

type SetGame = (
  code: string,
  playerId: string,
  playerName: string,
  isHost: boolean,
) => void;

/**
 * Restore a player's identity from localStorage after a page refresh.
 *
 * Without this, a player who refreshes (or whose tab reloads) while on an
 * in-game page loses their playerId, so the WebSocket URL becomes null and
 * they can never reconnect. Each game wraps this with its own prefix and
 * context in `GameContext` (exported there as `useRestoreSession(code)`).
 */
export function useSessionRestore(
  prefix: string,
  code: string | undefined,
  playerId: string | null,
  setGame: SetGame,
): void {
  useEffect(() => {
    if (playerId || !code) return;
    const session = loadSession(prefix);
    if (session && session.code.toUpperCase() === code.toUpperCase()) {
      setGame(code, session.playerId, session.isHost ? "Host" : "", session.isHost);
    }
  }, [prefix, code, playerId, setGame]);
}
