# Secrets are created and managed outside Terraform (via gcloud).
# We use data sources to reference them — no import required.

locals {
  secret_ids = [
    "mongo-uri",
    "mongo-db",
    "jwt-secret",
    "openai-key",
    "internal-secret",
    "gnews-key",
    "hirebase-key",
    "geocoding-key",
    "github-token",
    "brevo-key",
    "redis-host",
    "redis-port",
    "redis-password",
  ]
}

data "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secret_ids)
  secret_id = each.key
  project   = var.project_id
}
