"use client";

import { useCallback, useEffect, useState } from "react";
import { useDemoStream } from "./useDemoStream";
import { TopBar } from "./TopBar";
import { AgentMap } from "./AgentMap";
import { ActivityFeed } from "./ActivityFeed";
import { ScrapeTracker } from "./ScrapeTracker";
import { TierLeaderboard } from "./TierLeaderboard";
import { InsightToast } from "./InsightToast";
import { SummaryOverlay } from "./SummaryOverlay";
import { ArchScene } from "./ArchScene";
import { ShowcaseScene } from "./ShowcaseScene";
import { EventMapScene } from "./EventMapScene";
import { FramingScene } from "./FramingScene";
import { AudienceScene } from "./AudienceScene";
import { ProfileScene } from "./ProfileScene";
import { EconomyScene } from "./EconomyScene";
import { GateBar } from "./GateBar";
import { HubScene, MODULES, type ModuleId } from "./HubScene";
import { useFacts } from "./explain/facts";
import { ScrapingModule } from "./explain/ScrapingModule";
import { AlgorithmModule } from "./explain/AlgorithmModule";
import { RetrievalModule } from "./explain/RetrievalModule";

interface DemoDashboardProps {
  forceMock: boolean;
}

/** hub → a deep-dive module, or the narrated nine-scene run. */
type View = { kind: "hub" } | { kind: "run" } | { kind: "module"; id: ModuleId };

/**
 * Kiosk stage.
 *
 * The entry point is the hub, not the waterfall: at an exhibition the visitor
 * picks the question, so the presenter needs to open any part of the system
 * directly. The narrated run is still there as one door among the others.
 */
export function DemoDashboard({ forceMock }: DemoDashboardProps) {
  const { state, advance, dismissInsight, expireBeam } =
    useDemoStream(forceMock);
  const facts = useFacts();
  const [view, setView] = useState<View>({ kind: "hub" });

  const goHub = useCallback(() => setView({ kind: "hub" }), []);

  // presenter keyboard: digits pick a module from anywhere, Esc goes back,
  // and the "next" keys only advance while the narrated run is on screen.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "Backspace") {
        e.preventDefault();
        goHub();
        return;
      }
      const digit = Number(e.key);
      if (digit >= 1 && digit <= MODULES.length) {
        const m = MODULES[digit - 1];
        if (!m.ready) return;
        e.preventDefault();
        setView(m.id === "run" ? { kind: "run" } : { kind: "module", id: m.id });
        return;
      }
      if (
        view.kind === "run" &&
        (e.key === " " ||
          e.key === "Enter" ||
          e.key === "ArrowLeft" ||
          e.key === "ArrowRight")
      ) {
        e.preventDefault();
        advance();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance, goHub, view.kind]);

  const scene = state.scene?.scene ?? null;

  /* the swarm stage — the opening/idle screen and the summary backdrop */
  const swarmStage = (
    <div className="grid h-full min-h-0 grid-rows-[1fr_22%] gap-3">
      <div className="grid min-h-0 grid-cols-[28%_1fr] gap-3">
        <ActivityFeed feed={state.feed} agents={state.agents} />
        <div className="dk-card relative min-h-0 overflow-hidden">
          <AgentMap
            agents={state.agents}
            agentStatus={state.agentStatus}
            beams={state.beams}
            idle={state.scene === null && state.phase === null}
            expireBeam={expireBeam}
          />
        </div>
      </div>
      <footer className="min-h-0">
        <TierLeaderboard agents={state.agents} activeAgent={state.activeAgent} />
      </footer>
    </div>
  );

  /* focused side-feed layout: the agents narrate alongside the scene */
  const withFeed = (content: React.ReactNode) => (
    <div className="grid h-full min-h-0 grid-cols-[27%_1fr] gap-3">
      <ActivityFeed feed={state.feed} agents={state.agents} />
      <div className="relative min-h-0">{content}</div>
    </div>
  );

  let runStage: React.ReactNode;
  switch (scene) {
    case "arch":
      runStage = <ArchScene steps={state.archSteps} />;
      break;
    case "intake":
      runStage = withFeed(
        <div className="dk-card flex h-full min-h-0 items-center justify-center overflow-hidden p-6">
          <ScrapeTracker tracks={state.scrape} stage />
        </div>,
      );
      break;
    case "lexicon":
      runStage = withFeed(<ShowcaseScene showcase={state.showcase} />);
      break;
    case "event_map":
      runStage = withFeed(<EventMapScene eventMap={state.eventMap} />);
      break;
    case "framing":
      runStage = withFeed(
        <FramingScene
          framings={state.framings}
          contrast={state.contrast}
          verifier={state.verifier}
        />,
      );
      break;
    case "audience":
      runStage = withFeed(<AudienceScene audience={state.audience} />);
      break;
    case "profile":
      runStage = <ProfileScene profile={state.profile} />;
      break;
    case "economy":
      runStage = <EconomyScene economy={state.economy} />;
      break;
    default:
      // summary and the waiting screen live on the swarm stage
      runStage = swarmStage;
  }

  const factsOrNull = facts.status === "ready" ? facts.facts : null;

  return (
    <div className="demo-kiosk grid grid-rows-[10%_1fr] gap-3 p-3 pb-4">
      {view.kind === "run" ? (
        <TopBar
          scene={state.scene}
          phase={state.phase}
          mode={state.mode}
          llmMode={state.llmMode}
        />
      ) : (
        <ModuleBar view={view} onHome={goHub} unavailable={facts.status === "unavailable"} />
      )}

      {/* the gate strip only floats over the narrated run — reserving its
          height in a module would waste a band of the wall */}
      <main
        className={`relative min-h-0 ${view.kind === "run" ? "pb-[68px]" : ""}`}
      >
        {view.kind === "hub" && (
          <HubScene
            onEnter={(id) =>
              setView(id === "run" ? { kind: "run" } : { kind: "module", id })
            }
          />
        )}
        {view.kind === "module" && view.id === "scraping" && (
          <ScrapingModule facts={factsOrNull} />
        )}
        {view.kind === "module" && view.id === "algorithm" && (
          <AlgorithmModule facts={factsOrNull} />
        )}
        {view.kind === "module" && view.id === "retrieval" && (
          <RetrievalModule facts={factsOrNull} />
        )}
        {view.kind === "run" && (
          <>
            {runStage}
            {state.insight && (
              <InsightToast insight={state.insight} onDone={dismissInsight} />
            )}
            {state.summary && <SummaryOverlay summary={state.summary} />}
            <GateBar gate={state.gate} onAdvance={advance} />
          </>
        )}
      </main>
    </div>
  );
}

