locals {
  registry_base = "${var.region}-docker.pkg.dev/${var.project_id}/${var.registry_name}"

  secret_ref = {
    for k in local.secret_ids :
    k => data.google_secret_manager_secret.secrets[k].secret_id
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# ML SERVICE  (internal-only, 8GB RAM, min 1 instance to keep BERT warm)
# ─────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "ml" {
  name     = "cv-ml"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.ml.email

    scaling {
      min_instance_count = var.ml_min_instances
      max_instance_count = var.ml_max_instances
    }

    # Allow up to 15 minutes for initial model download + BERT loading
    timeout = "900s"

    containers {
      image = "${local.registry_base}/cv-ml:${var.ml_image_tag}"

      resources {
        limits = {
          memory = "8Gi"
          cpu    = "2"
        }
        startup_cpu_boost = true
        cpu_idle          = false
      }

      ports {
        container_port = 8080
      }

      # ── Non-secret env vars ──────────────────────────────────────────────────

      env {
        name  = "SERVICE_TYPE"
        value = "ml"
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.ml_models.name
      }
      env {
        name  = "GCS_MODEL_PREFIX"
        value = var.gcs_model_prefix
      }
      env {
        name  = "OPENAI_MODEL"
        value = var.openai_model
      }
      env {
        name  = "OPENAI_EMBEDDING_MODEL"
        value = var.openai_embedding_model
      }
      env {
        name  = "LLM_PROVIDER"
        value = var.llm_provider
      }
      env {
        name  = "EMBEDDING_PROVIDER"
        value = var.embedding_provider
      }
      env {
        name  = "CV_EXTRACTION_METHOD"
        value = var.cv_extraction_method
      }
      env {
        name  = "REDIS_DB"
        value = var.redis_db
      }
      # Prevent OpenMP conflict between PyTorch and CatBoost (causes SIGSEGV on load)
      env {
        name  = "KMP_DUPLICATE_LIB_OK"
        value = "TRUE"
      }
      env {
        name  = "OMP_NUM_THREADS"
        value = "1"
      }
      env {
        name  = "TOKENIZERS_PARALLELISM"
        value = "false"
      }

      # ── Secrets ──────────────────────────────────────────────────────────────

      env {
        name = "MONGO_URI"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["mongo-uri"]
            version = "latest"
          }
        }
      }
      env {
        name = "MONGO_DB"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["mongo-db"]
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["jwt-secret"]
            version = "latest"
          }
        }
      }
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["openai-key"]
            version = "latest"
          }
        }
      }
      env {
        name = "INTERNAL_SERVICE_SECRET"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["internal-secret"]
            version = "latest"
          }
        }
      }

      # TCP probe: waits for uvicorn to bind port 8080.
      # Heavy ML imports (torch + transformers) take 60-90s before uvicorn starts.
      # failure_threshold=18 gives 5 + 18*10 = 185s total — enough headroom.
      startup_probe {
        tcp_socket {
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 18
      }

      # HTTP liveness starts only after 10 min — enough for GCS download + BERT load.
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 600
        timeout_seconds       = 10
        period_seconds        = 60
        failure_threshold     = 3
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.secret_access,
    google_storage_bucket_iam_member.ml_gcs_read,
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# API SERVICE  (public, 512MB, scale 0→3)
# ─────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "api" {
  name     = "cv-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.api_max_instances
    }

    containers {
      image = "${local.registry_base}/cv-api:${var.api_image_tag}"

      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1"
        }
        cpu_idle = true
      }

      ports {
        container_port = 8080
      }

      # ── Non-secret env vars ──────────────────────────────────────────────────

      env {
        name  = "SERVICE_TYPE"
        value = "api"
      }
      env {
        name  = "ML_SERVICE_URL"
        value = google_cloud_run_v2_service.ml.uri
      }
      env {
        name  = "OPENAI_MODEL"
        value = var.openai_model
      }
      env {
        name  = "OPENAI_EMBEDDING_MODEL"
        value = var.openai_embedding_model
      }
      env {
        name  = "LLM_PROVIDER"
        value = var.llm_provider
      }
      env {
        name  = "EMBEDDING_PROVIDER"
        value = var.embedding_provider
      }
      env {
        name  = "CV_EXTRACTION_METHOD"
        value = var.cv_extraction_method
      }
      env {
        name  = "REDIS_DB"
        value = var.redis_db
      }
      env {
        name  = "BREVO_SENDER_EMAIL"
        value = var.brevo_sender_email
      }
      env {
        name  = "BREVO_SENDER_NAME"
        value = var.brevo_sender_name
      }

      # ── Secrets ──────────────────────────────────────────────────────────────

      env {
        name = "MONGO_URI"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["mongo-uri"]
            version = "latest"
          }
        }
      }
      env {
        name = "MONGO_DB"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["mongo-db"]
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["jwt-secret"]
            version = "latest"
          }
        }
      }
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["openai-key"]
            version = "latest"
          }
        }
      }
      env {
        name = "INTERNAL_SERVICE_SECRET"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["internal-secret"]
            version = "latest"
          }
        }
      }
      env {
        name = "GNEWS_API_KEY"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["gnews-key"]
            version = "latest"
          }
        }
      }
      env {
        name = "HIREBASE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["hirebase-key"]
            version = "latest"
          }
        }
      }
      env {
        name = "GEOCODING_API_KEY"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["geocoding-key"]
            version = "latest"
          }
        }
      }
      env {
        name = "GITHUB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["github-token"]
            version = "latest"
          }
        }
      }
      env {
        name = "BREVO_API_KEY"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["brevo-key"]
            version = "latest"
          }
        }
      }
      env {
        name = "REDIS_HOST"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["redis-host"]
            version = "latest"
          }
        }
      }
      env {
        name = "REDIS_PORT"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["redis-port"]
            version = "latest"
          }
        }
      }
      env {
        name = "REDIS_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = local.secret_ref["redis-password"]
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 12
      }
    }
  }

  depends_on = [
    google_cloud_run_v2_service.ml,
    google_secret_manager_secret_iam_member.secret_access,
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND SERVICE  (public, 256MB, scale 0→10)
# ─────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  name     = "cv-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.frontend.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.frontend_max_instances
    }

    containers {
      image = "${local.registry_base}/cv-frontend:${var.frontend_image_tag}"

      resources {
        limits = {
          memory = "256Mi"
          cpu    = "1"
        }
        cpu_idle = true
      }

      ports {
        container_port = 8080
      }
    }
  }

  depends_on = [google_cloud_run_v2_service.api]
}
