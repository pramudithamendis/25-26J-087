terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Remote state stored in GCS.
  # The bucket must exist before running `terraform init`.
  # Create it once manually: gsutil mb -l us-central1 gs://talent-scan-ai-tfstate
  backend "gcs" {
    bucket = "talent-scan-ai-tfstate"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
