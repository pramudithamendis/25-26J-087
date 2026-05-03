# Deployment Guide

Complete guide for running the project locally and deploying to Google Cloud Platform.

---

## Table of Contents

1. [How the Project Works](#how-the-project-works)
2. [Local Development (Docker Compose)](#local-development)
3. [Environment Variables Reference](#environment-variables-reference)
4. [GCP Deployment — Step by Step](#gcp-deployment)
   - [Step 1 — Prerequisites](#step-1--prerequisites)
   - [Step 2 — Create GCP Account & Project](#step-2--create-gcp-account--project)
   - [Step 3 — Enable GCP APIs](#step-3--enable-gcp-apis)
   - [Step 4 — Set Up MongoDB Atlas](#step-4--set-up-mongodb-atlas)
   - [Step 5 — Set Up Redis](#step-5--set-up-redis)
   - [Step 6 — Upload ML Models to GCS](#step-6--upload-ml-models-to-gcs)
   - [Step 7 — Store Secrets in Secret Manager](#step-7--store-secrets-in-secret-manager)
   - [Step 8 — Create Artifact Registry](#step-8--create-artifact-registry)
   - [Step 9 — Build & Push Docker Images](#step-9--build--push-docker-images)
   - [Step 10 — Deploy ML Service](#step-10--deploy-ml-service)
   - [Step 11 — Deploy API Service](#step-11--deploy-api-service)
   - [Step 12 — Deploy Worker](#step-12--deploy-worker)
   - [Step 13 — Deploy Frontend](#step-13--deploy-frontend)
   - [Step 14 — Wire Up Permissions](#step-14--wire-up-permissions)
5. [Troubleshooting](#troubleshooting)

---

## How the Project Works

### What this project does

An AI-powered HR platform that:
- Parses and analyzes candidate CVs
- Matches candidates to job descriptions using semantic similarity
- Predicts employee turnover risk using ML models (Random Forest, XGBoost, CatBoost)
- Generates SHAP-based explanations for predictions
- Runs agentic AI evaluation pipelines using OpenAI
- Extracts skills from CVs using a fine-tuned BERT NER model
- Generates interview questions from GitHub project files
- Tracks hiring duration forecasts

### Architecture overview

```
Browser
  │
  ▼
┌─────────────────────┐
│  Frontend (React)   │  Vite + React 19 + Tailwind
│  Cloud Run          │  Served as static files via nginx
└────────┬────────────┘
         │ HTTPS API calls
         ▼
┌─────────────────────┐
│  API Service        │  FastAPI (lightweight — no ML models)
│  Cloud Run          │  Handles: auth, users, jobs, CVs, articles,
│  512MB RAM          │  trends, geocoding, ESCO, admin, questions
└────────┬────────────┘
         │ Internal HTTP (ML requests only)
         ▼
┌─────────────────────┐         ┌─────────────────────┐
│  ML Service         │         │  Worker (RQ)         │
│  Cloud Run          │         │  GCE VM (always-on)  │
│  4GB RAM            │         │  Processes async jobs│
│  Handles: turnover  │         │  APScheduler crons   │
│  predict, evaluate, │         └──────────┬───────────┘
│  skill extraction   │                    │
└────────┬────────────┘                    │
         │                                 │
         ▼                                 ▼
┌─────────────────────────────────────────────────────┐
│                  Shared Services                     │
│  MongoDB Atlas  │  Redis  │  GCS (ML models)         │
│  Secret Manager │  OpenAI API                        │
└─────────────────────────────────────────────────────┘
```

### How each service is deployed

| Service | Technology | Where | Scales to zero? |
|---|---|---|---|
| Frontend | React SPA + nginx | Cloud Run | Yes |
| API Service | FastAPI (no ML) | Cloud Run | Yes |
| ML Service | FastAPI (BERT + ensemble) | Cloud Run | Yes (cold start ~90s) |
| Worker | RQ + APScheduler | GCE e2-small VM | No (always on) |
| Database | MongoDB Atlas | Atlas (GCP region) | N/A |
| Cache/Queue | Redis | Redis Cloud (free) | N/A |
| Model Storage | Joblib/pickle files | GCS Bucket | N/A |

### Key files

```
chanmi-proj/
├── backend/
│   ├── app/
│   │   ├── main.py              ← Local dev entry point (full monolith)
│   │   ├── main_api.py          ← Production: lightweight API service
│   │   ├── main_ml.py           ← Production: ML-heavy service
│   │   ├── config.py            ← All settings (reads from .env)
│   │   ├── routes/              ← API endpoint routers (16 routers)
│   │   ├── services/            ← Business logic
│   │   ├── ml_models/           ← BERT NER model + ensemble PKL files
│   │   └── utils/gcs_loader.py  ← Downloads models from GCS on startup
│   ├── worker.py                ← RQ background job worker
│   ├── Dockerfile.api           ← Builds lightweight API image
│   ├── Dockerfile.ml            ← Builds ML-heavy image
│   ├── Dockerfile.worker        ← Builds worker image
│   ├── requirements.txt         ← Full dependencies (ML + API)
│   └── requirements.api.txt     ← Lightweight dependencies (no ML)
├── frontend/
│   ├── src/config/api.ts        ← API base URL (VITE_API_BASE_URL)
│   ├── Dockerfile               ← 2-stage build: Vite → nginx
│   └── nginx.conf               ← SPA routing config
└── docker-compose.yml           ← Local dev: all services in one stack
```

---

## Local Development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- `backend/.env` file filled in (copy from `backend/.env.example`)

### 1. Fill in your `.env` file

Copy the example and edit it:

```bash
cp backend/.env.example backend/.env
```

At minimum you need these filled in (see [Environment Variables Reference](#environment-variables-reference)):

```env
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_DB=cv_db
JWT_SECRET=any-long-random-string
OPENAI_API_KEY=sk-...
REDIS_HOST=redis
REDIS_PORT=6379
```

### 2. Start everything

```bash
docker compose up --build
```

First run takes 15–30 minutes (downloading Python, installing torch, etc.).  
Subsequent starts are fast (Docker caches layers).

You know it's ready when you see:
```
cv-eval-backend  | INFO:     Application startup complete.
```

### 3. Open in browser

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### Useful commands

```bash
# Stop everything
docker compose down

# View live logs for a service
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Restart just one service after a code change
docker compose restart backend

# Full reset (removes volumes too)
docker compose down -v
docker compose up --build
```

---

## Environment Variables Reference

### Required (app will not start without these)

| Variable | Where to get it | Example |
|---|---|---|
| `MONGO_URI` | MongoDB Atlas → Connect → Drivers | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGO_DB` | Your choice — name of the database | `cv_db` |
| `JWT_SECRET` | Generate any long random string | `openssl rand -hex 32` |

### Strongly recommended

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | Powers CV evaluation, embeddings, question generation | — |
| `OPENAI_MODEL` | GPT model for evaluations | `gpt-3.5-turbo` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-ada-002` |

### Redis (queue for background jobs)

| Variable | Local dev | Production |
|---|---|---|
| `REDIS_HOST` | `redis` (docker service name) | Redis Cloud hostname |
| `REDIS_PORT` | `6379` | `6379` |
| `REDIS_PASSWORD` | _(empty)_ | Redis Cloud password |
| `REDIS_DB` | `0` | `0` |

### Optional API keys (features degrade gracefully without these)

| Variable | Feature it enables |
|---|---|
| `GITHUB_TOKEN` | GitHub repo fetching for candidate profiles |
| `GNEWS_API_KEY` | News articles and industry trends |
| `HIREBASE_API_KEY` | Job market data sync |
| `GEOCODING_API_KEY` | Location-based candidate matching |
| `BREVO_API_KEY` | Email notifications |
| `BREVO_SENDER_EMAIL` | Sender address for emails |
| `BREVO_SENDER_NAME` | Sender name for emails |

### Provider switches (control which backend is used)

| Variable | Options | Recommended |
|---|---|---|
| `LLM_PROVIDER` | `openai` or `heuristic` | `openai` |
| `EMBEDDING_PROVIDER` | `openai` or `sentence-transformers` | `openai` |
| `CV_EXTRACTION_METHOD` | `openai` or `regex` | `openai` |

### Agentic AI settings

| Variable | Default | Notes |
|---|---|---|
| `USE_AGENTIC_EVALUATION` | `True` | Use multi-agent pipeline for evaluations |
| `AGENTIC_FALLBACK_TO_PIPELINE` | `True` | Fall back to simpler pipeline if agents fail |
| `MAX_AGENT_ITERATIONS` | `20` | Max steps per evaluation (controls cost) |
| `AGENT_TEMPERATURE` | `0.3` | LLM temperature for agents |

### GCP production-only variables (not needed locally)

| Variable | Set on | Purpose |
|---|---|---|
| `SERVICE_TYPE` | API, ML, Worker Cloud Run | `api`, `ml`, `worker`, or `full` |
| `ML_SERVICE_URL` | API Cloud Run only | Internal URL of the ML service |
| `GCS_BUCKET_NAME` | ML Cloud Run + Worker | GCS bucket where models are stored |
| `GCS_MODEL_PREFIX` | ML Cloud Run + Worker | Path prefix in bucket (default: `models/`) |
| `INTERNAL_SERVICE_SECRET` | API + ML Cloud Run | Shared secret for internal service calls |

---

## GCP Deployment

### Step 1 — Prerequisites

Install these tools on your local machine:

**Docker Desktop** — https://www.docker.com/products/docker-desktop/

**Google Cloud CLI:**
```bash
# macOS
brew install google-cloud-sdk

# Verify
gcloud version
```

**Windows:** Download and run the installer from **cloud.google.com/sdk/docs/install** (choose the Windows installer). After installation, restart your terminal, then verify:
```powershell
gcloud version
```

**Verify Docker is running:**
```bash
docker ps
```

---

### Step 2 — Create GCP Account & Project

1. Go to **console.cloud.google.com** and sign in
2. Click **"Select a project"** → **"New Project"**
3. Name: `chanmi-proj` (or anything you like)
4. Note your **Project ID** — it looks like `chanmi-proj-123456`
5. Add billing: **Billing** → Link a credit card
   - New accounts get **$300 free credit**
   - Expected monthly cost: $30–80

Log in and set your project:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

---

### Step 3 — Enable GCP APIs

Run once (takes ~1 minute):

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com
```

---

### Step 4 — Set Up MongoDB Atlas

Your app needs a MongoDB database. MongoDB Atlas has a free tier that works great for this.

1. Go to **cloud.mongodb.com** → create a free account
2. Create a **free M0 cluster**
   - Cloud provider: **GCP**
   - Region: **us-central1** (same region as your Cloud Run services)
3. Create a **database user**:
   - Security → Database Access → **Add New Database User**
   - Username: `chanmi-app`
   - Password: generate a strong password and **save it**
   - Role: **Atlas Admin**
4. Allow network access:
   - Security → Network Access → **Add IP Address**
   - Choose **Allow Access From Anywhere** (`0.0.0.0/0`)
   - This is required because Cloud Run IPs are dynamic
5. Get your **connection string**:
   - Clusters → **Connect** → **Drivers**
   - Driver: Python, Version: 3.12 or later
   - Copy the string — it looks like:
     ```
     mongodb+srv://chanmi-app:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
     ```
   - Replace `<password>` with your actual password
   - Add your database name before `?`:
     ```
     mongodb+srv://chanmi-app:YOURPASSWORD@cluster0.xxxxx.mongodb.net/cv_db?retryWrites=true&w=majority
     ```

---

### Step 5 — Set Up Redis

The background job worker uses Redis as a queue.

**Recommended: Redis Cloud (free tier)**

1. Go to **redis.io/try-free** → create a free account
2. Create a **free database** (30MB, enough for the queue)
   - Cloud: **GCP**, Region: **us-central1**
3. After creation, click on your database and note:
   - **Public endpoint** (host:port, e.g. `redis-12345.c1.us-central1-1.gce.redns.redis-cloud.com:12345`)
   - **Password** (under Security → Default user password)

You'll use these values for `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD`.

---

### Step 6 — Upload ML Models to GCS

Your ML models (~500MB total) are stored in GCS and downloaded by the ML service at startup.

**Create the bucket:**
```bash
# Pick a unique bucket name — all GCS bucket names are globally unique
gsutil mb -l us-central1 gs://chanmi-ml-models-YOUR_PROJECT_ID
```

**Upload models:**
```bash
# From the project root directory
gsutil -m cp -r backend/app/ml_models/skill_ner_bert \
  gs://chanmi-ml-models-YOUR_PROJECT_ID/models/skill_ner_bert

gsutil -m cp backend/app/ml_models/*.pkl \
  gs://chanmi-ml-models-YOUR_PROJECT_ID/models/

gsutil -m cp backend/app/ml_models/*.joblib \
  gs://chanmi-ml-models-YOUR_PROJECT_ID/models/

gsutil -m cp -r backend/app/ml_models/hiring_duration \
  gs://chanmi-ml-models-YOUR_PROJECT_ID/models/hiring_duration
```
**Windows**
```bash
# UPLOAD BERT MODEL (folder)
gsutil -m cp -r backend/app/ml_models/skill_ner_bert gs://ml-models-talent-scan-ai/models/skill_ner_bert

# UPLOAD HIRING DURATION MODEL (folder)
gsutil -m cp -r backend/app/ml_models/hiring_duration gs://ml-models-talent-scan-ai/models/hiring_duration

# UPLOAD ALL .pkl MODELS
gsutil -m cp backend/app/ml_models/*.pkl gs://ml-models-talent-scan-ai/models/

# UPLOAD ALL .joblib MODELS
gsutil -m cp backend/app/ml_models/*.joblib gs://ml-models-talent-scan-ai/models/

# VERIFY UPLOAD (use -r to confirm files inside subdirectories)
gsutil ls -r gs://ml-models-talent-scan-ai/models/
```

**Verify the upload:**
```bash
gsutil ls gs://chanmi-ml-models-YOUR_PROJECT_ID/models/
```

You should see:
```
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/skill_ner_bert/
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/rf.pkl
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/xgb.pkl
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/cat.pkl
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/random_forest_model.pkl
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/label_encoder.pkl
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/ensemble_soft_weighted_calibrated.joblib
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/hiring_duration/
gs://chanmi-ml-models-YOUR_PROJECT_ID/models/hiring_duration/stage_tracker_model.pkl
```

---

### Step 7 — Store Secrets in Secret Manager

Never put passwords in environment variables directly in Cloud Run. Use Secret Manager.

**Create each secret** (paste the value when prompted, or pipe it via echo):

```bash
# Database
echo -n "YOUR_MONGO_CONNECTION_STRING" | \
  gcloud secrets create mongo-uri --data-file=-

echo -n "cv_db" | \
  gcloud secrets create mongo-db --data-file=-

# Auth — generate a strong random secret
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create jwt-secret --data-file=-

# OpenAI
echo -n "sk-YOUR_OPENAI_KEY" | \
  gcloud secrets create openai-key --data-file=-

# Internal service authentication (random secret shared between API and ML)
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create internal-secret --data-file=-

# Optional — only add if you have these keys
echo -n "YOUR_GNEWS_KEY" | \
  gcloud secrets create gnews-key --data-file=-

echo -n "YOUR_HIREBASE_KEY" | \
  gcloud secrets create hirebase-key --data-file=-

echo -n "YOUR_GEOCODING_KEY" | \
  gcloud secrets create geocoding-key --data-file=-

echo -n "YOUR_GITHUB_TOKEN" | \
  gcloud secrets create github-token --data-file=-

echo -n "YOUR_BREVO_KEY" | \
  gcloud secrets create brevo-key --data-file=-

# Redis
echo -n "YOUR_REDIS_HOST" | \
  gcloud secrets create redis-host --data-file=-

echo -n "YOUR_REDIS_PORT" | \
  gcloud secrets create redis-port --data-file=-

echo -n "YOUR_REDIS_PASSWORD" | \
  gcloud secrets create redis-password --data-file=-
```
**Windows (PowerShell)**

> PowerShell's `echo` adds a trailing newline (`\r\n`) to piped values, which gets stored in Secret Manager and injected into your env vars — silently breaking MongoDB URIs, JWT signing, and Redis auth. Use this helper instead:

```powershell
# Paste this helper function once at the top of your session
function New-Secret($name, $value) {
    $tmp = [IO.Path]::GetTempFileName()
    [IO.File]::WriteAllText($tmp, $value)
    gcloud secrets create $name --data-file=$tmp
    Remove-Item $tmp
}

# DATABASE
New-Secret "mongo-uri" "YOUR_MONGO_CONNECTION_STRING"
New-Secret "mongo-db"  "cv_db"

# AUTH (generate secure random secrets)
$jwt      = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 64 | % {[char]$_})
$internal = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 64 | % {[char]$_})
New-Secret "jwt-secret"      $jwt
New-Secret "internal-secret" $internal

# OPENAI
New-Secret "openai-key" "sk-YOUR_OPENAI_KEY"

# OPTIONAL APIs
New-Secret "gnews-key"     "YOUR_GNEWS_KEY"
New-Secret "hirebase-key"  "YOUR_HIREBASE_KEY"
New-Secret "geocoding-key" "YOUR_GEOCODING_KEY"
New-Secret "github-token"  "YOUR_GITHUB_TOKEN"
New-Secret "brevo-key"     "YOUR_BREVO_KEY"

# REDIS
New-Secret "redis-host"     "YOUR_REDIS_HOST"
New-Secret "redis-port"     "YOUR_REDIS_PORT"
New-Secret "redis-password" "YOUR_REDIS_PASSWORD"

# VERIFY
gcloud secrets list
```

**Verify secrets were created:**
```bash
gcloud secrets list
```

---

### Step 8 — Create Artifact Registry

This is where your Docker images are stored.

```bash
gcloud artifacts repositories create chanmi-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Chanmi project Docker images"

# Authenticate Docker to push to it
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

### Step 9 — Build & Push Docker Images

Set variables (run these first so the commands below are shorter):

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export REGISTRY=$REGION-docker.pkg.dev/$PROJECT_ID/chanmi-repo
```

**Build and push the API image** (lightweight — no ML, builds fast ~5 min):
```bash
docker build \
  -f backend/Dockerfile.api \
  -t $REGISTRY/cv-api:latest \
  ./backend

docker push $REGISTRY/cv-api:latest
```

**Build and push the ML image** (heavy — includes torch/transformers, builds ~20 min first time):
```bash
docker build \
  -f backend/Dockerfile.ml \
  -t $REGISTRY/cv-ml:latest \
  ./backend

docker push $REGISTRY/cv-ml:latest
```

**Build and push the Worker image:**
```bash
docker build \
  -f backend/Dockerfile.worker \
  -t $REGISTRY/cv-worker:latest \
  ./backend

docker push $REGISTRY/cv-worker:latest
```
  > The frontend image is built last because it needs the API URL baked in — see Step 13.

**Windows (PowerShell):**
```powershell
$PROJECT_ID = gcloud config get-value project
$REGION = "us-central1"
$REGISTRY = "$REGION-docker.pkg.dev/$PROJECT_ID/talent-scan-ai"  

# Build and push the API image
docker build `
  -f backend/Dockerfile.api `
  -t "$REGISTRY/cv-api:latest" `
  ./backend

docker push $REGISTRY/cv-api:latest

# Build and push the ML image
docker build `
  -f backend/Dockerfile.ml `
  -t $REGISTRY/cv-ml:latest `
  ./backend

docker push $REGISTRY/cv-ml:latest

# Build and push the Worker image
docker build `
  -f backend/Dockerfile.worker `
  -t $REGISTRY/cv-worker:latest `
  ./backend

docker push $REGISTRY/cv-worker:latest
```



---

### Step 10 — Deploy ML Service

> **Important:** Grant GCS bucket access **before** deploying. The ML service downloads models from GCS the moment it starts — if the service account lacks access, the container crashes before it can bind to port 8080 and the deployment fails.

**Grant GCS read access first:**
```bash
# Get the default Compute service account Cloud Run uses
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA=$PROJECT_NUMBER-compute@developer.gserviceaccount.com

gsutil iam ch serviceAccount:$SA:roles/storage.objectViewer \
  gs://chanmi-ml-models-$PROJECT_ID
```

Then deploy:

```bash
gcloud run deploy cv-ml \
  --image $REGISTRY/cv-ml:latest \
  --region $REGION \
  --memory 8Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 2 \
  --no-allow-unauthenticated \
  --startup-cpu-boost \
  --set-env-vars "SERVICE_TYPE=ml,GCS_BUCKET_NAME=chanmi-ml-models-$PROJECT_ID,GCS_MODEL_PREFIX=models/" \
  --set-secrets "MONGO_URI=mongo-uri:latest" \
  --set-secrets "MONGO_DB=mongo-db:latest" \
  --set-secrets "JWT_SECRET=jwt-secret:latest" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest" \
  --set-secrets "INTERNAL_SERVICE_SECRET=internal-secret:latest"
```

After deploy, note the URL printed at the end:
```
Service URL: https://cv-ml-xxxxxxxxxx-uc.a.run.app
```

**Save this URL** — you need it for the next step.

> **Note:** The first startup takes 60–90 seconds while it downloads ~500MB of ML models from GCS. This is normal.

**Test it:**
```bash
curl https://cv-ml-xxxxxxxxxx-uc.a.run.app/health
# Expected: {"status":"ok","service":"ml","mongodb":"connected","models":{...}}
```

**Windows (PowerShell):**
```powershell
$BUCKET = "ml-models-talent-scan-ai"

# secret key access
gcloud secrets add-iam-policy-binding mongo-uri \
  --member="serviceAccount:781946113522-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# bucket access
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gsutil iam ch "serviceAccount:${SA}:roles/storage.objectViewer" gs://ml-models-talent-scan-ai

# deploy
gcloud run deploy cv-ml `
  --image "$REGISTRY/cv-ml:latest" `
  --region $REGION `
  --memory 8Gi `
  --cpu 2 `
  --min-instances 0 `
  --max-instances 2 `
  --no-allow-unauthenticated `
  --cpu-boost `
  --set-env-vars "SERVICE_TYPE=ml,GCS_BUCKET_NAME=$BUCKET,GCS_MODEL_PREFIX=models/" `
  --set-secrets "MONGO_URI=mongo-uri:latest,MONGO_DB=mongo-db:latest,JWT_SECRET=jwt-secret:latest,OPENAI_API_KEY=openai-key:latest,INTERNAL_SERVICE_SECRET=internal-secret:latest"
```

---

### Step 11 — Deploy API Service

Replace `YOUR_ML_URL` with the URL from Step 10:

```bash
ML_URL=https://cv-ml-xxxxxxxxxx-uc.a.run.app
```

**Windows (PowerShell):**
```powershell
$ML_URL = "https://cv-ml-xxxxxxxxxx-uc.a.run.app"
```

Then run the deploy (same on both platforms):
```bash
gcloud run deploy cv-api \
  --image $REGISTRY/cv-api:latest \
  --region $REGION \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --allow-unauthenticated \
  --set-env-vars "SERVICE_TYPE=api,ML_SERVICE_URL=$ML_URL,BREVO_SENDER_EMAIL=your@email.com,BREVO_SENDER_NAME=TalentScan AI" \
  --set-secrets "MONGO_URI=mongo-uri:latest" \
  --set-secrets "MONGO_DB=mongo-db:latest" \
  --set-secrets "JWT_SECRET=jwt-secret:latest" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest" \
  --set-secrets "INTERNAL_SERVICE_SECRET=internal-secret:latest" \
  --set-secrets "GNEWS_API_KEY=gnews-key:latest" \
  --set-secrets "GITHUB_TOKEN=github-token:latest" \
  --set-secrets "BREVO_API_KEY=brevo-key:latest" \
  --set-secrets "HIREBASE_API_KEY=hirebase-key:latest" \
  --set-secrets "GEOCODING_API_KEY=geocoding-key:latest" \
  --set-secrets "REDIS_HOST=redis-host:latest" \
  --set-secrets "REDIS_PORT=redis-port:latest" \
  --set-secrets "REDIS_PASSWORD=redis-password:latest"
```

Note your API URL:
```
Service URL: https://cv-api-xxxxxxxxxx-uc.a.run.app
```

**Test it:**
```bash
curl https://cv-api-xxxxxxxxxx-uc.a.run.app/health
# Expected: {"status":"ok","service":"api","mongodb":"connected"}
```

---

### Step 12 — Deploy Worker

The worker is a long-running background process. It runs on a small always-on GCE VM.

**Create the VM:**
```bash
gcloud compute instances create chanmi-worker \
  --zone=us-central1-a \
  --machine-type=e2-small \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=20GB
```

**SSH into it:**
```bash
gcloud compute ssh chanmi-worker --zone=us-central1-a
```

**Inside the VM — install Docker:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**Authenticate to Artifact Registry:**
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Pull and run the worker:**
```bash
docker pull us-central1-docker.pkg.dev/YOUR_PROJECT_ID/chanmi-repo/cv-worker:latest

docker run -d \
  --name cv-worker \
  --restart=always \
  -e SERVICE_TYPE=worker \
  -e MONGO_URI="YOUR_MONGO_CONNECTION_STRING" \
  -e MONGO_DB="cv_db" \
  -e JWT_SECRET="YOUR_JWT_SECRET" \
  -e OPENAI_API_KEY="YOUR_OPENAI_KEY" \
  -e REDIS_HOST="YOUR_REDIS_HOST" \
  -e REDIS_PORT="YOUR_REDIS_PORT" \
  -e REDIS_PASSWORD="YOUR_REDIS_PASSWORD" \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/chanmi-repo/cv-worker:latest
```

**Verify it's running:**
```bash
docker logs cv-worker
# Should show: "Worker started, listening on queue: evaluations"
```

Type `exit` to leave the SSH session.

---

### Step 13 — Deploy Frontend

The frontend React app has the API URL baked in at build time (Vite replaces `import.meta.env.VITE_API_BASE_URL` during `npm run build`).

**Build with your real API URL:**
```bash
API_URL=https://cv-api-xxxxxxxxxx-uc.a.run.app
```

**Windows (PowerShell):**
```powershell
$API_URL = "https://cv-api-xxxxxxxxxx-uc.a.run.app"
```

```bash
docker build \
  --build-arg VITE_API_BASE_URL=$API_URL \
  -f frontend/Dockerfile \
  -t $REGISTRY/cv-frontend:latest \
  ./frontend

docker push $REGISTRY/cv-frontend:latest
```

**Deploy to Cloud Run:**
```bash
gcloud run deploy cv-frontend \
  --image $REGISTRY/cv-frontend:latest \
  --region $REGION \
  --memory 128Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --allow-unauthenticated
```

Your app is now live at:
```
Service URL: https://cv-frontend-xxxxxxxxxx-uc.a.run.app
```

---

### Step 14 — Wire Up Permissions

**Allow the ML service to read models from GCS:**

> GCS bucket access was already granted in Step 10 (required before the first deploy). This is noted here for completeness — skip if you followed Step 10.

```bash
# Get the ML service's service account
ML_SA=$(gcloud run services describe cv-ml \
  --region $REGION \
  --format="value(spec.template.spec.serviceAccountName)")

# Grant GCS read access (already done in Step 10 — skip if so)
gsutil iam ch serviceAccount:$ML_SA:roles/storage.objectViewer \
  gs://chanmi-ml-models-$PROJECT_ID
```

**Windows (PowerShell):**
```powershell
$ML_SA = gcloud run services describe cv-ml `
  --region $REGION `
  --format="value(spec.template.spec.serviceAccountName)"

# Already done in Step 10 — skip if so
gsutil iam ch "serviceAccount:${ML_SA}:roles/storage.objectViewer" `
  gs://chanmi-ml-models-$PROJECT_ID
```

**Allow the API service to call the ML service:**

```bash
# Get the API service's service account
API_SA=$(gcloud run services describe cv-api \
  --region $REGION \
  --format="value(spec.template.spec.serviceAccountName)")

# Grant permission to invoke the ML service
gcloud run services add-iam-policy-binding cv-ml \
  --region $REGION \
  --member="serviceAccount:$API_SA" \
  --role="roles/run.invoker"
```

**Windows (PowerShell):**
```powershell
$API_SA = gcloud run services describe cv-api `
  --region $REGION `
  --format="value(spec.template.spec.serviceAccountName)"

gcloud run services add-iam-policy-binding cv-ml `
  --region $REGION `
  --member="serviceAccount:$API_SA" `
  --role="roles/run.invoker"
```

**Allow both services to access Secret Manager:**

```bash
for SA in $API_SA $ML_SA; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

**Windows (PowerShell):**
```powershell
foreach ($SA in @($API_SA, $ML_SA)) {
    gcloud projects add-iam-policy-binding $PROJECT_ID `
      --member="serviceAccount:$SA" `
      --role="roles/secretmanager.secretAccessor"
}
```

---

### Deployment complete

Your services:

| Service | URL |
|---|---|
| Frontend | `https://cv-frontend-xxxxxxxxxx-uc.a.run.app` |
| API | `https://cv-api-xxxxxxxxxx-uc.a.run.app` |
| API Docs | `https://cv-api-xxxxxxxxxx-uc.a.run.app/docs` |
| ML Service | `https://cv-ml-xxxxxxxxxx-uc.a.run.app` (internal) |

---

## Updating after code changes

> **Windows (PowerShell):** Re-set your variables at the start of each new terminal session before running these commands:
> ```powershell
> $PROJECT_ID = gcloud config get-value project
> $REGION = "us-central1"
> $REGISTRY = "$REGION-docker.pkg.dev/$PROJECT_ID/chanmi-repo"
> $API_URL = "https://cv-api-xxxxxxxxxx-uc.a.run.app"  # your actual API URL
> ```

When you change backend code:

```bash
# Rebuild and push the affected image
docker build -f backend/Dockerfile.api -t $REGISTRY/cv-api:latest ./backend
docker push $REGISTRY/cv-api:latest

# Redeploy (Cloud Run does a zero-downtime rollout)
gcloud run deploy cv-api --image $REGISTRY/cv-api:latest --region $REGION
```

For the ML service or worker, same pattern with `cv-ml` or `cv-worker`.

For the frontend (if backend URL hasn't changed):
```bash
docker build --build-arg VITE_API_BASE_URL=$API_URL \
  -f frontend/Dockerfile -t $REGISTRY/cv-frontend:latest ./frontend
docker push $REGISTRY/cv-frontend:latest
gcloud run deploy cv-frontend --image $REGISTRY/cv-frontend:latest --region $REGION
```

---

## Troubleshooting

### Backend won't start — `MongoDB connection failed`

Check your `MONGO_URI`:
- Password must be URL-encoded if it contains special characters (`@` → `%40`, `#` → `%23`)
- Network Access in Atlas must include `0.0.0.0/0`
- Test the connection string locally before deploying

### ML service cold start takes too long (>2 minutes)

Normal cold start is 60–90 seconds (downloading ~500MB from GCS). To eliminate this:
```bash
# Set minimum 1 instance so it stays warm
gcloud run services update cv-ml \
  --region $REGION \
  --min-instances 1
```
This costs ~$25–50/month extra but eliminates cold starts entirely.

### Worker container exits immediately

SSH into the VM and check logs:
```bash
docker logs cv-worker
```
Usually caused by a wrong Redis host/password or MongoDB URI. Fix the environment variable and restart:
```bash
docker stop cv-worker && docker rm cv-worker
# Re-run the docker run command with corrected values
```

### Frontend shows "Network Error" / API calls fail

The API URL is baked into the frontend at build time. If you see this:
1. Check `VITE_API_BASE_URL` matches your actual API service URL
2. Rebuild and redeploy the frontend with the correct URL

### `Permission denied` when ML service reads from GCS

The service account wasn't granted access. Run Step 14 again, or check:
```bash
gsutil iam get gs://chanmi-ml-models-$PROJECT_ID
```

### How to view Cloud Run logs

```bash
# Live logs
gcloud run services logs read cv-api --region $REGION --tail=50

# Or in the GCP Console:
# Cloud Run → select service → Logs tab
```

### How to update a secret

```bash
echo -n "NEW_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-
```

**Windows (PowerShell):**
```powershell
$tmp = [IO.Path]::GetTempFileName()
[IO.File]::WriteAllText($tmp, "NEW_VALUE")
gcloud secrets versions add SECRET_NAME --data-file=$tmp
Remove-Item $tmp
```

Cloud Run picks up the new version on the next request (no redeploy needed).

### Estimated costs

| Scenario | Monthly Cost |
|---|---|
| Low traffic (demo/dev) | $30–80 |
| Moderate traffic | $80–150 |
| ML service always warm (min=1) | +$30–50 |

The biggest cost lever is the ML service — keeping it at `min-instances 0` (scale to zero) saves the most money but means the first request after idle takes ~90 seconds.
