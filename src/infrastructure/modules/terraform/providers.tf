terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.38.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "3.2.4"
    }
    kubectl = {
      source  = "gavinbunney/kubectl" # "alekc/kubectl"
      version = "1.19.0" # "2.1.3"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "3.0.2"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.9.0"
    }

    # Not used anymore because of lack of native GPU support
    # Instead we use minikube without provider
    # kind = {
    #   source  = "tehcyx/kind"
    #   version = "0.9.0"
    # }

    # Azure
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.47.0"
    }
  }
}

########################################
# LOCALS
########################################
locals {
  kube_config_path = pathexpand("~/.kube/config")
}

########################################
# PROVIDERS
########################################
provider "azurerm" {
  features {}
  subscription_id = var.deployment_target == "azure" ? try(var.azure_subscription_id, "") : ""
}

# Kubernetes provider (default)
provider "kubernetes" {
  # Configuration for minikube (Linux/WSL2)
  # Only set these when deploying locally.
  config_path    = (var.deployment_target == "local_wsl2" || var.deployment_target == "local_linux") ? local.kube_config_path : null
  config_context = (var.deployment_target == "local_wsl2" || var.deployment_target == "local_linux") ? "minikube" : null
  /*
  host                   = kind_cluster.default[0].endpoint
  client_certificate     = kind_cluster.default[0].client_certificate
  client_key             = kind_cluster.default[0].client_key
  cluster_ca_certificate = kind_cluster.default[0].cluster_ca_certificate
  */

  # Configuration for Azure AKS
  # Only set these when deploying to Azure.
  host                   = var.deployment_target == "azure" ? data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.host : null
  client_certificate     = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_certificate) : null
  client_key             = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_key) : null
  cluster_ca_certificate = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.cluster_ca_certificate) : null
}

# Helm provider (default)
provider "helm" {
  kubernetes = {
    # Configuration for minikube (Linux/WSL2)
    # Only set these when deploying locally.
    config_path    = (var.deployment_target == "local_wsl2" || var.deployment_target == "local_linux") ? local.kube_config_path : null
    config_context = (var.deployment_target == "local_wsl2" || var.deployment_target == "local_linux") ? "minikube" : null

    /*
    host                   = kind_cluster.default[0].endpoint
    client_certificate     = kind_cluster.default[0].client_certificate
    client_key             = kind_cluster.default[0].client_key
    cluster_ca_certificate = kind_cluster.default[0].cluster_ca_certificate
    */
    host                   = var.deployment_target == "azure" ? data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.host : null
    client_certificate     = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_certificate) : null
    client_key             = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_key) : null
    cluster_ca_certificate = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.cluster_ca_certificate) : null
  }
}

# Kubectl provider
provider "kubectl" {
  config_path    = (var.deployment_target == "local_wsl2" || var.deployment_target == "local_linux") ? local.kube_config_path : null
  apply_retry_count = 10

  host                   = var.deployment_target == "azure" ? data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.host : null
  client_certificate     = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_certificate) : null
  client_key             = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_key) : null
  cluster_ca_certificate = var.deployment_target == "azure" ? base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.cluster_ca_certificate) : null
}

# Null provider
provider "null" {
}

# Docker provider
provider "docker" {
  host = "unix:///var/run/docker.sock"
}
