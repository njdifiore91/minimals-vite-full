# Terraform and Provider Version Constraints
#
# This file specifies Terraform and provider version constraints for the messaging module,
# ensuring compatibility and consistent behavior across environments.

terraform {
  required_version = ">= 1.0.0, < 2.0.0"
  
  required_providers {
    # AWS provider for infrastructure resources
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0, < 5.0.0"
    }
    
    # RabbitMQ provider for queue and exchange management
    rabbitmq = {
      source  = "cyrilgdn/rabbitmq"
      version = ">= 1.8.0, < 2.0.0"
    }
    
    # Random provider for generating random strings
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0, < 4.0.0"
    }
  }
}