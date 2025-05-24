# --------------------------------------------------------
# Kubernetes Module Variables
# --------------------------------------------------------
# This file defines all input variables for the Kubernetes module,
# enabling flexible and reusable infrastructure configuration across
# development, staging, and production environments for the
# Merchant Cash Advance (MCA) Application Processing System.

# --------------------------------------------------------
# Cluster Configuration Variables
# --------------------------------------------------------

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version to use for the cluster"
  type        = string
  default     = "1.27"
}

variable "region" {
  description = "Region where the Kubernetes cluster will be created"
  type        = string
}

variable "additional_regions" {
  description = "Additional regions for multi-region cluster configuration"
  type        = list(string)
  default     = []
}

variable "cloud_provider" {
  description = "Cloud provider where the Kubernetes cluster will be deployed (aws, azure, gcp)"
  type        = string
  validation {
    condition     = contains(["aws", "azure", "gcp"], var.cloud_provider)
    error_message = "Cloud provider must be one of: aws, azure, gcp."
  }
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# --------------------------------------------------------
# Node Pool Configuration Variables
# --------------------------------------------------------

variable "default_node_pool_name" {
  description = "Name of the default node pool"
  type        = string
  default     = "default"
}

variable "default_node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
  default     = 3
}

variable "default_node_min_count" {
  description = "Minimum number of nodes for autoscaling the default node pool"
  type        = number
  default     = 3
}

variable "default_node_max_count" {
  description = "Maximum number of nodes for autoscaling the default node pool"
  type        = number
  default     = 10
}

variable "default_node_disk_size" {
  description = "Disk size in GB for default node pool VMs"
  type        = number
  default     = 100
}

variable "default_node_machine_type" {
  description = "Machine type for default node pool VMs"
  type        = string
  default     = "Standard_D4s_v3" # Azure default, will be mapped to equivalent in other clouds
}

# GPU Node Pool for OCR Service
variable "enable_gpu_node_pool" {
  description = "Whether to create a GPU-enabled node pool for the OCR service"
  type        = bool
  default     = true
}

variable "gpu_node_pool_name" {
  description = "Name of the GPU node pool for OCR service"
  type        = string
  default     = "gpu-pool"
}

variable "gpu_node_count" {
  description = "Number of GPU nodes for OCR service"
  type        = number
  default     = 2
}

variable "gpu_node_min_count" {
  description = "Minimum number of GPU nodes for autoscaling"
  type        = number
  default     = 1
}

variable "gpu_node_max_count" {
  description = "Maximum number of GPU nodes for autoscaling"
  type        = number
  default     = 5
}

variable "gpu_node_machine_type" {
  description = "Machine type for GPU nodes (should support NVIDIA GPUs)"
  type        = string
  default     = "Standard_NC6s_v3" # Azure GPU VM, will be mapped to equivalent in other clouds
}

variable "gpu_type" {
  description = "Type of GPU to use for the OCR service"
  type        = string
  default     = "nvidia-tesla-v100"
}

# Additional Node Pools
variable "additional_node_pools" {
  description = "Additional node pools to create in the cluster"
  type = list(object({
    name                = string
    machine_type        = string
    node_count          = number
    min_count           = number
    max_count           = number
    disk_size_gb        = number
    node_labels         = map(string)
    node_taints         = list(string)
    auto_repair         = bool
    auto_upgrade        = bool
    preemptible         = bool
  }))
  default = []
}

# --------------------------------------------------------
# Networking Variables
# --------------------------------------------------------

variable "network_plugin" {
  description = "Network plugin to use for the Kubernetes cluster (kubenet, azure, calico)"
  type        = string
  default     = "kubenet"
}

variable "network_policy" {
  description = "Network policy to use for the Kubernetes cluster (calico, azure)"
  type        = string
  default     = "calico"
}

variable "pod_cidr" {
  description = "CIDR block for pod IP addresses"
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_cidr" {
  description = "CIDR block for Kubernetes service IP addresses"
  type        = string
  default     = "10.0.0.0/16"
}

variable "dns_service_ip" {
  description = "IP address for Kubernetes DNS service"
  type        = string
  default     = "10.0.0.10"
}

variable "docker_bridge_cidr" {
  description = "CIDR block for Docker bridge network"
  type        = string
  default     = "172.17.0.1/16"
}

variable "vnet_subnet_id" {
  description = "ID of the subnet where the Kubernetes cluster will be deployed"
  type        = string
  default     = null
}

