"""Application configuration loaded from environment variables."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Resolve the project root (parent of the backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the project root instead of just the current working directory
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Paths (Use absolute paths based on root directory for local runs, override with env in Docker)
DATA_PATH = os.getenv("DATA_PATH", str(BASE_DIR / "data" / "data.jsonl"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "chromadb"))
EMBEDDINGS_CACHE_PATH = os.getenv("EMBEDDINGS_CACHE_PATH", str(BASE_DIR / "data" / "embeddings_cache"))

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# App settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

logger.info("Configuration loaded from environment")
