# Node pool configuration for Kubernetes clusters across different cloud providers
# This file defines the node pools for the MCA Application Processing System,
# including specialized GPU-enabled nodes for the OCR service.

# Node pool configuration variables
variable "node_pools" {
  description = "Configuration for node pools in the Kubernetes cluster"
  type = object({
    # Standard node pool for general workloads
    standard = object({
      name                = string
      min_count           = number
      max_count           = number
      desired_count       = number
      disk_size_gb        = number
      labels              = map(string)
      taints              = list(object({
        key    = string
        value  = string
        effect = string
      }))
      # Cloud-specific machine types
      machine_type = object({
        aws    = string
        azure  = string
        google = string
      })
    })
    
    # Service-specific node pool for data processing
    service = object({
      name                = string
      min_count           = number
      max_count           = number
      desired_count       = number
      disk_size_gb        = number
      labels              = map(string)
      taints              = list(object({
        key    = string
        value  = string
        effect = string
      }))
      # Cloud-specific machine types
      machine_type = object({
        aws    = string
        azure  = string
        google = string
      })
    })
    
    # GPU-enabled node pool for OCR service
    gpu = object({
      name                = string
      min_count           = number
      max_count           = number
      desired_count       = number
      disk_size_gb        = number
      labels              = map(string)
      taints              = list(object({
        key    = string
        value  = string
        effect = string
      }))
      # Cloud-specific machine types with GPU
      machine_type = object({
        aws    = string
        azure  = string
        google = string
      })
      # GPU configuration
      gpu_type = object({
        aws    = string
        azure  = string
        google = string
      })
      gpu_count = number
    })
  })
  
  default = {
    standard = {
      name          = "standard"
      min_count     = 2
      max_count     = 5
      desired_count = 3
      disk_size_gb  = 100
      labels = {
        "node-type" = "standard"
        "workload"  = "general"
      }
      taints = []
      machine_type = {
        aws    = "m5.large"
        azure  = "Standard_D2s_v3"
        google = "e2-standard-2"
      }
    },
    service = {
      name          = "service"
      min_count     = 2
      max_count     = 8
      desired_count = 3
      disk_size_gb  = 150
      labels = {
        "node-type" = "service"
        "workload"  = "data-processing"
      }
      taints = [{
        key    = "dedicated"
        value  = "service"
        effect = "NoSchedule"
      }]
      machine_type = {
        aws    = "m5.xlarge"
        azure  = "Standard_D4s_v3"
        google = "e2-standard-4"
      }
    },
    gpu = {
      name          = "ocr-gpu"
      min_count     = 1
      max_count     = 4
      desired_count = 2
      disk_size_gb  = 200
      labels = {
        "node-type" = "gpu"
        "workload"  = "ocr-processing"
        "accelerator" = "nvidia-tesla"
      }
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "present"
        effect = "NoSchedule"
      }]
      machine_type = {
        aws    = "p3.2xlarge"
        azure  = "Standard_NC6s_v3"
        google = "n1-standard-4"
      }
      gpu_type = {
        aws    = "nvidia-tesla-v100"
        azure  = "nvidia-tesla-v100"
        google = "nvidia-tesla-v100"
      }
      gpu_count = 1
    }
  }
}

