# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    --mount=type=secret,id=npm_token,env=NPM_REMOTE_TOKEN \
    npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime
FROM python:3.13-slim
WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy backend and install
COPY backend/ ./
RUN uv pip install --system --no-cache .

# Copy built frontend + root index.html
COPY --from=frontend /app/dist /app/static
COPY --from=frontend /app/index.html /app/static/index.html

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
