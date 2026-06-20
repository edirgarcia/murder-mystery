// Centralized localStorage session handling, shared across all games.
//
// Each game namespaces its keys with a short prefix ("mm", "fq", "pd", "ww",
// "ba") so multiple games can be played from the same browser without
// colliding. Use these helpers instead of touching localStorage directly so
// the key scheme stays consistent everywhere.

export interface StoredSession {
  playerId: string;
  code: string;
  isHost: boolean;
}

export function saveSession(prefix: string, session: StoredSession): void {
  localStorage.setItem(`${prefix}_player_id`, session.playerId);
  localStorage.setItem(`${prefix}_game_code`, session.code);
  localStorage.setItem(`${prefix}_is_host`, String(session.isHost));
}

export function loadSession(prefix: string): StoredSession | null {
  const playerId = localStorage.getItem(`${prefix}_player_id`);
  const code = localStorage.getItem(`${prefix}_game_code`);
  if (!playerId || !code) return null;
  return {
    playerId,
    code,
    isHost: localStorage.getItem(`${prefix}_is_host`) === "true",
  };
}

export function clearSession(prefix: string): void {
  localStorage.removeItem(`${prefix}_player_id`);
  localStorage.removeItem(`${prefix}_game_code`);
  localStorage.removeItem(`${prefix}_is_host`);
}
