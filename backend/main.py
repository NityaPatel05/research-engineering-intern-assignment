"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log"),
    ],
)

logger = logging.getLogger(__name__)

# Suppress ChromaDB's broken PostHog telemetry logging
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

import math
import json

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from datetime import datetime


def sanitize_floats(obj):
    """Recursively walk a dict/list structure and replace any NaN/Inf float with 0."""
    if isinstance(obj, float):
        return 0.0 if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_floats(v) for v in obj]
    return obj


class SafeJSONResponse(JSONResponse):
    """JSONResponse that sanitizes NaN/Inf before serializing."""
    def render(self, content) -> bytes:
        cleaned = sanitize_floats(content)
        return json.dumps(cleaned, allow_nan=False).encode("utf-8")


from config import CORS_ORIGINS, DATA_PATH
from modules.ingestion.loader import load_data
from modules.ingestion.cleaner import clean_data
from modules.ingestion.profiler import profile_data

app_data = {
    "df": pl.DataFrame(),
    "bad_rows": [],
    "profile": {}
}