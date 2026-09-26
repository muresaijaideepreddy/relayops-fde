FROM node:24-alpine AS frontend
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@11.19.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 relayops \
    && mkdir -p /app/data && chown -R relayops:relayops /app
COPY --chown=relayops:relayops backend/ ./
COPY --from=frontend --chown=relayops:relayops /build/dist /app/frontend/dist
USER relayops
ENV DATABASE_URL=sqlite:////app/data/relayops.db
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
