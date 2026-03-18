output "cloud_run_url" {
  description = "Public URL of the FastAPI backend"
  value       = google_cloud_run_v2_service.api.uri
}

output "db_public_ip" {
  description = "Cloud SQL public IP"
  value       = google_sql_database_instance.main.public_ip_address
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.main.host
}

output "artifact_registry_url" {
  description = "Docker registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/log-analytics"
}