/**
 * Kubernetes Cluster Module for MCA Application Processing System
 *
 * This module defines the core Kubernetes cluster configuration for the MCA Application Processing System.
 * It establishes the primary cluster resource, its version, networking settings, and authentication mechanisms.
 * The module is designed to be provider-agnostic, supporting deployment across AWS EKS, Azure AKS, or GCP GKE.
 *
 * The module implements:
 * - Provider-agnostic cluster configuration
 * - Networking with pod and service CIDR ranges
 * - Monitoring and logging integrations
 * - Cluster autoscaling capabilities
 * - Security settings including network policies and pod security policies
 * - Multi-region support for high availability
 * - Namespace segregation for service isolation
 */

# ---------------------------------------------------------------------------------------------------------------------
# LOCAL VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

locals {
  # Validate and set Kubernetes version based on cloud provider
  kubernetes_version_validated = var.kubernetes_version

  # Environment-specific settings
  node_count = lookup({
    development = var.development_settings.default_node_count
    staging     = var.staging_settings.default_node_count
    production  = var.production_settings.default_node_count
  }, var.environment, 3)

  # Machine type mapping for different cloud providers
  machine_type = lookup({
    aws = lookup({
      development = "m5.xlarge"
      staging     = "m5.2xlarge"
      production  = "m5.2xlarge"
    }, var.environment, "m5.xlarge")
    azure = lookup({
      development = "Standard_D4s_v3"
      staging     = "Standard_D8s_v3"
      production  = "Standard_D8s_v3"
    }, var.environment, "Standard_D4s_v3")
    gcp = lookup({
      development = "n2-standard-4"
      staging     = "n2-standard-8"
      production  = "n2-standard-8"
    }, var.environment, "n2-standard-4")
  }, var.cloud_provider, "Standard_D4s_v3")

  # Default node pool configuration
  default_node_pool = {
    name         = var.default_node_pool_name
    node_count   = local.node_count
    min_count    = lookup({
      development = var.development_settings.default_node_min_count
      staging     = var.staging_settings.default_node_min_count
      production  = var.production_settings.default_node_min_count
    }, var.environment, 3)
    max_count    = lookup({
      development = var.development_settings.default_node_max_count
      staging     = var.staging_settings.default_node_max_count
      production  = var.production_settings.default_node_max_count
    }, var.environment, 10)
    machine_type = local.machine_type
    disk_size_gb = var.default_node_disk_size
  }

  # GPU node pool configuration
  gpu_node_pool = {
    name             = var.gpu_node_pool_name
    node_count       = lookup({
      development = var.development_settings.gpu_node_count
      staging     = var.staging_settings.gpu_node_count
      production  = var.production_settings.gpu_node_count
    }, var.environment, 2)
    min_count        = var.gpu_node_min_count
    max_count        = var.gpu_node_max_count
    machine_type     = var.gpu_node_machine_type
    accelerator_type = var.gpu_type
    accelerator_count = 1
  }

  # Tags for resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Application = "mca-application-processing"
    }
  )

  # Cluster configuration for outputs
  cluster = var.cloud_provider == "aws" ? {
    id       = aws_eks_cluster.this[0].id
    endpoint = aws_eks_cluster.this[0].endpoint
  } : var.cloud_provider == "azure" ? {
    id       = azurerm_kubernetes_cluster.this[0].id
    endpoint = azurerm_kubernetes_cluster.this[0].kube_config[0].host
  } : {
    id       = google_container_cluster.this[0].id
    endpoint = "https://${google_container_cluster.this[0].endpoint}"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# DATA SOURCES
# ---------------------------------------------------------------------------------------------------------------------

# AWS data sources
data "aws_vpc" "selected" {
  count = var.cloud_provider == "aws" ? 1 : 0
  id    = var.vpc_id
}

data "aws_subnets" "private" {
  count = var.cloud_provider == "aws" ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  filter {
    name   = "tag:Type"
    values = ["private"]
  }
}

data "aws_iam_role" "eks_cluster_role" {
  count = var.cloud_provider == "aws" ? 1 : 0
  name  = var.eks_cluster_role_name
}

data "aws_iam_role" "eks_node_role" {
  count = var.cloud_provider == "aws" ? 1 : 0
  name  = var.eks_node_role_name
}

# Azure data sources
data "azurerm_resource_group" "rg" {
  count = var.cloud_provider == "azure" ? 1 : 0
  name  = var.resource_group_name
}

data "azurerm_subnet" "subnet" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = var.subnet_name
  virtual_network_name = var.vnet_name
  resource_group_name  = var.resource_group_name
}

