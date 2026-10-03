import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { saveSession } from "@shared/session";
import HostLeftBanner from "@shared/components/HostLeftBanner";
import { createGame, getGameInfo, joinGame } from "../api/http";
import { useTC } from "../context/GameContext";

export default function HomePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setGame, setPlayers } = useTC();
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
      saveSession("tc", { playerId: host_id, code, isHost: true });
      setGame(code, host_id, hostName, true);
      navigate(`/lobby/${code}`);
    } catch (err: any) {
      setError(err.message);
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
      saveSession("tc", { playerId: player_id, code, isHost: false });
      setGame(code, player_id, name.trim(), false);
      const info = await getGameInfo(code);
      setPlayers(info.players);
      navigate(`/lobby/${code}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(217,119,6,0.18),_transparent_40%),radial-gradient(circle_at_bottom,_rgba(13,148,136,0.18),_transparent_45%)] px-4 py-10">
      <HostLeftBanner />
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-4xl items-center">
        <div className="grid w-full gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-5">
            <p className="text-sm uppercase tracking-[0.35em] text-mystery-300">Economic Strategy</p>
            <h1 className="max-w-xl text-5xl font-bold leading-tight text-white md:text-6xl">
              Trading City 🏛️
            </h1>
            <p className="max-w-xl text-lg leading-8 text-mystery-200">
              Run a specialised city. Produce, secretly commit your surplus, bid in open auctions,
              build projects that reshape the global market — and keep your city fed.
            </p>
            <div className="flex flex-wrap gap-3 text-sm text-mystery-200">
              <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2">8 rounds</span>
              <span className="rounded-full border border-teal-300/30 bg-teal-300/10 px-4 py-2">2–8 players</span>
              <span className="rounded-full border border-sky-300/30 bg-sky-300/10 px-4 py-2">Hidden lots, open bids</span>
            </div>
          </section>

          <section className="rounded-[28px] border border-white/10 bg-mystery-800/80 p-6 shadow-2xl backdrop-blur">
            <div className="space-y-4">
              {!joinCode && (
                <>
                  <button
                    onClick={handleCreate}
                    disabled={loading}
                    className="w-full rounded-2xl bg-amber-600 px-5 py-4 text-lg font-semibold text-white transition hover:bg-amber-500 disabled:opacity-50"
                  >
                    {loading ? "..." : "Create Lobby"}
                  </button>
                  <div className="flex items-center gap-3">
                    <hr className="flex-1 border-white/10" />
                    <span className="text-sm text-mystery-400">or join</span>
                    <hr className="flex-1 border-white/10" />
                  </div>
                </>
              )}

              <input
                type="text"
                placeholder="Your name"
                maxLength={30}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-mystery-900/80 px-4 py-3 text-lg text-white outline-none focus:border-mystery-400"
              />

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="CODE"
                  maxLength={4}
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  className="flex-1 rounded-2xl border border-white/10 bg-mystery-900/80 px-4 py-3 text-center text-lg tracking-[0.4em] text-white outline-none focus:border-mystery-400"
                />
                <button
                  onClick={handleJoin}
                  disabled={loading}
                  className="rounded-2xl bg-teal-600 px-6 py-3 text-lg font-semibold text-white transition hover:bg-teal-500 disabled:opacity-50"
                >
                  Join
                </button>
              </div>

              {error && <p className="text-sm text-red-300">{error}</p>}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
