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

export interface AudienceComment {
  text: string;
  likes: number;
  len: number;
  polar: number;
  hits: string[];
  ratio: number;
  weight: number;
}

export interface AudienceWalkStep {
  value: number;
  weight: number;
  cum: number;
  /** the step where the cumulative weight first reaches 0.85 of the total */
  hit: boolean;
}

export interface AudienceFacts {
  polar_lexicon_forms: number;
  quantile: number;
  comments: {
    total: number;
    articles: number;
    len_mean: number;
    len_median: number;
    len_max: number;
    len_under_4: number;
    zero_polar: number;
    ratio_mean: number;
    ratio_hist: Bucketed[];
  };
  weight: {
    curve: { likes: number; weight: number }[];
    max_likes: number;
    inert: number;
    shift_mean: number;
    shift_p85: number;
    articles: number;
    articles_unaffected: number;
    per_source: {
      source: string;
      source_he: string;
      comments: number;
      likes: number;
      avg_likes: number;
      inert: number;
      articles: number;
      articles_unaffected: number;
      mean_p85_shift: number;
    }[];
  };
  controversy: {
    articles: number;
    nonzero: number;
    at_one_like: number;
    at_even_split: number;
  };
  aggregate: {
    p85_mean: number;
    p85_median: number;
    p85_zero: number;
    p85_one: number;
    mean_median: number;
    p85_hist: Bucketed[];
    counts: { median: number; under_5: number; under_10: number; total: number };
  };
  artifacts: {
    ratio_one: number;
    single_token: number;
    examples: {
      source: string;
      source_he: string;
      text: string;
      likes: number;
      len: number;
    }[];
  };
  example: {
    article_id: string;
    source: string;
    source_he: string;
    title: string;
    comments: AudienceComment[];
    weighted: { mean: number; p85: number };
    unweighted: { mean: number; p85: number };
    sum_weight: number;
    target: number;
    walk: AudienceWalkStep[];
  } | null;
  hijack: {
    events: number;
    comparable: number;
    hijacked: number;
    per_source: {
      source: string;
      source_he: string;
      hijacked: number;
      total: number;
    }[];
    pairs: { article_he: string; comments_he: string; n: number }[];
    examples: {
      num_comments: number;
      source: string;
      source_he: string;
      title: string;
      article_he: string;
      comments_he: string;
      top_comment: string;
      top_likes: number;
    }[];
  };
  deviation: {
    source: string;
    source_he: string;
    n: number;
    mean: number;
    median: number;
  }[];
}

export interface OutletRow {
  source: string;
  source_he: string;
  n: number;
  /** the naive per-outlet mean over the same articles, for comparison */
  raw_mean: number | null;
  mean: number | null;
  lo: number | null;
  hi: number | null;
  significant: boolean;
  /** two-sided bootstrap p, null below the 3-observation floor */
  p: number | null;
}

export interface TopicCellRow {
  source: string;
  source_he: string;
  topic_he: string;
  n: number;
  mean: number | null;
  lo: number | null;
  hi: number | null;
  usable: boolean;
  significant: boolean;
  /** interval clears zero but n is under the floor — a false positive's shape */
  tempting: boolean;
}

export interface ChangeScan {
  metric: string;
  metric_he: string;
  source: string;
  source_he: string;
  n: number;
  too_short: boolean;
  at: string | null;
  before: number | null;
  after: number | null;
  shift: number | null;
  statistic: number | null;
  p: number | null;
  detected: boolean;
}

export interface Hit {
  what: string;
  p: number;
  source_he: string;
  metric_he: string;
  /** below/above the event median, or a change-point detection */
  direction: "below" | "above" | "shift";
}

export interface StatsFacts {
  constants: {
    bootstrap_iterations: number;
    bootstrap_seed: number;
    bootstrap_min_n: number;
    permutation_iterations: number;
    min_segment: number;
    min_cell_events: number;
    alpha: number;
  };
  events: number;
  raw_snapshot: { source: string; source_he: string; n: number; mean: number }[];
  metrics: {
    key: string;
    label_he: string;
    n: number;
    variance: {
      total: number;
      between: number;
      within: number;
      between_share: number | null;
      within_share: number | null;
    };
    outlets: OutletRow[];
  }[];
  curve: {
    source: string;
    source_he: string;
    points: { n: number; mean: number; lo: number; hi: number; width: number }[];
  };
  cells_meta: {
    key: string;
    label_he: string;
    total: number;
    usable: number;
    significant: number;
    tempting: number;
  }[];
  cells: Record<string, TopicCellRow[]>;
  scans: ChangeScan[];
  multiplicity: {
    ci_tests: number;
    cell_tests: number;
    scan_tests: number;
    tests: number;
    alpha: number;
    bonferroni: number;
    expected_false: number;
    hits: Hit[];
    survivors: Hit[];
  };
  power: {
    source: string;
    iterations: number;
    rows: { n: number; power_1sd: number; power_half_sd: number }[];
  };
  pairing: {
    sizes: { versions: number; events: number }[];
    two_version: number;
    events: number;
    pairs: { a: string; a_he: string; b: string; b_he: string; events: number }[];
    top_pair_two_version: number;
  };
  coverage: {
    source: string;
    source_he: string;
    covered: number;
    total_events: number;
    share: number;
    in_snapshot: number;
  }[];
}

