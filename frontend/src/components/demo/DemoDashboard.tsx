"use client";

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

interface DemoDashboardProps {
  forceMock: boolean;
}

export function DemoDashboard({ forceMock }: DemoDashboardProps) {
  const {
    state,
    dismissDebate,
    dismissInsight,
    dismissSummary,
    dismissClassification,
    expireBeam,
  } = useDemoStream(forceMock);

  const showScrape =
    state.phase?.phase === "intake" && state.scrape.length > 0;

  return (
    <div className="demo-kiosk grid grid-rows-[8%_1fr_22%] gap-3 p-3 pb-4">
      <TopBar phase={state.phase} mode={state.mode} />

      {/* main area: activity feed (right, 28%) + agent map */}
      <main className="relative grid min-h-0 grid-cols-[28%_1fr] gap-3">
        <ActivityFeed feed={state.feed} agents={state.agents} />

        <div className="dk-card relative min-h-0 overflow-hidden">
          <AgentMap
            agents={state.agents}
            agentStatus={state.agentStatus}
            beams={state.beams}
            idle={state.phase === null}
            expireBeam={expireBeam}
          />
          {showScrape && <ScrapeTracker tracks={state.scrape} />}
          {state.classification && (
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
      </main>

      {/* bottom cards */}
      <footer className="grid min-h-0 grid-cols-3 gap-3">
        <MetricsChart metrics={state.metrics} learned={state.learned} />
        <TierLeaderboard
          agents={state.agents}
          activeAgent={state.activeAgent}
        />
        <TokenEconomy tokens={state.tokens} agents={state.agents} />
      </footer>

      {/* transient overlays */}
      {state.insight && (
        <InsightToast insight={state.insight} onDone={dismissInsight} />
      )}
      {state.summary && (
        <SummaryOverlay summary={state.summary} onDone={dismissSummary} />
      )}
    </div>
  );
}
