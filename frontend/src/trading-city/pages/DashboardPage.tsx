import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AuctionHistory from "../components/AuctionHistory";
import AuctionStage from "../components/AuctionStage";
import CityCard from "../components/CityCard";
import MarketBoard from "../components/MarketBoard";
import PhaseHeader from "../components/PhaseHeader";
import ProjectCardView from "../components/ProjectCardView";
import ResourceBundle from "../components/ResourceBundle";
import { who } from "../components/labels";
import SkipIntroButton from "@shared/components/SkipIntroButton";
import { useTCConnection } from "../context/GameContext";
import { useNarration } from "../hooks/useNarration";
import type { PublicState } from "../types/game";
import { PriorityStrip } from "./player/ProjectsPanel";

function ReadyCount({ pub }: { pub: PublicState }) {
  if (!pub.ready) return null;
  const humans = pub.cities.filter((c) => !c.is_ai && c.owner_id).length;
  return (
    <p className="mt-4 text-center text-mystery-300">
      {pub.ready.length} / {humans} players ready to continue
    </p>
  );
}

function StagePanel({ pub, clockOffset }: { pub: PublicState; clockOffset: number }) {
  const name = (slot: number) => who(pub.cities[slot]);
  const humans = pub.cities.filter((c) => !c.is_ai && c.owner_id);

  switch (pub.phase) {
    case "city_selection":
      return (
        <div className="grid gap-3 md:grid-cols-4">
          {pub.cities.map((c) => (
            <CityCard key={c.slot} city={c} showEconomy={false} highlight={!!c.owner_id} />
          ))}
        </div>
      );
    case "production":
      return (
        <>
        <div className="grid gap-2 md:grid-cols-2">
          {pub.cities.map((c) => (
            <div key={c.slot} className="flex items-center justify-between rounded-xl bg-mystery-900/60 px-3 py-2">
              <span className="text-mystery-200">{who(c)}</span>
              <ResourceBundle bundle={pub.last_production[c.slot]} size="sm" empty="nothing" />
            </div>
          ))}
        </div>
        <ReadyCount pub={pub} />
        </>
      );
    case "market_study":
      return (
        <div className="space-y-4 text-center">
          <p className="text-2xl text-mystery-100">Study the market</p>
          <p className="text-mystery-300">
            Plan your next move: what could you build, and what are your rivals after?
          </p>
          <div className="flex justify-center">
            <PriorityStrip pub={pub} />
          </div>
          <ReadyCount pub={pub} />
        </div>
      );
    case "lot_creation":
      return (
        <div className="text-center">
          <p className="text-xl text-mystery-200">Merchants are secretly preparing their surplus lots…</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {humans.map((c) => (
              <span
                key={c.slot}
                className={`rounded-full px-4 py-2 text-lg ${
                  pub.lots_ready.includes(c.slot) ? "bg-emerald-600 text-white" : "bg-mystery-700 text-mystery-300"
                }`}
              >
                {pub.lots_ready.includes(c.slot) ? "🔒" : "⏳"} {c.owner_name}
              </span>
            ))}
          </div>
        </div>
      );
    case "auction":
      return <AuctionStage pub={pub} clockOffset={clockOffset} big />;
    case "projects": {
      const events = pub.project_log.filter((e) => e.round === pub.round);
      return (
        <div className="space-y-4">
          <PriorityStrip pub={pub} />
          {events.length > 0 && (
            <ul className="space-y-1 text-mystery-200">
              {events.map((e, i) => (
                <li key={i}>
                  🏗️ <b>{name(e.city)}</b> built <b>{e.card.name}</b>
                  {e.displaced && <span className="text-mystery-400"> (replacing {e.displaced})</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      );
    }
    case "upkeep":
      return (
        <>
        <div className="grid gap-2 md:grid-cols-2">
          {pub.cities.map((c) => {
            const u = pub.last_upkeep[c.slot];
            return (
              <div key={c.slot} className="flex items-center justify-between rounded-xl bg-mystery-900/60 px-3 py-2">
                <span className="text-mystery-200">{who(c)}</span>
                {u && u.missing === 0 ? (
                  <span className="text-emerald-300">✓ fed{u.shortage_before > 0 ? " — recovered" : ""}</span>
                ) : (
                  <span className="text-red-300">✗ shortage {u?.shortage_after}</span>
                )}
              </div>
            );
          })}
        </div>
        <ReadyCount pub={pub} />
        </>
      );
    case "cleanup":
      return (
        <p className="text-center text-xl text-mystery-200">
          {pub.discards_pending > 0
            ? `Waiting on ${pub.discards_pending} merchant(s) to clear their storehouses…`
            : "Closing the books for this round…"}
        </p>
      );
    default:
      return null;
  }
}

/** Live standings by final score (same formula as the winner), cash breaks ties.
 * Equal rows share a rank (1, 2, 2, 4). */
function Ranking({ pub }: { pub: PublicState }) {
  const ranked = [...pub.cities].sort((a, b) => b.score - a.score || b.cash - a.cash);
  const rankOf = (i: number): number =>
    i > 0 && ranked[i].score === ranked[i - 1].score && ranked[i].cash === ranked[i - 1].cash
      ? rankOf(i - 1)
      : i + 1;

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-xs uppercase text-mystery-500">
          <th className="w-8">#</th>
          <th>Merchant</th>
          <th className="text-right">Score</th>
          <th className="text-right">VP</th>
          <th className="text-right">Cash</th>
          <th className="text-right">Short</th>
        </tr>
      </thead>
      <tbody>
        {ranked.map((c, i) => (
          <tr key={c.slot} className={`border-t border-white/5 ${c.is_ai ? "text-mystery-400" : "text-white"}`}>
            <td className="py-1.5 font-bold text-amber-200">{rankOf(i)}</td>
            <td>
              {c.is_ai ? (
                <>
                  🤖 {c.name}
                </>
              ) : (
                <>
                  <span className="font-semibold">{c.owner_name ?? "—"}</span>{" "}
                  <span className="text-mystery-400">at {c.name}</span>
                </>
              )}{" "}
              <span className="text-xs text-mystery-500">{c.profile}</span>
            </td>
            <td className="text-right text-lg font-bold text-amber-200">{c.score}</td>
            <td className="text-right text-amber-100/70">{c.vp}</td>
            <td className="text-right text-emerald-300">${c.cash}</td>
            <td className={`text-right ${c.shortage ? "text-red-300" : "text-mystery-600"}`}>{c.shortage}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DashboardPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const narration = useNarration({ playAudio: true });
  const { state, send } = useTCConnection(code, narration.onEvent);
  narration.sendRef.current = send;
  const { pub, clockOffset } = state;

  useEffect(() => {
    if (pub?.phase === "finished" && code) navigate(`/result/${code}`, { replace: true });
  }, [code, navigate, pub?.phase]);

  if (!pub) return <p className="p-8 text-center text-mystery-300">Opening the trading floor…</p>;

  return (
    <div className="min-h-screen space-y-4 p-4">
      {narration.text && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
          <p className="animate-pulse px-6 text-center text-3xl font-bold leading-relaxed text-mystery-100 md:text-5xl">
            {narration.text}
          </p>
          <SkipIntroButton onSkip={narration.skip} />
        </div>
      )}
      <header className="rounded-2xl border border-white/10 bg-mystery-800/80 px-6 py-4">
        <PhaseHeader pub={pub} clockOffset={clockOffset} />
      </header>

      {pub.phase === "city_selection" ? (
        // Nothing to rank until cities are claimed: give the city cards the full width.
        <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-6">
          <StagePanel pub={pub} clockOffset={clockOffset} />
        </section>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <section className="min-h-[18rem] rounded-2xl border border-white/10 bg-mystery-800/60 p-6">
            <StagePanel pub={pub} clockOffset={clockOffset} />
          </section>

          <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
            <h2 className="mb-2 text-sm uppercase tracking-widest text-mystery-400">
              Ranking{" "}
              <span className="normal-case text-mystery-500">
                · score = VP{pub.rules.cash_per_vp ? ` + 1 per $${pub.rules.cash_per_vp}` : ""}, ties by cash
              </span>
            </h2>
            <Ranking pub={pub} />
          </section>
        </div>
      )}

      {pub.phase !== "city_selection" && (
        <div className="grid gap-4 xl:grid-cols-[2fr_1fr_1fr]">
          <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
            <h2 className="mb-2 text-sm uppercase tracking-widest text-mystery-400">
              Project Market <span className="normal-case text-mystery-500">· prestige tier: {pub.prestige_tier}</span>
            </h2>
            <div className="grid gap-2 md:grid-cols-4">
              {pub.project_slots.map((s) => (
                <ProjectCardView key={s.index} card={s.card} category={s.category} compact />
              ))}
            </div>
          </section>
          <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
            <h2 className="mb-2 text-sm uppercase tracking-widest text-mystery-400">Global Market</h2>
            <MarketBoard pub={pub} />
          </section>
          <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
            <h2 className="mb-2 text-sm uppercase tracking-widest text-mystery-400">Recent Lots</h2>
            <AuctionHistory pub={pub} limit={6} />
          </section>
        </div>
      )}
    </div>
  );
}