export interface EconomyStage {
  key: string;
  label_he: string;
  kind: "free" | "local" | "paid";
  n: number;
  unit_he: string;
  detail_he: string;
  usd: number;
}

export interface EconomySplit {
  key: string;
  label_he: string;
  calls: number;
  prompt_tokens: number;
  completion_tokens: number;
  usd: number;
  per_call_usd: number;
  derived: boolean;
}

export interface EconomyExcluded {
  key: string;
  label_he: string;
  detail_he: string;
  n: number | null;
  unit_he: string | null;
  prompt_tokens: number | null;
  usd: number | null;
  estimate: boolean;
}

/** The repair loop: what the verifier deleted, and what the loop won back. */
export interface RepairGuard {
  key: string;
  title_he: string;
  detail_he: string;
}

export interface RepairAttemptRow {
  n: number;
  calls: number;
  accepted: number;
  detail_he: string;
}

export interface RepairFacts {
  constants: {
    model: string;
    max_attempts: number;
    max_attempts_measured: number;
    max_tokens: number;
    lead_chars: number;
    contrast_lead_chars: number;
  };
  verifier: {
    quotes_total: number;
    quotes_rejected: number;
    terms_total: number;
    terms_rejected: number;
  };
  loop: {
    candidates_framing: number;
    candidates_contrast: number;
    entered: number;
    calls: number;
    fixed_fully: number;
    unchanged: number;
    violations_before: number;
    violations_after: number;
    regrounded: number;
    nulled: number;
    destroyed: number;
  };
  attempts: RepairAttemptRow[];
  bill: {
    prompt_tokens: number;
    completion_tokens: number;
    usd: number;
    per_item_usd: number;
    layer_usd: number;
    total_usd: number;
    share_of_layer: number;
  };
  guards: RepairGuard[];
  regression: { destroyed_before_guard: number; destroyed_now: number };
  stage: { events: number; recovered: number };
  example: {
    source: string;
    before: string;
    after: string;
    headline: string;
  } | null;
}

export interface EconomyFacts {
  constants: {
    model: string;
    temperature: number;
    embed_model: string;
    price_prompt_per_m: number;
    price_completion_per_m: number;
    lead_chars: number;
    contrast_lead_chars: number;
    contrast_versions: number;
    framing_max_tokens: number;
    contrast_max_tokens: number;
  };
  bill: {
    calls: number;
    cached_outputs: number;
    covered: boolean;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    prompt_usd: number;
    completion_usd: number;
    usd: number;
    reported_usd: number;
    completion_per_call: number;
    completion_token_share: number;
    completion_bill_share: number;
    price_prompt_per_m: number;
    price_completion_per_m: number;
  };
  stages: EconomyStage[];
  rate: {
    prompt_chars: number;
    prompt_tokens: number;
    chars_per_token: number;
    output_chars: number;
    completion_tokens: number;
    output_chars_per_token: number;
    gap: number;
    examples: { label_he: string; chars: number; tokens: number }[];
  };
  prompt: {
    framing: {
      calls: number;
      system_chars: number;
      user_median: number;
      user_mean: number;
      total_chars: number;
      system_share: number;
      max_tokens: number;
    };
    contrast: {
      calls: number;
      system_chars: number;
      user_median: number;
      user_mean: number;
      total_chars: number;
      system_share: number;
      max_tokens: number;
      lead_chars: number;
      versions: { versions: number; events: number }[];
    };
    system_chars_total: number;
    system_tokens: number;
    system_share_of_prompt: number;
    framing_share: number;
  };
  truncation: {
    lead_chars: number;
    versions: number;
    median_chars: number;
    over_cap: number;
    sent_chars: number;
    dropped_chars: number;
    dropped_tokens: number;
    dropped_usd: number;
    would_be_prompt_tokens: number;
    median_share_sent: number;
  };
  split: EconomySplit[];
  per_unit: { label_he: string; n: number; usd: number }[];
  cache: {
    entries: number;
    framing: number;
    contrast: number;
    showtime_calls: number;
    showcases: number;
    calls_per_loop: number;
    loop_usd: number;
    show_hours: number;
    loop_minutes: number;
    loops: number;
    day_usd: number;
    day_calls: number;
  };
  strawman: {
    articles: number;
    article_chars: number;
    comments: number;
    comment_chars: number;
    calls: number;
    system_chars: number;
    system_share: number;
    prompt_tokens: number;
    completion_tokens: number;
    per_call_completion: number;
    usd: number;
    ratio: number;
    days: number;
    month_usd: number;
    agents_month_usd: number;
    scene: {
      articles: number;
      prompt_per_article: number;
      completion_per_article: number;
      usd: number;
    };
  };
  excluded: EconomyExcluded[];
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
  audience: AudienceFacts;
  stats: StatsFacts;
  economy: EconomyFacts;
  repair: RepairFacts;
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
