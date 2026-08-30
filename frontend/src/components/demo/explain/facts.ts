"use client";

import { useEffect, useState } from "react";
import { demoApiBase } from "../useDemoStream";

/**
 * Mirror of demo/data/explainer_facts.json (built by
 * demo/snapshot/build_explainer_facts.py). Constants come from src/ at build
 * time; measurements come from the frozen snapshot. Keep both files in sync —
 * tests/test_explainer_facts.py asserts the Python side still produces this
 * shape.
 */

export interface RetryConst {
  max_attempts: number;
  initial_backoff_s: number;
  backoff_sequence_s: number[];
}
export interface CrawlConst {
  delay_seconds: number;
  min_discovered_for_alert: number;
  failure_rate_threshold: number;
}
export interface ExtractConst {
  min_len: number;
  min_paragraph_len: number;
}
export interface LexiconConst {
  single_prefixes: string[];
  prefix_pairs: string[];
  min_base_length: number;
}
export interface Constants {
  retry: RetryConst;
  crawl: CrawlConst;
  extract: ExtractConst;
  canonical: { tracking_params: string[] };
  windows: { max_window_tokens: number };
  lexicon: LexiconConst;
  categories_he: string[];
}

export interface SourceFact {
  id: string;
  source_he: string;
  discovery: "rss" | "next_data";
  feeds: string[];
  dom_selectors: string[];
  bespoke_he: string | null;
  articles: number;
  avg_chars: number;
  min_chars: number;
  max_chars: number;
}

export interface Bucket {
  bucket: string;
  n: number;
}

export interface WindowFacts {
  total: number;
  null_dominance: number;
  avg_len: number;
  min_len: number;
  max_len: number;
  at_or_over_cap: number;
  per_article: { avg: number; min: number; max: number };
  dominance_hist: Bucket[];
  active_hist: Bucket[];
}

export interface CommentFacts {
  total: number;
  articles_with_comments: number;
  avg_chars: number;
  avg_likes: number;
  max_likes: number;
  aggregates: number;
  avg_audience_mean: number;
  avg_audience_p85: number;
  avg_num_comments: number;
  max_num_comments: number;
}

export interface LexiconFacts {
  per_category: { category: number; name_he: string; base: number }[];
  article_base: number;
  article_expanded: number;
  article_factor: number;
  comment_base: number;
  comment_expanded: number;
  comment_factor: number;
}

export interface IdentityExample {
  clean_url: string;
  dirty_url: string;
  clean_canonical: string;
  dirty_canonical: string;
  article_id: string;
  dirty_article_id: string;
  stored_article_id: string;
  same: boolean;
}

export interface WorkedExample {
  article_id: string;
  source: string;
  source_he: string;
  title: string;
  text_chars: number;
  sentences_total: number;
  windows_total: number;
  sentences: { text: string; tokens: number }[];
  window: {
    index: number;
    raw: string;
    normalized: string;
    tokens: { t: string; category: number | null }[];
    window_len: number;
    counts: number[];
    cat_words: number;
    active: number;
    max_count: number;
    dominance: number | null;
  };
}

export interface Bucketed {
  label: string;
  n: number;
}

export interface RetrievalNeighbour {
  source: string;
  source_he: string;
  title: string;
  cos: number;
  jaccard: number;
  shared: string[];
  /** survived the one-per-source selection into the final event */
  kept: boolean;
}

