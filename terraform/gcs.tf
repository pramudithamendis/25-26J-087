# ML model storage bucket — already exists, import before first apply:
#   terraform import google_storage_bucket.ml_models ml-models-talent-scan-ai

resource "google_storage_bucket" "ml_models" {
  name                        = var.ml_models_bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  lifecycle {
    prevent_destroy = true
  }
}
