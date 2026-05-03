# This repository already exists (created manually).
# Import it once before terraform apply:
#   terraform import google_artifact_registry_repository.main \
#     projects/talent-scan-ai/locations/us-central1/repositories/talent-scan-ai

resource "google_artifact_registry_repository" "main" {
  repository_id = var.registry_name
  format        = "DOCKER"
  location      = var.region
  description   = "Docker images for TalentScan AI (frontend, api, ml, worker)"

  cleanup_policies {
    id     = "keep-10-most-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "1209600s" # 14 days
    }
  }
}