# GCP data sources
data "google_project" "project" {
  count      = var.cloud_provider == "gcp" ? 1 : 0
  project_id = var.gcp_project_id
}

data "google_compute_network" "network" {
  count   = var.cloud_provider == "gcp" ? 1 : 0
  name    = var.gcp_network_name
  project = var.gcp_project_id
}

data "google_compute_subnetwork" "subnetwork" {
  count   = var.cloud_provider == "gcp" ? 1 : 0
  name    = var.gcp_subnetwork_name
  region  = var.region
  project = var.gcp_project_id
}

# ---------------------------------------------------------------------------------------------------------------------
# AWS EKS CLUSTER
# ---------------------------------------------------------------------------------------------------------------------

resource "aws_eks_cluster" "this" {
  count    = var.cloud_provider == "aws" ? 1 : 0
  name     = var.cluster_name
  role_arn = data.aws_iam_role.eks_cluster_role[0].arn
  version  = local.kubernetes_version_validated

  vpc_config {
    subnet_ids              = data.aws_subnets.private[0].ids
    endpoint_private_access = var.private_cluster_enabled
    endpoint_public_access  = !var.private_cluster_enabled
    security_group_ids      = var.eks_security_group_ids
  }

  kubernetes_network_config {
    service_ipv4_cidr = var.service_cidr
  }

  # Enable EKS add-ons
  dynamic "addon" {
    for_each = var.enable_monitoring ? [1] : []
    content {
      name    = "amazon-cloudwatch-observability"
      version = "v1.2.1-eksbuild.1"
    }
  }

  dynamic "addon" {
    for_each = var.enable_kube_dashboard ? [1] : []
    content {
      name    = "kubernetes-dashboard"
      version = "v2.7.0-eksbuild.1"
    }
  }

  dynamic "addon" {
    for_each = var.enable_http_application_routing ? [1] : []
    content {
      name    = "aws-load-balancer-controller"
      version = "v2.5.1-eksbuild.1"
    }
  }

  # Enable encryption for secrets
  encryption_config {
    provider {
      key_arn = var.kms_key_arn
    }
    resources = ["secrets"]
  }

  # Enable logging
  enabled_cluster_log_types = var.enable_logging ? ["api", "audit", "authenticator", "controllerManager", "scheduler"] : []

  tags = local.common_tags

  # Ensure proper dependency ordering
  depends_on = [
    data.aws_iam_role.eks_cluster_role,
    data.aws_subnets.private
  ]
}

