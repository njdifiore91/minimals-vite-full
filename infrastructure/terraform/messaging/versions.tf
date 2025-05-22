# =============================================================================
# MCA Application Processing System - Messaging Versions
# =============================================================================
# This file specifies Terraform and provider version constraints for the
# messaging module, ensuring compatibility and consistent behavior across
# environments.
# =============================================================================

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    rabbitmq = {
      source  = "cyrilgdn/rabbitmq"
      version = ">= 1.8.0"
    }
  }
}