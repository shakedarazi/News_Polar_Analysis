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