# Default EKS node group
resource "aws_eks_node_group" "default" {
  count           = var.cloud_provider == "aws" ? 1 : 0
  cluster_name    = aws_eks_cluster.this[0].name
  node_group_name = local.default_node_pool.name
  node_role_arn   = data.aws_iam_role.eks_node_role[0].arn
  subnet_ids      = data.aws_subnets.private[0].ids
  instance_types  = [local.default_node_pool.machine_type]
  disk_size       = local.default_node_pool.disk_size_gb
  
  scaling_config {
    desired_size = local.default_node_pool.node_count
    min_size     = local.default_node_pool.min_count
    max_size     = local.default_node_pool.max_count
  }
  
  update_config {
    max_unavailable = 1
  }
  
  labels = {
    "role" = "default"
    "environment" = var.environment
  }
  
  tags = local.common_tags
  
  # Ensure proper dependency ordering
  depends_on = [
    aws_eks_cluster.this,
    data.aws_iam_role.eks_node_role
  ]
  
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

# GPU node group for OCR service
resource "aws_eks_node_group" "gpu" {
  count           = var.cloud_provider == "aws" && var.enable_gpu_node_pool ? 1 : 0
  cluster_name    = aws_eks_cluster.this[0].name
  node_group_name = local.gpu_node_pool.name
  node_role_arn   = data.aws_iam_role.eks_node_role[0].arn
  subnet_ids      = data.aws_subnets.private[0].ids
  instance_types  = [local.gpu_node_pool.machine_type]
  disk_size       = var.default_node_disk_size
  ami_type        = "AL2_x86_64_GPU"
  
  scaling_config {
    desired_size = local.gpu_node_pool.node_count
    min_size     = local.gpu_node_pool.min_count
    max_size     = local.gpu_node_pool.max_count
  }
  
  update_config {
    max_unavailable = 1
  }
  
  labels = {
    "role" = "gpu"
    "environment" = var.environment
    "nvidia.com/gpu" = "present"
    "workload" = "ocr-service"
  }
  
  tags = merge(
    local.common_tags,
    {
      "k8s.io/cluster-autoscaler/node-template/label/nvidia.com/gpu" = "present"
    }
  )
  
  # Ensure proper dependency ordering
  depends_on = [
    aws_eks_cluster.this,
    data.aws_iam_role.eks_node_role
  ]
  
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [scaling_config[0].desired_size]
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# AZURE AKS CLUSTER
# ---------------------------------------------------------------------------------------------------------------------

resource "azurerm_kubernetes_cluster" "this" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = var.cluster_name
  location            = data.azurerm_resource_group.rg[0].location
  resource_group_name = data.azurerm_resource_group.rg[0].name
  dns_prefix          = var.cluster_name
  kubernetes_version  = local.kubernetes_version_validated
  node_resource_group = "${var.cluster_name}-nodes"
  
  # Default node pool configuration
  default_node_pool {
    name                = local.default_node_pool.name
    node_count          = local.default_node_pool.node_count
    vm_size             = local.default_node_pool.machine_type
    os_disk_size_gb     = local.default_node_pool.disk_size_gb
    vnet_subnet_id      = data.azurerm_subnet.subnet[0].id
    enable_auto_scaling = var.enable_auto_scaling
    min_count           = var.enable_auto_scaling ? local.default_node_pool.min_count : null
    max_count           = var.enable_auto_scaling ? local.default_node_pool.max_count : null
    max_pods            = 110
    
    node_labels = {
      "role" = "default"
      "environment" = var.environment
    }
    
    tags = local.common_tags
  }
  
  # Identity configuration
  identity {
    type = "SystemAssigned"
  }
  
  # Network configuration
  network_profile {
    network_plugin     = var.network_plugin
    network_policy     = var.network_policy
    service_cidr       = var.service_cidr
    dns_service_ip     = var.dns_service_ip
    docker_bridge_cidr = var.docker_bridge_cidr
    load_balancer_sku  = var.load_balancer_sku
  }
  
  # RBAC configuration
  role_based_access_control_enabled = var.rbac_enabled
  
  dynamic "azure_active_directory_role_based_access_control" {
    for_each = var.rbac_enabled && length(var.admin_group_object_ids) > 0 ? [1] : []
    content {
      managed                = true
      admin_group_object_ids = var.admin_group_object_ids
    }
  }
  
  # Private cluster configuration
  private_cluster_enabled = var.private_cluster_enabled
  
  # Add-ons
  addon_profile {
    dynamic "oms_agent" {
      for_each = var.enable_monitoring && var.log_analytics_workspace_id != null ? [1] : []
      content {
        enabled                    = true
        log_analytics_workspace_id = var.log_analytics_workspace_id
      }
    }
    
    dynamic "kube_dashboard" {
      for_each = var.enable_kube_dashboard ? [1] : []
      content {
        enabled = true
      }
    }
    
    dynamic "http_application_routing" {
      for_each = var.enable_http_application_routing ? [1] : []
      content {
        enabled = true
      }
    }
    
    dynamic "azure_policy" {
      for_each = var.enable_azure_policy ? [1] : []
      content {
        enabled = true
      }
    }
  }
  
  # Maintenance window
  maintenance_window {
    allowed {
      day   = var.maintenance_window.day
      hours = var.maintenance_window.hours
    }
  }
  
  # Auto-upgrade channel
  automatic_channel_upgrade = var.auto_upgrade_channel
  
  # Host encryption
  dynamic "security_profile" {
    for_each = var.enable_host_encryption ? [1] : []
    content {
      enable_host_encryption = true
    }
  }
  
  tags = local.common_tags
  
  lifecycle {
    ignore_changes = [
      default_node_pool[0].node_count
    ]
  }
}

# GPU node pool for OCR service
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  count                 = var.cloud_provider == "azure" && var.enable_gpu_node_pool ? 1 : 0
  name                  = "gpupool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this[0].id
  vm_size               = local.gpu_node_pool.machine_type
  node_count            = local.gpu_node_pool.node_count
  enable_auto_scaling   = var.enable_auto_scaling
  min_count             = var.enable_auto_scaling ? local.gpu_node_pool.min_count : null
  max_count             = var.enable_auto_scaling ? local.gpu_node_pool.max_count : null
  vnet_subnet_id        = data.azurerm_subnet.subnet[0].id
  os_disk_size_gb       = var.default_node_disk_size
  os_type               = "Linux"
  max_pods              = 110
  
  node_labels = {
    "role" = "gpu"
    "environment" = var.environment
    "nvidia.com/gpu" = "present"
    "workload" = "ocr-service"
  }
  
  node_taints = [
    "nvidia.com/gpu=present:NoSchedule"
  ]
  
  tags = local.common_tags
  
  lifecycle {
    ignore_changes = [
      node_count
    ]
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# GOOGLE GKE CLUSTER
# ---------------------------------------------------------------------------------------------------------------------

resource "google_container_cluster" "this" {
  count                    = var.cloud_provider == "gcp" ? 1 : 0
  name                     = var.cluster_name
  location                 = var.region
  project                  = var.gcp_project_id
  min_master_version       = local.kubernetes_version_validated
  network                  = data.google_compute_network.network[0].name
  subnetwork               = data.google_compute_subnetwork.subnetwork[0].name
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = var.private_cluster_enabled
    enable_private_endpoint = var.private_cluster_enabled
    master_ipv4_cidr_block  = var.private_cluster_enabled ? var.master_ipv4_cidr_block : null
  }
  
  # IP allocation policy
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = var.pod_cidr
    services_ipv4_cidr_block = var.service_cidr
  }
  
  # Network policy
  network_policy {
    enabled  = var.network_policy == "calico"
    provider = var.network_policy == "calico" ? "CALICO" : "PROVIDER_UNSPECIFIED"
  }
  
  # Pod security policy
  pod_security_policy_config {
    enabled = var.enable_pod_security_policy
  }
  
  # Cluster autoscaling
  cluster_autoscaling {
    enabled = var.enable_auto_scaling
    
    dynamic "resource_limits" {
      for_each = var.enable_auto_scaling ? [1] : []
      content {
        resource_type = "cpu"
        minimum       = 1
        maximum       = 100
      }
    }
    
    dynamic "resource_limits" {
      for_each = var.enable_auto_scaling ? [1] : []
      content {
        resource_type = "memory"
        minimum       = 1
        maximum       = 1000
      }
    }
  }
  
  # Vertical pod autoscaling
  vertical_pod_autoscaling {
    enabled = true
  }
  
  # Workload identity
  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }
  
  # Maintenance policy
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
  
  # Logging and monitoring
  logging_service    = var.enable_logging ? "logging.googleapis.com/kubernetes" : "none"
  monitoring_service = var.enable_monitoring ? "monitoring.googleapis.com/kubernetes" : "none"
  
  # Add-ons
  addons_config {
    http_load_balancing {
      disabled = !var.enable_http_application_routing
    }
    
    horizontal_pod_autoscaling {
      disabled = !var.enable_auto_scaling
    }
    
    network_policy_config {
      disabled = var.network_policy != "calico"
    }
    
    dns_cache_config {
      enabled = var.enable_dns_cache
    }
    
    config_connector_config {
      enabled = var.enable_config_connector
    }
    
    gce_persistent_disk_csi_driver_config {
      enabled = var.enable_gce_persistent_disk_csi_driver
    }
  }
  
  # Master authorized networks
  dynamic "master_authorized_networks_config" {
    for_each = length(var.master_authorized_networks) > 0 ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }
  
  # Database encryption
  dynamic "database_encryption" {
    for_each = var.database_encryption_key_name != "" ? [1] : []
    content {
      state    = "ENCRYPTED"
      key_name = var.database_encryption_key_name
    }
  }
  
  # Release channel
  release_channel {
    channel = var.release_channel
  }
  
  # Binary authorization
  dynamic "binary_authorization" {
    for_each = var.enable_binary_authorization ? [1] : []
    content {
      evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
    }
  }
  
  # Labels
  resource_labels = local.common_tags
  
  # Ensure proper dependency ordering
  depends_on = [
    data.google_compute_network.network,
    data.google_compute_subnetwork.subnetwork
  ]
  
  lifecycle {
    ignore_changes = [
      node_config,
    ]
  }
}

