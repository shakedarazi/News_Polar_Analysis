import type {
  AiSummary,
  AlertsResponse,
  ArticleBias,
  ArticleDetail,
  ArticleFraming,
  ArticlesResponse,
  AskResponse,
  AskTurn,
  CategoryStat,
  DashboardFilters,
  DashboardStats,
  EventDeviation,
  EventDeviationProfile,
  EventDetail,
  EventSummary,
  PolarityTrendPoint,
  SourcePolarityBreakdown,
  SourceStat,
  TrendingTopic,
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

async function postJson<T>(path: string, body: unknown, timeoutMs = 45_000): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    if (err instanceof Error && (err.name === "TimeoutError" || err.name === "AbortError")) {
      throw new Error("הבקשה לקחה יותר מדי זמן. נסו שוב בעוד רגע.");
    }
    throw err;
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function patchJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: "PATCH" });
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
  q?: string;
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
  if (params.q) qs.set("q", params.q);
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

export function askAssistant(question: string, history: AskTurn[] = []) {
  // Relative path -> same-origin Next.js route (frontend/src/app/api/ask/route.ts),
  // which proxies server-side to the Python API. Avoids CORS entirely.
  //
  // The conversation is held here and sent with each question. The API is
  // stateless and its host spins down when idle, so a server-side session
  // store would be the only part of it that had to survive that.
  return postJson<AskResponse>("/api/ask", { question, history });
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

export function getArticleFramingClient(id: string) {
  return getJson<ArticleFraming>(`/api/articles/${id}/framing`);
}

export function generateArticleFramingClient(id: string) {
  return postJson<ArticleFraming>(`/api/articles/${id}/framing/generate`, {});
}

export function getEventDeviationProfile(metric = "audience_mean", category?: string) {
  const qs = new URLSearchParams({ metric });
  if (category) qs.set("category", category);
  return fetchApi<EventDeviationProfile>(`/api/analytics/event-deviation?${qs}`);
}

export function getEventDeviation(eventId: string, metric = "audience_mean") {
  return fetchApi<EventDeviation>(
    `/api/events/${eventId}/deviation?metric=${encodeURIComponent(metric)}`,
  );
}

export function getTrendingClient() {
  return getJson<TrendingTopic[]>("/api/trending");
}

export function getEvents(params: {
  category?: string;
  source?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.source) qs.set("source", params.source);
  if (params.start_date) qs.set("start_date", params.start_date);
  if (params.end_date) qs.set("end_date", params.end_date);
  qs.set("limit", String(params.limit ?? 20));
  return fetchApi<EventSummary[]>(`/api/events?${qs}`);
}

export function getEventDetail(eventId: string) {
  return fetchApi<EventDetail>(`/api/events/${eventId}/timeline`);
}

export function getAlertsClient(params: { alert_type?: string; severity?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.alert_type) qs.set("alert_type", params.alert_type);
  if (params.severity) qs.set("severity", params.severity);
  const suffix = qs.toString() ? `?${qs}` : "";
  return getJson<AlertsResponse>(`/api/alerts${suffix}`);
}

export function markAlertReadClient(alertId: string) {
  return patchJson<{ status: string; unread_count: number }>(`/api/alerts/${alertId}/read`);
}

export function markAllAlertsReadClient() {
  return patchJson<{ status: string; unread_count: number }>("/api/alerts/read-all");
}
