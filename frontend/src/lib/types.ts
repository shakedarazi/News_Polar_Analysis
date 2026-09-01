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
  // Null until the polarization pass has run for this article — "not measured",
  // which is not the same as measured and found to be zero.
  audience_issue_mean: number | null;
  audience_affective_mean: number | null;
  audience_issue_p85: number | null;
  audience_affective_p85: number | null;
  polarization_lexicon_version: string | null;
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
  /** How many of the analyzed articles carry the research-lexicon reading. */
  polarization_count: number;
  avg_issue: number | null;
  avg_affective: number | null;
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
