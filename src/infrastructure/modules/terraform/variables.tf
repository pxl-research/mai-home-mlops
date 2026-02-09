variable "cluster_create" {
  description = "A flag to determine if the cluster resource should be created."
  type        = bool
  default     = false
}

variable "deployment_target" {
  description = "Deployment target. Can be 'local_wsl2', 'local_linux' or 'azure'"
  type        = string
  default     = "local_wsl2"
}

variable "gpu_used" {
  description = "A flag to determine if the cluster uses GPU."
  type        = bool
  default     = false
}

variable "profiles" {
  type    = list(string)
  default = ["all"]
}

variable "cluster_name" {
  description = "The name to assign to the Kubernetes cluster (e.g., kind cluster name)."
  type        = string
  default     = "kind"
}

variable "project_namespace_name" {
  description = "The primary Kubernetes namespace for the application deployment."
  type        = string
  default     = "default"
}

variable "ingress_namespace_name" {
  description = "The Kubernetes namespace where the Ingress Controller will be installed."
  type        = string
  default     = "ingress-nginx"
}

variable "storage_classes" {
  description = "A map of storage class configurations, where the map keys are local references and the values define the properties of the StorageClass object."
  type = map(object({
    name                = string
    provisioner         = string
    reclaim_policy      = string
    volume_binding_mode = string
  }))
  default = {}
}

variable "services" {
  description = "A map containing configuration details for dynamic application deployment (Docker, k8s manifest values)."
  type = map(object({
    profiles = optional(list(string), ["all"])

    service = object({
      container_name = string
      ports = list(object({
        name          = string
        target_port   = number
        service_port  = number
        protocol      = string
      }))
    })

    deployment = optional(object({
      replica_count           = optional(number, 1)
      image_name              = string
      image_tag               = string
      docker_context          = optional(string, null)
      dockerfile_path         = optional(string, null)
      command                 = optional(string, null)
      request_cpu             = string
      request_memory          = string
      limit_cpu               = string
      limit_memory            = string
      limit_gpu               = optional(number, 0)
      platform_os             = optional(string, "linux")
      platform_architecture   = optional(string, "amd64")
      restart                 = optional(string, "Always")
      env_file                = optional(string, null)
      environment             = optional(map(string), {})
      # depends_on              = optional(list(string), [])
      depends_on = optional(map(object({
        # The key of this map is the name of the dependent app (e.g., "vector_server").
        # The value is the configuration for the Init Container's check.

        # The port to check on the dependency. Defaults to the dependency's service_port.
        check_port: optional(number),

        # If provided, use this HTTP path (e.g., "/health"). This implies an HTTP check.
        http_path: optional(string),

        # If provided, use this command array (e.g., ["nc", "-z"]). This implies an EXEC check.
        exec_command: optional(list(string)),
      })), {})
      liveness_probe = optional(object({
        target_port           = number
        path                  = optional(string, null)       # for httpGet
        command               = optional(list(string), null) # for exec (e.g., ["sh", "-c", "curl -f http://localhost:8000/livez || exit 1"])
        initial_delay_seconds = optional(number, 60)
        period_seconds        = optional(number, 1200)
        timeout_seconds       = optional(number, 3)
        failure_threshold     = optional(number, 3)
      }), null)
      readiness_probe = optional(object({
        target_port           = number
        path                  = optional(string, null)       # for httpGet
        command               = optional(list(string), null) # for exec
        initial_delay_seconds = optional(number, 30)
        period_seconds        = optional(number, 300)
        timeout_seconds       = optional(number, 3)
        success_threshold     = optional(number, 3)
        failure_threshold     = optional(number, 2)
      }), null)
    }), null)

    statefulset = optional(object({
      replica_count          = optional(number, 1)
      image_name             = string
      image_tag              = string
      docker_context         = string
      dockerfile_path        = string
      command                = optional(string, null)
      request_cpu            = string
      request_memory         = string
      limit_cpu              = string
      limit_memory           = string
      limit_gpu              = optional(number, 0)
      platform_os            = optional(string, "linux")
      platform_architecture  = optional(string, "amd64")
      restart                = optional(string, "Always")
      env_file               = optional(string, null)
      environment            = optional(map(string), {})
      # depends_on             = optional(list(string), [])
      depends_on = optional(map(object({
        # The key of this map is the name of the dependent app (e.g., "vector_server").
        # The value is the configuration for the Init Container's check.

        # The port to check on the dependency. Defaults to the dependency's service_port.
        check_port: optional(number),

        # If provided, use this HTTP path (e.g., "/health"). This implies an HTTP check.
        http_path: optional(string),

        # If provided, use this command array (e.g., ["nc", "-z"]). This implies an EXEC check.
        exec_command: optional(list(string)),
      })), {})
      liveness_probe = optional(object({
        target_port           = number
        path                  = optional(string, null)       # for httpGet
        command               = optional(list(string), null) # for exec (e.g., ["sh", "-c", "curl -f http://localhost:8000/livez || exit 1"])
        initial_delay_seconds = optional(number, 60)
        period_seconds        = optional(number, 1200)
        timeout_seconds       = optional(number, 3)
        failure_threshold     = optional(number, 3)
      }), null)
      readiness_probe = optional(object({
        target_port           = number
        path                  = optional(string, null)       # for httpGet
        command               = optional(list(string), null) # for exec
        initial_delay_seconds = optional(number, 30)
        period_seconds        = optional(number, 300)
        timeout_seconds       = optional(number, 3)
        success_threshold     = optional(number, 3)
        failure_threshold     = optional(number, 2)
      }), null)
      data_volumes = map(object({
        mount_path         = string
        storage_request    = string
        storage_class_name = string
        access_mode        = string
      }))
    }), null)

    # service = optional(object({
    #   type = string
    # }), null)

    ingress = optional(object({
      path = string
    }), null)
  }))
  default = {}
}

variable "k8s_base_path" {
  description = "The relative path to the base Kubernetes manifest templates."
  type        = string
  default     = "./../kubernetes"
}

variable "base_images_to_load" {
  description = "A list of Docker images to pre-load into the Kind cluster for Argo Workflows."
  type        = list(string)
  default     = []
}

variable "ingress_host" {
  description = "The host name to configure in the Kubernetes Ingress resources."
  type        = string
  default     = "localhost"
}

variable "ingress_port" {
  description = "The port number of the Gateway API or Ingress Controller."
  type        = number
  default     = 80
}

variable "argo_workflows_version" {
  description = "The chart version for the Argo Workflows Helm release."
  type        = string
  default     = "0.45.26"
}
