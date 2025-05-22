# versions.tf - Global Terraform version and provider constraints

terraform {
  # Terraform version constraint
  # Specify a minimum version to ensure required features are available
  # and a maximum version to prevent unexpected changes from future versions
  required_version = ">= 1.5.0, < 2.0.0"

  # Provider requirements for global infrastructure
  # These providers are used across all environments
  required_providers {
    # AWS provider for S3-compatible storage and other AWS resources
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    # Azure provider for Azure resources
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }

    # Google Cloud provider for GCP resources
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }

    # Kubernetes provider for interacting with Kubernetes clusters
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }

    # Helm provider for deploying Helm charts
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }

    # Random provider for generating random values
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }

    # Time provider for time-based operations
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }

    # TLS provider for certificate generation
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}