# TalentScan AI — Terraform Deployment Guide

This guide walks you through deploying TalentScan AI to Google Cloud using Terraform.
After the one-time setup below, all future deploys happen automatically when you push to `main`.

---

## What Gets Deployed

| Resource | Type | Notes |
|----------|------|-------|
| `cv-frontend` | Cloud Run | React SPA, scales 0→10 |
| `cv-api` | Cloud Run | FastAPI (no ML), scales 0→3 |
| `cv-ml` | Cloud Run | FastAPI + BERT, min 1 instance (keeps model warm) |
| `talent-scan-worker` | GCE e2-small | Always-on RQ worker + APScheduler |
| `sa-api/ml/worker/frontend/cicd` | Service Accounts | Least-privilege IAM |
| `ml-models-talent-scan-ai` | GCS Bucket | Already exists — imported |
| `talent-scan-ai` (AR) | Artifact Registry | Already exists — imported |
| 13 secrets | Secret Manager | Already exist — imported |

---

## Prerequisites

- [Terraform >= 1.6](https://developer.hashicorp.com/terraform/install)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated to `talent-scan-ai`
- Docker Desktop running
- GitHub repo with this codebase pushed

---

## One-Time Setup

### Step 1 — Enable GCP APIs

```powershell
gcloud services enable `
  run.googleapis.com `
  artifactregistry.googleapis.com `
  storage.googleapis.com `
  secretmanager.googleapis.com `
  compute.googleapis.com `
  iam.googleapis.com `
  cloudresourcemanager.googleapis.com `
  iamcredentials.googleapis.com `
  --project=talent-scan-ai
```

### Step 2 — Create Terraform state bucket

```powershell
gsutil mb -l us-central1 -p talent-scan-ai gs://talent-scan-ai-tfstate
gsutil versioning set on gs://talent-scan-ai-tfstate
```

### Step 3 — Initialize Terraform

```powershell
cd terraform
terraform init
```

### Step 4 — Import already-existing resources

Since you already created these resources manually, import them so Terraform can manage them:

```powershell
# Artifact Registry repository
terraform import google_artifact_registry_repository.main `
  projects/talent-scan-ai/locations/us-central1/repositories/talent-scan-ai

# ML models GCS bucket
terraform import google_storage_bucket.ml_models ml-models-talent-scan-ai

# Secrets — PowerShell requires backtick-escaped inner quotes
terraform import "google_secret_manager_secret.secrets[`"mongo-uri`"]"       projects/talent-scan-ai/secrets/mongo-uri
terraform import "google_secret_manager_secret.secrets[`"mongo-db`"]"        projects/talent-scan-ai/secrets/mongo-db
terraform import "google_secret_manager_secret.secrets[`"jwt-secret`"]"      projects/talent-scan-ai/secrets/jwt-secret
terraform import "google_secret_manager_secret.secrets[`"openai-key`"]"      projects/talent-scan-ai/secrets/openai-key
terraform import "google_secret_manager_secret.secrets[`"internal-secret`"]" projects/talent-scan-ai/secrets/internal-secret
terraform import "google_secret_manager_secret.secrets[`"gnews-key`"]"       projects/talent-scan-ai/secrets/gnews-key
terraform import "google_secret_manager_secret.secrets[`"hirebase-key`"]"    projects/talent-scan-ai/secrets/hirebase-key
terraform import "google_secret_manager_secret.secrets[`"geocoding-key`"]"   projects/talent-scan-ai/secrets/geocoding-key
terraform import "google_secret_manager_secret.secrets[`"github-token`"]"    projects/talent-scan-ai/secrets/github-token
terraform import "google_secret_manager_secret.secrets[`"brevo-key`"]"       projects/talent-scan-ai/secrets/brevo-key
terraform import "google_secret_manager_secret.secrets[`"redis-host`"]"      projects/talent-scan-ai/secrets/redis-host
terraform import "google_secret_manager_secret.secrets[`"redis-port`"]"      projects/talent-scan-ai/secrets/redis-port
terraform import "google_secret_manager_secret.secrets[`"redis-password`"]"  projects/talent-scan-ai/secrets/redis-password
```

> **Note:** If any secret name differs from what's above (e.g. you used `openai-api-key` instead of `openai-key`),
> update the key in `terraform/secrets.tf` locals AND the `secret_ref` lookups in `terraform/cloud_run.tf`.

### Step 5 — Plan and apply (infrastructure only)

```powershell
terraform plan
terraform apply
```

This creates: service accounts, IAM bindings, firewall rules, and the GCE worker VM.
The Cloud Run services will fail on first apply if the Docker images don't exist yet — that's expected.
Run Step 6 to push images, then apply again.

### Step 6 — Build and push Docker images (first time)

From the project root (not the `terraform/` directory):

```powershell
$TAG = git rev-parse --short HEAD
$REGISTRY = "us-central1-docker.pkg.dev/talent-scan-ai/talent-scan-ai"

gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

# API image (~5 min)
docker build -f backend/Dockerfile.api -t "$REGISTRY/cv-api:$TAG" -t "$REGISTRY/cv-api:latest" ./backend
docker push "$REGISTRY/cv-api:$TAG"
docker push "$REGISTRY/cv-api:latest"

# ML image (~20 min first time)
docker build -f backend/Dockerfile.ml -t "$REGISTRY/cv-ml:$TAG" -t "$REGISTRY/cv-ml:latest" ./backend
docker push "$REGISTRY/cv-ml:$TAG"
docker push "$REGISTRY/cv-ml:latest"

# Worker image
docker build -f backend/Dockerfile.worker -t "$REGISTRY/cv-worker:$TAG" -t "$REGISTRY/cv-worker:latest" ./backend
docker push "$REGISTRY/cv-worker:$TAG"
docker push "$REGISTRY/cv-worker:latest"
```

### Step 7 — Deploy backend Cloud Run services

```powershell
cd terraform
terraform apply `
  -var="api_image_tag=$TAG" `
  -var="ml_image_tag=$TAG" `
  -var="worker_image_tag=$TAG" `
  -target=google_cloud_run_v2_service.ml `
  -target=google_cloud_run_v2_service.api `
  -auto-approve
```

### Step 8 — Build and push frontend with API URL

```powershell
$API_URL = terraform output -raw api_url

docker build `
  --build-arg VITE_API_BASE_URL=$API_URL `
  -f frontend/Dockerfile `
  -t "$REGISTRY/cv-frontend:$TAG" `
  -t "$REGISTRY/cv-frontend:latest" `
  ./frontend

docker push "$REGISTRY/cv-frontend:$TAG"
docker push "$REGISTRY/cv-frontend:latest"
```

### Step 9 — Deploy frontend Cloud Run service

```powershell
terraform apply `
  -var="api_image_tag=$TAG" `
  -var="ml_image_tag=$TAG" `
  -var="worker_image_tag=$TAG" `
  -var="frontend_image_tag=$TAG" `
  -auto-approve
```

### Step 10 — Verify deployment

```powershell
$FRONTEND_URL = terraform output -raw frontend_url
$API_URL      = terraform output -raw api_url

# API health check
Invoke-RestMethod "$API_URL/health"

# Open frontend
Start-Process $FRONTEND_URL

# Open API docs
Start-Process "$API_URL/docs"

# Worker logs (SSH via IAP)
gcloud compute ssh talent-scan-worker --zone=us-central1-a `
  --tunnel-through-iap -- "docker logs cv-worker --tail=50"
```

---

## GitHub Actions Setup (CI/CD)

After the one-time manual deploy above, push to `main` will auto-deploy via `.github/workflows/deploy.yml`.

### Create the CI/CD service account key

Two authentication options. **Option A (recommended):** Workload Identity Federation — no JSON key stored in GitHub.

