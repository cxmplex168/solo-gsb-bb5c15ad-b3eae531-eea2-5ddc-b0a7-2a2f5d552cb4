#!/bin/sh
# Container startup hook:
# 1. install Python dependencies (idempotent when already baked into the image)
# 2. launch the API -- the application creates the SQLite tables on startup
set -e

echo "[entrypoint] Installing dependencies..."
pip install --no-cache-dir -r /app/requirements.txt

echo "[entrypoint] Starting API (tables are initialized on application startup)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
