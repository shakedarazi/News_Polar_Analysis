"use client";

import { useEffect, useReducer, useRef } from "react";
import { DEFAULT_AGENTS } from "./roster";
import { startMockStream } from "./mockStream";
import type {
  DemoEvent,
  DemoState,
  FeedItem,
  ScrapeUrlTrack,
  StateSnapshot,
  StreamMode,
} from "./types";

const MAX_FEED = 12;
const MAX_BEAMS = 10;
const MAX_SCRAPE_URLS = 3;
/** fall back to mock if the backend is unreachable this long */
const MOCK_FALLBACK_MS = 5_000;
/** while in auto-mock, probe the real backend at this interval */
const LIVE_PROBE_MS = 15_000;
const MAX_BACKOFF_MS = 15_000;
/** live stream with no events for this long → kiosk auto-restart via POST /control/restart */
const STALL_RESTART_MS = 90_000;

export function demoApiBase(): string {
  return (
    process.env.NEXT_PUBLIC_DEMO_API?.replace(/\/$/, "") ||
    "http://localhost:8010"
  );
}

/* ---------------- reducer ---------------- */

type Action =
  | { type: "event"; ev: DemoEvent }
  | { type: "snapshot"; snap: StateSnapshot }
  | { type: "mode"; mode: StreamMode }
  | { type: "dismiss_debate" }
  | { type: "dismiss_insight"; id: number }
  | { type: "dismiss_summary" }
  | { type: "dismiss_classification"; id: number }
  | { type: "expire_beam"; id: number };

// seeded randomly so ids stay unique even if the module is re-evaluated
// (dev HMR) while reduced state survives
let nextId = Math.floor(Math.random() * 1_000_000_000);
function uid(): number {
  return nextId++;
}

export function initialDemoState(): DemoState {
  return {
    mode: "connecting",
    autoplay: true,
    agents: DEFAULT_AGENTS,
    agentStatus: {},
    activeAgent: null,
    scene: null,
    gate: null,
    archSteps: [],
    showcase: null,
    retrieval: null,
    economy: null,
    learnedItems: [],
    llmMode: null,
    phase: null,
    feed: [],
    beams: [],
    scrape: [],
    classification: null,
    debate: null,
    metrics: [],
    learned: 0,
    tokens: { totalTokens: 0, totalCostUsd: 0, lastAgent: null, pulse: 0 },
    insight: null,
    summary: null,
  };
}

/** transient state cleared on `reset` (roster, mode, autoplay survive) */
function clearedRun(state: DemoState): DemoState {
  return {
    ...initialDemoState(),
    mode: state.mode,
    autoplay: state.autoplay,
    agents: state.agents,
  };
}