export interface RetrievalFacts {
  model: string;
  dims: number;
  vectors: number;
  bytes: number;
  query_ms: number;
  min_text_chars: number;
  passage_lead_chars: number;
  cluster_sim: number;
  keyword_jaccard: number;
  corpus: {
    total: number;
    indexed: number;
    too_short: number;
    per_source: {
      source: string;
      source_he: string;
      articles: number;
      indexed: number;
    }[];
  };
  events: { total: number; versions: number; three_plus: number };
  keyword: {
    found: number;
    total: number;
    recall: number;
    zero_overlap: number;
    blind_events: number;
    median: number | null;
    histogram: Bucketed[];
  };
  similarity: {
    pairs: number;
    mean: number;
    median: number;
    histogram: Bucketed[];
    above: { threshold: number; n: number; pct: number }[];
  };
  sweep: {
    threshold: number;
    events: number;
    three_plus: number;
    versions: number;
    chosen: boolean;
  }[];
  example: {
    topic_he: string | null;
    seed: { source: string; source_he: string; title: string };
    neighbours: RetrievalNeighbour[];
    rejected: {
      source: string;
      source_he: string;
      title: string;
      cos: number;
    } | null;
  };
  duplicates: {
    threshold: number;
    pairs: number;
    examples: {
      cos: number;
      source: string;
      source_he: string;
      title: string;
      url_a: string;
      url_b: string;
      id_a: string;
      id_b: string;
    }[];
  };
}

export interface FramingOutput {
  actor: string | null;
  responsibility: string | null;
  loaded_terms: string[];
  voice: string | null;
  lead_perspective: string | null;
}

export interface ContrastRow {
  source: string;
  source_he: string;
  title: string;
  distinctive: string | null;
  evidence: string | null;
  /** survived the grounding check; false means the quote was not in the text */
  kept: boolean;
}

export interface FramingFacts {
  model: string;
  temperature: number;
  lead_chars: number;
  max_tokens: { framing: number; contrast: number };
  contrast_versions: number;
  keys: string[];
  framing_system: string;
  contrast_system: string;
  cache: { framing: number; contrast: number };
  distribution: {
    total: number;
    voice: Bucketed[];
    terms_per_article: { terms: number; n: number }[];
    actor_null: number;
    responsibility_null: number;
  };
  verifier: {
    terms_total: number;
    terms_rejected: number;
    actors_total: number;
    actors_rejected: number;
    actors_exact: number;
    actors_word_level: number;
    quotes_total: number;
    quotes_rejected: number;
    quote_reasons: { kind: string; n: number }[];
  };
  acronyms: {
    framing_hits: number;
    framing_total: number;
    contrast_hits: number;
    contrast_total: number;
    distinct: number;
    examples: string[];
  };
  term_example: {
    source: string;
    source_he: string;
    title: string;
    lead: string;
    framing: FramingOutput;
    kept: string[];
    dropped: string[];
  } | null;
  quote_examples: {
    kind: string;
    source: string;
    source_he: string;
    evidence: string;
    excerpt: string;
  }[];
  contrast_example: {
    topic_he: string | null;
    shared: string | null;
    per_source: ContrastRow[];
  } | null;
}

export interface Facts {
  available: true;
  corpus: { articles: number };
  constants: Constants;
  identity_example: IdentityExample;
  worked_example: WorkedExample;
  sources: SourceFact[];
  windows: WindowFacts;
  comments: CommentFacts;
  lexicon: LexiconFacts;
  retrieval: RetrievalFacts;
  framing: FramingFacts;
}

type FactsState =
  | { status: "loading" }
  | { status: "ready"; facts: Facts }
  | { status: "unavailable" };

/**
 * Fetch the explainer facts once.
 *
 * Deliberately has no retry loop and no failure UI beyond `unavailable`: the
 * modules are built so their diagrams render from the code they describe, and
 * only the measured strips disappear. A kiosk with no facts file is degraded,
 * not broken.
 */
export function useFacts(): FactsState {
  const [state, setState] = useState<FactsState>({ status: "loading" });

  useEffect(() => {
    const ctrl = new AbortController();
    fetch(`${demoApiBase()}/facts`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.available) setState({ status: "ready", facts: data as Facts });
        else setState({ status: "unavailable" });
      })
      .catch(() => setState({ status: "unavailable" }));
    return () => ctrl.abort();
  }, []);

  return state;
}
