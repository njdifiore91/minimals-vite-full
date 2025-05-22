# Kubernetes Module Variables
# This file defines all input variables for the Kubernetes module, enabling flexible and reusable
# infrastructure configuration across development, staging, and production environments.

# ---------------------------------------------------------------------------------------------------------------------
# CLUSTER CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version to use for the cluster"
  type        = string
  default     = "1.25.0"
}

variable "cloud_provider" {
  description = "Cloud provider where the cluster will be deployed (aws, azure, gcp)"
  type        = string
  validation {
    condition     = contains(["aws", "azure", "gcp", "on-prem"], var.cloud_provider)
    error_message = "Allowed values for cloud_provider are: aws, azure, gcp, or on-prem."
  }
}

variable "region" {
  description = "Primary region where the cluster will be deployed"
  type        = string
}

variable "additional_regions" {
  description = "Additional regions for multi-region cluster configuration (for high availability)"
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Allowed values for environment are: development, staging, or production."
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------------------------------------------------
# NETWORKING CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "vpc_id" {
  description = "ID of the VPC where the cluster will be deployed"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "List of subnet IDs where the cluster nodes will be deployed"
  type        = list(string)
  default     = []
}

variable "pod_cidr" {
  description = "CIDR block for pod IP addresses"
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_cidr" {
  description = "CIDR block for service IP addresses"
  type        = string
  default     = "10.96.0.0/16"
}

variable "enable_private_endpoint" {
  description = "Whether to enable private endpoint for the Kubernetes API server"
  type        = bool
  default     = true
}

variable "enable_private_nodes" {
  description = "Whether to enable private nodes (no public IP addresses)"
  type        = bool
  default     = true
}

variable "authorized_networks" {
  description = "List of CIDR blocks that can access the Kubernetes API server"
  type        = list(string)
  default     = []
}

# ---------------------------------------------------------------------------------------------------------------------
# NODE POOL CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "default_node_pool_name" {
  description = "Name of the default node pool"
  type        = string
  default     = "default"
}

variable "default_node_pool_machine_type" {
  description = "Machine type for the default node pool"
  type        = string
  default     = "n2-standard-4"
}

variable "default_node_pool_min_count" {
  description = "Minimum number of nodes in the default node pool"
  type        = number
  default     = 1
}

variable "default_node_pool_max_count" {
  description = "Maximum number of nodes in the default node pool"
  type        = number
  default     = 5
}

variable "default_node_pool_disk_size_gb" {
  description = "Disk size (in GB) for each node in the default node pool"
  type        = number
  default     = 100
}

variable "enable_gpu_node_pool" {
  description = "Whether to create a GPU-enabled node pool for OCR service"
  type        = bool
  default     = true
}

variable "gpu_node_pool_name" {
  description = "Name of the GPU-enabled node pool"
  type        = string
  default     = "gpu-pool"
}

variable "gpu_node_pool_machine_type" {
  description = "Machine type for the GPU-enabled node pool"
  type        = string
  default     = "n1-standard-8"
}

variable "gpu_node_pool_accelerator_type" {
  description = "GPU accelerator type for the GPU-enabled node pool"
  type        = string
  default     = "nvidia-tesla-t4"
}

variable "gpu_node_pool_accelerator_count" {
  description = "Number of GPUs per node in the GPU-enabled node pool"
  type        = number
  default     = 1
}

variable "gpu_node_pool_min_count" {
  description = "Minimum number of nodes in the GPU-enabled node pool"
  type        = number
  default     = 0
}

variable "gpu_node_pool_max_count" {
  description = "Maximum number of nodes in the GPU-enabled node pool"
  type        = number
  default     = 3
}

variable "gpu_node_pool_disk_size_gb" {
  description = "Disk size (in GB) for each node in the GPU-enabled node pool"
  type        = number
  default     = 100
}