# AWS EKS Node Groups
resource "aws_eks_node_group" "standard" {
  count = var.cloud_provider == "aws" ? 1 : 0
  
  cluster_name    = var.cluster_name
  node_group_name = var.node_pools.standard.name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.subnet_ids
  
  scaling_config {
    desired_size = var.node_pools.standard.desired_count
    max_size     = var.node_pools.standard.max_count
    min_size     = var.node_pools.standard.min_count
  }
  
  instance_types = [var.node_pools.standard.machine_type.aws]
  disk_size      = var.node_pools.standard.disk_size_gb
  
  labels = var.node_pools.standard.labels
  
  # Ensure zero-downtime upgrades
  update_config {
    max_unavailable_percentage = 25
  }
  
  # Enable autoscaling
  tags = {
    "k8s.io/cluster-autoscaler/enabled"             = "true"
    "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
  }
  
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "service" {
  count = var.cloud_provider == "aws" ? 1 : 0
  
  cluster_name    = var.cluster_name
  node_group_name = var.node_pools.service.name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.subnet_ids
  
  scaling_config {
    desired_size = var.node_pools.service.desired_count
    max_size     = var.node_pools.service.max_count
    min_size     = var.node_pools.service.min_count
  }
  
  instance_types = [var.node_pools.service.machine_type.aws]
  disk_size      = var.node_pools.service.disk_size_gb
  
  labels = var.node_pools.service.labels
  
  # Apply taints
  taint {
    key    = var.node_pools.service.taints[0].key
    value  = var.node_pools.service.taints[0].value
    effect = var.node_pools.service.taints[0].effect
  }
  
  # Ensure zero-downtime upgrades
  update_config {
    max_unavailable_percentage = 25
  }
  
  # Enable autoscaling
  tags = {
    "k8s.io/cluster-autoscaler/enabled"             = "true"
    "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
  }
  
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "gpu" {
  count = var.cloud_provider == "aws" ? 1 : 0
  
  cluster_name    = var.cluster_name
  node_group_name = var.node_pools.gpu.name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.subnet_ids
  
  scaling_config {
    desired_size = var.node_pools.gpu.desired_count
    max_size     = var.node_pools.gpu.max_count
    min_size     = var.node_pools.gpu.min_count
  }
  
  # GPU-enabled instance type
  instance_types = [var.node_pools.gpu.machine_type.aws]
  disk_size      = var.node_pools.gpu.disk_size_gb
  
  labels = var.node_pools.gpu.labels
  
  # Apply GPU taints
  taint {
    key    = var.node_pools.gpu.taints[0].key
    value  = var.node_pools.gpu.taints[0].value
    effect = var.node_pools.gpu.taints[0].effect
  }
  
  # Ensure zero-downtime upgrades
  update_config {
    max_unavailable = 1
  }
  
  # Enable autoscaling
  tags = {
    "k8s.io/cluster-autoscaler/enabled"             = "true"
    "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
  }
  
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

# Azure AKS Node Pools
resource "azurerm_kubernetes_cluster_node_pool" "standard" {
  count = var.cloud_provider == "azure" ? 1 : 0
  
  name                  = var.node_pools.standard.name
  kubernetes_cluster_id = var.cluster_id
  vm_size               = var.node_pools.standard.machine_type.azure
  os_disk_size_gb       = var.node_pools.standard.disk_size_gb
  
  node_count           = var.node_pools.standard.desired_count
  enable_auto_scaling  = true
  min_count            = var.node_pools.standard.min_count
  max_count            = var.node_pools.standard.max_count
  
  node_labels = var.node_pools.standard.labels
  
  # Ensure zero-downtime upgrades
  upgrade_settings {
    max_surge = "25%"
  }
  
  lifecycle {
    ignore_changes = [node_count]
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "service" {
  count = var.cloud_provider == "azure" ? 1 : 0
  
  name                  = var.node_pools.service.name
  kubernetes_cluster_id = var.cluster_id
  vm_size               = var.node_pools.service.machine_type.azure
  os_disk_size_gb       = var.node_pools.service.disk_size_gb
  
  node_count           = var.node_pools.service.desired_count
  enable_auto_scaling  = true
  min_count            = var.node_pools.service.min_count
  max_count            = var.node_pools.service.max_count
  
  node_labels = var.node_pools.service.labels
  
  # Apply taints
  node_taints = [
    "${var.node_pools.service.taints[0].key}=${var.node_pools.service.taints[0].value}:${var.node_pools.service.taints[0].effect}"
  ]
  
  # Ensure zero-downtime upgrades
  upgrade_settings {
    max_surge = "25%"
  }
  
  lifecycle {
    ignore_changes = [node_count]
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  count = var.cloud_provider == "azure" ? 1 : 0
  
  name                  = var.node_pools.gpu.name
  kubernetes_cluster_id = var.cluster_id
  vm_size               = var.node_pools.gpu.machine_type.azure
  os_disk_size_gb       = var.node_pools.gpu.disk_size_gb
  
  node_count           = var.node_pools.gpu.desired_count
  enable_auto_scaling  = true
  min_count            = var.node_pools.gpu.min_count
  max_count            = var.node_pools.gpu.max_count
  
  node_labels = var.node_pools.gpu.labels
  
  # Apply GPU taints
  node_taints = [
    "${var.node_pools.gpu.taints[0].key}=${var.node_pools.gpu.taints[0].value}:${var.node_pools.gpu.taints[0].effect}"
  ]
  
  # Ensure zero-downtime upgrades
  upgrade_settings {
    max_surge = "25%"
  }
  
  lifecycle {
    ignore_changes = [node_count]
  }
}

# Google GKE Node Pools
resource "google_container_node_pool" "standard" {
  count = var.cloud_provider == "google" ? 1 : 0
  
  name       = var.node_pools.standard.name
  cluster    = var.cluster_name
  location   = var.location
  node_count = var.node_pools.standard.desired_count
  
  autoscaling {
    min_node_count = var.node_pools.standard.min_count
    max_node_count = var.node_pools.standard.max_count
  }
  
  node_config {
    machine_type = var.node_pools.standard.machine_type.google
    disk_size_gb = var.node_pools.standard.disk_size_gb
    
    labels = var.node_pools.standard.labels
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
  
  # Ensure zero-downtime upgrades
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
  
  lifecycle {
    ignore_changes = [node_count]
  }
}

resource "google_container_node_pool" "service" {
  count = var.cloud_provider == "google" ? 1 : 0
  
  name       = var.node_pools.service.name
  cluster    = var.cluster_name
  location   = var.location
  node_count = var.node_pools.service.desired_count
  
  autoscaling {
    min_node_count = var.node_pools.service.min_count
    max_node_count = var.node_pools.service.max_count
  }
  
  node_config {
    machine_type = var.node_pools.service.machine_type.google
    disk_size_gb = var.node_pools.service.disk_size_gb
    
    labels = var.node_pools.service.labels
    
    # Apply taints
    taint {
      key    = var.node_pools.service.taints[0].key
      value  = var.node_pools.service.taints[0].value
      effect = var.node_pools.service.taints[0].effect
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
  
  # Ensure zero-downtime upgrades
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
  
  lifecycle {
    ignore_changes = [node_count]
  }
}

resource "google_container_node_pool" "gpu" {
  count = var.cloud_provider == "google" ? 1 : 0
  
  name       = var.node_pools.gpu.name
  cluster    = var.cluster_name
  location   = var.location
  node_count = var.node_pools.gpu.desired_count
  
  autoscaling {
    min_node_count = var.node_pools.gpu.min_count
    max_node_count = var.node_pools.gpu.max_count
  }
  
  node_config {
    machine_type = var.node_pools.gpu.machine_type.google
    disk_size_gb = var.node_pools.gpu.disk_size_gb
    
    labels = var.node_pools.gpu.labels
    
    # Apply GPU taints
    taint {
      key    = var.node_pools.gpu.taints[0].key
      value  = var.node_pools.gpu.taints[0].value
      effect = var.node_pools.gpu.taints[0].effect
    }
    
    # Configure GPU
    guest_accelerator {
      type  = var.node_pools.gpu.gpu_type.google
      count = var.node_pools.gpu.gpu_count
    }
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
  
  # Ensure zero-downtime upgrades
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
  
  lifecycle {
    ignore_changes = [node_count]
  }
}

# Additional variables needed for node pools
variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "cluster_id" {
  description = "ID of the Kubernetes cluster (required for Azure)"
  type        = string
  default     = ""
}

variable "location" {
  description = "Location/region where the cluster is deployed"
  type        = string
  default     = ""
}

variable "node_role_arn" {
  description = "ARN of the IAM role for nodes (required for AWS)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "List of subnet IDs where nodes will be deployed (required for AWS)"
  type        = list(string)
  default     = []
}

# Outputs for node pools
output "node_pools" {
  description = "Details of the created node pools"
  value = {
    standard = var.cloud_provider == "aws" ? aws_eks_node_group.standard : (
              var.cloud_provider == "azure" ? azurerm_kubernetes_cluster_node_pool.standard : (
              var.cloud_provider == "google" ? google_container_node_pool.standard : null))
    service = var.cloud_provider == "aws" ? aws_eks_node_group.service : (
              var.cloud_provider == "azure" ? azurerm_kubernetes_cluster_node_pool.service : (
              var.cloud_provider == "google" ? google_container_node_pool.service : null))
    gpu = var.cloud_provider == "aws" ? aws_eks_node_group.gpu : (
          var.cloud_provider == "azure" ? azurerm_kubernetes_cluster_node_pool.gpu : (
          var.cloud_provider == "google" ? google_container_node_pool.gpu : null))
  }
}

# NVIDIA GPU Operator installation (optional)
variable "install_gpu_operator" {
  description = "Whether to install the NVIDIA GPU Operator for GPU support"
  type        = bool
  default     = true
}

# Helm release for NVIDIA GPU Operator
resource "helm_release" "gpu_operator" {
  count = var.install_gpu_operator && var.cloud_provider != "" ? 1 : 0
  
  name       = "gpu-operator"
  repository = "https://nvidia.github.io/gpu-operator"
  chart      = "gpu-operator"
  namespace  = "gpu-operator"
  version    = "v23.3.2"  # Use appropriate version
  
  # Create namespace if it doesn't exist
  create_namespace = true
  
  # Values for the GPU Operator
  set {
    name  = "operator.defaultRuntime"
    value = "containerd"
  }
  
  depends_on = [
    aws_eks_node_group.gpu,
    azurerm_kubernetes_cluster_node_pool.gpu,
    google_container_node_pool.gpu
  ]
}