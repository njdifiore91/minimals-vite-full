/**
 * Terraform and provider version constraints for the messaging module.
 * This file ensures compatibility and consistent behavior across environments.
 */

terraform {
  # Terraform version constraint
  required_version = ">= 1.2.0"

  # Required providers for different cloud platforms
  required_providers {
    # AWS provider for Amazon MQ (RabbitMQ) deployment
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.16.0, < 5.0.0"
    }

    # Azure provider for Azure Service Bus deployment
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0, < 4.0.0"
    }

    # Google Cloud provider for GCP Pub/Sub deployment
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0, < 5.0.0"
    }

    # Kubernetes provider for self-hosted RabbitMQ on Kubernetes
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0, < 3.0.0"
    }

    # Helm provider for deploying RabbitMQ via Helm charts
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.0, < 3.0.0"
    }

    # Random provider for generating random strings (e.g., passwords)
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0, < 4.0.0"
    }
  }
}