variable "additional_node_pools" {
  description = "Additional node pools to create (for specialized workloads)"
  type = list(object({
    name                = string
    machine_type        = string
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

# ---------------------------------------------------------------------------------------------------------------------
# MONITORING AND LOGGING CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "enable_monitoring" {
  description = "Whether to enable monitoring for the cluster"
  type        = bool
  default     = true
}

variable "monitoring_service" {
  description = "Monitoring service to use (stackdriver, datadog, prometheus)"
  type        = string
  default     = "stackdriver"
}

variable "enable_logging" {
  description = "Whether to enable logging for the cluster"
  type        = bool
  default     = true
}

variable "logging_service" {
  description = "Logging service to use (stackdriver, elasticsearch, loki)"
  type        = string
  default     = "stackdriver"
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

# ---------------------------------------------------------------------------------------------------------------------
# SECURITY CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "enable_network_policy" {
  description = "Whether to enable Kubernetes NetworkPolicy"
  type        = bool
  default     = true
}

variable "enable_pod_security_policy" {
  description = "Whether to enable PodSecurityPolicy"
  type        = bool
  default     = true
}

variable "enable_rbac" {
  description = "Whether to enable RBAC authorization"
  type        = bool
  default     = true
}

variable "enable_shielded_nodes" {
  description = "Whether to enable Shielded Nodes features on all nodes"
  type        = bool
  default     = true
}

variable "enable_binary_authorization" {
  description = "Whether to enable Binary Authorization"
  type        = bool
  default     = false
}

variable "master_authorized_networks_config_cidr_blocks" {
  description = "List of CIDR blocks to allow access to the Kubernetes master"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

# ---------------------------------------------------------------------------------------------------------------------
# ENVIRONMENT-SPECIFIC CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "development_node_count" {
  description = "Number of nodes for development environment"
  type        = number
  default     = 1
}

variable "staging_node_count" {
  description = "Number of nodes for staging environment"
  type        = number
  default     = 2
}

variable "production_node_count" {
  description = "Number of nodes for production environment"
  type        = number
  default     = 3
}

variable "development_machine_type" {
  description = "Machine type for development environment"
  type        = string
  default     = "n2-standard-2"
}

variable "staging_machine_type" {
  description = "Machine type for staging environment"
  type        = string
  default     = "n2-standard-4"
}

variable "production_machine_type" {
  description = "Machine type for production environment"
  type        = string
  default     = "n2-standard-8"
}

# ---------------------------------------------------------------------------------------------------------------------
# RESOURCE ALLOCATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "resource_quotas" {
  description = "Resource quotas for each namespace"
  type = map(object({
    cpu_request     = string
    memory_request  = string
    cpu_limit       = string
    memory_limit    = string
    pods            = number
    services        = number
    persistent_volumes = number
  }))
  default = {
    "email-service" = {
      cpu_request     = "1"
      memory_request  = "2Gi"
      cpu_limit       = "2"
      memory_limit    = "4Gi"
      pods            = 10
      services        = 5
      persistent_volumes = 2
    },
    "document-service" = {
      cpu_request     = "2"
      memory_request  = "4Gi"
      cpu_limit       = "4"
      memory_limit    = "8Gi"
      pods            = 10
      services        = 5
      persistent_volumes = 5
    },
    "ocr-service" = {
      cpu_request     = "4"
      memory_request  = "8Gi"
      cpu_limit       = "8"
      memory_limit    = "16Gi"
      pods            = 10
      services        = 5
      persistent_volumes = 10
    },
    "data-service" = {
      cpu_request     = "2"
      memory_request  = "4Gi"
      cpu_limit       = "4"
      memory_limit    = "8Gi"
      pods            = 10
      services        = 5
      persistent_volumes = 5
    },
    "notification-service" = {
      cpu_request     = "1"
      memory_request  = "2Gi"
      cpu_limit       = "2"
      memory_limit    = "4Gi"
      pods            = 10
      services        = 5
      persistent_volumes = 2
    }
  }
}

variable "limit_ranges" {
  description = "Default container resource limits for each namespace"
  type = map(object({
    default_request_cpu    = string
    default_request_memory = string
    default_limit_cpu      = string
    default_limit_memory   = string
  }))
  default = {
    "email-service" = {
      default_request_cpu    = "100m"
      default_request_memory = "256Mi"
      default_limit_cpu      = "500m"
      default_limit_memory   = "512Mi"
    },
    "document-service" = {
      default_request_cpu    = "200m"
      default_request_memory = "512Mi"
      default_limit_cpu      = "1"
      default_limit_memory   = "1Gi"
    },
    "ocr-service" = {
      default_request_cpu    = "500m"
      default_request_memory = "1Gi"
      default_limit_cpu      = "2"
      default_limit_memory   = "4Gi"
    },
    "data-service" = {
      default_request_cpu    = "200m"
      default_request_memory = "512Mi"
      default_limit_cpu      = "1"
      default_limit_memory   = "1Gi"
    },
    "notification-service" = {
      default_request_cpu    = "100m"
      default_request_memory = "256Mi"
      default_limit_cpu      = "500m"
      default_limit_memory   = "512Mi"
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# ADDON CONFIGURATION VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "enable_horizontal_pod_autoscaler" {
  description = "Whether to enable the Horizontal Pod Autoscaler addon"
  type        = bool
  default     = true
}

variable "enable_http_load_balancing" {
  description = "Whether to enable the HTTP (L7) load balancing addon"
  type        = bool
  default     = true
}

variable "enable_network_policy_config" {
  description = "Whether to enable NetworkPolicy addon"
  type        = bool
  default     = true
}

variable "enable_dns_cache" {
  description = "Whether to enable NodeLocal DNSCache addon"
  type        = bool
  default     = true
}

variable "enable_config_connector" {
  description = "Whether to enable Config Connector addon"
  type        = bool
  default     = false
}

variable "enable_gce_persistent_disk_csi_driver" {
  description = "Whether to enable the GCE PD CSI driver addon"
  type        = bool
  default     = true
}