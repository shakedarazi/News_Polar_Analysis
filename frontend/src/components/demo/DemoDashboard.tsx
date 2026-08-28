"use client";

import { useEffect } from "react";
import { useDemoStream } from "./useDemoStream";
import { TopBar } from "./TopBar";
import { AgentMap } from "./AgentMap";
import { ActivityFeed } from "./ActivityFeed";
import { ScrapeTracker } from "./ScrapeTracker";
import { MetricsChart } from "./MetricsChart";
import { TierLeaderboard } from "./TierLeaderboard";
import { TokenEconomy } from "./TokenEconomy";
import { DebateOverlay } from "./DebateOverlay";
import { InsightToast } from "./InsightToast";
import { SummaryOverlay } from "./SummaryOverlay";
import { ClassificationFlash } from "./ClassificationFlash";
import { ArchScene } from "./ArchScene";
import { ShowcaseScene } from "./ShowcaseScene";
import { RetrievalScene } from "./RetrievalScene";
import { LearningScene } from "./LearningScene";
import { EconomyScene } from "./EconomyScene";
import { GateBar } from "./GateBar";

interface DemoDashboardProps {
  forceMock: boolean;
}

/**
 * Scene-driven kiosk stage: one focused layout per scene (see demo/EVENTS.md,
 * "The scene machine") instead of one busy wall. Space/Enter/arrow keys and
 * the on-screen gate button advance the demo (HITL).
 */
export function DemoDashboard({ forceMock }: DemoDashboardProps) {
  const {
    state,
    advance,
    dismissDebate,
    dismissInsight,
    dismissClassification,
    expireBeam,
  } = useDemoStream(forceMock);

  // presenter keyboard: any "next" key clears the current gate
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key === " " ||
        e.key === "Enter" ||
        e.key === "ArrowLeft" ||
        e.key === "ArrowRight"
      ) {
        e.preventDefault();
        advance();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [advance]);

  const scene = state.scene?.scene ?? null;
  const showScrape =
    state.phase?.phase === "intake" && state.scrape.length > 0;

  /* the swarm stage — the rounds scene, and the idle/waiting screen */
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
          {scene === "rounds" && showScrape && (
            <ScrapeTracker tracks={state.scrape} />
          )}
          {scene === "rounds" && state.classification && (
            <ClassificationFlash
              item={state.classification}
              onDone={dismissClassification}
            />
          )}
          {state.debate && (
            <DebateOverlay
              debate={state.debate}
              agents={state.agents}
              onClose={dismissDebate}
            />
          )}
        </div>
      </div>
      <footer className="grid min-h-0 grid-cols-3 gap-3">
        <MetricsChart metrics={state.metrics} learned={state.learned} />
        <TierLeaderboard agents={state.agents} activeAgent={state.activeAgent} />
        <TokenEconomy tokens={state.tokens} agents={state.agents} />
      </footer>
    </div>
  );

  /* focused side-feed layout used by the intake/lexicon/rag scenes */
  const withFeed = (content: React.ReactNode) => (
    <div className="grid h-full min-h-0 grid-cols-[27%_1fr] gap-3">
      <ActivityFeed feed={state.feed} agents={state.agents} />
      <div className="relative min-h-0">{content}</div>
    </div>
  );

  let stage: React.ReactNode;
  switch (scene) {
    case "arch":
      stage = <ArchScene steps={state.archSteps} />;
      break;
    case "intake":
      stage = withFeed(
        <div className="dk-card flex h-full min-h-0 items-center justify-center overflow-hidden p-6">
          <ScrapeTracker tracks={state.scrape} stage />
        </div>,
      );
      break;
    case "lexicon":
      stage = withFeed(<ShowcaseScene showcase={state.showcase} />);
      break;
    case "rag":
      stage = withFeed(<RetrievalScene retrieval={state.retrieval} />);
      break;
    case "learning":
      stage = (
        <LearningScene
          metrics={state.metrics}
          learned={state.learned}
          learnedItems={state.learnedItems}
        />
      );
      break;
    case "economy":
      stage = <EconomyScene economy={state.economy} tokens={state.tokens} />;
      break;
    default:
      // rounds, summary, and the waiting screen all live on the swarm stage
      stage = swarmStage;
  }

  return (
    <div className="demo-kiosk grid grid-rows-[10%_1fr] gap-3 p-3 pb-4">
      <TopBar
        scene={state.scene}
        phase={state.phase}
        mode={state.mode}
        llmMode={state.llmMode}
      />

      <main className="relative min-h-0">
        {stage}

        {/* transient overlays (any scene) */}
        {state.insight && (
          <InsightToast insight={state.insight} onDone={dismissInsight} />
        )}
        {state.summary && <SummaryOverlay summary={state.summary} />}
        <GateBar gate={state.gate} onAdvance={advance} />
      </main>
    </div>
  );
}
