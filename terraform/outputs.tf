output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "artifact_registry_url" {
  description = "Base image URL prefix for docker push / pull."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.registry_name}"
}

output "frontend_url" {
  description = "Public URL of the React frontend."
  value       = google_cloud_run_v2_service.frontend.uri
}

output "api_url" {
  description = "Public URL of the FastAPI service. Pass as VITE_API_BASE_URL when building the frontend image."
  value       = google_cloud_run_v2_service.api.uri
}

output "ml_url" {
  description = "Internal URL of the ML service (only reachable within GCP)."
  value       = google_cloud_run_v2_service.ml.uri
}

output "worker_vm_ip" {
  description = "External IP of the worker VM (for SSH)."
  value       = google_compute_instance.worker.network_interface[0].access_config[0].nat_ip
}

output "ml_models_bucket" {
  value = google_storage_bucket.ml_models.name
}