/** Header for the hub and the explainer modules — where am I, and how out. */
function ModuleBar({
  view,
  onHome,
  unavailable,
}: {
  view: View;
  onHome: () => void;
  unavailable: boolean;
}) {
  const mod =
    view.kind === "module" ? MODULES.find((m) => m.id === view.id) : null;

  return (
    <header className="dk-card flex items-center gap-4 px-5">
      <div className="flex items-baseline gap-3">
        <span className="text-[15px] font-bold text-[var(--dk-accent)]">
          Trust
        </span>
        <span className="text-[13px] text-[var(--dk-ink-3)]">
          ניתוח מסגור והקהל בכלי תקשורת ישראליים
        </span>
      </div>

      {mod && (
        <div className="flex items-baseline gap-3">
          <span className="text-[var(--dk-ink-3)]">/</span>
          <span className="text-[19px] font-bold">{mod.title_he}</span>
          <span className="text-[13.5px] text-[var(--dk-ink-2)]">
            {mod.sub_he}
          </span>
        </div>
      )}

      <div className="ms-auto flex items-center gap-3">
        {unavailable && (
          <span className="rounded-full border border-[var(--dk-warn)]/40 px-2.5 py-0.5 text-[12px] text-[var(--dk-warn)]">
            אין קובץ מדידות — דיאגרמות בלבד
          </span>
        )}
        {view.kind !== "hub" && (
          <button
            onClick={onHome}
            className="rounded-xl border border-[var(--dk-border)] px-4 py-1.5 text-[14px] font-semibold text-[var(--dk-ink-2)] transition-colors hover:border-[var(--dk-accent)]/60 hover:text-[var(--dk-accent)]"
          >
            ← למפה (Esc)
          </button>
        )}
      </div>
    </header>
  );
}
