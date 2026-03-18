# Docker image registry for our container images
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "log-analytics"
  description   = "Docker images for log analytics engine"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
}