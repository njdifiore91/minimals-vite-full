# Terraform and provider version constraints

terraform {
  # Require Terraform version 1.0.0 or higher, but less than 2.0.0
  required_version = ">= 1.0.0, < 2.0.0"

  # Required providers with version constraints
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}