#### Option A: Workload Identity Federation

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="talent-scan-ai" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Create provider linked to your GitHub repo
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="talent-scan-ai" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow GitHub Actions (from YOUR repo) to impersonate sa-cicd
# Replace YOUR_GITHUB_USERNAME/YOUR_REPO_NAME with your actual repo
gcloud iam service-accounts add-iam-policy-binding \
  "sa-cicd@talent-scan-ai.iam.gserviceaccount.com" \
  --project="talent-scan-ai" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe talent-scan-ai --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME"
```

**Add GitHub secrets:**
| Secret name | Value |
|-------------|-------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | `sa-cicd@talent-scan-ai.iam.gserviceaccount.com` |

Get project number: `gcloud projects describe talent-scan-ai --format='value(projectNumber)'`

#### Option B: Service Account Key (simpler, less secure)

```bash
gcloud iam service-accounts keys create sa-cicd-key.json \
  --iam-account=sa-cicd@talent-scan-ai.iam.gserviceaccount.com \
  --project=talent-scan-ai
```

Add `GCP_SA_KEY` GitHub secret with the contents of `sa-cicd-key.json`, then uncomment Option B in `.github/workflows/deploy.yml`.

> Delete `sa-cicd-key.json` locally after adding it to GitHub — never commit it.

---

## Ongoing Deployments

After setup, just push to `main`:

```powershell
git add .
git commit -m "your changes"
git push origin main
```

GitHub Actions will:
1. Build and push all Docker images (tagged with the git commit SHA)
2. Deploy ML and API services via Terraform
3. Read the API URL, build frontend with it baked in
4. Deploy the frontend service
5. Print a summary table with all URLs

### Manual trigger (skip ML rebuild when only frontend changed)

Go to **GitHub → Actions → Build & Deploy → Run workflow**, then:
- Check "Skip rebuilding the ML image" to save ~20 min when you only changed frontend/API code

---

## Updating the Worker VM

The worker VM startup script runs on every boot. After deploying a new worker image:

```powershell
# Option 1: Reset the VM (triggers startup script, ~1 min downtime)
gcloud compute instances reset talent-scan-worker --zone=us-central1-a

# Option 2: SSH and update manually (zero downtime)
gcloud compute ssh talent-scan-worker --zone=us-central1-a --tunnel-through-iap -- `
  "docker pull us-central1-docker.pkg.dev/talent-scan-ai/talent-scan-ai/cv-worker:latest && docker restart cv-worker"
```

---

## Rotating a Secret

```powershell
# Example: rotate OpenAI API key
$newKey = "sk-new-key-here"
$tmp = [IO.Path]::GetTempFileName()
[IO.File]::WriteAllText($tmp, $newKey)
gcloud secrets versions add openai-key --data-file=$tmp --project=talent-scan-ai
Remove-Item $tmp

# Cloud Run services pick up the new version on next instance start.
# To force immediate rotation, redeploy:
cd terraform
terraform apply -auto-approve
```

---

## Rollback

Each deploy tags images with the git commit SHA. To roll back:

```powershell
cd terraform
$SHA = "abc1234"  # the commit SHA to roll back to
terraform apply `
  -var="api_image_tag=$SHA" `
  -var="ml_image_tag=$SHA" `
  -var="worker_image_tag=$SHA" `
  -var="frontend_image_tag=$SHA" `
  -auto-approve
```

---

## Terraform State

State is stored in `gs://talent-scan-ai-tfstate/terraform/state`. To inspect:

```powershell
terraform state list
terraform state show google_cloud_run_v2_service.api
```

---

## Cost Estimate

| Resource | Est. monthly cost |
|----------|------------------|
| Cloud Run frontend (scale-to-zero) | ~$0–2 |
| Cloud Run API (scale-to-zero) | ~$0–5 |
| Cloud Run ML (min 1 instance, 8GB) | ~$80–120 |
| GCE e2-small worker (always-on) | ~$15 |
| Artifact Registry storage | ~$1–5 |
| GCS ML models bucket | ~$1–3 |
| Secret Manager | ~$0.30/secret/month |
| **Total estimate** | **~$100–150/month** |

To reduce cost: set `ml_min_instances = 0` in `terraform.tfvars` (ML service cold starts take ~90s).
