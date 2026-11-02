locals {
  name = "siga-inebi-prod"
  apis = toset([
    "run.googleapis.com", "artifactregistry.googleapis.com", "sqladmin.googleapis.com",
    "secretmanager.googleapis.com", "storage.googleapis.com", "iam.googleapis.com",
    "iamcredentials.googleapis.com", "cloudresourcemanager.googleapis.com", "sts.googleapis.com",
  ])
  labels = { application = "siga-inebi", environment = "prod", managed_by = "terraform" }
  # No DEMO_ADMIN_PASSWORD: production has no synthetic admin nor seed data.
  # ADMIN_PASSWORD seeds only the one-time createsuperuser job; the web service
  # and the migrate job never receive it.
  secrets = {
    DATABASE_PASSWORD = "database-password"
    DJANGO_SECRET_KEY = "django-secret-key"
    ADMIN_PASSWORD    = "admin-password"
  }
  runtime_env = {
    DJANGO_SETTINGS_MODULE = "config.settings.cloud_run"
    DJANGO_ENVIRONMENT     = "production"
    DJANGO_ALLOWED_HOSTS   = ".run.app,localhost,127.0.0.1"
    DATABASE_ENGINE        = "postgresql"
    DATABASE_NAME          = google_sql_database.prod.name
    DATABASE_USER          = google_sql_user.prod.name
    DATABASE_HOST          = "/cloudsql/${google_sql_database_instance.prod.connection_name}"
    DATABASE_PORT          = "5432"
    DATABASE_CONN_MAX_AGE  = "60"
    GCS_BUCKET_NAME        = google_storage_bucket.media.name
    STORAGE_SA_EMAIL       = google_service_account.runtime.email
    TIME_ZONE              = "America/Guatemala"
  }
}

resource "google_project_service" "apis" {
  for_each           = local.apis
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "prod" {
  location      = var.region
  repository_id = local.name
  format        = "DOCKER"
  description   = "Immutable reviewed production images"
  labels        = local.labels
  depends_on    = [google_project_service.apis]

  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-recent-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-older-than-7d"
    action = "DELETE"
    condition {
      older_than = "604800s"
    }
  }
}

resource "google_service_account" "runtime" {
  account_id   = local.name
  display_name = "SIGA INEBI production web and maintenance jobs"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_service_account_iam_member" "sign_self" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket" "media" {
  name                        = "${var.project_id}-${local.name}-media"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
  versioning { enabled = true }
  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "media" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "random_password" "secrets" {
  for_each = local.secrets
  length   = 48
  special  = false
}

resource "google_secret_manager_secret" "prod" {
  for_each  = local.secrets
  secret_id = "${local.name}-${each.value}"
  labels    = local.labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "prod" {
  for_each    = local.secrets
  secret      = google_secret_manager_secret.prod[each.key].id
  secret_data = random_password.secrets[each.key].result
}

resource "google_secret_manager_secret_iam_member" "runtime" {
  for_each  = local.secrets
  secret_id = google_secret_manager_secret.prod[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_sql_database_instance" "prod" {
  name                = "${local.name}-pg16"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true
  settings {
    tier                        = "db-f1-micro"
    edition                     = "ENTERPRISE"
    availability_type           = "ZONAL"
    disk_type                   = "PD_HDD"
    disk_size                   = 10
    disk_autoresize             = false
    deletion_protection_enabled = true
    user_labels                 = local.labels
    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
      # No authorized public client networks; use the authenticated SQL connector.
    }
    database_flags {
      name  = "timezone"
      value = "America/Guatemala"
    }
    backup_configuration {
      enabled                        = true
      start_time                     = "07:00"
      point_in_time_recovery_enabled = false
      backup_retention_settings {
        retained_backups = 3
        retention_unit   = "COUNT"
      }
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "prod" {
  name     = "siga_inebi_prod"
  instance = google_sql_database_instance.prod.name
}

resource "google_sql_user" "prod" {
  name     = "siga_inebi_prod"
  instance = google_sql_database_instance.prod.name
  password = random_password.secrets["DATABASE_PASSWORD"].result
}
