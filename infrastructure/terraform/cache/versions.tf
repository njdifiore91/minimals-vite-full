/**
 * versions.tf
 *
 * This file defines Terraform and provider version constraints for the Redis cache infrastructure.
 * It ensures compatibility and consistent behavior across development, staging, and production environments.
 * The file supports deployment on AWS, Azure, or GCP depending on the chosen cloud platform.
 */

terraform {
  # Terraform version constraint
  # Using >= 1.0.0 and < 2.0.0 to ensure compatibility with all modules
  required_version = ">= 1.0.0, < 2.0.0"

  # Required providers with version constraints
  required_providers {
    # AWS provider for ElastiCache Redis deployment
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }

    # Azure provider for Azure Cache for Redis deployment
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0, < 4.0.0"
    }

    # Google Cloud provider for Memorystore Redis deployment
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0, < 5.0.0"
    }

    # Kubernetes provider for self-hosted Redis on Kubernetes
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0, < 3.0.0"
    }

    # Helm provider for Redis Helm chart deployment
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.0, < 3.0.0"
    }
  }
}

# AWS provider configuration
provider "aws" {
  # Provider configuration will be supplied via environment variables or terraform.tfvars
  # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

  # Default tags for all AWS resources
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "MCA Application"
      ManagedBy   = "Terraform"
      Service     = "Redis Cache"
    }
  }
}

# Azure provider configuration
provider "azurerm" {
  # Provider configuration will be supplied via environment variables or terraform.tfvars
  # ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_SUBSCRIPTION_ID, ARM_TENANT_ID

  features {
    # Enable Redis Cache specific features
    resource_group {
      prevent_deletion_if_contains_resources = true
    }

    key_vault {
      purge_soft_delete_on_destroy = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Google Cloud provider configuration
provider "google" {
  # Provider configuration will be supplied via environment variables or terraform.tfvars
  # GOOGLE_CREDENTIALS, GOOGLE_PROJECT, GOOGLE_REGION

  # Default labels for all GCP resources
  default_labels = {
    environment = var.environment
    project     = "mca-application"
    managed_by  = "terraform"
    service     = "redis-cache"
  }
}

# Kubernetes provider configuration
provider "kubernetes" {
  # Configuration will be loaded from the kubeconfig file or environment variables
  # KUBE_CONFIG_PATH, KUBE_CTX
}

# Helm provider configuration
provider "helm" {
  kubernetes {
    # Configuration will be loaded from the kubeconfig file or environment variables
    # KUBE_CONFIG_PATH, KUBE_CTX
  }
}

# Variables used in provider configurations
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}