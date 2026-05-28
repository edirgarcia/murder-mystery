import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createGame, getGameInfo, joinGame } from "../api/http";
import { useBastaActions } from "../context/GameContext";

export default function HomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setGame, setPlayers } = useBastaActions();
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState(searchParams.get("join")?.toUpperCase() ?? "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    const hostName = name.trim() || "Host";
    setLoading(true);
    setError("");
    try {
      const { code, host_id } = await createGame(hostName);
      localStorage.setItem("ba_player_id", host_id);
      localStorage.setItem("ba_game_code", code);
      localStorage.setItem("ba_is_host", "true");
      setGame(code, host_id, hostName, true);
      navigate(`/lobby/${code}`);
    } catch (e: any) {
      setError(e.message);
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
      localStorage.setItem("ba_player_id", player_id);
      localStorage.setItem("ba_game_code", code);
      localStorage.setItem("ba_is_host", "false");
      setGame(code, player_id, name.trim(), false);
      const info = await getGameInfo(code);
      setPlayers(info.players);
      navigate(`/lobby/${code}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-md flex-col justify-center space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-amber-200">
            Word race
          </p>
          <h1 className="mt-2 text-6xl font-black leading-none text-mystery-100">
            Basta ✏️
          </h1>
        </div>

        <div className="space-y-4 rounded-lg border border-mystery-700 bg-mystery-800 p-5 shadow-xl">
          {!joinCode && (
            <>
              <button
                onClick={handleCreate}
                disabled={loading}
                className="w-full rounded-lg bg-amber-300 px-4 py-3 text-lg font-black text-mystery-900 transition hover:bg-amber-200 disabled:opacity-50"
              >
                {loading ? "..." : "Create Game"}
              </button>

              <div className="flex items-center gap-3">
                <hr className="flex-1 border-mystery-600" />
                <span className="text-sm font-semibold text-mystery-400">or join</span>
                <hr className="flex-1 border-mystery-600" />
              </div>
            </>
          )}

          <label className="block space-y-2">
            <span className="text-sm font-semibold text-mystery-200">Name</span>
            <input
              type="text"
              maxLength={30}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-mystery-600 bg-mystery-900 px-4 py-3 text-lg text-white outline-none focus:border-amber-300"
            />
          </label>

          <div className="flex gap-2">
            <label className="block flex-1 space-y-2">
              <span className="text-sm font-semibold text-mystery-200">Code</span>
              <input
                type="text"
                maxLength={4}
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                className="w-full rounded-lg border border-mystery-600 bg-mystery-900 px-4 py-3 text-center text-lg uppercase tracking-[0.25em] text-white outline-none focus:border-amber-300"
              />
            </label>
            <button
              onClick={handleJoin}
              disabled={loading}
              className="mt-7 rounded-lg bg-teal-300 px-5 py-3 text-lg font-black text-mystery-900 transition hover:bg-teal-200 disabled:opacity-50"
            >
              Join
            </button>
          </div>

          {error && <p className="text-center text-sm text-rose-200">{error}</p>}
        </div>
      </div>
    </div>
  );
}
