/**
 * # Database Module - Terraform Version Constraints
 *
 * This file defines the Terraform and provider version constraints for the database module.
 * It ensures compatibility and consistent behavior across environments when deploying
 * PostgreSQL 14 in a primary-replica configuration.
 *
 * ## Purpose
 *
 * - Establishes minimum required Terraform version for this module
 * - Defines compatible provider versions for AWS, Azure, and GCP
 * - Ensures consistent provider initialization across environments
 * - Prevents version conflicts and compatibility issues
 *
 * ## Usage
 *
 * This module supports deployment of PostgreSQL 14 on multiple cloud platforms:
 * - AWS: Amazon RDS for PostgreSQL with Multi-AZ and read replicas
 * - Azure: Azure Database for PostgreSQL with geo-redundancy
 * - GCP: Cloud SQL for PostgreSQL with high availability
 *
 * The actual cloud provider is determined by the root module configuration.
 *
 * ## Features
 *
 * - Primary database with read replicas (2 for production, 1 for staging)
 * - Multi-AZ deployment for high availability
 * - Automated backups with 30-day retention
 * - Point-in-time recovery with 5-minute RPO
 * - Enhanced monitoring with 15-second metrics
 */

terraform {
  /**
   * Terraform Version Constraint
   * 
   * Requires Terraform 1.2.0 or higher for the following features:
   * - Improved provider configuration with dependency lock files
   * - Enhanced module composition capabilities
   * - Better error handling and validation
   * - Support for complex validation rules in variable definitions
   */
  required_version = ">= 1.2.0"

  /**
   * Required Providers
   * 
   * Defines the providers needed for PostgreSQL deployment across different cloud platforms.
   * Version constraints ensure compatibility while allowing for minor version updates.
   */
  required_providers {
    /**
     * AWS Provider
     * 
     * Used for deploying PostgreSQL on Amazon RDS with features like:
     * - Multi-AZ deployment with automatic failover
     * - Read replicas for scaling read operations
     * - Performance Insights for query analysis
     * - Enhanced monitoring with CloudWatch integration
     * 
     * Version constraint allows for minor updates but prevents major version changes
     * that might introduce breaking changes.
     */
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.16.0, < 5.0.0"
    }

    /**
     * Azure Provider
     * 
     * Used for deploying PostgreSQL on Azure Database for PostgreSQL with features like:
     * - Zone-redundant high availability
     * - Read replicas for scaling read operations
     * - Advanced Threat Protection
     * - Integration with Azure Monitor
     * 
     * Version constraint ensures compatibility with Azure Database for PostgreSQL features
     * while preventing breaking changes from major version updates.
     */
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0, < 4.0.0"
    }

    /**
     * Google Cloud Provider
     * 
     * Used for deploying PostgreSQL on Cloud SQL with features like:
     * - High availability configuration
     * - Read replicas across zones
     * - Integration with Cloud Monitoring
     * - Automated backups and point-in-time recovery
     * 
     * Version constraint allows for minor updates while preventing major version changes
     * that might introduce breaking changes.
     */
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0, < 5.0.0"
    }

    /**
     * Random Provider
     * 
     * Used for generating random values such as:
     * - Database passwords
     * - Unique identifiers
     * - Suffix for globally unique resource names
     * 
     * Version constraint ensures compatibility with the latest security features
     * while preventing breaking changes from major version updates.
     */
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0, < 4.0.0"
    }
  }
}

/**
 * AWS Provider Configuration
 *
 * Used when deploying PostgreSQL on AWS RDS with the following features:
 * - Multi-AZ deployment for high availability
 * - Read replicas across availability zones
 * - Automated backups with point-in-time recovery
 * - Enhanced monitoring with CloudWatch integration
 */
provider "aws" {
  # Provider configuration will be passed from the root module
  # This block ensures the provider is properly initialized
  # Configuration options like region and credentials are defined in the root module
}

/**
 * Azure Provider Configuration
 *
 * Used when deploying PostgreSQL on Azure Database for PostgreSQL with the following features:
 * - Zone-redundant high availability
 * - Read replicas for scaling read operations
 * - Geo-redundant backups for disaster recovery
 * - Advanced Threat Protection and Azure Monitor integration
 */
provider "azurerm" {
  # Provider configuration will be passed from the root module
  # This block ensures the provider is properly initialized
  features {
    # Required empty block for Azure provider initialization
    # Specific features can be enabled/disabled in the root module
  }
}

/**
 * Google Cloud Provider Configuration
 *
 * Used when deploying PostgreSQL on Cloud SQL with the following features:
 * - High availability configuration with automatic failover
 * - Read replicas across zones
 * - Automated backups and point-in-time recovery
 * - Integration with Cloud Monitoring and Cloud Logging
 */
provider "google" {
  # Provider configuration will be passed from the root module
  # This block ensures the provider is properly initialized
  # Configuration options like project and region are defined in the root module
}