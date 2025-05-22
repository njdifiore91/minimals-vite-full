/**
 * Kubernetes Cluster Module for MCA Application Processing System
 *
 * This module defines the core Kubernetes cluster configuration in a provider-agnostic way,
 * supporting deployment across AWS EKS, Azure AKS, or GCP GKE. It includes settings for
 * networking, monitoring, autoscaling, and security.
 *
 * The module is designed to support the microservices architecture of the MCA Application
 * Processing System, with specific configurations for GPU-enabled nodes required by the
 * OCR service and namespace segregation for service isolation.
 */

# Local variables for common configurations across providers
locals {
  # Common tags to be applied to all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Application = "MCA-Processing-System"
      ManagedBy   = "Terraform"
    }
  )

  # Kubernetes version validation
  kubernetes_version_validated = var.kubernetes_version != "" ? var.kubernetes_version : "1.25.0"

  # Node count based on environment
  node_count = var.environment == "development" ? var.development_node_count : 
               var.environment == "staging" ? var.staging_node_count : 
               var.production_node_count

  # Machine type based on environment
  machine_type = var.environment == "development" ? var.development_machine_type : 
                 var.environment == "staging" ? var.staging_machine_type : 
                 var.production_machine_type

  # Default node pool configurations
  default_node_pool = {
    name                = var.default_node_pool_name
    machine_type        = var.default_node_pool_machine_type != "" ? var.default_node_pool_machine_type : local.machine_type
    node_count          = local.node_count
    min_count           = var.default_node_pool_min_count
    max_count           = var.default_node_pool_max_count
    enable_auto_scaling = var.enable_horizontal_pod_autoscaler
    disk_size_gb        = var.default_node_pool_disk_size_gb
    node_labels         = {}
    node_taints         = []
  }

  # GPU node pool configurations for OCR service
  gpu_node_pool = {
    name                = var.gpu_node_pool_name
    machine_type        = var.gpu_node_pool_machine_type
    node_count          = 0  # Start with 0 and let autoscaling handle it
    min_count           = var.gpu_node_pool_min_count
    max_count           = var.gpu_node_pool_max_count
    enable_auto_scaling = var.enable_horizontal_pod_autoscaler
    disk_size_gb        = var.gpu_node_pool_disk_size_gb
    node_labels         = { "accelerator" = "nvidia" }
    node_taints         = ["nvidia.com/gpu=present:NoSchedule"]
    accelerator_type    = var.gpu_node_pool_accelerator_type
    accelerator_count   = var.gpu_node_pool_accelerator_count
  }

  # Network configuration
  network_config = {
    service_cidr       = var.service_cidr
    pod_cidr           = var.pod_cidr
    docker_bridge_cidr = "172.17.0.1/16"  # Default Docker bridge CIDR
    dns_service_ip     = cidrhost(var.service_cidr, 10)  # Default DNS service IP
  }

  # Addon configurations
  addons = {
    monitoring_enabled          = var.enable_monitoring
    logging_enabled             = var.enable_logging
    http_load_balancing         = var.enable_http_load_balancing
    horizontal_pod_autoscaler   = var.enable_horizontal_pod_autoscaler
    network_policy              = var.enable_network_policy
    pod_security_policy         = var.enable_pod_security_policy
    dns_cache                   = var.enable_dns_cache
    config_connector            = var.enable_config_connector
    gce_persistent_disk_csi     = var.enable_gce_persistent_disk_csi_driver
  }
}

# AWS EKS Cluster
resource "aws_eks_cluster" "this" {
  count = var.cloud_provider == "aws" ? 1 : 0

  name     = var.cluster_name
  role_arn = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:role/${var.cluster_name}-cluster-role"
  version  = local.kubernetes_version_validated

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = var.enable_private_endpoint
    endpoint_public_access  = !var.enable_private_endpoint
    public_access_cidrs     = var.authorized_networks
  }

  kubernetes_network_config {
    service_ipv4_cidr = local.network_config.service_cidr
  }

  # Enable logging
  enabled_cluster_log_types = local.addons.logging_enabled ? ["api", "audit", "authenticator", "controllerManager", "scheduler"] : []

  # Enable encryption for secrets
  encryption_config {
    provider {
      key_arn = "arn:aws:kms:${var.region}:${data.aws_caller_identity.current[0].account_id}:key/${var.cluster_name}-key"
    }
    resources = ["secrets"]
  }

  tags = local.common_tags
}

# AWS data sources
data "aws_caller_identity" "current" {
  count = var.cloud_provider == "aws" ? 1 : 0
}

