# ==========================================
# Stage 1: Build Frontend Assets (React + Vite)
# ==========================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app

# Copy dependency manifests and install
COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN npm ci || npm install

# Copy configuration and source files
COPY index.html vite.config.ts tsconfig.json ./
COPY src/ ./src/

# Compile static distribution bundle to /app/dist
RUN npm run build


# ==========================================
# Stage 2: Production Runtime (Python + FastAPI)
# ==========================================
FROM python:3.13-slim AS production
WORKDIR /app

# Install curl for container health check
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy compiled frontend from Stage 1
COPY --from=frontend-builder /app/dist /app/dist

# Copy backend application source code
COPY backend/ /app/backend/

# Ensure data directory exists for SQLite
RUN mkdir -p /app/backend/app/data

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    ENVIRONMENT=production

EXPOSE 8000

# Automated container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Launch production server supporting dynamic cloud host $PORT
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
