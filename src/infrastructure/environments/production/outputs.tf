# For debugging
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.pixie_aks.name
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.pixie_aks.kube_admin_config_raw
  sensitive = true
}

output "argo_workflows_url" {
  value = "https://${helm_release.argo_workflows.name}.${azurerm_kubernetes_cluster.pixie_aks.dns_prefix}.${local.location}.cloudapp.azure.com"
}
