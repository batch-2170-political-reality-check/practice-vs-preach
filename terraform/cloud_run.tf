locals {
  registry_host = "${local.location}-docker.pkg.dev"
  image_repo    = "${data.google_project.project.project_id}/${data.google_project.project.project_id}"
  image_name    = "rag:${var.rag_image_tag}"
  rag_image     = "${local.registry_host}/${local.image_repo}/${local.image_name}"
}

# Enable required APIs
resource "google_project_service" "cloud_run" {
  project            = data.google_project.project.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  project            = data.google_project.project.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "project-registry" {
  location      = local.location
  repository_id = data.google_project.project.name
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]
}

resource "google_cloud_run_v2_service" "rag_service" {
  name     = "rag-service"
  location = local.location
  project  = data.google_project.project.project_id

  template {
    containers {
      image = local.rag_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        startup_cpu_boost = true
      }

      # # Environment variables
      # env {
      #   name  = "ENVIRONMENT"
      #   value = "production"
      # }

      # # If you need secrets (API keys, etc.)
      # env {
      #   name = "API_KEY"
      #   value_source {
      #     secret_key_ref {
      #       secret  = google_secret_manager_secret.api_key.secret_id
      #       version = "latest"
      #     }
      #   }
      # }

      ports {
        container_port = 8000
      }
    }

    # # Service account (recommended for security)
    # service_account = google_service_account.cloud_run_sa.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # depends_on = [google_project_service.cloud_run]
}

# Service publicly accessible (i.e. anyone can curl)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.rag_service.project
  location = google_cloud_run_v2_service.rag_service.location
  name     = google_cloud_run_v2_service.rag_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# # Service account for Cloud Run
# resource "google_service_account" "cloud_run_sa" {
#   project      = data.google_project.project.id
#   account_id   = "rag-cloud-run-sa"
#   display_name = "Cloud Run Service Account for RAG"
# }

# # Grant permissions (example: access to GCS for document storage)
# resource "google_project_iam_member" "cloud_run_storage" {
#   project = data.google_project.project.id
#   role    = "roles/storage.objectViewer"
#   member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
# }

# Output the service URL
output "rag_service_url" {
  value       = google_cloud_run_v2_service.rag_service.uri
  description = "URL of the deployed RAG service"
}
