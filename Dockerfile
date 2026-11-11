FROM node:22-bookworm-slim AS ui
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/ ./backend/
RUN pip install --no-cache-dir -r backend/requirements.lock && pip install --no-deps -e backend
COPY fixtures/ ./fixtures/
COPY --from=ui /build/dist ./frontend/dist
RUN useradd --create-home copilot && mkdir -p /app/data && chown -R copilot:copilot /app
USER copilot
ENV DATABASE_PATH=/app/data/copilot.sqlite3
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
