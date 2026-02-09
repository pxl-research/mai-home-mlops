terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source = "hashicorp/kubernetes"
      version = "2.38.0"
    }
    null = {
      source = "hashicorp/null"
      version = "3.2.4"
    }
    kubectl = {
      source = "alekc/kubectl"
      version = "2.1.3"
    }
    helm = {
      source = "hashicorp/helm"
      version = "3.0.2"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "3.6.2"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.47.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}

provider "kubernetes" {
  host                   = data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.host
  client_certificate     = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_certificate)
  client_key             = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.cluster_ca_certificate)
}

provider "null" {
}

provider "helm" {
  kubernetes = {
    host                   = data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.host
    client_certificate     = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_certificate)
    client_key             = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_key)
    cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.cluster_ca_certificate)
  }
}

provider "kubectl" {
  host                   = data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.host
  client_certificate     = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_certificate)
  client_key             = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.pixie_aks_data.kube_config.0.cluster_ca_certificate)
}

data "external" "docker_host_lookup" {
  program = ["bash", "-c", "docker context inspect --format '{\"host\":\"{{.Endpoints.docker.Host}}\"}'"]
}
provider "docker" {
  host = "unix:///var/run/docker.sock" # data.external.docker_host_lookup.result.host
}