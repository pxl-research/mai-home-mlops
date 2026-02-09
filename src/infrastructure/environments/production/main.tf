# Azure Resource Group
resource "azurerm_resource_group" "pixie_k8s_rg" {
  name     = local.resource_group_name
  location = local.location
}

# Azure Kubernetes Service (AKS) Cluster
resource "azurerm_kubernetes_cluster" "pixie_aks" {
  name                = local.aks_cluster_name
  location            = azurerm_resource_group.pixie_k8s_rg.location
  resource_group_name = azurerm_resource_group.pixie_k8s_rg.name
  dns_prefix          = local.aks_cluster_name

  default_node_pool {
    name       = "default"
    node_count = local.node_count
    vm_size    = local.vm_size
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    Environment = "LocalDev"
  }
}

# Data source to fetch the AKS cluster credentials after creation
data "azurerm_kubernetes_cluster" "pixie_aks_data" {
  name                = azurerm_kubernetes_cluster.pixie_aks.name
  resource_group_name = azurerm_kubernetes_cluster.pixie_aks.resource_group_name
  depends_on = [azurerm_kubernetes_cluster.pixie_aks]
}

resource "kubernetes_namespace" "argo_namespace" {
  metadata {
    name = local.argo_namespace_name
  }
  depends_on = [azurerm_kubernetes_cluster.pixie_aks, data.azurerm_kubernetes_cluster.pixie_aks_data]
}

resource "kubernetes_namespace" "pixie_namespace" {
  metadata {
    name = local.pixie_namespace_name
  }
  depends_on = [azurerm_kubernetes_cluster.pixie_aks, data.azurerm_kubernetes_cluster.pixie_aks_data]
}

resource "helm_release" "argo_workflows" {
  name       = "argo-workflows"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-workflows"
  version    = "${local.argo_workflows_version}"
  namespace  = kubernetes_namespace.argo_namespace.metadata.0.name
  values = [
    file("${local.k8s_base_path}/argo-workflows-values.yaml")
  ]
  depends_on = [
    kubernetes_namespace.argo_namespace, 
    azurerm_kubernetes_cluster.pixie_aks
  ]
}

resource "kubectl_manifest" "hera_rbac" {
  for_each = {
    serviceaccount  = "${local.k8s_base_path}/hera-submitter-sa.yaml"
    clusterrole     = "${local.k8s_base_path}/hera-submitter-role.yaml"
    binding_hera    = "${local.k8s_base_path}/hera-submitter-binding.yaml"
    binding_default = "${local.k8s_base_path}/argo-default-task-binding.yaml"
  }

  yaml_body = file(each.value)

  depends_on = [
    helm_release.argo_workflows,
    kubernetes_namespace.argo_namespace,
    azurerm_kubernetes_cluster.pixie_aks
  ]
}

# ------------------------------------------------------------------------------
# App: Ingest Server (Docker Build/Load steps are REMOVED)
# ------------------------------------------------------------------------------

# **Removed:** docker_image.ingest_server (Local build)
# **Removed:** null_resource.minikube_image_load (Local load)

# Build Docker image locally
resource "docker_image" "ingest_server" {
  name = "${local.ingest_server_full_image_name}:${local.ingest_server_image_tag}"
  build {
    context    = local.apps_path
    dockerfile = "${local.ingest_server_app_path}/Dockerfile"
    build_args = {
      ARGO_WORKFLOWS_SERVER = local.argo_workflows_server
    }
  }
  depends_on = [kubectl_manifest.hera_rbac]
}

# Login and push Docker image
resource "null_resource" "ghcr_login" {
  provisioner "local-exec" {
    command = "echo \"${var.ghcr_pat}\" | docker login ghcr.io -u ${local.ghcr_username} --password-stdin"
  }
  depends_on = [docker_image.ingest_server]
}

resource "null_resource" "push_ingest_server" {
  provisioner "local-exec" {
    command = "docker push ${local.ingest_server_full_image_name}:${local.ingest_server_image_tag}"
  }

  # Ensure the image is built and the login is complete before pushing
  depends_on = [
    docker_image.ingest_server,
    null_resource.ghcr_login,
  ]
}

# Rollout trigger remains a good pattern for forcing redeployment on image change
resource "null_resource" "rollout_trigger" {
  triggers = {
    # In a real pipeline, this value would be set externally based on image push time/hash.
    timestamp = timestamp() 
  }
  depends_on = [kubectl_manifest.hera_rbac] # Depend on previous K8s resources
}

# Kubernetes Secret
resource "kubernetes_secret" "ghcr_pull_secret" {
  metadata {
    name      = "ghcr-imagepullsecret"
    namespace = kubernetes_namespace.pixie_namespace.metadata.0.name
  }

  type = "kubernetes.io/dockerconfigjson"

  data = {
    # The key for this type of secret must be exactly .dockerconfigjson
    ".dockerconfigjson" = jsonencode(local.docker_config_json_map)
  }
  
  # Ensure the namespace is ready before creating the secret
  depends_on = [
    kubernetes_namespace.pixie_namespace 
  ]
}

# Deployment Manifest - Image name updated to use ACR full path
resource "kubectl_manifest" "ingest_server_deployment" {
  yaml_body = templatefile("${local.ingest_server_k8s_path}/deployment.yaml", {
    app_name        = local.ingest_server_app_name
    namespace_name  = kubernetes_namespace.pixie_namespace.metadata[0].name
    image_name      = local.ingest_server_full_image_name
    image_tag       = local.ingest_server_image_tag
    rollout_trigger = null_resource.rollout_trigger.triggers.timestamp
    is_local_deployment = false 
    image_pull_secret_name = kubernetes_secret.ghcr_pull_secret.metadata.0.name 
  })
  wait = false # true
  depends_on = [
    null_resource.rollout_trigger,
    kubernetes_secret.ghcr_pull_secret,
    null_resource.push_ingest_server
    # azurerm_container_registry.pixie_acr # Ensure ACR exists before deploying manifests that reference it
  ]
}

# Service Manifest
resource "kubectl_manifest" "ingest_server_service" {
  yaml_body = templatefile("${local.ingest_server_k8s_path}/service.yaml", {
    app_name = local.ingest_server_app_name
    namespace_name  = kubernetes_namespace.pixie_namespace.metadata[0].name
    is_local_deployment = false
  })
  depends_on = [kubectl_manifest.ingest_server_deployment]
}

# Ingress Manifest (NEW)
resource "kubectl_manifest" "ingest_server_ingress" {
  yaml_body = templatefile("${local.k8s_base_path}/ingress.yaml", {
    app_name = local.ingest_server_app_name
    namespace_name = kubernetes_namespace.pixie_namespace.metadata[0].name
    # Use your production FQDN. This FQDN must point to the AKS Ingress Controller's IP.
    ingress_host = local.ingress_host
  })
  depends_on = [
    kubectl_manifest.ingest_server_service,
    # Add dependency on the Helm release for the Ingress Controller if managed by Terraform
  ]
}

# For Hera scripts:
# Minikube image load is replaced with a simple null_resource dependency
resource "null_resource" "hera_echo_base_image_dependency" {
  # This resource now only serves as a dependency anchor, 
  # assuming 'python:3.11-alpine' is available from Docker Hub or a configured repository.
  depends_on = [kubectl_manifest.ingest_server_ingress]
}