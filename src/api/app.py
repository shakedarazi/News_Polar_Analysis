"""Read-only HTTP API and simple browse UI."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.db.browse import (
    count_articles,
    get_article_detail,
    get_dashboard_stats,
    list_articles,
    list_categories,
    list_sources,
)
from src.db.config import require_database_url
from src.db.migrations import apply_migrations

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
    allow_methods=["GET"],
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
def api_stats() -> dict:
    return get_dashboard_stats()


@app.get("/api/sources")
def api_sources() -> list[dict]:
    return list_sources()


@app.get("/api/categories")
def api_categories() -> list[dict]:
    return list_categories()


@app.get("/api/articles")
def api_articles(
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    items = list_articles(
        source=source,
        category=category,
        min_audience_mean=min_audience_mean,
        limit=limit,
        offset=offset,
    )
    total = count_articles(
        source=source,
        category=category,
        min_audience_mean=min_audience_mean,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


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
