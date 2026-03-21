# Deployment — Azure Container Apps

## Overview

Single Docker container on **Azure Container Apps**. FastAPI serves API/WebSocket + pre-built frontend static files.

```
Internet  →  Azure Container Apps  →  Single container
                                        ├── FastAPI (API + WebSocket)
                                        └── Static files (Vite build output)
```

## Live URL

https://party-games.kindbay-3e682a74.westus3.azurecontainerapps.io

## Azure Resources

| Resource | Name | Resource Group | Location |
|---|---|---|---|
| Shared ACR | edirgashared.azurecr.io | sharedACR-RG | westus3 |
| Resource Group | party-games-rg | — | westus3 |
| Container Apps Env | party-games-env | party-games-rg | westus3 |
| Container App | party-games | party-games-rg | westus3 |
| Managed Identity | party-games-identity | party-games-rg | westus3 |

The managed identity has `AcrPull` on the shared ACR.

## Deploy (build & push)

### Standard flow (no corporate proxy)

```bash
# 1. Login to ACR
az acr login --name edirgashared

# 2. Build for amd64 (Azure requires linux/amd64)
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 \
  --secret id=npmrc,src=$HOME/.npmrc \
  --secret id=npm_token,env=NPM_REMOTE_TOKEN \
  -t edirgashared.azurecr.io/party-games:latest .

# 3. Push
docker push edirgashared.azurecr.io/party-games:latest

# 4. Update container app
az containerapp update \
  --name party-games \
  --resource-group party-games-rg \
  --image edirgashared.azurecr.io/party-games:latest
```

### With Zscaler / corporate SSL proxy

If `az acr login` fails with SSL errors, it's because Docker Desktop's Linux VM
doesn't trust the Zscaler root CA that's intercepting HTTPS traffic. Two fixes needed:

**1. Add the registry as insecure in `~/.docker/daemon.json`:**

```json
{
  "insecure-registries": ["edirgashared.azurecr.io"]
}
```

Restart Docker Desktop after changing this.

**2. Login via manual token exchange (bypasses `az acr login`):**

```bash
# Get Azure AD token, exchange for ACR refresh token, login Docker
ACCESS_TOKEN=$(az account get-access-token --query accessToken -o tsv)
REFRESH_TOKEN=$(curl -s "https://edirgashared.azurecr.io/oauth2/exchange" \
  -d "grant_type=access_token&service=edirgashared.azurecr.io&access_token=$ACCESS_TOKEN" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['refresh_token'])")
docker login edirgashared.azurecr.io \
  -u 00000000-0000-0000-0000-000000000000 \
  -p "$REFRESH_TOKEN"
```

Then proceed with steps 2-4 from the standard flow above.

## Docker Image

Multi-stage build. The `npm ci` step uses a BuildKit secret to mount `~/.npmrc`
(corporate artifactory auth) without baking it into the image.

See `Dockerfile` at the repo root.

## Static File Serving

Implemented in `main.py`:

- Middleware strips game prefixes from API paths (`/murder-mystery/api/mm/...` → `/api/mm/...`),
  matching what Vite's dev proxy does
- SPA fallback: each game path serves its HTML entry point
- `/assets/*` serves Vite build output (JS, CSS)
- `/` serves `index.html` (main menu)

## Configuration

| Variable | Purpose | Example |
|---|---|---|
| `CORS_ORIGINS` | Extra allowed CORS origins (comma-separated) | `https://games.yourdomain.com` |

Localhost origins are always included. State is in-memory — no database needed.

## Scaling Constraints

- **Max replicas: 1** — state is in-memory, multiple replicas would have separate game rooms
- **Scale to zero** — app shuts down when idle; in-progress games are lost (acceptable for short-lived party games)
- **If persistence is ever needed** — add Redis for game state and bump `max-replicas`

## Cost Estimate

| Resource | Estimated Cost |
|---|---|
| Container Apps (mostly scaled to zero) | ~$0/month |
| Container Registry (Basic, shared) | ~$5/month (shared across projects) |
| **Total** | **~$0-5/month** |
