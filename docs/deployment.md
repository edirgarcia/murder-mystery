# Deployment Plan — Azure Container Apps

## Overview

Deploy the entire platform as a single Docker container on **Azure Container Apps**. FastAPI serves both the API/WebSocket endpoints and the pre-built frontend static files.

```
Internet  →  Azure Container Apps  →  Single container
                                        ├── FastAPI (API + WebSocket)
                                        └── Static files (Vite build output)
```

## Why Azure Container Apps

- **WebSocket support** — required for real-time game updates
- **Scale to zero** — no cost when nobody is playing
- **Free tier** — 2M requests/month, 180k vCPU-seconds, 360k GiB-seconds
- **Built-in HTTPS** — free managed TLS certificates
- **Custom domains** — supported on the free tier
- **Simple** — no Kubernetes knowledge needed

## Docker Image

Multi-stage build: Node builds the frontend, Python runs everything.

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime
FROM python:3.13-slim
WORKDIR /app
COPY backend/ ./
RUN pip install --no-cache-dir .
COPY --from=frontend /app/dist /app/static
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Static File Serving

Add a `StaticFiles` mount and SPA fallback to `main.py` so FastAPI serves the frontend:

- Mount `/static` → built Vite output at `/app/static`
- For each game, serve its HTML entry point as a catch-all for client-side routes:
  - `/murder-mystery/*` → `static/murder-mystery.html`
  - `/funny-questions/*` → `static/funny-questions.html`
  - `/werewolf/*` → `static/werewolf.html`
  - `/prisoners-dilemma/*` → `static/prisoners-dilemma.html`
- Root `/` → `static/index.html` (main menu)

The Vite build output structure (from `rollupOptions.input`) already produces separate HTML files per game, so no changes to the frontend build are needed.

## Azure Resources

Minimal set of Azure resources required:

1. **Resource Group** — logical container for everything
2. **Container Apps Environment** — networking/logging layer
3. **Container App** — the actual running app
4. **Azure Container Registry (ACR)** — stores the Docker image

## Deployment Steps

### One-time setup

```bash
# 1. Create resource group
az group create --name party-games-rg --location eastus

# 2. Create container registry
az acr create --name partygamesacr --resource-group party-games-rg --sku Basic

# 3. Create Container Apps environment
az containerapp env create \
  --name party-games-env \
  --resource-group party-games-rg \
  --location eastus

# 4. Build and push image
az acr build --registry partygamesacr --image party-games:latest .

# 5. Deploy container app
az containerapp create \
  --name party-games \
  --resource-group party-games-rg \
  --environment party-games-env \
  --image partygamesacr.azurecr.io/party-games:latest \
  --registry-server partygamesacr.azurecr.io \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 0.25 \
  --memory 0.5Gi
```

### Subsequent deploys

```bash
# Build new image and update
az acr build --registry partygamesacr --image party-games:latest .
az containerapp update \
  --name party-games \
  --resource-group party-games-rg \
  --image partygamesacr.azurecr.io/party-games:latest
```

### Custom domain (optional)

```bash
az containerapp hostname add \
  --name party-games \
  --resource-group party-games-rg \
  --hostname games.yourdomain.com

# Then add CNAME in your DNS provider and bind the certificate
az containerapp hostname bind \
  --name party-games \
  --resource-group party-games-rg \
  --hostname games.yourdomain.com \
  --environment party-games-env \
  --validation-method CNAME
```

## Configuration

Environment variables to set on the container app:

| Variable | Purpose | Example |
|---|---|---|
| `CORS_ORIGINS` | Allowed origins for CORS | `https://games.yourdomain.com` |

Since state is in-memory and games are ephemeral, no database or Redis config is needed.

## Scaling Constraints

- **Max replicas: 1** — state is in-memory, so only one instance can exist. Multiple replicas would each have separate game rooms with no way to sync.
- **Scale to zero** — when idle, the app shuts down. Any in-progress games are lost, which is acceptable since games last minutes, not hours.
- **If persistence is ever needed** — add Redis for game state and bump `max-replicas` above 1.

## Cost Estimate

For a party game with sporadic use (a few sessions per week):

| Resource | Estimated Cost |
|---|---|
| Container Apps (mostly scaled to zero) | ~$0/month |
| Container Registry (Basic tier) | ~$5/month |
| **Total** | **~$5/month** |

The ACR Basic tier is the only fixed cost. Container Apps consumption is effectively free for low-traffic hobby projects.

## Implementation Checklist

When ready to implement:

- [ ] Create `Dockerfile` at the repo root
- [ ] Add static file serving + SPA fallback routes to `main.py`
- [ ] Update `CORS_ORIGINS` to accept the production domain
- [ ] Create Azure resources (resource group, ACR, environment, container app)
- [ ] Build and deploy the first image
- [ ] (Optional) Configure custom domain and DNS