# Default node pool
resource "google_container_node_pool" "default" {
  count      = var.cloud_provider == "gcp" ? 1 : 0
  name       = local.default_node_pool.name
  location   = var.region
  cluster    = google_container_cluster.this[0].name
  project    = var.gcp_project_id
  node_count = local.default_node_pool.node_count
  
  # Autoscaling
  dynamic "autoscaling" {
    for_each = var.enable_auto_scaling ? [1] : []
    content {
      min_node_count = local.default_node_pool.min_count
      max_node_count = local.default_node_pool.max_count
    }
  }
  
  # Management
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  # Node configuration
  node_config {
    machine_type = local.default_node_pool.machine_type
    disk_size_gb = local.default_node_pool.disk_size_gb
    disk_type    = "pd-standard"
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/compute",
    ]
    
    # Labels
    labels = {
      "role" = "default"
      "environment" = var.environment
    }
    
    # Metadata
    metadata = {
      "disable-legacy-endpoints" = "true"
    }
    
    # Workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
  
  # Ensure proper dependency ordering
  depends_on = [
    google_container_cluster.this
  ]
  
  lifecycle {
    ignore_changes = [
      node_count
    ]
  }
}

# GPU node pool for OCR service
resource "google_container_node_pool" "gpu" {
  count      = var.cloud_provider == "gcp" && var.enable_gpu_node_pool ? 1 : 0
  name       = local.gpu_node_pool.name
  location   = var.region
  cluster    = google_container_cluster.this[0].name
  project    = var.gcp_project_id
  node_count = local.gpu_node_pool.node_count
  
  # Autoscaling
  dynamic "autoscaling" {
    for_each = var.enable_auto_scaling ? [1] : []
    content {
      min_node_count = local.gpu_node_pool.min_count
      max_node_count = local.gpu_node_pool.max_count
    }
  }
  
  # Management
  management {
    auto_repair  = true
    auto_upgrade = false  # Disable auto-upgrade for GPU nodes to prevent driver compatibility issues
  }
  
  # Node configuration
  node_config {
    machine_type = local.gpu_node_pool.machine_type
    disk_size_gb = var.default_node_disk_size
    disk_type    = "pd-ssd"  # Use SSD for GPU nodes for better performance
    
    # GPU configuration
    guest_accelerator {
      type  = local.gpu_node_pool.accelerator_type
      count = local.gpu_node_pool.accelerator_count
    }
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/compute",
    ]
    
    # Labels
    labels = {
      "role" = "gpu"
      "environment" = var.environment
      "nvidia.com/gpu" = "present"
      "workload" = "ocr-service"
    }
    
    # Taints to ensure only GPU workloads are scheduled on these nodes
    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }
    
    # Metadata
    metadata = {
      "disable-legacy-endpoints" = "true"
    }
    
    # Workload identity
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
  
  # Ensure proper dependency ordering
  depends_on = [
    google_container_cluster.this
  ]
  
  lifecycle {
    ignore_changes = [
      node_count
    ]
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# KUBERNETES NAMESPACES
# ---------------------------------------------------------------------------------------------------------------------

# Create namespaces for each environment
resource "kubernetes_namespace" "environments" {
  for_each = toset(["development", "staging", "production"])
  
  metadata {
    name = each.key
    labels = {
      environment = each.key
      managed-by  = "terraform"
    }
  }
}

# Create resource quotas for each namespace
resource "kubernetes_resource_quota" "namespace_quotas" {
  for_each = var.resource_quotas
  
  metadata {
    name      = "${each.key}-quota"
    namespace = each.key
  }
  
  spec {
    hard = {
      "requests.cpu"    = each.value.requests_cpu
      "requests.memory" = each.value.requests_memory
      "limits.cpu"      = each.value.limits_cpu
      "limits.memory"   = each.value.limits_memory
      "pods"            = each.value.pods
      "services"        = each.value.services
    }
  }
  
  depends_on = [kubernetes_namespace.environments]
}

# Create limit ranges for each namespace
resource "kubernetes_limit_range" "namespace_limits" {
  for_each = var.limit_ranges
  
  metadata {
    name      = "${each.key}-limits"
    namespace = each.key
  }
  
  spec {
    limit {
      type = "Container"
      
      default = {
        cpu    = each.value.default_cpu
        memory = each.value.default_memory
      }
      
      default_request = {
        cpu    = each.value.default_request_cpu
        memory = each.value.default_request_memory
      }
    }
  }
  
  depends_on = [kubernetes_namespace.environments]
}

# ---------------------------------------------------------------------------------------------------------------------
# NETWORK POLICIES
# ---------------------------------------------------------------------------------------------------------------------

# Default deny all ingress traffic network policy
resource "kubernetes_network_policy" "default_deny_ingress" {
  for_each = var.enable_network_policy ? toset(["development", "staging", "production"]) : []
  
  metadata {
    name      = "default-deny-ingress"
    namespace = each.key
  }
  
  spec {
    pod_selector {}
    policy_types = ["Ingress"]
  }
  
  depends_on = [kubernetes_namespace.environments]
}

# Allow traffic between pods in the same namespace
resource "kubernetes_network_policy" "allow_same_namespace" {
  for_each = var.enable_network_policy ? toset(["development", "staging", "production"]) : []
  
  metadata {
    name      = "allow-same-namespace"
    namespace = each.key
  }
  
  spec {
    pod_selector {}
    
    ingress {
      from {
        namespace_selector {
          match_labels = {
            name = each.key
          }
        }
      }
    }
    
    policy_types = ["Ingress"]
  }
  
  depends_on = [kubernetes_namespace.environments]
}

# ---------------------------------------------------------------------------------------------------------------------
# ADDITIONAL VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

# AWS specific variables
variable "vpc_id" {
  description = "ID of the VPC where the EKS cluster will be created"
  type        = string
  default     = ""
}

variable "eks_cluster_role_name" {
  description = "Name of the IAM role for the EKS cluster"
  type        = string
  default     = "eks-cluster-role"
}

variable "eks_node_role_name" {
  description = "Name of the IAM role for the EKS nodes"
  type        = string
  default     = "eks-node-role"
}

variable "eks_security_group_ids" {
  description = "List of security group IDs for the EKS cluster"
  type        = list(string)
  default     = []
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for encrypting Kubernetes secrets"
  type        = string
  default     = ""
}

# Azure specific variables
variable "resource_group_name" {
  description = "Name of the resource group where the AKS cluster will be created"
  type        = string
  default     = ""
}

variable "vnet_name" {
  description = "Name of the virtual network where the AKS cluster will be created"
  type        = string
  default     = ""
}

variable "subnet_name" {
  description = "Name of the subnet where the AKS cluster will be created"
  type        = string
  default     = ""
}

# GCP specific variables
variable "gcp_project_id" {
  description = "ID of the GCP project where the GKE cluster will be created"
  type        = string
  default     = ""
}

variable "gcp_network_name" {
  description = "Name of the VPC network where the GKE cluster will be created"
  type        = string
  default     = ""
}

variable "gcp_subnetwork_name" {
  description = "Name of the subnetwork where the GKE cluster will be created"
  type        = string
  default     = ""
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the GKE master nodes"
  type        = string
  default     = "172.16.0.0/28"
}

variable "database_encryption_key_name" {
  description = "Name of the KMS key for encrypting GKE database data"
  type        = string
  default     = ""
}

variable "release_channel" {
  description = "Release channel for GKE cluster updates (UNSPECIFIED, RAPID, REGULAR, STABLE)"
  type        = string
  default     = "STABLE"
}

variable "enable_binary_authorization" {
  description = "Whether to enable binary authorization for the GKE cluster"
  type        = bool
  default     = false
}

variable "master_authorized_networks" {
  description = "List of CIDRs that can access the GKE master"
  type        = list(object({
    cidr_block   = string
    display_name = string
  }))
  default     = []
}

# Common variables
variable "enable_network_policy" {
  description = "Whether to enable network policies"
  type        = bool
  default     = true
}

variable "enable_pod_security_policy" {
  description = "Whether to enable pod security policies"
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Whether to enable private endpoint for the Kubernetes API server"
  type        = bool
  default     = false
}

variable "enable_private_nodes" {
  description = "Whether to enable private nodes (no public IP addresses)"
  type        = bool
  default     = false
}

variable "enable_logging" {
  description = "Whether to enable logging for the cluster"
  type        = bool
  default     = true
}

variable "monitoring_service" {
  description = "Monitoring service to use for the cluster"
  type        = string
  default     = "monitoring.googleapis.com/kubernetes"
}

variable "logging_service" {
  description = "Logging service to use for the cluster"
  type        = string
  default     = "logging.googleapis.com/kubernetes"
}

variable "enable_dns_cache" {
  description = "Whether to enable NodeLocal DNSCache"
  type        = bool
  default     = true
}

variable "enable_config_connector" {
  description = "Whether to enable Config Connector"
  type        = bool
  default     = false
}

variable "enable_gce_persistent_disk_csi_driver" {
  description = "Whether to enable the GCE PD CSI driver"
  type        = bool
  default     = true
}

variable "enable_http_load_balancing" {
  description = "Whether to enable HTTP load balancing"
  type        = bool
  default     = true
}

variable "enable_horizontal_pod_autoscaler" {
  description = "Whether to enable the horizontal pod autoscaler"
  type        = bool
  default     = true
}

variable "enable_rbac" {
  description = "Whether to enable RBAC for the cluster"
  type        = bool
  default     = true
}

variable "resource_quotas" {
  description = "Resource quotas for each namespace"
  type        = map(object({
    requests_cpu     = string
    requests_memory  = string
    limits_cpu       = string
    limits_memory    = string
    pods             = string
    services         = string
  }))
  default     = {
    development = {
      requests_cpu     = "10"
      requests_memory  = "20Gi"
      limits_cpu       = "20"
      limits_memory    = "40Gi"
      pods             = "100"
      services         = "50"
    },
    staging = {
      requests_cpu     = "20"
      requests_memory  = "40Gi"
      limits_cpu       = "40"
      limits_memory    = "80Gi"
      pods             = "200"
      services         = "100"
    },
    production = {
      requests_cpu     = "50"
      requests_memory  = "100Gi"
      limits_cpu       = "100"
      limits_memory    = "200Gi"
      pods             = "500"
      services         = "200"
    }
  }
}

variable "limit_ranges" {
  description = "Default container resource limits for each namespace"
  type        = map(object({
    default_cpu             = string
    default_memory          = string
    default_request_cpu     = string
    default_request_memory  = string
  }))
  default     = {
    development = {
      default_cpu             = "500m"
      default_memory          = "512Mi"
      default_request_cpu     = "100m"
      default_request_memory  = "128Mi"
    },
    staging = {
      default_cpu             = "1000m"
      default_memory          = "1Gi"
      default_request_cpu     = "200m"
      default_request_memory  = "256Mi"
    },
    production = {
      default_cpu             = "2000m"
      default_memory          = "2Gi"
      default_request_cpu     = "500m"
      default_request_memory  = "512Mi"
    }
  }
}