import type {
  AiSummary,
  ArticleBias,
  ArticleDetail,
  ArticlesResponse,
  AskResponse,
  CategoryStat,
  DashboardFilters,
  DashboardStats,
  PolarityTrendPoint,
  SourcePolarityBreakdown,
  SourceStat,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 30 } });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function filtersToQuery(filters: DashboardFilters): URLSearchParams {
  const qs = new URLSearchParams();
  if (filters.source) qs.set("source", filters.source);
  if (filters.category) qs.set("category", filters.category);
  if (filters.start_date) qs.set("start_date", filters.start_date);
  if (filters.end_date) qs.set("end_date", filters.end_date);
  return qs;
}

export function getStats(filters: DashboardFilters = {}) {
  const qs = filtersToQuery(filters);
  const suffix = qs.toString() ? `?${qs}` : "";
  return fetchApi<DashboardStats>(`/api/stats${suffix}`);
}

export function getPolarityTrend(filters: DashboardFilters = {}) {
  const qs = filtersToQuery(filters);
  const suffix = qs.toString() ? `?${qs}` : "";
  return fetchApi<PolarityTrendPoint[]>(`/api/analytics/polarity-trend${suffix}`);
}

export function getPolarityBySource(filters: Omit<DashboardFilters, "source"> = {}) {
  const qs = filtersToQuery(filters);
  const suffix = qs.toString() ? `?${qs}` : "";
  return fetchApi<SourcePolarityBreakdown[]>(`/api/analytics/polarity-by-source${suffix}`);
}

export function getSources() {
  return fetchApi<SourceStat[]>("/api/sources");
}

export function getCategories() {
  return fetchApi<CategoryStat[]>("/api/categories");
}

export function getArticles(params: {
  source?: string;
  category?: string;
  min_audience_mean?: number;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const qs = new URLSearchParams();
  if (params.source) qs.set("source", params.source);
  if (params.category) qs.set("category", params.category);
  if (params.min_audience_mean !== undefined) {
    qs.set("min_audience_mean", String(params.min_audience_mean));
  }
  if (params.start_date) qs.set("start_date", params.start_date);
  if (params.end_date) qs.set("end_date", params.end_date);
  qs.set("limit", String(params.limit ?? 50));
  qs.set("offset", String(params.offset ?? 0));
  return fetchApi<ArticlesResponse>(`/api/articles?${qs}`);
}

export function getArticle(id: string) {
  return fetchApi<ArticleDetail>(`/api/articles/${id}`);
}

export function getArticleClient(id: string) {
  // Relative path -> same-origin Next.js proxy route, for client components
  // (e.g. the quick-view modal) that can't use server-side fetch.
  return getJson<ArticleDetail>(`/api/articles/${id}`);
}

export function askAssistant(question: string) {
  // Relative path -> same-origin Next.js route (frontend/src/app/api/ask/route.ts),
  // which proxies server-side to the Python API. Avoids CORS entirely.
  return postJson<AskResponse>("/api/ask", { question });
}

export function getArticleSummaryClient(id: string) {
  return getJson<AiSummary>(`/api/articles/${id}/summary`);
}

export function generateArticleSummaryClient(id: string) {
  return postJson<AiSummary>(`/api/articles/${id}/summary/generate`, {});
}

export function getArticleBiasClient(id: string) {
  return getJson<ArticleBias>(`/api/articles/${id}/bias`);
}

export function generateArticleBiasClient(id: string) {
  return postJson<ArticleBias>(`/api/articles/${id}/bias/generate`, {});
}
