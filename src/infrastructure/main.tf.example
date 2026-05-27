locals {
  # Variables which can occur in multiple places in configuration
  apps_path = "${path.module}/../apps"
  ingress_port = 80
}

module "development" {
  k8s_base_path           = "${path.module}/modules/kubernetes"
  source = "./modules/terraform"

  # Build argument
  # --------------
  cluster_create          = var.cluster_create
  deployment_target       = var.deployment_target
  gpu_used                = var.gpu_used
  profiles                = var.profiles

  # Main configuration
  # ------------------
  cluster_name            = "pixie"
  project_namespace_name  = "pixie"
  argo_workflows_version  = "0.45.26"
  ingress_host            = "localhost"
  ingress_port            = local.ingress_port

  # Applications
  # ------------
  # Preload base images for Argo Workflows
  base_images_to_load = [
    "python:3.11-alpine"
  ]

  storage_classes = {
    fast_storage = {
      name = "fast-storage"
      provisioner = "rancher.io/local-path"
      reclaim_policy = "Delete"
      volume_binding_mode = "WaitForFirstConsumer"
    }
  }

  services = {
    /*
    database_server = {
      service = {
        container_name      = "pixie-db"
        ports = [
          {
            name            = "http"
            target_port     = 5432
            service_port    = 5432
            protocol        = "TCP"
          }
        ]
      }


      statefulset = {
        replica_count   = 1
        image_name      = "pixie-db"
        image_tag       = "1.0.2"
        docker_context  = local.apps_path
        dockerfile_path = "${local.apps_path}/database_server"
        request_cpu     = "128m"
        request_memory  = "128Mi"
        limit_cpu       = "256m"
        limit_memory    = "256Mi"
        restart         = "Always"
        env_file        = ".env" # Path starting relatively from Dockerfile path
        data_volumes = {
          pgdata = { # Only a-z, A-Z, digits and - allowed
            mount_path         = "/var/lib/app/data"
            storage_request    = "1Gi"
            storage_class_name = "fast-storage"
            access_mode        = "ReadWriteOnce"
          }
        }
      }
    }
    */
    /*
    pixie-vector-db = {
      service = {
        container_name      = "pixie-vector-db"
        ports = [
          {
            name            = "http"
            target_port     = 6333
            service_port    = 6333
            protocol        = "TCP"
          },
          {
            name            = "grpc"
            target_port     = 6334
            service_port    = 6334
            protocol        = "TCP"
          }
        ]
      }

      statefulset = {
        replica_count   = 1
        image_name      = "pixie-vector-db"
        image_tag       = "1.0.2"
        docker_context  = local.apps_path
        dockerfile_path = "${local.apps_path}/vector_server"
        request_cpu     = "500m"
        request_memory  = "1Gi"
        limit_cpu       = "1000m"
        limit_memory    = "4Gi"
        restart         = "Always"
        data_volumes = {
          qdrant-data = { # Only a-z, A-Z, digits and - allowed
            mount_path         = "/qdrant/storage"
            storage_request    = "1Gi"
            storage_class_name = "fast-storage"
            access_mode        = "ReadWriteOnce"
          }
        }
      }
    }
    */

    /*
    pixie-ingest = {
      service = {
        container_name      = "pixie-ingest"
        ports = [
          {
            name            = "http"
            target_port     = 8080
            service_port    = local.ingress_port
            protocol        = "TCP"
          }
        ]
      }

      deployment = {
        replica_count   = 1

        # Remote Docker apps, e.g. (note: this one uses port 80, doesn't have liveness or readiness checks, and does not have a .env file):
        # image_name      = "tiangolo/uvicorn-gunicorn-fastapi"
        # image_tag       = "python3.10"
        # docker_context  = null
        # dockerfile_path = null

        # Local Docker apps
        image_name      = "pixie-ingest"
        image_tag       = "1.0.0"
        docker_context  = local.apps_path
        dockerfile_path = "${local.apps_path}/ingest_server"
        request_cpu     = "128m"
        request_memory  = "128Mi"
        limit_cpu       = "256m"
        limit_memory    = "256Mi"
        restart         = "Always" # Always (default), OnFailure, Never
        env_file        = ".env" # Path starting relatively from Dockerfile path
        # environment overrides any variables with the same name that are loaded from env_file
        # environment = {
        #   X=""
        #   Y=""
        # }
        # depends_on = { pixie-vector-db = { http_path = "/readyz" } }
        # NOTE: Probes are run from the container, not externally and thus not via ingress controller or gateway!!!
        # So we use INTERNAL port number and internal path.
        liveness_probe = {
          target_port           = 8080
          # Using an exec command similar to Docker Compose healthcheck 'test'
          command               = ["sh", "-c", "wget -q -O /dev/null http://localhost:${8080}/livez || exit 1"]
          # path                  = "/livez" # or we can use the path
          initial_delay_seconds = 60
          period_seconds        = 1200
          timeout_seconds       = 3
          failure_threshold     = 3
        }
        readiness_probe = {
          target_port           = 8080
          # Readiness continues to use the HTTP GET path
          path                  = "/readyz"
          initial_delay_seconds = 30
          period_seconds        = 300
          timeout_seconds       = 3 # Adding default timeout
          success_threshold     = 3
          failure_threshold     = 2
        }
      }
      ingress = {
        path = "/ingest"
      }
    }
    */
    /**/
    pixie-embedding-model = {
      profiles = [
        "all"
      ]
      service = {
        container_name      = "pixie-embedding-model"
        ports = [
          {
            name            = "http"
            target_port     = 8000
            service_port    = local.ingress_port
            protocol        = "TCP"
          }
        ]
      }
      deployment = {
        replica_count   = 1
        # Local Docker apps
        image_name      = "pixie-embedding-model"
        image_tag       = "1.0.0"
        docker_context  = local.apps_path
        dockerfile_path = "${local.apps_path}/embedding_model"
        command         = "uvicorn main:app --host 0.0.0.0 --port 8000"
        request_cpu     = "128m"
        request_memory  = "1024Mi"
        limit_cpu       = "256m"
        limit_memory    = "1024Mi"
        limit_gpu       = 1
        restart         = "Always" # Always (default), OnFailure, Never
      }
      ingress = {
        path = "/embedding-model"
      }
    }
    /*
    pixie-ingest-dup = {
      service = {
        container_name      = "pixie-ingest-dup"
        ports = [
          {
            name            = "http"
            target_port     = 8080
            service_port    = local.ingress_port
            protocol        = "TCP"
          }
        ]
      }

      deployment = {
        replica_count   = 1

        # Remote Docker apps, e.g. (note: this one uses port 80, doesn't have liveness or readiness checks, and does not have a .env file):
        # image_name      = "tiangolo/uvicorn-gunicorn-fastapi"
        # image_tag       = "python3.10"
        # docker_context  = null
        # dockerfile_path = null

        # Local Docker apps
        image_name      = "pixie-ingest-dup"
        image_tag       = "1.0.0"
        docker_context  = local.apps_path
        dockerfile_path = "${local.apps_path}/ingest_server"
        request_cpu     = "128m"
        request_memory  = "128Mi"
        limit_cpu       = "256m"
        limit_memory    = "256Mi"
        restart         = "Always" # Always (default), OnFailure, Never
        env_file        = ".env" # Path starting relatively from Dockerfile path
        # environment overrides any variables with the same name that are loaded from env_file
        # environment = {
        #   X=""
        #   Y=""
        # }
        # depends_on = { pixie-vector-db = { http_path = "/readyz" } }
        # NOTE: Probes are run from the container, not externally and thus not via ingress controller or gateway!!!
        # So we use INTERNAL port number and internal path.
        liveness_probe = {
          target_port           = 8080
        # Using an exec command similar to Docker Compose healthcheck 'test'
          command               = ["sh", "-c", "wget -q -O /dev/null http://localhost:${8080}/livez || exit 1"]
          # path                  = "/livez" # or we can use the path
          initial_delay_seconds = 60
          period_seconds        = 1200
          timeout_seconds       = 3
          failure_threshold     = 3
        }
        readiness_probe = {
          # Readiness continues to use the HTTP GET path
          target_port           = 8080
          path                  = "/readyz"
          initial_delay_seconds = 30
          period_seconds        = 300
          timeout_seconds       = 3 # Adding default timeout
          success_threshold     = 3
          failure_threshold     = 2
        }
      }
      ingress = {
        path = "/ingestdup"
      }
    }
    */
  }
}