# Azure AKS Cluster
resource "azurerm_kubernetes_cluster" "this" {
  count = var.cloud_provider == "azure" ? 1 : 0

  name                = var.cluster_name
  location            = var.region
  resource_group_name = "${var.cluster_name}-rg"
  dns_prefix          = var.cluster_name
  kubernetes_version  = local.kubernetes_version_validated

  default_node_pool {
    name                = local.default_node_pool.name
    vm_size             = local.default_node_pool.machine_type
    node_count          = local.default_node_pool.node_count
    min_count           = local.default_node_pool.enable_auto_scaling ? local.default_node_pool.min_count : null
    max_count           = local.default_node_pool.enable_auto_scaling ? local.default_node_pool.max_count : null
    enable_auto_scaling = local.default_node_pool.enable_auto_scaling
    os_disk_size_gb     = local.default_node_pool.disk_size_gb
    node_labels         = local.default_node_pool.node_labels
    vnet_subnet_id      = var.subnet_ids[0]
    availability_zones  = ["1", "2", "3"]
    type                = "VirtualMachineScaleSets"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin     = "azure"
    network_policy     = local.addons.network_policy ? "calico" : null
    service_cidr       = local.network_config.service_cidr
    dns_service_ip     = local.network_config.dns_service_ip
    docker_bridge_cidr = local.network_config.docker_bridge_cidr
    pod_cidr           = local.network_config.pod_cidr
    load_balancer_sku  = "standard"
  }

  # Azure Monitor for containers
  monitor_metrics {
    enabled = local.addons.monitoring_enabled
  }

  # Enable RBAC
  role_based_access_control_enabled = var.enable_rbac
  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  tags = local.common_tags
}

# GCP GKE Cluster
resource "google_container_cluster" "this" {
  count = var.cloud_provider == "gcp" ? 1 : 0

  name     = var.cluster_name
  location = var.region
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  min_master_version = local.kubernetes_version_validated
  
  # Network configuration
  networking_mode = "VPC_NATIVE"
  
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = local.network_config.pod_cidr
    services_ipv4_cidr_block = local.network_config.service_cidr
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = var.enable_private_nodes
    enable_private_endpoint = var.enable_private_endpoint
    master_ipv4_cidr_block  = "172.16.0.0/28"  # Master IP CIDR block
  }

  # Authorized networks for cluster access
  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = length(var.master_authorized_networks_config_cidr_blocks) > 0 ? var.master_authorized_networks_config_cidr_blocks : []
      content {
        cidr_block   = cidr_blocks.value.cidr_block
        display_name = cidr_blocks.value.display_name
      }
    }
  }

  # Network policy configuration
  network_policy {
    enabled  = local.addons.network_policy
    provider = "CALICO"
  }

  # Pod security policy configuration
  pod_security_policy_config {
    enabled = local.addons.pod_security_policy
  }

  # Cluster addons configuration
  addons_config {
    http_load_balancing {
      disabled = !local.addons.http_load_balancing
    }

    horizontal_pod_autoscaling {
      disabled = !local.addons.horizontal_pod_autoscaler
    }

    network_policy_config {
      disabled = !local.addons.network_policy
    }
    
    gcp_filestore_csi_driver_config {
      enabled = local.addons.gce_persistent_disk_csi
    }
    
    dns_cache_config {
      enabled = local.addons.dns_cache
    }
  }

  # Maintenance window configuration
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }

  # Enable workload identity for GCP service account integration
  workload_identity_config {
    workload_pool = "${data.google_project.project[0].project_id}.svc.id.goog"
  }

  # Enable shielded nodes for enhanced security
  node_config {
    shielded_instance_config {
      enable_secure_boot          = var.enable_shielded_nodes
      enable_integrity_monitoring = var.enable_shielded_nodes
    }
  }

  resource_labels = local.common_tags
}

# GCP data sources
data "google_project" "project" {
  count = var.cloud_provider == "gcp" ? 1 : 0
}

# GPU Node Pool for GKE (for OCR service)
resource "google_container_node_pool" "gpu" {
  count = var.cloud_provider == "gcp" && var.enable_gpu_node_pool ? 1 : 0

  name     = local.gpu_node_pool.name
  location = var.region
  cluster  = google_container_cluster.this[0].name

  initial_node_count = local.gpu_node_pool.node_count
  
  autoscaling {
    min_node_count = local.gpu_node_pool.min_count
    max_node_count = local.gpu_node_pool.max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = local.gpu_node_pool.machine_type
    disk_size_gb = local.gpu_node_pool.disk_size_gb
    
    # GPU configuration
    guest_accelerator {
      type  = local.gpu_node_pool.accelerator_type
      count = local.gpu_node_pool.accelerator_count
    }
    
    # GPU requires COS image
    image_type = "COS_CONTAINERD"
    
    # Labels and taints
    labels = local.gpu_node_pool.node_labels
    
    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }
    
    # Metadata
    metadata = {
      disable-legacy-endpoints = "true"
    }
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/trace.append"
    ]
  }
}

