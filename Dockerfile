# Stage 1: Build frontend
FROM node:22-alpine AS frontend
WORKDIR /build
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci
COPY webapp/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY bot/ bot/
COPY api/ api/
COPY alembic/ alembic/
COPY alembic.ini ./

# Copy built frontend
COPY --from=frontend /build/dist/ webapp/dist/

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
