# Kubernetes Provider Configuration for Multi-Cloud Deployments

# Define required providers with version constraints
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.20.0, < 3.0.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0, < 4.0.0"
    }
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

# Default Kubernetes provider configuration
# This will be used when no specific provider is referenced
provider "kubernetes" {
  # Configuration will be provided by the module consumer
  # through environment variables or explicit configuration
}

# AWS EKS provider configuration
provider "kubernetes" {
  alias = "eks"
  
  host                   = var.eks_cluster_endpoint
  cluster_ca_certificate = base64decode(var.eks_cluster_ca_certificate)
  
  # Use AWS EKS token for authentication
  # This is the recommended approach for EKS authentication
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args = [
      "eks",
      "get-token",
      "--cluster-name",
      var.eks_cluster_name,
      "--region",
      var.aws_region
    ]
  }
}

# Azure AKS provider configuration
provider "kubernetes" {
  alias = "aks"
  
  host                   = var.aks_cluster_endpoint
  cluster_ca_certificate = base64decode(var.aks_cluster_ca_certificate)
  
  # Use Azure AKS token for authentication
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "az"
    args = [
      "aks",
      "get-credentials",
      "--resource-group",
      var.aks_resource_group,
      "--name",
      var.aks_cluster_name,
      "--file",
      "-"
    ]
  }
}

# Google GKE provider configuration
provider "kubernetes" {
  alias = "gke"
  
  host                   = "https://${var.gke_cluster_endpoint}"
  cluster_ca_certificate = base64decode(var.gke_cluster_ca_certificate)
  
  # Use GCP GKE token for authentication
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "gcloud"
    args = [
      "container",
      "clusters",
      "get-credentials",
      var.gke_cluster_name,
      "--region",
      var.gke_region,
      "--project",
      var.gcp_project_id
    ]
  }
}

# Generic Kubernetes provider configuration for on-premises or other providers
# This can be used for any Kubernetes cluster with kubeconfig authentication
provider "kubernetes" {
  alias = "generic"
  
  config_path    = var.kubeconfig_path
  config_context = var.kubeconfig_context
}

# AWS provider configuration for EKS-related resources
provider "aws" {
  region = var.aws_region
  
  # Default tags to be applied to all AWS resources
  default_tags {
    tags = var.default_aws_tags
  }
}

# Azure provider configuration for AKS-related resources
provider "azurerm" {
  features {}
  
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

# Google provider configuration for GKE-related resources
provider "google" {
  project = var.gcp_project_id
  region  = var.gke_region
}

# Variable definitions for provider configurations
variable "eks_cluster_endpoint" {
  description = "The endpoint for the EKS Kubernetes API server"
  type        = string
  default     = ""
}

variable "eks_cluster_ca_certificate" {
  description = "The base64 encoded certificate data required to communicate with the EKS cluster"
  type        = string
  default     = ""
  sensitive   = true
}

variable "eks_cluster_name" {
  description = "The name of the EKS cluster"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "The AWS region where the EKS cluster is deployed"
  type        = string
  default     = "us-west-2"
}

variable "default_aws_tags" {
  description = "Default tags to apply to all AWS resources"
  type        = map(string)
  default     = {}
}

variable "aks_cluster_endpoint" {
  description = "The endpoint for the AKS Kubernetes API server"
  type        = string
  default     = ""
}

variable "aks_cluster_ca_certificate" {
  description = "The base64 encoded certificate data required to communicate with the AKS cluster"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aks_resource_group" {
  description = "The Azure resource group where the AKS cluster is deployed"
  type        = string
  default     = ""
}

variable "aks_cluster_name" {
  description = "The name of the AKS cluster"
  type        = string
  default     = ""
}

variable "azure_subscription_id" {
  description = "The Azure subscription ID"
  type        = string
  default     = ""
}

variable "azure_tenant_id" {
  description = "The Azure tenant ID"
  type        = string
  default     = ""
}

variable "gke_cluster_endpoint" {
  description = "The endpoint for the GKE Kubernetes API server"
  type        = string
  default     = ""
}

variable "gke_cluster_ca_certificate" {
  description = "The base64 encoded certificate data required to communicate with the GKE cluster"
  type        = string
  default     = ""
  sensitive   = true
}

variable "gke_cluster_name" {
  description = "The name of the GKE cluster"
  type        = string
  default     = ""
}

variable "gke_region" {
  description = "The GCP region where the GKE cluster is deployed"
  type        = string
  default     = "us-central1"
}

variable "gcp_project_id" {
  description = "The GCP project ID"
  type        = string
  default     = ""
}

variable "kubeconfig_path" {
  description = "Path to the kubeconfig file for generic Kubernetes clusters"
  type        = string
  default     = "~/.kube/config"
}

variable "kubeconfig_context" {
  description = "Context to use from the kubeconfig file for generic Kubernetes clusters"
  type        = string
  default     = ""
}