function applyEvent(state: DemoState, ev: DemoEvent): DemoState {
  switch (ev.type) {
    case "scene":
      // one focus per scene: entering a scene clears the previous scene's
      // payloads and transient overlays
      return {
        ...state,
        scene: ev,
        archSteps: [],
        showcase: null,
        retrieval: null,
        classification: null,
        insight: null,
        debate: state.debate?.end ? null : state.debate,
        summary: ev.scene === "summary" ? state.summary : null,
      };

    case "gate":
      return { ...state, gate: ev };

    case "gate_cleared":
      return state.gate?.gate_id === ev.gate_id
        ? { ...state, gate: null }
        : state;

    case "arch_step":
      return {
        ...state,
        archSteps: [
          ...state.archSteps.filter((s) => s.step !== ev.step),
          ev,
        ],
      };

    case "showcase":
      return { ...state, showcase: ev };

    case "retrieval":
      return { ...state, retrieval: ev };

    case "economy":
      return { ...state, economy: ev };

    case "llm_mode":
      return { ...state, llmMode: ev };

    case "phase":
      return { ...state, phase: ev, summary: null };

    case "agent_status": {
      if (typeof ev.agent !== "string") return state;
      const active =
        ev.state === "working" || ev.state === "debating"
          ? ev.agent
          : state.activeAgent === ev.agent &&
              (ev.state === "idle" || ev.state === "done")
            ? null
            : state.activeAgent;
      return {
        ...state,
        activeAgent: active,
        agentStatus: {
          ...state.agentStatus,
          [ev.agent]: { state: ev.state, task_he: ev.task_he },
        },
      };
    }

    case "message": {
      const beam = {
        id: uid(),
        from: ev.from,
        to: ev.to,
        kind: ev.kind,
        summary_he: ev.summary_he ?? "",
      };
      return { ...state, beams: [...state.beams, beam].slice(-MAX_BEAMS) };
    }

    case "reasoning": {
      const item: FeedItem = {
        id: uid(),
        agent: ev.agent,
        level: ev.level ?? "info",
        text_he: ev.text_he ?? "",
      };
      return { ...state, feed: [item, ...state.feed].slice(0, MAX_FEED) };
    }

    case "scrape_step": {
      if (typeof ev.url !== "string") return state;
      const existing = state.scrape.find((t) => t.url === ev.url);
      let scrape: ScrapeUrlTrack[];
      const step = {
        strategy: ev.strategy,
        status: ev.status,
        note_he: ev.note_he,
      };
      if (existing) {
        scrape = state.scrape.map((t) =>
          t.url === ev.url
            ? {
                ...t,
                article_title: ev.article_title || t.article_title,
                steps: [
                  // one entry per strategy — later statuses replace "trying"
                  ...t.steps.filter((s) => s.strategy !== ev.strategy),
                  step,
                ],
              }
            : t,
        );
      } else {
        scrape = [
          ...state.scrape,
          { url: ev.url, article_title: ev.article_title ?? "", steps: [step] },
        ].slice(-MAX_SCRAPE_URLS);
      }
      return { ...state, scrape };
    }

    case "classification":
      return { ...state, classification: { id: uid(), ev } };

    case "debate_start":
      return { ...state, debate: { start: ev, turns: [], end: null } };

    case "debate_turn": {
      if (!state.debate || state.debate.start.debate_id !== ev.debate_id) {
        return state;
      }
      return {
        ...state,
        debate: { ...state.debate, turns: [...state.debate.turns, ev] },
      };
    }

    case "debate_end": {
      if (!state.debate || state.debate.start.debate_id !== ev.debate_id) {
        return state;
      }
      return { ...state, debate: { ...state.debate, end: ev } };
    }

    case "metric": {
      const metrics = [
        ...state.metrics.filter((m) => m.round !== ev.round),
        ev,
      ].sort((a, b) => a.round - b.round);
      return {
        ...state,
        metrics,
        learned: Math.max(state.learned, ev.learned ?? 0),
      };
    }

    case "tokens":
      return {
        ...state,
        tokens: {
          totalTokens: ev.total_tokens ?? state.tokens.totalTokens,
          totalCostUsd: ev.total_cost_usd ?? state.tokens.totalCostUsd,
          lastAgent: ev.agent ?? state.tokens.lastAgent,
          pulse: state.tokens.pulse + 1,
        },
      };

    case "learn":
      return {
        ...state,
        learned: ev.memory_size ?? state.learned,
        learnedItems: [...state.learnedItems, ev].slice(-10),
      };

    case "insight":
      return { ...state, insight: { id: uid(), ev } };

    case "run_summary":
      return { ...state, summary: ev, debate: null, insight: null };

    case "reset":
      return clearedRun(state);

    default:
      return state;
  }
}

