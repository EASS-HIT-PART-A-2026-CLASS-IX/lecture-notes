# Azure Container Apps Deployment Playbook

This guide walks EX3 teams through deploying their Docker Compose stack (FastAPI API, Redis, nginx/frontends, and optional extras) to Azure Container Apps using the Azure for Students credit. Follow it end-to-end so graders can browse your project live without you incurring charges.

---

```mermaid
flowchart LR
    Local["Local Compose Stack"]
    Build["docker buildx\nlinux/amd64 images"]
    ACR["Azure Container Registry"]
    Release["docker-compose.release.yml"]
    ACAEnv["Container Apps Environment"]
    Apps["Container Apps\n(api / frontend / worker)"]
    Ingress["Ingress rules\n(frontend/api)"]
    Monitor["Log Analytics\n(telemetry)"]

    Local --> Build --> ACR
    Local --> Release --> ACAEnv
    ACR --> ACAEnv --> Apps --> Ingress
    Apps --> Monitor
```

## 1. Prerequisites

- Azure for Students account with active \$100 credit.
- CLI tools installed locally:
  - `az` (Azure CLI) logged in with `az login`.
  - `docker`, `docker compose`, and `docker buildx`.
- A Compose stack that runs locally: `docker compose up --build` succeeds.
- Each service has a Dockerfile and can be built for `linux/amd64`.
- No secrets committed to Git; use environment variables or Azure secrets instead.

---

## 2. Prepare a Release Compose File

1. Keep your development file (e.g. `docker-compose.yml`) as-is.
2. Create `docker-compose.deploy.yml` that replaces every `build:` block with an image reference (`<acr>.azurecr.io/service:tag`) and strips dev-only mounts.
3. Generate the final release file:

```bash
docker compose -f docker-compose.yml -f docker-compose.deploy.yml config \
  > docker-compose.release.yml
```

Only include published ports for services that must be reachable from a browser (typically the nginx or frontend gateway).

---

## 3. Define Azure Variables

Pick values once and reuse them. Keep them in a shell script or `.env` that you `source` locally (never commit real secrets).

```bash
export SUBSCRIPTION="<your-subscription-id>"
export LOCATION="westeurope"
export RESOURCE_GROUP="eass8-ex3-rg"
export ACR_NAME="eass8acr$RANDOM"    # must be unique, lowercase
export ENV_NAME="eass8-containerapps"
```

Update the subscription context:

```bash
az account set --subscription "$SUBSCRIPTION"
```

---

## 4. Provision Azure Infrastructure

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.ContainerRegistry

az group create -n "$RESOURCE_GROUP" -l "$LOCATION"

az acr create -n "$ACR_NAME" -g "$RESOURCE_GROUP" \
  --sku Basic --admin-enabled true
ACR_LOGIN_SERVER=$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" \
  --query loginServer -o tsv)

az monitor log-analytics workspace create \
  -g "$RESOURCE_GROUP" -n "${RESOURCE_GROUP}-log" -l "$LOCATION"
LAW_ID=$(az monitor log-analytics workspace show \
  -g "$RESOURCE_GROUP" -n "${RESOURCE_GROUP}-log" \
  --query customerId -o tsv)
LAW_KEY=$(az monitor log-analytics workspace get-shared-keys \
  -g "$RESOURCE_GROUP" -n "${RESOURCE_GROUP}-log" \
  --query primarySharedKey -o tsv)

az containerapp env create \
  -g "$RESOURCE_GROUP" -n "$ENV_NAME" -l "$LOCATION" \
  --logs-workspace-id "$LAW_ID" \
  --logs-workspace-key "$LAW_KEY"
```

---

## 5. Build and Push Images

Azure Container Apps currently runs on `linux/amd64`. If you are on Apple Silicon, force that platform.

```bash
docker buildx create --name eass8 --use || docker buildx use eass8

# Example for three services; adjust paths, tags, and Dockerfiles
docker buildx build --platform linux/amd64 \
  -t "$ACR_LOGIN_SERVER/api:1" \
  -f services/api/Dockerfile services/api --push

docker buildx build --platform linux/amd64 \
  -t "$ACR_LOGIN_SERVER/recommender:1" \
  -f services/recommender/Dockerfile services/recommender --push

