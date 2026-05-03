locals {
  worker_startup_script = <<-SCRIPT
    #!/bin/bash
    set -euo pipefail
    exec > >(tee /var/log/worker-startup.log | logger -t startup-script) 2>&1

    echo "=== TalentScan Worker startup ==="
    echo "Started: $(date)"

    # 1. Install Docker if not present
    if ! command -v docker &>/dev/null; then
      curl -fsSL https://get.docker.com | sh
      systemctl enable docker
      systemctl start docker
    fi

    # 2. Install gcloud if not present
    if ! command -v gcloud &>/dev/null; then
      curl -sSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
        | tar xz -C /opt
      /opt/google-cloud-sdk/install.sh --quiet
      ln -sf /opt/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud
    fi

    # 3. Authenticate Docker with Artifact Registry using the attached service account
    gcloud auth configure-docker ${var.region}-docker.pkg.dev --quiet

    # 4. Fetch secrets from Secret Manager
    get_secret() { gcloud secrets versions access latest --secret="$1" --project="${var.project_id}"; }

    MONGO_URI=$(get_secret "mongo-uri")
    MONGO_DB=$(get_secret "mongo-db")
    JWT_SECRET=$(get_secret "jwt-secret")
    OPENAI_API_KEY=$(get_secret "openai-key")
    REDIS_HOST=$(get_secret "redis-host")
    REDIS_PORT=$(get_secret "redis-port")
    REDIS_PASSWORD=$(get_secret "redis-password")
    GNEWS_API_KEY=$(get_secret "gnews-key")
    HIREBASE_API_KEY=$(get_secret "hirebase-key")
    GEOCODING_API_KEY=$(get_secret "geocoding-key")
    GITHUB_TOKEN=$(get_secret "github-token")
    BREVO_API_KEY=$(get_secret "brevo-key")
    INTERNAL_SERVICE_SECRET=$(get_secret "internal-secret")

    # 5. Pull the latest worker image
    WORKER_IMAGE="${var.region}-docker.pkg.dev/${var.project_id}/${var.registry_name}/cv-worker:${var.worker_image_tag}"
    docker pull "$WORKER_IMAGE"

    # 6. Stop and remove old container (idempotent)
    docker stop cv-worker 2>/dev/null || true
    docker rm   cv-worker 2>/dev/null || true

    # 7. Start worker container
    docker run -d \
      --name cv-worker \
      --restart=always \
      --log-driver=gcplogs \
      --log-opt gcp-project="${var.project_id}" \
      -e SERVICE_TYPE=worker \
      -e MONGO_URI="$MONGO_URI" \
      -e MONGO_DB="$MONGO_DB" \
      -e JWT_SECRET="$JWT_SECRET" \
      -e JWT_ALGORITHM="HS256" \
      -e OPENAI_API_KEY="$OPENAI_API_KEY" \
      -e OPENAI_MODEL="${var.openai_model}" \
      -e OPENAI_EMBEDDING_MODEL="${var.openai_embedding_model}" \
      -e LLM_PROVIDER="${var.llm_provider}" \
      -e EMBEDDING_PROVIDER="${var.embedding_provider}" \
      -e REDIS_HOST="$REDIS_HOST" \
      -e REDIS_PORT="$REDIS_PORT" \
      -e REDIS_DB="${var.redis_db}" \
      -e REDIS_PASSWORD="$REDIS_PASSWORD" \
      -e GCS_BUCKET_NAME="${google_storage_bucket.ml_models.name}" \
      -e GCS_MODEL_PREFIX="${var.gcs_model_prefix}" \
      -e GNEWS_API_KEY="$GNEWS_API_KEY" \
      -e HIREBASE_API_KEY="$HIREBASE_API_KEY" \
      -e GEOCODING_API_KEY="$GEOCODING_API_KEY" \
      -e GITHUB_TOKEN="$GITHUB_TOKEN" \
      -e BREVO_API_KEY="$BREVO_API_KEY" \
      -e BREVO_SENDER_EMAIL="${var.brevo_sender_email}" \
      -e BREVO_SENDER_NAME="${var.brevo_sender_name}" \
      -e INTERNAL_SERVICE_SECRET="$INTERNAL_SERVICE_SECRET" \
      "$WORKER_IMAGE"

    echo "cv-worker started. $(docker ps --filter name=cv-worker --format 'Status: {{.Status}}')"
    echo "=== Startup complete: $(date) ==="
  SCRIPT
}

# ── GCE Worker VM ─────────────────────────────────────────────────────────────

resource "google_compute_instance" "worker" {
  name         = "talent-scan-worker"
  machine_type = var.worker_machine_type
  zone         = var.zone
  tags         = ["talent-scan-worker"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = var.worker_disk_size_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  service_account {
    email  = google_service_account.worker.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = local.worker_startup_script

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  depends_on = [
    google_service_account.worker,
    google_storage_bucket_iam_member.worker_gcs_read,
    google_artifact_registry_repository_iam_member.worker_ar_read,
    google_secret_manager_secret_iam_member.secret_access,
  ]
}

# ── Firewall: SSH via IAP only ────────────────────────────────────────────────

resource "google_compute_firewall" "worker_ssh_iap" {
  name    = "talent-scan-worker-ssh-iap"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  target_tags   = ["talent-scan-worker"]
  source_ranges = ["35.235.240.0/20"] # Google IAP IP range
  direction     = "INGRESS"
}
