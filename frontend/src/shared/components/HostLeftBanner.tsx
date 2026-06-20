import { useEffect, useState } from "react";
import { HOST_LEFT_NOTICE_KEY } from "../constants";

/**
 * Shown on a game's home page when a player was returned here because the
 * host ended the game (closed their dashboard). Reads and clears a one-shot
 * sessionStorage flag set by useWebSocket on the `host_left` event.
 */
export default function HostLeftBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(HOST_LEFT_NOTICE_KEY)) {
      sessionStorage.removeItem(HOST_LEFT_NOTICE_KEY);
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  return (
    <div className="mx-auto mb-4 flex max-w-md items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <span>The host ended the game. You can join or start a new one below.</span>
      <button
        onClick={() => setVisible(false)}
        aria-label="Dismiss"
        className="shrink-0 text-amber-300 transition hover:text-amber-100"
      >
        ✕
      </button>
    </div>
  );
}
