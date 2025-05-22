# Terraform providers configuration for Kubernetes module
# This file configures the Terraform providers required for Kubernetes resource management,
# including the Kubernetes provider and cloud-specific providers (AWS, Azure, GCP).

# Define required Terraform version and providers with version constraints
terraform {
  required_version = ">= 1.3.0"
  
  required_providers {
    # Kubernetes provider for managing Kubernetes resources
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.20.0, < 3.0.0"
    }
    
    # AWS provider for EKS authentication and resources
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 6.0.0"
      optional = true
    }
    
    # Azure provider for AKS authentication and resources
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0, < 4.0.0"
      optional = true
    }
    
    # Google provider for GKE authentication and resources
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0, < 5.0.0"
      optional = true
    }
  }
}

# Kubernetes provider configuration with dynamic authentication based on cloud provider
# This provider will be configured based on the cloud provider being used (AWS EKS, Azure AKS, or GCP GKE)
provider "kubernetes" {
  # Configuration will be provided by one of the following methods:
  # 1. EKS authentication (AWS)
  # 2. AKS authentication (Azure)
  # 3. GKE authentication (Google)
  # 4. Direct kubeconfig file
  
  # Common configuration options
  alias                  = var.kubernetes_provider_alias
  host                   = var.kubernetes_host
  cluster_ca_certificate = var.kubernetes_cluster_ca_certificate
  token                  = var.kubernetes_token
  
  # Dynamic configuration based on authentication method
  dynamic "exec" {
    for_each = var.kubernetes_exec_enabled ? [1] : []
    
    content {
      api_version = var.kubernetes_exec_api_version
      command     = var.kubernetes_exec_command
      args        = var.kubernetes_exec_args
    }
  }
  
  # Additional provider configuration
  client_certificate     = var.kubernetes_client_certificate
  client_key             = var.kubernetes_client_key
  config_path            = var.kubernetes_config_path
  config_context         = var.kubernetes_config_context
  
  # Timeouts for API operations
  dynamic "timeouts" {
    for_each = var.kubernetes_timeouts != null ? [var.kubernetes_timeouts] : []
    
    content {
      create = lookup(timeouts.value, "create", null)
      update = lookup(timeouts.value, "update", null)
      delete = lookup(timeouts.value, "delete", null)
    }
  }
}

# AWS provider configuration for EKS authentication
provider "aws" {
  # Only configure if using AWS EKS
  count = var.cloud_provider == "aws" ? 1 : 0
  
  region                   = var.aws_region
  profile                  = var.aws_profile
  shared_credentials_files = var.aws_shared_credentials_files
  
  # Use environment variables for authentication if not specified:
  # - AWS_ACCESS_KEY_ID
  # - AWS_SECRET_ACCESS_KEY
  # - AWS_SESSION_TOKEN (optional)
  
  # Additional provider settings
  dynamic "assume_role" {
    for_each = var.aws_assume_role != null ? [var.aws_assume_role] : []
    
    content {
      role_arn     = assume_role.value.role_arn
      session_name = lookup(assume_role.value, "session_name", null)
      external_id  = lookup(assume_role.value, "external_id", null)
    }
  }
}

# Azure provider configuration for AKS authentication
provider "azurerm" {
  # Only configure if using Azure AKS
  count = var.cloud_provider == "azure" ? 1 : 0
  
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
  client_id       = var.azure_client_id
  client_secret   = var.azure_client_secret
  
  # Use environment variables for authentication if not specified:
  # - ARM_SUBSCRIPTION_ID
  # - ARM_TENANT_ID
  # - ARM_CLIENT_ID
  # - ARM_CLIENT_SECRET
  
  # Additional provider settings
  features {}
}

# Google provider configuration for GKE authentication
provider "google" {
  # Only configure if using GCP GKE
  count = var.cloud_provider == "google" ? 1 : 0
  
  project     = var.google_project
  region      = var.google_region
  zone        = var.google_zone
  credentials = var.google_credentials
  
  # Use environment variables for authentication if not specified:
  # - GOOGLE_CREDENTIALS
  # - GOOGLE_PROJECT
  # - GOOGLE_REGION
  # - GOOGLE_ZONE
}

# Provider aliases for multi-cluster management
provider "kubernetes" {
  alias = "admin"
  
  host                   = var.admin_kubernetes_host
  cluster_ca_certificate = var.admin_kubernetes_cluster_ca_certificate
  token                  = var.admin_kubernetes_token
  
  # Additional configuration for admin cluster
  dynamic "exec" {
    for_each = var.admin_kubernetes_exec_enabled ? [1] : []
    
    content {
      api_version = var.admin_kubernetes_exec_api_version
      command     = var.admin_kubernetes_exec_command
      args        = var.admin_kubernetes_exec_args
    }
  }
}