variable "load_balancer_sku" {
  description = "SKU of the load balancer for Kubernetes services (basic or standard)"
  type        = string
  default     = "standard"
}

variable "private_cluster_enabled" {
  description = "Whether to create a private Kubernetes cluster"
  type        = bool
  default     = false
}

# --------------------------------------------------------
# Authentication and RBAC Variables
# --------------------------------------------------------

variable "rbac_enabled" {
  description = "Whether to enable RBAC for the Kubernetes cluster"
  type        = bool
  default     = true
}

variable "admin_group_object_ids" {
  description = "Object IDs of Azure AD groups with admin access to the cluster"
  type        = list(string)
  default     = []
}

variable "service_account_issuer" {
  description = "Issuer URL for service account tokens"
  type        = string
  default     = ""
}

# --------------------------------------------------------
# Monitoring and Logging Variables
# --------------------------------------------------------

variable "enable_monitoring" {
  description = "Whether to enable monitoring for the Kubernetes cluster"
  type        = bool
  default     = true
}

variable "log_analytics_workspace_id" {
  description = "ID of the Log Analytics workspace for cluster monitoring"
  type        = string
  default     = null
}

variable "enable_log_analytics_solution" {
  description = "Whether to enable the Log Analytics solution for container insights"
  type        = bool
  default     = true
}

variable "metrics_retention_days" {
  description = "Number of days to retain metrics"
  type        = number
  default     = 30
}

variable "enable_datadog_integration" {
  description = "Whether to enable Datadog integration for monitoring"
  type        = bool
  default     = false
}

# --------------------------------------------------------
# Add-ons Variables
# --------------------------------------------------------

variable "enable_http_application_routing" {
  description = "Whether to enable HTTP application routing"
  type        = bool
  default     = false
}

variable "enable_kube_dashboard" {
  description = "Whether to enable the Kubernetes dashboard"
  type        = bool
  default     = false
}

variable "enable_azure_policy" {
  description = "Whether to enable Azure Policy for Kubernetes"
  type        = bool
  default     = false
}

variable "enable_auto_scaling" {
  description = "Whether to enable cluster autoscaler"
  type        = bool
  default     = true
}

variable "enable_host_encryption" {
  description = "Whether to enable host encryption"
  type        = bool
  default     = false
}

# --------------------------------------------------------
# Environment-specific Variables
# --------------------------------------------------------

variable "development_settings" {
  description = "Development environment specific settings"
  type = object({
    default_node_count = number
    default_node_min_count = number
    default_node_max_count = number
    enable_gpu_node_pool = bool
    gpu_node_count = number
  })
  default = {
    default_node_count = 2
    default_node_min_count = 2
    default_node_max_count = 4
    enable_gpu_node_pool = true
    gpu_node_count = 1
  }
}

variable "staging_settings" {
  description = "Staging environment specific settings"
  type = object({
    default_node_count = number
    default_node_min_count = number
    default_node_max_count = number
    enable_gpu_node_pool = bool
    gpu_node_count = number
  })
  default = {
    default_node_count = 3
    default_node_min_count = 3
    default_node_max_count = 6
    enable_gpu_node_pool = true
    gpu_node_count = 2
  }
}

variable "production_settings" {
  description = "Production environment specific settings"
  type = object({
    default_node_count = number
    default_node_min_count = number
    default_node_max_count = number
    enable_gpu_node_pool = bool
    gpu_node_count = number
  })
  default = {
    default_node_count = 5
    default_node_min_count = 5
    default_node_max_count = 10
    enable_gpu_node_pool = true
    gpu_node_count = 3
  }
}

# --------------------------------------------------------
# Maintenance Variables
# --------------------------------------------------------

variable "maintenance_window" {
  description = "Maintenance window for the Kubernetes cluster"
  type = object({
    day   = string
    hours = list(number)
  })
  default = {
    day   = "Sunday"
    hours = [2, 3, 4]
  }
}

variable "auto_upgrade_channel" {
  description = "Auto-upgrade channel for the Kubernetes cluster (none, patch, stable, rapid, node-image)"
  type        = string
  default     = "stable"
}

# --------------------------------------------------------
# Backup and Disaster Recovery Variables
# --------------------------------------------------------

variable "enable_backup" {
  description = "Whether to enable backup for the Kubernetes cluster"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "enable_disaster_recovery" {
  description = "Whether to enable disaster recovery for the Kubernetes cluster"
  type        = bool
  default     = false
}