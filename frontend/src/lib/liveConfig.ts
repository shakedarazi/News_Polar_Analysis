/**
 * Shared polling interval for the dashboard's live-update components
 * (LiveIndicator, TrendingWidget, NotificationBell). This system has no
 * WebSocket/SSE/pub-sub infrastructure (checked: FastAPI in src/api/app.py
 * is plain request/response, no background workers) — polling is the
 * documented fallback per the feature spec, kept to a single shared
 * constant instead of scattering intervals per component.
 *
 * 30s sits in the middle of the "20-60s" range called for — frequent enough
 * to feel live, far from aggressive polling.
 */
export const LIVE_POLL_INTERVAL_MS = 30_000;
