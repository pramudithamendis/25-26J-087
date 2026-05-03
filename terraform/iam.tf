# ── Service accounts ──────────────────────────────────────────────────────────

resource "google_service_account" "api" {
  account_id   = "talentscan-api"
  display_name = "TalentScan API — Cloud Run"
}

resource "google_service_account" "ml" {
  account_id   = "talentscan-ml"
  display_name = "TalentScan ML — Cloud Run"
}

resource "google_service_account" "frontend" {
  account_id   = "talentscan-frontend"
  display_name = "TalentScan Frontend — Cloud Run"
}

resource "google_service_account" "worker" {
  account_id   = "talentscan-worker"
  display_name = "TalentScan Worker — GCE VM"
}

resource "google_service_account" "cicd" {
  account_id   = "talentscan-cicd"
  display_name = "TalentScan CI/CD — GitHub Actions"
}

# ── Secret access (least-privilege per service) ───────────────────────────────

locals {
  secret_bindings = {
    api = [
      "mongo-uri", "mongo-db", "jwt-secret", "openai-key", "internal-secret",
      "gnews-key", "hirebase-key", "geocoding-key", "github-token", "brevo-key",
      "redis-host", "redis-port", "redis-password"
    ]
    ml = [
      "mongo-uri", "mongo-db", "jwt-secret", "openai-key", "internal-secret"
    ]
    worker = [
      "mongo-uri", "mongo-db", "jwt-secret", "openai-key",
      "gnews-key", "hirebase-key", "geocoding-key", "github-token", "brevo-key",
      "redis-host", "redis-port", "redis-password"
    ]
  }

  secret_binding_pairs = flatten([
    for sa_key, secrets in local.secret_bindings : [
      for secret_id in secrets : {
        sa_key    = sa_key
        secret_id = secret_id
      }
    ]
  ])
}

resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = {
    for pair in local.secret_binding_pairs :
    "${pair.sa_key}--${pair.secret_id}" => pair
  }

  secret_id = data.google_secret_manager_secret.secrets[each.value.secret_id].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member = (
    each.value.sa_key == "api"    ? "serviceAccount:${google_service_account.api.email}" :
    each.value.sa_key == "ml"     ? "serviceAccount:${google_service_account.ml.email}" :
    "serviceAccount:${google_service_account.worker.email}"
  )
}

# ── GCS: ML service and worker can read model files ───────────────────────────

resource "google_storage_bucket_iam_member" "ml_gcs_read" {
  bucket = google_storage_bucket.ml_models.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ml.email}"
}

resource "google_storage_bucket_iam_member" "worker_gcs_read" {
  bucket = google_storage_bucket.ml_models.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.worker.email}"
}

# ── Artifact Registry: worker VM can pull images ──────────────────────────────

resource "google_artifact_registry_repository_iam_member" "worker_ar_read" {
  location   = var.region
  repository = google_artifact_registry_repository.main.repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.worker.email}"
}

# ── Artifact Registry: CI/CD can push images ──────────────────────────────────

resource "google_artifact_registry_repository_iam_member" "cicd_ar_write" {
  location   = var.region
  repository = google_artifact_registry_repository.main.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.cicd.email}"
}

# ── Cloud Run: CI/CD can deploy services ──────────────────────────────────────

resource "google_project_iam_member" "cicd_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_compute_admin" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_iam_token" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_project_iam_member" "cicd_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

# ── Cloud Run public access (frontend + API) ──────────────────────────────────

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  name     = google_cloud_run_v2_service.frontend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ML service: internal ingress blocks internet traffic.
# allUsers invoker allows the API service to call it without identity tokens
# (API authenticates via INTERNAL_SERVICE_SECRET header instead).
resource "google_cloud_run_v2_service_iam_member" "ml_internal_invoker" {
  name     = google_cloud_run_v2_service.ml.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
