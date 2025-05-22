# Variables for Kubernetes provider configuration

# General configuration
variable "cloud_provider" {
  description = "The cloud provider where the Kubernetes cluster is hosted. Valid values are 'aws', 'azure', 'google', or 'custom'."
  type        = string
  default     = "custom"
  validation {
    condition     = contains(["aws", "azure", "google", "custom"], var.cloud_provider)
    error_message = "The cloud_provider value must be one of 'aws', 'azure', 'google', or 'custom'."
  }
}

# Kubernetes provider configuration
variable "kubernetes_provider_alias" {
  description = "Alias for the Kubernetes provider."
  type        = string
  default     = "default"
}

variable "kubernetes_host" {
  description = "The hostname (in form of URI) of the Kubernetes API server."
  type        = string
  default     = ""
}

variable "kubernetes_cluster_ca_certificate" {
  description = "PEM-encoded root certificates bundle for TLS authentication with the Kubernetes API server."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_token" {
  description = "Authentication token for the Kubernetes API server."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_client_certificate" {
  description = "PEM-encoded client certificate for TLS authentication with the Kubernetes API server."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_client_key" {
  description = "PEM-encoded client key for TLS authentication with the Kubernetes API server."
  type        = string
  default     = ""
  sensitive   = true
}

variable "kubernetes_config_path" {
  description = "Path to the kubeconfig file."
  type        = string
  default     = ""
}

variable "kubernetes_config_context" {
  description = "Context to choose from the kubeconfig file."
  type        = string
  default     = ""
}

variable "kubernetes_exec_enabled" {
  description = "Whether to use the exec authentication plugin."
  type        = bool
  default     = false
}

variable "kubernetes_exec_api_version" {
  description = "API version to use for the exec authentication plugin."
  type        = string
  default     = "client.authentication.k8s.io/v1beta1"
}

variable "kubernetes_exec_command" {
  description = "Command to execute for the exec authentication plugin."
  type        = string
  default     = ""
}

variable "kubernetes_exec_args" {
  description = "Arguments to pass to the command for the exec authentication plugin."
  type        = list(string)
  default     = []
}

variable "kubernetes_timeouts" {
  description = "Timeout settings for Kubernetes operations."
  type        = map(string)
  default     = null
}

# AWS provider configuration
variable "aws_region" {
  description = "The AWS region where the EKS cluster is deployed."
  type        = string
  default     = ""
}

variable "aws_profile" {
  description = "The AWS profile to use for authentication."
  type        = string
  default     = ""
}

variable "aws_shared_credentials_files" {
  description = "List of paths to AWS shared credentials files."
  type        = list(string)
  default     = null
}

variable "aws_assume_role" {
  description = "AWS IAM role to assume for EKS operations."
  type        = object({
    role_arn     = string
    session_name = optional(string)
    external_id  = optional(string)
  })
  default     = null
}

# Azure provider configuration
variable "azure_subscription_id" {
  description = "The Azure subscription ID where the AKS cluster is deployed."
  type        = string
  default     = ""
}

variable "azure_tenant_id" {
  description = "The Azure tenant ID for authentication."
  type        = string
  default     = ""
}

variable "azure_client_id" {
  description = "The Azure client ID for authentication."
  type        = string
  default     = ""
}

variable "azure_client_secret" {
  description = "The Azure client secret for authentication."
  type        = string
  default     = ""
  sensitive   = true
}

# Google provider configuration
variable "google_project" {
  description = "The GCP project ID where the GKE cluster is deployed."
  type        = string
  default     = ""
}

variable "google_region" {
  description = "The GCP region where the GKE cluster is deployed."
  type        = string
  default     = ""
}

variable "google_zone" {
  description = "The GCP zone where the GKE cluster is deployed."
  type        = string
  default     = ""
}

variable "google_credentials" {
  description = "The GCP credentials for authentication."
  type        = string
  default     = ""
  sensitive   = true
}

# Admin cluster configuration for multi-cluster management
variable "admin_kubernetes_host" {
  description = "The hostname of the admin Kubernetes API server."
  type        = string
  default     = ""
}

variable "admin_kubernetes_cluster_ca_certificate" {
  description = "PEM-encoded root certificates bundle for the admin Kubernetes API server."
  type        = string
  default     = ""
  sensitive   = true
}

variable "admin_kubernetes_token" {
  description = "Authentication token for the admin Kubernetes API server."
  type        = string
  default     = ""
  sensitive   = true
}

variable "admin_kubernetes_exec_enabled" {
  description = "Whether to use the exec authentication plugin for the admin cluster."
  type        = bool
  default     = false
}

variable "admin_kubernetes_exec_api_version" {
  description = "API version to use for the exec authentication plugin for the admin cluster."
  type        = string
  default     = "client.authentication.k8s.io/v1beta1"
}

variable "admin_kubernetes_exec_command" {
  description = "Command to execute for the exec authentication plugin for the admin cluster."
  type        = string
  default     = ""
}

variable "admin_kubernetes_exec_args" {
  description = "Arguments to pass to the command for the exec authentication plugin for the admin cluster."
  type        = list(string)
  default     = []
}