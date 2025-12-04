locals {
  registry_host = "${local.location}-docker.pkg.dev"
  image_repo    = "${data.google_project.project.project_id}/${data.google_project.project.project_id}"
  image_name    = "rag:${var.rag_image_tag}"
  rag_image     = "${local.registry_host}/${local.image_repo}/${local.image_name}"

  env_vars = {
    PERSIST_DIR  = "data/chroma_store"
    SPEECHES_CSV = "data/speeches-wahlperiode-21-small.csv"
  }
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

resource "google_project_service" "secret_manager" {
  project            = data.google_project.project.project_id
  service            = "secretmanager.googleapis.com"
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

      dynamic "env" {
        for_each = local.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        startup_cpu_boost = true
      }

      # Secrets
      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8000
      }
    }

    # Service account (recommended for security)
    service_account = google_service_account.project_sa.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.cloud_run]
}

# Service publicly accessible (i.e. anyone can curl)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.rag_service.project
  location = google_cloud_run_v2_service.rag_service.location
  name     = google_cloud_run_v2_service.rag_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# # Grant permissions (example: access to GCS for document storage)
# resource "google_project_iam_member" "cloud_run_storage" {
#   project = data.google_project.project.project_id
#   role    = "roles/storage.objectViewer"
#   member  = "serviceAccount:${google_service_account.project_sa.email}"
# }

# Create API key in https://console.cloud.google.com/apis/credentials. Then
# `printf "YOUR_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-`
#
# Make sure the secret doesn't have a trailing \n:
# `gcloud secrets versions access 2 --secret=gemini-api-key --out-file=/tmp/secret`
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secret_manager]
}

# Grant Cloud Run access to the secret
resource "google_secret_manager_secret_iam_member" "cloud_run_secret_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.project_sa.email}"
}

# Output the service URL
output "rag_service_url" {
  value       = google_cloud_run_v2_service.rag_service.uri
  description = "URL of the deployed RAG service"
}
