locals {
  # Naming
  argo_namespace_name      = "argo"
  pixie_namespace_name     = "pixie"
  ingest_server_app_name   = "pixie-ingest"
  ingest_server_image_name = "pixie-ingest"
  ingest_server_image_tag  = "1.0.0"

  # Azure, GHCR naming and other configuration
  resource_group_name   = "pixie_k8s_rg"
  aks_cluster_name      = "pixie"
  acr_name              = "pxlpixieacr"
  location              = "westeurope"
  vm_size               = "Standard_DS2_v2"
  node_count            = 1
  ghcr_registry_server  = "ghcr.io"
  ghcr_username         = "tomquaremepxl"

  # TODO:
  # Service Principal details for ACR/Image pulling (replace with actual values or data sources)

  # GHCR
  # Updated to use GHCR format (ghcr.io/<owner>/<repo>/<image>:<tag>)
  # Assuming the owner/repo are stored in local.ghcr_image_prefix.
  ghcr_image_prefix = "${local.ghcr_registry_server}/${local.ghcr_username}"
  ingest_server_full_image_name = "${local.ghcr_image_prefix}/${local.ingest_server_image_name}"

  # The actual Docker config JSON structure
  local_auth_token = base64encode("${local.ghcr_username}:${var.ghcr_pat}") # Base64 encoded 'USERNAME:PAT' string
  docker_config_json_map = {
    auths = {
      "${local.ghcr_registry_server}" = {
        username = local.ghcr_username 
        password = var.ghcr_pat 
        auth     = local.local_auth_token
      }
    }
  }

  # General paths
  apps_path       = "${path.module}/../../../apps"
  k8s_apps_path   = "${path.module}/../../../kubernetes/apps"
  k8s_base_path   = "${path.module}/../../../kubernetes/base"

  # Apps specific paths
  ingest_server_app_path = "${local.apps_path}/ingest_server"
  ingest_server_k8s_path = "${local.k8s_apps_path}/ingest_server"

  # Ingress
  ingress_host = "local.dev.pixie-ingest.com"

  # Packages
  argo_workflows_version = "0.45.26" # this is 3.7.2 outside of helm
  argo_workflows_server = "http://argo-workflows-server.argo.svc.cluster.local:2746" # TODO: Is this ok? or should it be "https://argo-workflows.pixie.westeurope.cloudapp.azure.com"
}
