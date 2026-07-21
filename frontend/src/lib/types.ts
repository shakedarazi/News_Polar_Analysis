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
};

export type DateRange = { min: string | null; max: string | null };

export type DashboardStats = {
  total_articles: number;
  total_comments: number;
  avg_audience_mean: number | null;
  top_source: string | null;
  by_source: { source: string; article_count: number; avg_audience_mean: number | null }[];
  by_category: { category: string; article_count: number; avg_audience_mean: number | null }[];
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
  analyzed_count: number;
  high_count: number;
  mid_count: number;
  low_count: number;
  avg_polarity: number | null;
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
