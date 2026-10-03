import { useNavigate, useParams } from "react-router-dom";
import { clearSession } from "@shared/session";
import AuctionHistory from "../components/AuctionHistory";
import BuiltProjects from "../components/BuiltProjects";
import { useTCConnection } from "../context/GameContext";

export default function ResultPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { pub, playerId } = useTCConnection(code).state;

  if (!pub) return <p className="p-8 text-center text-mystery-300">Tallying the ledgers…</p>;

  const winner = pub.standings[0];
  const cashNote = pub.rules.cash_per_vp
    ? `Score = VP + 1 per $${pub.rules.cash_per_vp} of leftover cash.`
    : "Score = VP. Cash breaks ties.";

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-10">
      <header className="text-center">
        <p className="text-sm uppercase tracking-[0.35em] text-mystery-400">Final Ledger</p>
        {winner && (
          <h1 className="mt-2 text-5xl font-bold text-amber-200">
            🏆 {winner.owner_name}
          </h1>
        )}
        <p className="mt-2 text-sm text-mystery-400">{cashNote}</p>
      </header>

      <ol className="space-y-2">
        {pub.standings.map((s, i) => {
          const city = pub.cities[s.slot];
          return (
            <li
              key={s.slot}
              className={`flex items-center justify-between rounded-2xl px-5 py-4 ${
                city.owner_id === playerId ? "bg-amber-500/20 ring-1 ring-amber-300/50" : "bg-mystery-800/80"
              }`}
            >
              <div>
                <p className="text-lg font-semibold text-white">
                  {i + 1}. {s.owner_name}
                </p>
                <p className="text-sm text-mystery-400">{city.name}</p>
                <div className="mt-2">
                  <BuiltProjects city={city} empty="No projects built" />
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-amber-200">{s.score}</p>
                <p className="text-xs text-mystery-400">
                  {s.vp} VP · ${s.cash}
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
        <h2 className="mb-2 text-sm uppercase tracking-widest text-mystery-400">Market History</h2>
        <AuctionHistory pub={pub} viewerSlot={pub.cities.find((c) => c.owner_id === playerId)?.slot} />
      </section>

      <button
        onClick={() => {
          clearSession("tc");
          navigate("/");
        }}
        className="w-full rounded-2xl bg-mystery-700 py-3 font-semibold text-white"
      >
        Back to start
      </button>
    </div>
  );
}
