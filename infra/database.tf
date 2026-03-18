# Cloud SQL — Postgres 16
resource "google_sql_database_instance" "main" {
  name             = "log-analytics-db"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"   # cheapest tier — fine for dev
    availability_type = "ZONAL"
    disk_size         = 10
    disk_autoresize   = false

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "allow-all-dev"
        value = "0.0.0.0/0"   # restrict this in production
      }
    }
  }

  deletion_protection = false   # allow easy cleanup
}

resource "google_sql_database" "logdb" {
  name     = "logdb"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "loguser" {
  name     = "loguser"
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# Redis — Memorystore
resource "google_redis_instance" "main" {
  name           = "log-analytics-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  depends_on = [google_project_service.redis]
}