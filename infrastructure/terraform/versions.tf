# versions.tf
# Specifies Terraform version constraints and required provider versions to ensure consistent
# infrastructure deployment across different environments and by different team members.

terraform {
  # Require Terraform version 1.5.0 or higher for the MCA Application Processing System
  # This ensures compatibility with all required provider versions and features
  required_version = ">= 1.5.0"

  # Configure required providers with version constraints
  required_providers {
    # AWS provider for S3-compatible storage, container registry, and other AWS services
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }

    # Kubernetes provider for container orchestration
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.23.0, < 3.0.0"
    }

    # PostgreSQL provider for database management
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = ">= 1.20.0, < 2.0.0"
    }

    # RabbitMQ provider for message queue management
    rabbitmq = {
      source  = "cyrilgdn/rabbitmq"
      version = ">= 1.5.0, < 2.0.0"
    }

    # Random provider for generating random values (used for resource naming)
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5.0, < 4.0.0"
    }

    # Helm provider for Kubernetes application deployment
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.10.0, < 3.0.0"
    }

    # Null provider for resource dependencies and provisioning
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2.0, < 4.0.0"
    }

    # Local provider for local file operations
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4.0, < 3.0.0"
    }

    # Template provider for template rendering
    template = {
      source  = "hashicorp/template"
      version = ">= 2.2.0, < 3.0.0"
    }
  }

  # Backend configuration for state management
  # The actual backend configuration is in a separate file to allow for environment-specific settings
  # This is just a placeholder to indicate that a backend is required
  backend "s3" {}

  # Provider feature flags
  # These are used to enable or disable specific provider features
  # AWS provider features
  provider_meta "aws" {
    module_name = "mca-application-processing-system"
  }
}

# Provider configuration is in separate files to allow for better organization
# See providers.tf for the actual provider configuration