variable "ghcr_pat" {
  description = "GitHub Personal Access Token with neccessary scope for GHCR."
  type        = string
  sensitive   = true
}

variable "azure_subscription_id" {
  description = "Azure subscription ID."
  type        = string
  sensitive   = true
}