function reducer(state: DemoState, action: Action): DemoState {
  switch (action.type) {
    case "event":
      try {
        return applyEvent(state, action.ev);
      } catch {
        return state; // never crash on malformed events
      }

    case "snapshot": {
      const snap = action.snap;
      const agentStatus = { ...state.agentStatus };
      if (snap.agent_states && typeof snap.agent_states === "object") {
        for (const [id, st] of Object.entries(snap.agent_states)) {
          if (st && typeof st.state === "string") {
            agentStatus[id] = { state: st.state, task_he: st.task_he };
          }
        }
      }
      return {
        ...state,
        agents:
          Array.isArray(snap.agents) && snap.agents.length > 0
            ? snap.agents
            : state.agents,
        agentStatus,
        autoplay:
          typeof snap.autoplay === "boolean" ? snap.autoplay : state.autoplay,
        scene: snap.scene ?? state.scene,
        gate: snap.gate !== undefined ? snap.gate : state.gate,
        archSteps: Array.isArray(snap.arch_steps)
          ? snap.arch_steps
          : state.archSteps,
        showcase: snap.showcase ?? state.showcase,
        retrieval: snap.retrieval ?? state.retrieval,
        economy: snap.economy ?? state.economy,
        learnedItems: Array.isArray(snap.learned)
          ? snap.learned
          : state.learnedItems,
        llmMode: snap.llm_mode ?? state.llmMode,
        phase: snap.phase ?? state.phase,
        metrics: Array.isArray(snap.metrics) ? snap.metrics : state.metrics,
        tokens: snap.tokens
          ? {
              totalTokens: snap.tokens.total_tokens ?? 0,
              totalCostUsd: snap.tokens.total_cost_usd ?? 0,
              lastAgent: snap.tokens.agent ?? null,
              pulse: state.tokens.pulse,
            }
          : state.tokens,
        feed: Array.isArray(snap.feed)
          ? snap.feed
              .slice(-MAX_FEED)
              .reverse()
              .map((r) => ({
                id: uid(),
                agent: r.agent,
                level: r.level ?? "info",
                text_he: r.text_he ?? "",
              }))
          : state.feed,
      };
    }

    case "mode":
      return state.mode === action.mode
        ? state
        : action.mode === "mock"
          ? { ...clearedRun(state), mode: "mock", agents: DEFAULT_AGENTS }
          : { ...state, mode: action.mode };

    case "dismiss_debate":
      return { ...state, debate: null };

    case "dismiss_insight":
      return state.insight?.id === action.id
        ? { ...state, insight: null }
        : state;

    case "dismiss_summary":
      return { ...state, summary: null };

    case "dismiss_classification":
      return state.classification?.id === action.id
        ? { ...state, classification: null }
        : state;

    case "expire_beam":
      return {
        ...state,
        beams: state.beams.filter((b) => b.id !== action.id),
      };

    default:
      return state;
  }
}

/* ---------------- hook ---------------- */

export interface DemoStreamApi {
  state: DemoState;
  /** HITL: clear the currently open gate (space / on-screen button) */
  advance: () => void;
  dismissDebate: () => void;
  dismissInsight: (id: number) => void;
  dismissSummary: () => void;
  dismissClassification: (id: number) => void;
  expireBeam: (id: number) => void;
}

function parseEvent(raw: string): DemoEvent | null {
  try {
    const obj: unknown = JSON.parse(raw);
    if (
      typeof obj === "object" &&
      obj !== null &&
      typeof (obj as { type?: unknown }).type === "string"
    ) {
      return obj as DemoEvent;
    }
  } catch {
    /* malformed payload — ignore */
  }
  return null;
}

/**
 * Connects to the demo backend SSE stream, with:
 * - initial GET /state snapshot for roster/recovery,
 * - auto-reconnect with exponential backoff,
 * - automatic mock fallback when the backend is unreachable (or ?mock=1),
 * - periodic probing to return to live once the backend appears.
 */
