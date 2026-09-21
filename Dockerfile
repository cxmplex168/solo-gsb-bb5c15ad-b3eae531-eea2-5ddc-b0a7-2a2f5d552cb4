FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/experiments.db \
    PORT=8000

WORKDIR /app

# Pre-copy and pre-install dependencies for better image-layer caching.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && mkdir -p /data

EXPOSE 8000
VOLUME ["/data"]

ENTRYPOINT ["/app/entrypoint.sh"]
