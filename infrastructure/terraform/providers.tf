# Terraform providers configuration for MCA Application Processing System
# This file configures all required providers for infrastructure deployment
#
# This configuration supports multi-cloud and multi-region deployments for the
# Merchant Cash Advance (MCA) Application Processing System, enabling the deployment
# of microservices across AWS, Azure, and GCP with appropriate provider settings.
#
# The file includes:
# - Provider version constraints to ensure compatibility
# - Multi-region provider configurations for high availability
# - Backend configuration for Terraform state management
# - Provider-specific settings for optimal resource management

terraform {
  # Specify the required Terraform version
  required_version = ">= 1.5.0, < 2.0.0"

  # Define required providers with version constraints
  required_providers {
    # AWS provider for EKS, RDS, ElastiCache, S3, etc.
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0, < 6.0.0"
    }

    # Azure provider for AKS, Azure Database, etc.
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.70.0, < 4.0.0"
    }

    # Google Cloud provider for GKE, Cloud SQL, etc.
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0, < 6.0.0"
    }

    # Kubernetes provider for K8s resources
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.23.0, < 3.0.0"
    }

    # Helm provider for deploying charts
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.11.0, < 3.0.0"
    }

    # Random provider for generating unique identifiers
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5.0, < 4.0.0"
    }
    
    # PostgreSQL provider for database management
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = ">= 1.20.0, < 2.0.0"
    }
    
    # Datadog provider for monitoring
    datadog = {
      source  = "DataDog/datadog"
      version = ">= 3.30.0, < 4.0.0"
    }
  }

  # Backend configuration for storing Terraform state
  # This uses S3 as an example, but can be adapted for Azure Blob Storage or GCS
  backend "s3" {
    # These values should be overridden in environment-specific configurations
    # bucket         = "mca-terraform-state"
    # key            = "infrastructure/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "mca-terraform-locks"
    # encrypt        = true
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.aws_region

  # Default tags applied to all AWS resources
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "MCA-Application-System"
      ManagedBy   = "Terraform"
      Service     = "Dollar-Funding-MCA"
    }
  }
}

# AWS Provider for secondary region (disaster recovery)
provider "aws" {
  alias  = "secondary"
  region = var.aws_secondary_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "MCA-Application-System"
      ManagedBy   = "Terraform"
      Service     = "Dollar-Funding-MCA"
      Role        = "DR"
    }
  }
}

# AWS Provider for US-West region (multi-region deployment)
provider "aws" {
  alias  = "us-west"
  region = "us-west-2"
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "MCA-Application-System"
      ManagedBy   = "Terraform"
      Service     = "Dollar-Funding-MCA"
      Region      = "US-West"
    }
  }
}

# Azure Provider Configuration
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    virtual_machine {
      delete_os_disk_on_deletion     = true
      graceful_shutdown              = true
      skip_shutdown_and_force_delete = false
    }
  }

  # These should be set via environment variables or Azure CLI authentication
  # subscription_id = var.azure_subscription_id
  # tenant_id       = var.azure_tenant_id
}

# Azure Provider for secondary region
provider "azurerm" {
  alias = "secondary"
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
  # These should be set via environment variables or Azure CLI authentication
  # subscription_id = var.azure_subscription_id
  # tenant_id       = var.azure_tenant_id
}

# Google Cloud Provider Configuration
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# Google Cloud Provider for secondary region
provider "google" {
  alias   = "secondary"
  project = var.gcp_project_id
  region  = var.gcp_secondary_region
  zone    = var.gcp_secondary_zone
}

# Kubernetes Provider Configuration
# This will be configured after the cluster is created
provider "kubernetes" {
  # Configuration will be loaded from the kubeconfig file or via cluster endpoints
  # For AWS EKS:
  # host                   = module.eks.cluster_endpoint
  # cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  # token                  = data.aws_eks_cluster_auth.cluster.token
  
  # For Azure AKS:
  # host                   = data.azurerm_kubernetes_cluster.main.kube_config.0.host
  # client_certificate     = base64decode(data.azurerm_kubernetes_cluster.main.kube_config.0.client_certificate)
  # client_key             = base64decode(data.azurerm_kubernetes_cluster.main.kube_config.0.client_key)
  # cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.main.kube_config.0.cluster_ca_certificate)
  
  # For GCP GKE:
  # host                   = "https://${data.google_container_cluster.main.endpoint}"
  # token                  = data.google_client_config.provider.access_token
  # cluster_ca_certificate = base64decode(data.google_container_cluster.main.master_auth.0.cluster_ca_certificate)
}

# Kubernetes Provider for secondary cluster
provider "kubernetes" {
  alias = "secondary"
  # Configuration for secondary cluster
}

# Helm Provider Configuration
provider "helm" {
  kubernetes {
    # Configuration will be loaded from the kubeconfig file or via cluster endpoints
    # host                   = module.eks.cluster_endpoint
    # cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    # token                  = data.aws_eks_cluster_auth.cluster.token
  }
}

# Helm Provider for secondary cluster
provider "helm" {
  alias = "secondary"
  kubernetes {
    # Configuration for secondary cluster
  }
}

# PostgreSQL Provider Configuration
provider "postgresql" {
  # These values should be provided via variables or environment variables
  # host            = module.postgresql.primary_endpoint
  # port            = 5432
  # database        = "postgres"
  # username        = var.postgresql_admin_username
  # password        = var.postgresql_admin_password
  # sslmode         = "require"
  # connect_timeout = 15
  # superuser       = false
}

# Datadog Provider Configuration
provider "datadog" {
  # These values should be provided via variables or environment variables
  # api_key = var.datadog_api_key
  # app_key = var.datadog_app_key
  # api_url = "https://api.datadoghq.com/"
}