# Default Node Pool for GKE
resource "google_container_node_pool" "default" {
  count = var.cloud_provider == "gcp" ? 1 : 0

  name     = local.default_node_pool.name
  location = var.region
  cluster  = google_container_cluster.this[0].name

  initial_node_count = local.default_node_pool.node_count
  
  autoscaling {
    min_node_count = local.default_node_pool.min_count
    max_node_count = local.default_node_pool.max_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    machine_type = local.default_node_pool.machine_type
    disk_size_gb = local.default_node_pool.disk_size_gb
    
    # Labels
    labels = local.default_node_pool.node_labels
    
    # Metadata
    metadata = {
      disable-legacy-endpoints = "true"
    }
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/trace.append"
    ]
  }
}

# Node Group for AWS EKS
resource "aws_eks_node_group" "default" {
  count = var.cloud_provider == "aws" ? 1 : 0

  cluster_name    = aws_eks_cluster.this[0].name
  node_group_name = local.default_node_pool.name
  node_role_arn   = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:role/${var.cluster_name}-node-role"
  subnet_ids      = var.subnet_ids

  scaling_config {
    desired_size = local.default_node_pool.node_count
    min_size     = local.default_node_pool.min_count
    max_size     = local.default_node_pool.max_count
  }

  instance_types = [local.default_node_pool.machine_type]
  disk_size      = local.default_node_pool.disk_size_gb

  labels = local.default_node_pool.node_labels

  tags = local.common_tags
}

# GPU Node Group for AWS EKS (for OCR service)
resource "aws_eks_node_group" "gpu" {
  count = var.cloud_provider == "aws" && var.enable_gpu_node_pool ? 1 : 0

  cluster_name    = aws_eks_cluster.this[0].name
  node_group_name = local.gpu_node_pool.name
  node_role_arn   = "arn:aws:iam::${data.aws_caller_identity.current[0].account_id}:role/${var.cluster_name}-node-role"
  subnet_ids      = var.subnet_ids

  scaling_config {
    desired_size = local.gpu_node_pool.node_count
    min_size     = local.gpu_node_pool.min_count
    max_size     = local.gpu_node_pool.max_count
  }

  # GPU instance types
  instance_types = ["g4dn.xlarge"]
  disk_size      = local.gpu_node_pool.disk_size_gb

  labels = local.gpu_node_pool.node_labels

  # GPU taints
  taint {
    key    = "nvidia.com/gpu"
    value  = "present"
    effect = "NO_SCHEDULE"
  }

  tags = local.common_tags
}

# GPU Node Pool for Azure AKS (for OCR service)
resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  count = var.cloud_provider == "azure" && var.enable_gpu_node_pool ? 1 : 0

  name                  = local.gpu_node_pool.name
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this[0].id
  vm_size               = "Standard_NC6s_v3"  # GPU-enabled VM size
  node_count            = local.gpu_node_pool.node_count
  enable_auto_scaling   = local.gpu_node_pool.enable_auto_scaling
  min_count             = local.gpu_node_pool.min_count
  max_count             = local.gpu_node_pool.max_count
  os_disk_size_gb       = local.gpu_node_pool.disk_size_gb
  node_labels           = local.gpu_node_pool.node_labels
  node_taints           = ["nvidia.com/gpu=present:NoSchedule"]
  availability_zones    = ["1", "2", "3"]

  tags = local.common_tags
}

# Provider-agnostic Kubernetes cluster output
locals {
  # Determine which cluster to use based on the provider
  cluster = {
    id       = var.cloud_provider == "aws" ? join("", aws_eks_cluster.this.*.id) : var.cloud_provider == "azure" ? join("", azurerm_kubernetes_cluster.this.*.id) : join("", google_container_cluster.this.*.id)
    endpoint = var.cloud_provider == "aws" ? join("", aws_eks_cluster.this.*.endpoint) : var.cloud_provider == "azure" ? join("", azurerm_kubernetes_cluster.this.*.kube_config.0.host) : join("", google_container_cluster.this.*.endpoint)
    name     = var.cluster_name
    provider = var.cloud_provider
  }
}