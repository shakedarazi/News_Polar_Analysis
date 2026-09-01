"""Read-only HTTP API and simple browse UI."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.db.browse import (
    count_articles,
    get_article_detail,
    get_dashboard_stats,
    get_polarity_by_source,
    get_polarity_trend,
    list_articles,
    list_categories,
    list_sources,
)
from src.db.alerts import count_unread, detect_and_save_alerts, list_alerts, mark_all_read, mark_read
from src.db.bias import generate_and_save_bias, get_article_for_bias, get_bias
from src.db.config import require_database_url
from src.db.event_stats import get_event_deviation, get_source_profiles
from src.db.events import get_event_detail, list_events
from src.db.framing import generate_and_save_framing, get_article_for_framing, get_framing
from src.db.migrations import apply_migrations
from src.db.summary import generate_and_save_summary, get_article_for_summary, get_summary
from src.db.trending import DEFAULT_LIMIT as TRENDING_DEFAULT_LIMIT
from src.db.trending import get_trending_topics
from src.nlp.qa import answer_question

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = ROOT / "web" / "static"

app = FastAPI(title="News Polar Analysis", version="1.0.0")

_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup() -> None:
    require_database_url()
    apply_migrations()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/stats")
def api_stats(
    source: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    return get_dashboard_stats(
        source=source,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/sources")
def api_sources() -> list[dict]:
    return list_sources()


@app.get("/api/categories")
def api_categories() -> list[dict]:
    return list_categories()


@app.get("/api/analytics/polarity-trend")
def api_polarity_trend(
    source: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    return get_polarity_trend(
        source=source,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/analytics/polarity-by-source")
def api_polarity_by_source(
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    return get_polarity_by_source(
        category=category,
        start_date=start_date,
        end_date=end_date,
    )


@app.get("/api/analytics/event-deviation")
def api_event_deviation(
    metric: str = Query("audience_mean"),
    category: str | None = None,
) -> dict:
    """Per-outlet deviation from the median of the same event.

    Deliberately a different endpoint from /polarity-by-source rather than more
    fields on it: that one answers "how charged is this outlet's output", this
    one answers "how charged is this outlet given the same story". Merging them
    would invite reading one number as the other.
    """
    try:
        return get_source_profiles(metric=metric, category=category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/events/{event_id}/deviation")
def api_event_deviation_detail(
    event_id: str,
    metric: str = Query("audience_mean"),
) -> dict:
    try:
        result = get_event_deviation(event_id, metric=metric)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@app.get("/api/articles")
def api_articles(
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    items = list_articles(
        source=source,
        category=category,
        min_audience_mean=min_audience_mean,
        start_date=start_date,
        end_date=end_date,
        q=q,
        limit=limit,
        offset=offset,
    )
    total = count_articles(
        source=source,
        category=category,
        min_audience_mean=min_audience_mean,
        start_date=start_date,
        end_date=end_date,
        q=q,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


class AskRequest(BaseModel):
    question: str


@app.post("/api/ai/ask")
def api_ai_ask(body: AskRequest) -> dict:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty")
    try:
        result = answer_question(question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # OpenAI/network errors
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}") from exc
    return {"answer": result.answer, "sources": result.sources}


@app.get("/api/articles/{article_id}")
def api_article_detail(article_id: str) -> dict:
    article = get_article_detail(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.get("/api/articles/{article_id}/summary")
def api_get_article_summary(article_id: str) -> dict:
    if get_article_for_summary(article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")
    summary = get_summary(article_id)
    if summary is None:
        return {"status": "missing"}
    return {"status": "ready", **summary}


@app.post("/api/articles/{article_id}/summary/generate")
def api_generate_article_summary(article_id: str) -> dict:
    try:
        summary = generate_and_save_summary(article_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # OpenAI/network/parsing errors
        raise HTTPException(status_code=502, detail=f"AI summary failed: {exc}") from exc
    return {"status": "ready", **summary}


@app.get("/api/trending")
def api_trending(limit: int = Query(default=TRENDING_DEFAULT_LIMIT, ge=1, le=12)) -> list[dict]:
    return get_trending_topics(limit=limit)


@app.get("/api/events")
def api_events(
    category: str | None = None,
    source: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    return list_events(
        category=category,
        source=source,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@app.get("/api/events/{event_id}/timeline")
def api_event_timeline(event_id: str) -> dict:
    event = get_event_detail(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _bias_response(bias: dict) -> dict:
    if bias["applicable"]:
        return {"status": "ready", **bias}
    return {"status": "not_applicable", **bias}


@app.get("/api/articles/{article_id}/bias")
def api_get_article_bias(article_id: str) -> dict:
    if get_article_for_bias(article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")
    bias = get_bias(article_id)
    if bias is None:
        return {"status": "missing"}
    return _bias_response(bias)


@app.post("/api/articles/{article_id}/bias/generate")
def api_generate_article_bias(article_id: str) -> dict:
    try:
        bias = generate_and_save_bias(article_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # OpenAI/network/parsing errors
        raise HTTPException(status_code=502, detail=f"AI bias analysis failed: {exc}") from exc
    return _bias_response(bias)


@app.get("/api/articles/{article_id}/framing")
def api_get_article_framing(article_id: str) -> dict:
    if get_article_for_framing(article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")
    framing = get_framing(article_id)
    if framing is None:
        return {"status": "missing"}
    return {"status": "ready", **framing}


@app.post("/api/articles/{article_id}/framing/generate")
def api_generate_article_framing(article_id: str) -> dict:
    try:
        framing = generate_and_save_framing(article_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # OpenAI/network/parsing errors
        raise HTTPException(status_code=502, detail=f"AI framing analysis failed: {exc}") from exc
    return {"status": "ready", **framing}


@app.get("/api/alerts")
def api_alerts(
    alert_type: str | None = None,
    severity: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    detect_and_save_alerts()
    return {
        "items": list_alerts(alert_type=alert_type, severity=severity, limit=limit),
        "unread_count": count_unread(),
    }


@app.patch("/api/alerts/{alert_id}/read")
def api_mark_alert_read(alert_id: str) -> dict:
    if not mark_read(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "ok", "unread_count": count_unread()}


@app.patch("/api/alerts/read-all")
def api_mark_all_alerts_read() -> dict:
    mark_all_read()
    return {"status": "ok", "unread_count": count_unread()}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    index_path = ROOT / "web" / "index.html"
    if not index_path.is_file():
        return (
            "<h1>News Polar Analysis API</h1>"
            "<p>Legacy UI removed. Run the Next.js frontend: cd frontend && npm run dev</p>"
        )
    return index_path.read_text(encoding="utf-8")
