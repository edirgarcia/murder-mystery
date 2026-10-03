import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AuctionHistory from "../components/AuctionHistory";
import CityCard from "../components/CityCard";
import MarketBoard from "../components/MarketBoard";
import PhaseHeader from "../components/PhaseHeader";
import ResourceBundle from "../components/ResourceBundle";
import { bundleSize } from "../components/resources";
import { useTCConnection } from "../context/GameContext";
import { useNarration } from "../hooks/useNarration";
import BidPanel from "./player/BidPanel";
import CitySelection from "./player/CitySelection";
import LotPanel from "./player/LotPanel";
import ProjectsPanel from "./player/ProjectsPanel";
import { ContinueButton, DiscardPanel, ProductionSummary, UpkeepSummary } from "./player/RoundSummary";

const TABS = ["City", "Projects", "Market", "Rivals", "History"] as const;

/** The narrator's current line, mirrored on phones (audio plays on the TV). */
function NarrationCaption({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <p className="rounded-xl border border-amber-300/30 bg-amber-400/10 px-3 py-2 text-sm italic text-amber-100">
      🔊 {text}
    </p>
  );
}
type Tab = (typeof TABS)[number];

export default function PlayerPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const narration = useNarration({ playAudio: false });
  const { state } = useTCConnection(code, narration.onEvent);
  const [tab, setTab] = useState<Tab>("City");
  const { pub, priv, playerId, clockOffset } = state;

  useEffect(() => {
    if (state.isHost && code) navigate(`/dashboard/${code}`, { replace: true });
  }, [code, navigate, state.isHost]);

  useEffect(() => {
    if (pub?.phase === "finished" && code) navigate(`/result/${code}`, { replace: true });
  }, [code, navigate, pub?.phase]);

  if (!code || !playerId || !pub) {
    return <p className="p-8 text-center text-mystery-300">Connecting to the market…</p>;
  }

  if (pub.phase === "city_selection") {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
        <PhaseHeader pub={pub} clockOffset={clockOffset} />
        <NarrationCaption text={narration.text} />
        <CitySelection pub={pub} code={code} playerId={playerId} />
      </div>
    );
  }

  const city = pub.cities.find((c) => c.owner_id === playerId);
  if (!city || !priv) return <p className="p-8 text-center text-mystery-300">Loading your city…</p>;

  const inventorySize = bundleSize(priv.inventory);

  let action: React.ReactNode = null;
  switch (pub.phase) {
    case "production":
      action = <ProductionSummary code={code} playerId={playerId} pub={pub} city={city} />;
      break;
    case "market_study":
      action = (
        <div className="space-y-3">
          <p className="text-sm text-mystery-300">
            Look at what you could build before you decide what to sell. Outlined cards are ones you can
            already afford.
          </p>
          <ContinueButton code={code} playerId={playerId} pub={pub} city={city} />
          <ProjectsPanel code={code} playerId={playerId} pub={pub} priv={priv} interactive={false} />
        </div>
      );
      break;
    case "lot_creation":
      action = <LotPanel code={code} playerId={playerId} city={city} priv={priv} />;
      break;
    case "auction":
      action = <BidPanel code={code} playerId={playerId} pub={pub} city={city} clockOffset={clockOffset} />;
      break;
    case "projects":
      action = <ProjectsPanel code={code} playerId={playerId} pub={pub} priv={priv} interactive />;
      break;
    case "upkeep":
      action = <UpkeepSummary code={code} playerId={playerId} pub={pub} city={city} priv={priv} />;
      break;
    case "cleanup":
      action = <DiscardPanel code={code} playerId={playerId} priv={priv} />;
      break;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 px-4 py-4">
      <header className="flex items-center justify-between rounded-2xl bg-mystery-800/80 px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-mystery-400">{city.profile} city</p>
          <p className="text-lg font-bold text-white">{city.name}</p>
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <p className="text-xs text-mystery-400">Cash</p>
            <p className="text-lg font-bold text-emerald-300">${city.cash}</p>
          </div>
          <div>
            <p className="text-xs text-mystery-400">VP</p>
            <p className="text-lg font-bold text-amber-200">{city.vp}</p>
          </div>
          {city.shortage > 0 && (
            <div>
              <p className="text-xs text-mystery-400">Shortage</p>
              <p className="text-lg font-bold text-red-300">{city.shortage}</p>
            </div>
          )}
        </div>
      </header>

      <section className="space-y-3 rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
        <PhaseHeader pub={pub} clockOffset={clockOffset} />
        <NarrationCaption text={narration.text} />
        {action}
      </section>

      <nav className="flex gap-1 overflow-x-auto rounded-xl bg-mystery-800/60 p-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${
              tab === t ? "bg-mystery-600 text-white" : "text-mystery-300"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      <section className="rounded-2xl border border-white/10 bg-mystery-800/60 p-4">
        {tab === "City" && (
          <div className="space-y-4">
            <div>
              <p className="mb-1 text-xs uppercase tracking-wider text-mystery-400">
                Storehouse ({inventorySize}
                {city.storage !== null ? ` / ${city.storage}` : ""})
              </p>
              <ResourceBundle bundle={priv.inventory} empty="Empty" />
              {city.storage !== null && inventorySize > city.storage && (
                <p className="mt-1 text-xs text-amber-300">Over storage — excess is discarded at Cleanup.</p>
              )}
            </div>
            <CityCard city={city} />
          </div>
        )}
        {tab === "Projects" && (
          <ProjectsPanel code={code} playerId={playerId} pub={pub} priv={priv} interactive={false} />
        )}
        {tab === "Market" && <MarketBoard pub={pub} />}
        {tab === "Rivals" && (
          <div className="grid gap-3 sm:grid-cols-2">
            {pub.cities
              .filter((c) => c.slot !== city.slot)
              .map((c) => (
                <CityCard key={c.slot} city={c} />
              ))}
          </div>
        )}
        {tab === "History" && <AuctionHistory pub={pub} viewerSlot={city.slot} />}
      </section>
    </div>
  );
}
