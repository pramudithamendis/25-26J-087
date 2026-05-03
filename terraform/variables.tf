variable "project_id" {
  description = "GCP project ID."
  type        = string
  default     = "talent-scan-ai"
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for the worker GCE VM."
  type        = string
  default     = "us-central1-a"
}

variable "registry_name" {
  description = "Artifact Registry Docker repository name."
  type        = string
  default     = "talent-scan-ai"
}

variable "ml_models_bucket_name" {
  description = "GCS bucket that stores ML model files."
  type        = string
  default     = "ml-models-talent-scan-ai"
}

variable "gcs_model_prefix" {
  description = "Path prefix inside the ML models bucket."
  type        = string
  default     = "models/"
}

# ── Cloud Run sizing ──────────────────────────────────────────────────────────

variable "ml_min_instances" {
  description = "Min instances for ML service. 1 keeps BERT warm (avoids 90s cold start), costs ~$40/month extra."
  type        = number
  default     = 1
}

variable "ml_max_instances" {
  description = "Max instances for ML service."
  type        = number
  default     = 2
}

variable "api_max_instances" {
  description = "Max instances for the API service."
  type        = number
  default     = 3
}

variable "frontend_max_instances" {
  description = "Max instances for the frontend service."
  type        = number
  default     = 10
}

# ── Worker VM ─────────────────────────────────────────────────────────────────

variable "worker_machine_type" {
  description = "GCE machine type for the always-on worker VM."
  type        = string
  default     = "e2-small"
}

variable "worker_disk_size_gb" {
  description = "Boot disk size in GB for the worker VM."
  type        = number
  default     = 20
}

# ── Image tags (updated by GitHub Actions on each deploy) ────────────────────

variable "api_image_tag" {
  description = "Docker image tag for the API service."
  type        = string
  default     = "latest"
}

variable "ml_image_tag" {
  description = "Docker image tag for the ML service."
  type        = string
  default     = "latest"
}

variable "worker_image_tag" {
  description = "Docker image tag for the worker."
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Docker image tag for the frontend."
  type        = string
  default     = "latest"
}

# ── Non-secret env overrides ──────────────────────────────────────────────────

variable "openai_model" {
  type    = string
  default = "gpt-3.5-turbo"
}

variable "openai_embedding_model" {
  type    = string
  default = "text-embedding-ada-002"
}

variable "llm_provider" {
  type    = string
  default = "openai"
}

variable "embedding_provider" {
  type    = string
  default = "openai"
}

variable "cv_extraction_method" {
  type    = string
  default = "openai"
}

variable "mongo_db" {
  type    = string
  default = "cv_db"
}

variable "redis_db" {
  type    = string
  default = "0"
}

variable "brevo_sender_email" {
  type    = string
  default = ""
}

variable "brevo_sender_name" {
  type    = string
  default = "TalentScan AI"
}
