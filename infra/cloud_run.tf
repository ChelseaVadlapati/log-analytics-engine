# Service account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "log-analytics-run"
  display_name = "Log Analytics Cloud Run SA"
}

# Cloud Run — FastAPI backend
resource "google_cloud_run_v2_service" "api" {
  name     = "log-analytics-api"
  location = var.region

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      # Image will be updated by CI/CD after first build
      image = "${var.region}-docker.pkg.dev/${var.project_id}/log-analytics/api:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "ELASTICSEARCH_URL"
        value = "http://localhost:9200"   # update after ES deploy
      }

      env {
        name  = "POSTGRES_URL"
        value = "postgresql://loguser:${var.db_password}@${google_sql_database_instance.main.public_ip_address}/logdb"
      }
    }
  }

  depends_on = [
    google_project_service.run,
    google_artifact_registry_repository.main,
  ]
}

# Make Cloud Run service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}