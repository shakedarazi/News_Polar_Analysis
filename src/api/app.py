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
from src.db.config import require_database_url
from src.db.migrations import apply_migrations
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


@app.get("/api/articles")
def api_articles(
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    items = list_articles(
        source=source,
        category=category,
        min_audience_mean=min_audience_mean,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    total = count_articles(
        source=source,
        category=category,
        min_audience_mean=min_audience_mean,
        start_date=start_date,
        end_date=end_date,
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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    index_path = ROOT / "web" / "index.html"
    if not index_path.is_file():
        return (
            "<h1>News Polar Analysis API</h1>"
            "<p>Legacy UI removed. Run the Next.js frontend: cd frontend && npm run dev</p>"
        )
    return index_path.read_text(encoding="utf-8")
