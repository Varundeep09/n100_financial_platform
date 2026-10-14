"""FastAPI REST Service Layer (Module 11 / Sprint 6).

Production REST API providing programmatic access to 92 Nifty 100 constituent
fundamentals, financial ratio models, multi-parameter screener engine,
sector benchmarks, and institutional report downloads.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("n100_api")

# Determine repository root and database path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "nifty100.db"
START_TIME = time.time()

app = FastAPI(
    title="N100 Financial Intelligence Platform API",
    description=(
        "Production-grade RESTful service exposing 16 endpoints for institutional "
        "fundamental intelligence, ratio analytics, screener filtering, and reporting "
        "across the Nifty 100 universe."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for Streamlit frontend and local analytics consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_path() -> Path:
    """Resolve the SQLite database path from environment or default locations."""
    env_path = os.getenv("DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    candidates = [
        DEFAULT_DB_PATH,
        Path("db/nifty100.db"),
        Path("../db/nifty100.db"),
        REPO_ROOT / "db" / "nifty100.db",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()

    return DEFAULT_DB_PATH


def query_db_table_counts(db_path: Path) -> dict[str, int]:
    """Query row counts for all tables in the SQLite database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found at: {db_path}")

    counts: dict[str, int] = {}
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        tables = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name;"
            ).fetchall()
        ]
        for tbl in tables:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            counts[tbl] = cnt
    finally:
        conn.close()

    return counts


@app.get(
    "/",
    tags=["Root"],
    summary="API Root Information",
    description="Returns platform metadata, versioning, and link to interactive documentation.",
)
def root_info() -> dict[str, Any]:
    """Root info endpoint returning basic metadata."""
    return {
        "platform": "N100 Financial Intelligence Platform API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get(
    "/health",
    tags=["Diagnostic"],
    summary="System Health & Database Verification",
    description="Returns service health status, server uptime, and row counts across all database tables.",
    status_code=status.HTTP_200_OK,
)
@app.get(
    "/api/v1/health",
    tags=["Diagnostic"],
    summary="System Health & Database Verification (v1)",
    description="Returns service health status, server uptime, and row counts across all database tables.",
    status_code=status.HTTP_200_OK,
)
def health_check() -> JSONResponse:
    """Diagnostic health check verifying DB connectivity and constituent table counts."""
    db_path = get_db_path()
    try:
        table_counts = query_db_table_counts(db_path)
        payload = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(time.time() - START_TIME, 2),
            "db_status": "connected",
            "db_path": str(db_path),
            "total_tables": len(table_counts),
            "db_row_counts": table_counts,
        }
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        err_payload = {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(time.time() - START_TIME, 2),
            "db_status": "error",
            "error_detail": str(exc),
            "db_row_counts": {},
        }
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=err_payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
