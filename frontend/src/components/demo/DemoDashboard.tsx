"use client";

import { useEffect } from "react";
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

interface DemoDashboardProps {
  forceMock: boolean;
}

/**
 * Scene-driven kiosk stage: one focused layout per scene (see demo/EVENTS.md,
 * "The scene machine") instead of one busy wall. Space/Enter/arrow keys and
 * the on-screen gate button advance the demo (HITL).
 */
export function DemoDashboard({ forceMock }: DemoDashboardProps) {
  const { state, advance, dismissInsight, expireBeam } =
    useDemoStream(forceMock);

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
    case "event_map":
      stage = withFeed(<EventMapScene eventMap={state.eventMap} />);
      break;
    case "framing":
      stage = withFeed(
        <FramingScene
          framings={state.framings}
          contrast={state.contrast}
          verifier={state.verifier}
        />,
      );
      break;
    case "audience":
      stage = withFeed(<AudienceScene audience={state.audience} />);
      break;
    case "profile":
      stage = <ProfileScene profile={state.profile} />;
      break;
    case "economy":
      stage = <EconomyScene economy={state.economy} />;
      break;
    default:
      // summary and the waiting screen live on the swarm stage
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
