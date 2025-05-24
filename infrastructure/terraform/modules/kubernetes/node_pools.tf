# Node Pools Configuration for MCA Application Processing System
# This file defines the various node pools for the Kubernetes cluster,
# including specialized GPU-enabled nodes for the OCR service.

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version to use for the node pools"
  type        = string
}

variable "node_pools_labels" {
  description = "Map of maps containing node labels by node-pool name"
  type        = map(map(string))
  default     = {}
}

variable "node_pools_taints" {
  description = "Map of lists containing node taints by node-pool name"
  type        = map(list(object({ key = string, value = string, effect = string })))
  default     = {}
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "cloud_provider" {
  description = "Cloud provider where the cluster is deployed (gcp, azure, aws)"
  type        = string
  default     = "gcp"
  validation {
    condition     = contains(["gcp", "azure", "aws"], var.cloud_provider)
    error_message = "Cloud provider must be one of: gcp, azure, aws."
  }
}

variable "region" {
  description = "Region where the cluster is deployed"
  type        = string
}

# Local variables for node pool configuration based on environment
locals {
  # Cloud provider specific configurations
  cloud_configs = {
    gcp = {
      # GCP machine types and disk types
      standard_machine_types = {
        development = "n2-standard-4"
        staging     = "n2-standard-8"
        production  = "n2-standard-8"
      }
      ocr_machine_types = {
        development = "n1-standard-8"
        staging     = "n1-standard-8"
        production  = "n1-standard-16"
      }
      data_machine_types = {
        development = "n2-standard-8"
        staging     = "n2-standard-16"
        production  = "n2-standard-16"
      }
      disk_types = {
        standard = "pd-standard"
        ssd      = "pd-ssd"
      }
      gpu_types = {
        development = "nvidia-tesla-t4"
        staging     = "nvidia-tesla-t4"
        production  = "nvidia-tesla-v100"
      }
    }
    azure = {
      # Azure VM sizes and disk types
      standard_machine_types = {
        development = "Standard_D4s_v3"
        staging     = "Standard_D8s_v3"
        production  = "Standard_D8s_v3"
      }
      ocr_machine_types = {
        development = "Standard_NC6s_v3"
        staging     = "Standard_NC6s_v3"
        production  = "Standard_NC12s_v3"
      }
      data_machine_types = {
        development = "Standard_D8s_v3"
        staging     = "Standard_D16s_v3"
        production  = "Standard_D16s_v3"
      }
      disk_types = {
        standard = "Standard_LRS"
        ssd      = "Premium_LRS"
      }
      gpu_types = {
        development = "nvidia-tesla-t4"
        staging     = "nvidia-tesla-t4"
        production  = "nvidia-tesla-v100"
      }
    }
    aws = {
      # AWS instance types and volume types
      standard_machine_types = {
        development = "m5.xlarge"
        staging     = "m5.2xlarge"
        production  = "m5.2xlarge"
      }
      ocr_machine_types = {
        development = "g4dn.2xlarge"
        staging     = "g4dn.2xlarge"
        production  = "p3.2xlarge"
      }
      data_machine_types = {
        development = "m5.2xlarge"
        staging     = "m5.4xlarge"
        production  = "m5.4xlarge"
      }
      disk_types = {
        standard = "gp2"
        ssd      = "gp3"
      }
      gpu_types = {
        development = "nvidia-tesla-t4"
        staging     = "nvidia-tesla-t4"
        production  = "nvidia-tesla-v100"
      }
    }
  }

  # Get the cloud provider specific configuration
  cloud_config = local.cloud_configs[var.cloud_provider]

  # Standard node pool configuration
  standard_node_pool_config = {
    development = {
      min_count     = 1
      max_count     = 3
      machine_type  = local.cloud_config.standard_machine_types.development
      disk_size_gb  = 100
      disk_type     = local.cloud_config.disk_types.standard
    }
    staging = {
      min_count     = 2
      max_count     = 5
      machine_type  = local.cloud_config.standard_machine_types.staging
      disk_size_gb  = 100
      disk_type     = local.cloud_config.disk_types.standard
    }
    production = {
      min_count     = 3
      max_count     = 10
      machine_type  = local.cloud_config.standard_machine_types.production
      disk_size_gb  = 100
      disk_type     = local.cloud_config.disk_types.ssd
    }
  }

  # OCR service node pool configuration with GPU
  ocr_node_pool_config = {
    development = {
      min_count        = 1
      max_count        = 2
      machine_type     = local.cloud_config.ocr_machine_types.development
      accelerator_type = local.cloud_config.gpu_types.development
      accelerator_count = 1
      disk_size_gb     = 100
      disk_type        = local.cloud_config.disk_types.ssd
    }
    staging = {
      min_count        = 1
      max_count        = 3
      machine_type     = local.cloud_config.ocr_machine_types.staging
      accelerator_type = local.cloud_config.gpu_types.staging
      accelerator_count = 1
      disk_size_gb     = 200
      disk_type        = local.cloud_config.disk_types.ssd
    }
    production = {
      min_count        = 2
      max_count        = 5
      machine_type     = local.cloud_config.ocr_machine_types.production
      accelerator_type = local.cloud_config.gpu_types.production
      accelerator_count = 1
      disk_size_gb     = 200
      disk_type        = local.cloud_config.disk_types.ssd
    }
  }

  # Data service node pool configuration
  data_node_pool_config = {
    development = {
      min_count     = 1
      max_count     = 3
      machine_type  = local.cloud_config.data_machine_types.development
      disk_size_gb  = 100
      disk_type     = local.cloud_config.disk_types.standard
    }
    staging = {
      min_count     = 2
      max_count     = 5
      machine_type  = local.cloud_config.data_machine_types.staging
      disk_size_gb  = 200
      disk_type     = local.cloud_config.disk_types.standard
    }
    production = {
      min_count     = 3
      max_count     = 8
      machine_type  = local.cloud_config.data_machine_types.production
      disk_size_gb  = 200
      disk_type     = local.cloud_config.disk_types.ssd
    }
  }

  # Default node labels
  default_node_labels = {
    "app.kubernetes.io/managed-by" = "terraform"
    "environment"                  = var.environment
  }

  # Default node taints
  default_node_taints = []

  # OCR node taints to ensure GPU workloads are scheduled appropriately
  ocr_node_taints = [
    {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NoSchedule"
    }
  ]
}

# Standard node pool for general workloads
resource "google_container_node_pool" "standard" {
  count      = var.cloud_provider == "gcp" ? 1 : 0
  name       = "standard-pool"
  cluster    = var.cluster_name
  version    = var.kubernetes_version
  node_count = null
  location   = var.region

  autoscaling {
    min_node_count = local.standard_node_pool_config[var.environment].min_count
    max_node_count = local.standard_node_pool_config[var.environment].max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    machine_type = local.standard_node_pool_config[var.environment].machine_type
    disk_size_gb = local.standard_node_pool_config[var.environment].disk_size_gb
    disk_type    = local.standard_node_pool_config[var.environment].disk_type
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only"
    ]

    labels = merge(
      local.default_node_labels,
      { "node-pool" = "standard" },
      lookup(var.node_pools_labels, "standard", {})
    )

    dynamic "taint" {
      for_each = concat(
        local.default_node_taints,
        lookup(var.node_pools_taints, "standard", [])
      )
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Azure AKS node pool for standard workloads
resource "azurerm_kubernetes_cluster_node_pool" "standard" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "standard"
  kubernetes_cluster_id = var.cluster_name
  vm_size               = local.standard_node_pool_config[var.environment].machine_type
  os_disk_size_gb       = local.standard_node_pool_config[var.environment].disk_size_gb
  os_disk_type          = local.standard_node_pool_config[var.environment].disk_type == local.cloud_config.disk_types.ssd ? "Managed" : "Ephemeral"
  enable_auto_scaling   = true
  min_count             = local.standard_node_pool_config[var.environment].min_count
  max_count             = local.standard_node_pool_config[var.environment].max_count
  node_labels           = merge(
    local.default_node_labels,
    { "node-pool" = "standard" },
    lookup(var.node_pools_labels, "standard", {})
  )
  
  dynamic "node_taints" {
    for_each = concat(
      local.default_node_taints,
      lookup(var.node_pools_taints, "standard", [])
    )
    content {
      key    = node_taints.value.key
      value  = node_taints.value.value
      effect = node_taints.value.effect
    }
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# AWS EKS node group for standard workloads
resource "aws_eks_node_group" "standard" {
  count           = var.cloud_provider == "aws" ? 1 : 0
  cluster_name    = var.cluster_name
  node_group_name = "standard-pool"
  node_role_arn   = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:role/eks-node-group-role"
  subnet_ids      = data.aws_subnets.private[0].ids
  version         = var.kubernetes_version
  
  scaling_config {
    desired_size = local.standard_node_pool_config[var.environment].min_count
    min_size     = local.standard_node_pool_config[var.environment].min_count
    max_size     = local.standard_node_pool_config[var.environment].max_count
  }
  
  instance_types = [local.standard_node_pool_config[var.environment].machine_type]
  
  disk_size = local.standard_node_pool_config[var.environment].disk_size_gb
  
  labels = merge(
    local.default_node_labels,
    { "node-pool" = "standard" },
    lookup(var.node_pools_labels, "standard", {})
  )
  
  # AWS doesn't support taints directly in the node group resource
  # They need to be applied separately using kubectl or the Kubernetes provider
  
  update_config {
    max_unavailable = 1
  }
  
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

# Data sources for AWS (only created when using AWS)
data "aws_caller_identity" "current" {
  count = var.cloud_provider == "aws" ? 1 : 0
}

data "aws_subnets" "private" {
  count = var.cloud_provider == "aws" ? 1 : 0
  filter {
    name   = "tag:Name"
    values = ["*private*"]
  }
}

# OCR service node pool with GPU for document processing (GCP)
resource "google_container_node_pool" "ocr" {
  count      = var.cloud_provider == "gcp" ? 1 : 0
  name       = "ocr-gpu-pool"
  cluster    = var.cluster_name
  version    = var.kubernetes_version
  node_count = null
  location   = var.region

  autoscaling {
    min_node_count = local.ocr_node_pool_config[var.environment].min_count
    max_node_count = local.ocr_node_pool_config[var.environment].max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = false  # Disable auto-upgrade for GPU nodes to prevent driver compatibility issues
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    machine_type = local.ocr_node_pool_config[var.environment].machine_type
    disk_size_gb = local.ocr_node_pool_config[var.environment].disk_size_gb
    disk_type    = local.ocr_node_pool_config[var.environment].disk_type
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only"
    ]

    # GPU configuration
    guest_accelerator {
      type  = local.ocr_node_pool_config[var.environment].accelerator_type
      count = local.ocr_node_pool_config[var.environment].accelerator_count
    }

    labels = merge(
      local.default_node_labels,
      { 
        "node-pool" = "ocr-gpu",
        "nvidia.com/gpu" = "present",
        "workload" = "ocr-service"
      },
      lookup(var.node_pools_labels, "ocr", {})
    )

    dynamic "taint" {
      for_each = concat(
        local.default_node_taints,
        local.ocr_node_taints,
        lookup(var.node_pools_taints, "ocr", [])
      )
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# OCR service node pool with GPU for document processing (Azure)
resource "azurerm_kubernetes_cluster_node_pool" "ocr" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "ocrgpu"
  kubernetes_cluster_id = var.cluster_name
  vm_size               = local.ocr_node_pool_config[var.environment].machine_type  # This should be a GPU-enabled VM size like Standard_NC6s_v3
  os_disk_size_gb       = local.ocr_node_pool_config[var.environment].disk_size_gb
  os_disk_type          = "Managed"
  enable_auto_scaling   = true
  min_count             = local.ocr_node_pool_config[var.environment].min_count
  max_count             = local.ocr_node_pool_config[var.environment].max_count
  node_labels           = merge(
    local.default_node_labels,
    { 
      "node-pool" = "ocr-gpu",
      "nvidia.com/gpu" = "present",
      "workload" = "ocr-service"
    },
    lookup(var.node_pools_labels, "ocr", {})
  )
  
  # Add taints to ensure only GPU workloads are scheduled on these nodes
  node_taints = [
    "nvidia.com/gpu=present:NoSchedule"
  ]
  
  # Disable automatic upgrades for GPU nodes to prevent driver compatibility issues
  upgrade_settings {
    max_surge = "33%"
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# OCR service node group with GPU for document processing (AWS)
resource "aws_eks_node_group" "ocr" {
  count           = var.cloud_provider == "aws" ? 1 : 0
  cluster_name    = var.cluster_name
  node_group_name = "ocr-gpu-pool"
  node_role_arn   = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:role/eks-node-group-role"
  subnet_ids      = data.aws_subnets.private[0].ids
  version         = var.kubernetes_version
  
  scaling_config {
    desired_size = local.ocr_node_pool_config[var.environment].min_count
    min_size     = local.ocr_node_pool_config[var.environment].min_count
    max_size     = local.ocr_node_pool_config[var.environment].max_count
  }
  
  # Use GPU-enabled instance types (g4dn.xlarge, p3.2xlarge, etc.)
  instance_types = [local.ocr_node_pool_config[var.environment].machine_type]
  
  disk_size = local.ocr_node_pool_config[var.environment].disk_size_gb
  
  labels = merge(
    local.default_node_labels,
    { 
      "node-pool" = "ocr-gpu",
      "nvidia.com/gpu" = "present",
      "workload" = "ocr-service"
    },
    lookup(var.node_pools_labels, "ocr", {})
  )
  
  # AWS doesn't support taints directly in the node group resource
  # They need to be applied separately using kubectl or the Kubernetes provider
  
  update_config {
    max_unavailable = 1
  }
  
  # Add a custom AMI with pre-installed NVIDIA drivers if needed
  # ami_type = "AL2_x86_64_GPU"
  
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

# Data service node pool for database operations (GCP)
resource "google_container_node_pool" "data" {
  count      = var.cloud_provider == "gcp" ? 1 : 0
  name       = "data-pool"
  cluster    = var.cluster_name
  version    = var.kubernetes_version
  node_count = null
  location   = var.region

  autoscaling {
    min_node_count = local.data_node_pool_config[var.environment].min_count
    max_node_count = local.data_node_pool_config[var.environment].max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  node_config {
    machine_type = local.data_node_pool_config[var.environment].machine_type
    disk_size_gb = local.data_node_pool_config[var.environment].disk_size_gb
    disk_type    = local.data_node_pool_config[var.environment].disk_type
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only"
    ]

    labels = merge(
      local.default_node_labels,
      { 
        "node-pool" = "data",
        "workload" = "data-service"
      },
      lookup(var.node_pools_labels, "data", {})
    )

    dynamic "taint" {
      for_each = concat(
        local.default_node_taints,
        lookup(var.node_pools_taints, "data", [])
      )
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Data service node pool for database operations (Azure)
resource "azurerm_kubernetes_cluster_node_pool" "data" {
  count                 = var.cloud_provider == "azure" ? 1 : 0
  name                  = "data"
  kubernetes_cluster_id = var.cluster_name
  vm_size               = local.data_node_pool_config[var.environment].machine_type
  os_disk_size_gb       = local.data_node_pool_config[var.environment].disk_size_gb
  os_disk_type          = local.data_node_pool_config[var.environment].disk_type == local.cloud_config.disk_types.ssd ? "Managed" : "Ephemeral"
  enable_auto_scaling   = true
  min_count             = local.data_node_pool_config[var.environment].min_count
  max_count             = local.data_node_pool_config[var.environment].max_count
  node_labels           = merge(
    local.default_node_labels,
    { 
      "node-pool" = "data",
      "workload" = "data-service"
    },
    lookup(var.node_pools_labels, "data", {})
  )
  
  dynamic "node_taints" {
    for_each = concat(
      local.default_node_taints,
      lookup(var.node_pools_taints, "data", [])
    )
    content {
      key    = node_taints.value.key
      value  = node_taints.value.value
      effect = node_taints.value.effect
    }
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Data service node group for database operations (AWS)
resource "aws_eks_node_group" "data" {
  count           = var.cloud_provider == "aws" ? 1 : 0
  cluster_name    = var.cluster_name
  node_group_name = "data-pool"
  node_role_arn   = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:role/eks-node-group-role"
  subnet_ids      = data.aws_subnets.private[0].ids
  version         = var.kubernetes_version
  
  scaling_config {
    desired_size = local.data_node_pool_config[var.environment].min_count
    min_size     = local.data_node_pool_config[var.environment].min_count
    max_size     = local.data_node_pool_config[var.environment].max_count
  }
  
  instance_types = [local.data_node_pool_config[var.environment].machine_type]
  
  disk_size = local.data_node_pool_config[var.environment].disk_size_gb
  
  labels = merge(
    local.default_node_labels,
    { 
      "node-pool" = "data",
      "workload" = "data-service"
    },
    lookup(var.node_pools_labels, "data", {})
  )
  
  # AWS doesn't support taints directly in the node group resource
  # They need to be applied separately using kubectl or the Kubernetes provider
  
  update_config {
    max_unavailable = 1
  }
  
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

# Outputs for node pool IDs
output "standard_node_pool_id" {
  description = "ID of the standard node pool"
  value       = var.cloud_provider == "gcp" ? google_container_node_pool.standard[0].id : (
                var.cloud_provider == "azure" ? azurerm_kubernetes_cluster_node_pool.standard[0].id : (
                var.cloud_provider == "aws" ? aws_eks_node_group.standard[0].id : null
                ))
}

output "ocr_node_pool_id" {
  description = "ID of the OCR GPU node pool"
  value       = var.cloud_provider == "gcp" ? google_container_node_pool.ocr[0].id : (
                var.cloud_provider == "azure" ? azurerm_kubernetes_cluster_node_pool.ocr[0].id : (
                var.cloud_provider == "aws" ? aws_eks_node_group.ocr[0].id : null
                ))
}

output "data_node_pool_id" {
  description = "ID of the data service node pool"
  value       = var.cloud_provider == "gcp" ? google_container_node_pool.data[0].id : (
                var.cloud_provider == "azure" ? azurerm_kubernetes_cluster_node_pool.data[0].id : (
                var.cloud_provider == "aws" ? aws_eks_node_group.data[0].id : null
                ))
}