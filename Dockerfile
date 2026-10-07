# One image serves both the API and the built React app.
#
#   docker build -t rego \
#     --build-arg VITE_SUPABASE_URL=https://xxxx.supabase.co \
#     --build-arg VITE_SUPABASE_ANON_KEY=<anon key> .
#
# The two build arguments are the PUBLIC Supabase URL and anon key. They are baked
# into the browser bundle. Never pass a service key here.

# --- 1. Build the frontend ---------------------------------------------------------
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
# Same origin as the API, so a relative base and no CORS.
ENV VITE_API_BASE_URL=/api \
    VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
RUN npm run build

# --- 2. Install the Python dependencies ----------------------------------------------
FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install "poetry==2.3.2"
COPY pyproject.toml poetry.lock ./
# Runtime dependencies only: no dev tools, and not the optional `ct` group.
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# --- 3. Runtime -------------------------------------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src
COPY --from=web /web/dist ./frontend/dist

RUN useradd --create-home --uid 10001 rego \
    && mkdir -p /app/artifacts/models \
    && chown -R rego:rego /app/artifacts
USER rego

ENV ENVIRONMENT=production \
    FRONTEND_DIST=/app/frontend/dist \
    MODEL_ARTIFACT_DIR=/app/artifacts/models \
    PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health/' % os.environ.get('PORT','8000'), timeout=4)"

# Railway sets PORT.
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
