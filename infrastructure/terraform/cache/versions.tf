# Terraform version constraint to ensure compatibility across environments
terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  # Required providers for Redis deployment
  required_providers {
    # AWS provider for ElastiCache Redis
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }
    
    # Azure provider for Azure Cache for Redis
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.70.0, < 4.0.0"
      
      # Provider features for Redis management
      features {}
    }
    
    # GCP provider for Memorystore Redis
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0, < 6.0.0"
    }
    
    # Kubernetes provider for self-hosted Redis on K8s
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.23.0, < 3.0.0"
    }
    
    # Helm provider for Redis Helm charts
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.10.0, < 3.0.0"
    }
    
    # Random provider for generating unique identifiers
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5.0, < 4.0.0"
    }
  }
}

# Provider configuration is conditionally loaded based on the cloud platform
# specified in the variables. The actual provider blocks are defined in main.tf
# to allow for dynamic configuration based on environment variables.