export function useDemoStream(forceMock: boolean): DemoStreamApi {
  const [state, dispatch] = useReducer(reducer, undefined, initialDemoState);
  const apiRef = useRef<Omit<DemoStreamApi, "state">>({
    advance: () => {
      void fetch(`${demoApiBase()}/control/advance`, { method: "POST" }).catch(
        () => undefined,
      );
    },
    dismissDebate: () => dispatch({ type: "dismiss_debate" }),
    dismissInsight: (id) => dispatch({ type: "dismiss_insight", id }),
    dismissSummary: () => dispatch({ type: "dismiss_summary" }),
    dismissClassification: (id) =>
      dispatch({ type: "dismiss_classification", id }),
    expireBeam: (id) => dispatch({ type: "expire_beam", id }),
  });
  // Latest state for timer callbacks (stall check must see open gates).
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    let disposed = false;
    let es: EventSource | null = null;
    let mock: { stop: () => void } | null = null;
    let cleanupDom: (() => void) | null = null;
    let sawLive = false;
    let attempts = 0;
    let lastEventAt = Date.now();
    const timers = new Set<ReturnType<typeof setTimeout>>();

    const later = (fn: () => void, ms: number) => {
      const t = setTimeout(() => {
        timers.delete(t);
        if (!disposed) fn();
      }, ms);
      timers.add(t);
      return t;
    };

    const base = demoApiBase();

    const stopMock = () => {
      mock?.stop();
      mock = null;
    };

    const startMock = () => {
      if (disposed || mock) return;
      dispatch({ type: "mode", mode: "mock" });
      mock = startMockStream((ev) => {
        if (!disposed) dispatch({ type: "event", ev });
      });
    };

    const fetchSnapshot = async (): Promise<boolean> => {
      try {
        const ctrl = new AbortController();
        const t = later(() => ctrl.abort(), 4_000);
        const res = await fetch(`${base}/state`, { signal: ctrl.signal });
        clearTimeout(t);
        timers.delete(t);
        if (!res.ok) return false;
        const snap: unknown = await res.json();
        if (disposed || typeof snap !== "object" || snap === null) {
          return false;
        }
        dispatch({ type: "snapshot", snap: snap as StateSnapshot });
        return true;
      } catch {
        return false;
      }
    };

    const connect = () => {
      if (disposed || forceMock) return;
      es?.close();
      es = new EventSource(`${base}/events`);

      es.onopen = () => {
        if (disposed) return;
        attempts = 0;
        sawLive = true;
        lastEventAt = Date.now(); // a fresh connection is never a stall
        stopMock();
        dispatch({ type: "mode", mode: "live" });
        // refresh the snapshot on every (re)connect for recovery
        void fetchSnapshot();
      };

      es.onmessage = (msg: MessageEvent<string>) => {
        if (disposed) return;
        lastEventAt = Date.now();
        const ev = parseEvent(msg.data);
        if (ev) dispatch({ type: "event", ev });
      };

      es.onerror = () => {
        if (disposed) return;
        es?.close();
        es = null;
        attempts += 1;
        const delay = Math.min(MAX_BACKOFF_MS, 1_000 * 2 ** attempts);
        // backend gone for a while → keep the wall alive with the mock
        if (sawLive && attempts >= 3) startMock();
        later(connect, delay);
      };
    };

    if (forceMock) {
      startMock();
    } else {
      connect();
      // never reached the backend within the window → mock fallback
      later(() => {
        if (!sawLive && !mock) startMock();
      }, MOCK_FALLBACK_MS);
      // while mocked, probe for the real backend and switch back when it appears
      const probe = () => {
        if (disposed) return;
        if (mock) {
          void fetchSnapshot().then((ok) => {
            if (ok && !disposed && mock) {
              stopMock();
              dispatch({ type: "event", ev: { type: "reset", ts: Date.now() } });
              attempts = 0;
              connect();
            }
          });
        }
        later(probe, LIVE_PROBE_MS);
      };
      later(probe, LIVE_PROBE_MS);
      // kiosk auto-restart: a live but stalled backend gets a restart poke.
      // ONLY in autoplay (unattended kiosk) mode — in presenter mode (HITL)
      // a long silence is the presenter talking, never a stall. Open gates
      // also reset the clock, whatever the mode.
      const stallCheck = () => {
        const st = stateRef.current;
        if (st.gate !== null || !st.autoplay || st.mode !== "live") {
          lastEventAt = Date.now();
        } else if (es && Date.now() - lastEventAt > STALL_RESTART_MS) {
          lastEventAt = Date.now();
          console.warn(
            `[demo] stall restart: mode=${st.mode} autoplay=${st.autoplay} gate=${st.gate}`,
          );
          void fetch(`${base}/control/restart`, { method: "POST" }).catch(
            () => undefined,
          );
        }
        later(stallCheck, 30_000);
      };
      later(stallCheck, 30_000);
      // recover instantly when the kiosk tab regains focus/visibility
      const onVisible = () => {
        if (!document.hidden) void fetchSnapshot();
      };
      document.addEventListener("visibilitychange", onVisible);
      window.addEventListener("focus", onVisible);
      cleanupDom = () => {
        document.removeEventListener("visibilitychange", onVisible);
        window.removeEventListener("focus", onVisible);
      };
    }

    return () => {
      disposed = true;
      es?.close();
      es = null;
      stopMock();
      cleanupDom?.();
      for (const t of timers) clearTimeout(t);
      timers.clear();
    };
  }, [forceMock]);

  return { state, ...apiRef.current };
}
