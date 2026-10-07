# Portfolio Terminal: one container, FastAPI serving the API and the built React app.

# --- build the frontend -------------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Supabase URL + publishable key are baked into the bundle (they're public by design).
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
RUN npm run build

# --- backend ------------------------------------------------------------------
FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app backend/app
# The analysis parser and ingest write path live at the repo root (shared with Streamlit).
COPY markdown_to_json.py analysis_db.py ./
COPY --from=web /web/dist frontend/dist
ENV PYTHONUNBUFFERED=1
# Render sets $PORT; 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