docker buildx build --platform linux/amd64 \
  -t "$ACR_LOGIN_SERVER/frontend:1" \
  -f services/frontend/Dockerfile services/frontend --push
```

Update `docker-compose.deploy.yml` with the pushed image tags.

---

## 6. Install Compose Extension and Deploy

```bash
az extension add --name containerapp --upgrade
az extension add --name containerapp-compose --upgrade

ACR_USER=$(az acr credential show -n "$ACR_NAME" \
  --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR_NAME" \
  --query passwords[0].value -o tsv)

az containerapp compose create \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENV_NAME" \
  --location "$LOCATION" \
  --compose-file docker-compose.release.yml \
  --registry "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS"
```

Each Compose service becomes an individual Container App instance inside the shared environment.

---

## 7. Open Ingress and Set Secrets

Expose only the entrypoint you want graders to hit (usually `frontend` or `nginx`). Internal services communicate over the automatically created internal network.

```bash
# Example: expose frontend on port 80
az containerapp update \
  -g "$RESOURCE_GROUP" -n frontend \
  --ingress external --target-port 80 \
  --min-replicas 1 --max-replicas 2

# Optional: expose API directly for debugging
az containerapp update \
  -g "$RESOURCE_GROUP" -n api \
  --ingress external --target-port 8000 \
  --min-replicas 1 --max-replicas 2
```

Set secrets and environment variables without hardcoding them in the Compose file:

```bash
az containerapp secret set \
  -g "$RESOURCE_GROUP" -n api \
  --secrets db_url="postgresql://user:pass@host:5432/db"

az containerapp update \
  -g "$RESOURCE_GROUP" -n api \
  --set-env-vars DATABASE_URL=secretref:db_url
```

Repeat for any other sensitive values (JWT keys, API keys, etc.).

---

## 8. Wire the Frontend to the API

Fetch the public FQDNs:

```bash
FRONTEND_URL=$(az containerapp show \
  -g "$RESOURCE_GROUP" -n frontend \
  --query properties.configuration.ingress.fqdn -o tsv)
API_URL=$(az containerapp show \
  -g "$RESOURCE_GROUP" -n api \
  --query properties.configuration.ingress.fqdn -o tsv)
```

If the frontend needs the API URL, set it as an environment variable:

```bash
az containerapp update \
  -g "$RESOURCE_GROUP" -n frontend \
  --set-env-vars VITE_API_BASE="https://$API_URL"
```

Enable CORS in FastAPI for `https://$FRONTEND_URL`. If you do not want to touch code, route API calls through an nginx reverse proxy in the frontend container.

---

## 9. Validate the Deployment

1. Visit `https://$FRONTEND_URL` in a browser—ensure the UI loads and can call the API.
2. Run automated smoke tests from your CI or local machine pointing to the cloud URLs.
3. Inspect logs if something fails:

```bash
az containerapp logs show \
  -g "$RESOURCE_GROUP" -n api --follow
```

4. Screenshot the application running and capture the `az containerapp show` outputs for submission evidence.

---

## 10. Document for Graders

Your EX3 README must include:

- The full set of commands above with your actual resource names.
- The public URL(s) and any demo credentials.
- A link to an unlisted YouTube walkthrough (≤3 min) showing the live Azure deployment responding to real requests.
- A rollback/cleanup checklist (below) so graders know you are staying within the free tier.
- Notes about monitoring the credit balance (`Cost Management + Billing` → `Cost analysis`).

---

## 11. Tear Down (After Demo Week)

```bash
az group delete -n "$RESOURCE_GROUP" --yes --no-wait
```

This removes the Container Apps environment, the ACR, and the Log Analytics workspace—preventing accidental credit usage.

---

## 12. Troubleshooting Checklist

- **Ingress returns 404:** verify the target port matches the container listener (`uvicorn` defaults to 8000).
- **Image fails to start:** use `az containerapp revisions list` and `az containerapp revision show` to read container logs and exit codes.
- **Apple Silicon crash:** rebuild images with `--platform linux/amd64` and push again.
- **Secret not found:** double-check the `secretref:` syntax and that the secret name matches exactly.
- **Compose feature unsupported:** Container Apps ignores `depends_on`, `profiles`, and volume mounts. Replace mounts with Azure File shares or bake data into the image when necessary.

Document any extra fixes you needed so your teammates (and graders) can reproduce the deployment quickly.
