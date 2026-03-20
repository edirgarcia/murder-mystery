import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createGame, getGameInfo, joinGame } from "../api/http";
import { useWWActions } from "../context/GameContext";

export default function HomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setGame, setPlayers } = useWWActions();

  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState(searchParams.get("join")?.toUpperCase() ?? "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    setLoading(true);
    setError("");
    try {
      const hostName = name.trim() || "Host";
      const { code, host_id } = await createGame(hostName);
      localStorage.setItem("ww_player_id", host_id);
      localStorage.setItem("ww_game_code", code);
      localStorage.setItem("ww_is_host", "true");
      setGame(code, host_id, hostName, true);
      navigate(`/lobby/${code}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create game");
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin() {
    if (!name.trim()) return setError("Enter your name");
    if (!joinCode.trim()) return setError("Enter a game code");

    setLoading(true);
    setError("");
    try {
      const code = joinCode.trim().toUpperCase();
      const { player_id } = await joinGame(code, name.trim());
      localStorage.setItem("ww_player_id", player_id);
      localStorage.setItem("ww_game_code", code);
      localStorage.setItem("ww_is_host", "false");
      setGame(code, player_id, name.trim(), false);
      const info = await getGameInfo(code);
      setPlayers(info.players);
      navigate(`/lobby/${code}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to join game");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <p className="text-mystery-400 uppercase tracking-wider text-sm">Party Mode</p>
          <h1 className="text-5xl text-mystery-100 font-bold">Werewolf</h1>
          <p className="text-mystery-300 mt-2">Read faces, hide lies, survive the night.</p>
        </div>

        <div className="bg-mystery-800 border border-mystery-700 rounded-2xl p-5 space-y-3 shadow-xl">
          {!joinCode && (
            <button
              onClick={handleCreate}
              disabled={loading}
              className="w-full rounded-xl py-3 bg-red-600 hover:bg-red-500 transition text-white font-semibold disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create Game"}
            </button>
          )}

          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={30}
            placeholder="Your name"
            className="w-full rounded-xl bg-mystery-700 border border-mystery-600 px-4 py-3 outline-none focus:border-red-400"
          />

          <div className="flex gap-2">
            <input
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              maxLength={4}
              placeholder="CODE"
              className="flex-1 rounded-xl bg-mystery-700 border border-mystery-600 px-4 py-3 tracking-[0.3em] uppercase text-center outline-none focus:border-red-400"
            />
            <button
              onClick={handleJoin}
              disabled={loading}
              className="rounded-xl px-5 bg-mystery-600 hover:bg-mystery-500 transition disabled:opacity-50"
            >
              Join
            </button>
          </div>

          {error && <p className="text-red-300 text-sm text-center">{error}</p>}
        </div>
      </div>
    </div>
  );
}
