# infrastructure/terraform/modules/monitoring/versions.tf

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0"
    }
    
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.0"
    }
    
    datadog = {
      source  = "datadog/datadog"
      version = ">= 3.20.0"
    }
    
    null = {
      source  = "hashicorp/null"
      version = ">= 3.1.0"
    }
    
    random = {
      source  = "hashicorp/random"
      version = ">= 3.3.0"
    }
  }
}