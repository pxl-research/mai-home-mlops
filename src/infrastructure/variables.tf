variable "cluster_create" {
  description = "A flag to determine if the cluster resource should be created."
  type        = bool
  default     = false # create resources assuming cluster already exists
}

variable "deployment_target" {
  description = "Deployment target. Can be 'local_wsl2', 'local_linux' or 'azure'."
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
