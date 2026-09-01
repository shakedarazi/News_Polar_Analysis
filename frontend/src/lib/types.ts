export type BiasLabel = "שמאל" | "מרכז" | "ימין";

export type ArticleSummary = {
  article_id: string;
  source: string;
  title: string | null;
  canonical_url: string;
  primary_category: string | null;
  category_confidence: number | null;
  first_seen_at: string;
  analyzed_at: string | null;
  num_comments: number | null;
  audience_mean: number | null;
  audience_p85: number | null;
  controversy_mean: number | null;
  // The research lexicon's two axes (docs/adr/0004). A second reading of the
  // same comments against a different word list — never summed with the above.
  audience_issue_mean: number | null;
  audience_affective_mean: number | null;
  bias_label: BiasLabel | null;
  bias_score: number | null;
  bias_confidence: number | null;
};

export type ArticlesResponse = {
  items: ArticleSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type Aggregation = {
  num_comments: number;
  audience_mean: number | null;
  audience_p85: number | null;
  controversy_mean: number | null;
  controversy_p85: number | null;
  sum_engagement_weight: number;
  analyzed_at: string;
  // Optional, not just nullable, and the distinction matters. Null means the
  // polarization pass has not run for this article - "not measured", which is
  // not the same as measured and found to be zero. Undefined means the backend
  // answering is old enough not to have the column at all: the frontend deploys
  // from Vercel and the API from Render, so between the two there is a window
  // where a new page talks to an old API. Marked optional so the compiler makes
  // every reader handle that window instead of printing NaN through it.
  audience_issue_mean?: number | null;
  audience_affective_mean?: number | null;
  audience_issue_p85?: number | null;
  audience_affective_p85?: number | null;
  polarization_lexicon_version?: string | null;
};

export type WindowFeature = {
  sentence_idx: number;
  window_len: number;
  c1: number;
  c2: number;
  c3: number;
  c4: number;
  c5: number;
  c6: number;
  c7: number;
  active: number;
  dominance: number | null;
};

export type CommentItem = {
  comment_id: string;
  text: string;
  author: string | null;
  like_count: number;
  polar_ratio: number | null;
  comment_score: number | null;
  controversy: number | null;
};

export type ArticleDetail = {
  article_id: string;
  source: string;
  title: string | null;
  text: string;
  canonical_url: string;
  primary_category: string | null;
  category_confidence: number | null;
  category_rationale: string | null;
  first_seen_at: string;
  analyzed_at: string | null;
  comments_fetched_at: string | null;
  aggregation: Aggregation | null;
  windows: WindowFeature[];
  comments: CommentItem[];
  /** The event this article belongs to, or null when it stands alone.
   * Optional because Vercel and Render deploy independently: an API older
   * than this field omits the key entirely. */
  event?: ArticleEventLink | null;
};

export type ArticleEventLink = {
  event_id: string;
  title: string | null;
  article_count: number;
  source_count: number;
};

export type LeadingArticle = {
  article_id: string;
  source: string;
  title: string | null;
  primary_category: string | null;
  first_seen_at: string;
  canonical_url: string;
  snippet: string | null;
  audience_mean: number | null;
  audience_p85: number | null;
  num_comments: number | null;
  bias_label: BiasLabel | null;
  bias_score: number | null;
  bias_confidence: number | null;
};

export type DateRange = { min: string | null; max: string | null };

export type DashboardStats = {
  total_articles: number;
  total_comments: number;
  avg_audience_mean: number | null;
  top_source: string | null;
  by_source: {
    source: string;
    article_count: number;
    analyzed_count: number;
    avg_audience_mean: number | null;
  }[];
  by_category: { category: string; article_count: number; avg_audience_mean: number | null }[];
  active_events_count: number;
  hottest_articles: LeadingArticle[];
  date_range: DateRange;
};

export type SourceStat = { source: string; article_count: number };
export type CategoryStat = { category: string; article_count: number };

export type PolarityTrendPoint = {
  date: string;
  avg_polarity: number | null;
  article_count: number;
};

export type SourcePolarityBreakdown = {
  source: string;
  article_count: number;
  analyzed_count: number;
  high_count: number;
  mid_count: number;
  low_count: number;
  avg_polarity: number | null;
  /**
   * How many of the analyzed articles carry the research-lexicon reading.
   * Optional for the same reason as Aggregation's polarization fields: an
   * older API omits these keys entirely, not merely sets them null.
   */
  polarization_count?: number;
  avg_issue?: number | null;
  avg_affective?: number | null;
};

export type DashboardFilters = {
  source?: string;
  category?: string;
  start_date?: string;
  end_date?: string;
};

export type QaSourceArticle = {
  article_id: string;
  source: string;
  title: string | null;
  primary_category: string | null;
  first_seen_at: string;
  snippet: string | null;
  audience_mean: number | null;
  audience_p85: number | null;
  num_comments: number | null;
};

export type AskResponse = {
  answer: string;
  sources: QaSourceArticle[];
};

export type AiSummaryStatus = "missing" | "ready";

export type AiSummary = {
  status: AiSummaryStatus;
  summary?: string;
  key_points?: string[];
  topic?: string | null;
  entities?: string[];
  sentiment?: string | null;
  model?: string | null;
  generated_at?: string | null;
};

export type ArticleBiasStatus = "missing" | "ready" | "not_applicable";

export type ArticleBias = {
  status: ArticleBiasStatus;
  applicable?: boolean;
  label?: BiasLabel | null;
  score?: number | null;
  confidence?: number | null;
  rationale?: string | null;
  model?: string | null;
  generated_at?: string | null;
};

export type TrendDirection = "up" | "down" | "flat" | "new";

export type TrendingItemType = "event" | "entity";

export type SparklinePoint = { date: string; count: number };

export type TrendingTopic = {
  rank: number;
  item_type: TrendingItemType;
  name: string;
  event_id: string | null;
  href: string;
  current_count: number;
  previous_count: number;
  unique_sources: number;
  growth_pct: number | null;
  direction: TrendDirection;
  sparkline: SparklinePoint[];
};

export type EventSummary = {
  event_id: string;
  title: string | null;
  primary_category: string | null;
  article_count: number;
  source_count: number;
  sources: string[];
  first_seen_at: string;
  last_seen_at: string;
};

export type EventTimelineItem = {
  article_id: string;
  source: string;
  title: string | null;
  canonical_url: string;
  primary_category: string | null;
  first_seen_at: string;
  summary_sentiment: string | null;
  bias_label: BiasLabel | null;
  bias_score: number | null;
  bias_confidence: number | null;
  snippet: string | null;
  audience_mean: number | null;
  status_label: string;
};

export type AlertType =
  | "topic_spike"
  | "source_activity"
  | "sentiment_shift"
  | "event_polarization"
  | "new_event";

export type AlertSeverity = "low" | "medium" | "high";

export type AlertItem = {
  alert_id: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  related_article_id: string | null;
  related_event_id: string | null;
  related_topic: string | null;
  related_source: string | null;
  link_path: string | null;
  is_read: boolean;
  created_at: string;
};

export type AlertsResponse = {
  items: AlertItem[];
  unread_count: number;
};

export type EventDetail = {
  event_id: string;
  title: string | null;
  primary_category: string | null;
  article_count: number;
  source_count: number;
  first_seen_at: string;
  last_seen_at: string;
  dominant_sentiment: string | null;
  bias_distribution: Record<string, number> | null;
  avg_audience_mean: number | null;
  timeline: EventTimelineItem[];
};

export type ArticleFramingStatus = "missing" | "ready";

/** Structural framing variables, already verified server-side: everything in
 * `loaded_terms` occurs in the text the model was shown. `dropped_terms` is
 * what the verifier rejected — evidence the check ran, not an error log.
 * Fields are optional because an API deployed before this feature omits the
 * keys entirely, and Vercel and Render deploy independently. */
export type ArticleFraming = {
  status: ArticleFramingStatus;
  actor?: string | null;
  rejected_actor?: string | null;
  responsibility?: string | null;
  loaded_terms?: string[];
  dropped_terms?: string[];
  voice?: "active" | "passive" | null;
  lead_perspective?: string | null;
  model?: string | null;
  generated_at?: string | null;
};

/** One outlet's distance from the median of the same event, over many events.
 * Both intervals come from the same bootstrap; `significant_adjusted` is the
 * Bonferroni-corrected one and the only field that should be read as a claim. */
export type SourceDeviation = {
  source: string;
  events: number;
  mean_deviation: number;
  ci_low: number | null;
  ci_high: number | null;
  significant: boolean;
  ci_low_adjusted: number | null;
  ci_high_adjusted: number | null;
  significant_adjusted: boolean;
};

export type EventDeviationProfile = {
  metric: string;
  sources: SourceDeviation[];
  events_used: number;
  events_considered: number;
  pair_events: number;
  pair_share: number | null;
  tests_run: number;
  min_observations: number;
};

export type EventVersionDeviation = {
  article_id: string;
  source: string;
  value: number;
  deviation: number;
  num_comments: number;
};

export type EventDeviation = {
  event_id: string;
  metric: string;
  median: number | null;
  comparable: boolean;
  versions: EventVersionDeviation[];
};
