/**
 * Kubernetes Module Outputs
 *
 * This file exports essential output values from the Kubernetes module that are needed by other
 * infrastructure components and application deployments. It provides cluster endpoints, authentication
 * data, and node pool information that downstream modules and services require for connectivity and
 * deployment.
 *
 * The outputs are designed to be provider-agnostic, working across AWS EKS, Azure AKS, and GCP GKE
 * while providing a consistent interface for other modules to consume.
 */

# ---------------------------------------------------------------------------------------------------------------------
# DATA SOURCES FOR AUTHENTICATION
# ---------------------------------------------------------------------------------------------------------------------

# AWS EKS cluster authentication data source
data "aws_eks_cluster_auth" "this" {
  count = var.cloud_provider == "aws" ? 1 : 0
  name  = aws_eks_cluster.this[0].name
}

# GCP client configuration data source
data "google_client_config" "current" {
  count = var.cloud_provider == "gcp" ? 1 : 0
}

# ---------------------------------------------------------------------------------------------------------------------
# CLUSTER INFORMATION OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "cluster_id" {
  description = "The ID of the Kubernetes cluster"
  value       = local.cluster.id
}

output "cluster_name" {
  description = "The name of the Kubernetes cluster"
  value       = var.cluster_name
}

output "cluster_endpoint" {
  description = "The endpoint for the Kubernetes API server"
  value       = local.cluster.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "The certificate authority data for the Kubernetes cluster"
  value       = var.cloud_provider == "aws" ? base64decode(aws_eks_cluster.this[0].certificate_authority[0].data) : var.cloud_provider == "azure" ? base64decode(azurerm_kubernetes_cluster.this[0].kube_config[0].cluster_ca_certificate) : base64decode(google_container_cluster.this[0].master_auth[0].cluster_ca_certificate)
  sensitive   = true
}

output "cluster_version" {
  description = "The Kubernetes version running on the cluster"
  value       = local.kubernetes_version_validated
}

output "cloud_provider" {
  description = "The cloud provider where the Kubernetes cluster is running"
  value       = var.cloud_provider
}

output "region" {
  description = "The region where the Kubernetes cluster is deployed"
  value       = var.region
}

output "additional_regions" {
  description = "Additional regions for multi-region cluster configuration"
  value       = var.additional_regions
}

# ---------------------------------------------------------------------------------------------------------------------
# NODE POOL INFORMATION OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "default_node_pool_name" {
  description = "The name of the default node pool"
  value       = local.default_node_pool.name
}

output "default_node_pool_id" {
  description = "The ID of the default node pool"
  value       = var.cloud_provider == "aws" ? join("", aws_eks_node_group.default.*.id) : var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.this[0].default_node_pool[0].id : join("", google_container_node_pool.default.*.id)
}

output "default_node_pool_machine_type" {
  description = "The machine type of the default node pool"
  value       = local.default_node_pool.machine_type
}

output "default_node_pool_node_count" {
  description = "The number of nodes in the default node pool"
  value       = local.default_node_pool.node_count
}

output "gpu_node_pool_enabled" {
  description = "Whether the GPU node pool is enabled"
  value       = var.enable_gpu_node_pool
}

output "gpu_node_pool_name" {
  description = "The name of the GPU node pool"
  value       = var.enable_gpu_node_pool ? local.gpu_node_pool.name : null
}

output "gpu_node_pool_id" {
  description = "The ID of the GPU node pool"
  value       = var.enable_gpu_node_pool ? (var.cloud_provider == "aws" ? join("", aws_eks_node_group.gpu.*.id) : var.cloud_provider == "azure" ? join("", azurerm_kubernetes_cluster_node_pool.gpu.*.id) : join("", google_container_node_pool.gpu.*.id)) : null
}

output "gpu_node_pool_machine_type" {
  description = "The machine type of the GPU node pool"
  value       = var.enable_gpu_node_pool ? local.gpu_node_pool.machine_type : null
}

output "gpu_node_pool_accelerator_type" {
  description = "The GPU accelerator type used in the GPU node pool"
  value       = var.enable_gpu_node_pool ? local.gpu_node_pool.accelerator_type : null
}

output "gpu_node_pool_accelerator_count" {
  description = "The number of GPUs per node in the GPU node pool"
  value       = var.enable_gpu_node_pool ? local.gpu_node_pool.accelerator_count : null
}

# ---------------------------------------------------------------------------------------------------------------------
# AUTHENTICATION OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "kubeconfig" {
  description = "Kubernetes configuration for connecting to the cluster"
  value       = var.cloud_provider == "aws" ? {
    host                   = aws_eks_cluster.this[0].endpoint
    cluster_ca_certificate = base64decode(aws_eks_cluster.this[0].certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.this[0].token
  } : var.cloud_provider == "azure" ? {
    host                   = azurerm_kubernetes_cluster.this[0].kube_config[0].host
    cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.this[0].kube_config[0].cluster_ca_certificate)
    client_certificate     = base64decode(azurerm_kubernetes_cluster.this[0].kube_config[0].client_certificate)
    client_key             = base64decode(azurerm_kubernetes_cluster.this[0].kube_config[0].client_key)
  } : {
    host                   = "https://${google_container_cluster.this[0].endpoint}"
    cluster_ca_certificate = base64decode(google_container_cluster.this[0].master_auth[0].cluster_ca_certificate)
    token                  = data.google_client_config.current[0].access_token
  }
  sensitive = true
}

output "kubeconfig_raw" {
  description = "Raw kubeconfig file content for connecting to the cluster"
  value       = var.cloud_provider == "aws" ? templatefile("${path.module}/templates/kubeconfig-aws.tpl", {
    cluster_name           = var.cluster_name
    cluster_endpoint       = aws_eks_cluster.this[0].endpoint
    cluster_ca_certificate = aws_eks_cluster.this[0].certificate_authority[0].data
    region                 = var.region
  }) : var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.this[0].kube_config_raw : templatefile("${path.module}/templates/kubeconfig-gcp.tpl", {
    cluster_name           = var.cluster_name
    cluster_endpoint       = google_container_cluster.this[0].endpoint
    cluster_ca_certificate = google_container_cluster.this[0].master_auth[0].cluster_ca_certificate
    project_id             = data.google_project.project[0].project_id
    location               = var.region
  })
  sensitive = true
}

# ---------------------------------------------------------------------------------------------------------------------
# SERVICE ACCOUNT OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "service_accounts" {
  description = "Service accounts created for each microservice"
  value       = {
    email_service        = { for k, v in kubernetes_service_account.email_service : k => v.metadata[0].name }
    document_service     = { for k, v in kubernetes_service_account.document_service : k => v.metadata[0].name }
    ocr_service          = { for k, v in kubernetes_service_account.ocr_service : k => v.metadata[0].name }
    data_service         = { for k, v in kubernetes_service_account.data_service : k => v.metadata[0].name }
    notification_service = { for k, v in kubernetes_service_account.notification_service : k => v.metadata[0].name }
    api_gateway          = { for k, v in kubernetes_service_account.api_gateway : k => v.metadata[0].name }
    cicd                 = { for k, v in kubernetes_service_account.cicd : k => v.metadata[0].name }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# NAMESPACE OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "namespaces" {
  description = "List of namespaces created for the environments"
  value       = ["development", "staging", "production"]
}

output "resource_quotas" {
  description = "Resource quotas configured for each namespace"
  value       = var.resource_quotas
}

output "limit_ranges" {
  description = "Default container resource limits for each namespace"
  value       = var.limit_ranges
}

# ---------------------------------------------------------------------------------------------------------------------
# NETWORKING OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "pod_cidr" {
  description = "CIDR block for pod IP addresses"
  value       = var.pod_cidr
}

output "service_cidr" {
  description = "CIDR block for service IP addresses"
  value       = var.service_cidr
}

output "network_policy_enabled" {
  description = "Whether network policies are enabled"
  value       = var.enable_network_policy
}

# ---------------------------------------------------------------------------------------------------------------------
# MONITORING AND LOGGING OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "monitoring_enabled" {
  description = "Whether monitoring is enabled for the cluster"
  value       = var.enable_monitoring
}

output "logging_enabled" {
  description = "Whether logging is enabled for the cluster"
  value       = var.enable_logging
}

output "monitoring_service" {
  description = "Monitoring service used for the cluster"
  value       = var.monitoring_service
}

output "logging_service" {
  description = "Logging service used for the cluster"
  value       = var.logging_service
}

# ---------------------------------------------------------------------------------------------------------------------
# SECURITY OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "rbac_enabled" {
  description = "Whether RBAC is enabled for the cluster"
  value       = var.enable_rbac
}

output "pod_security_policy_enabled" {
  description = "Whether Pod Security Policy is enabled for the cluster"
  value       = var.enable_pod_security_policy
}

output "private_endpoint_enabled" {
  description = "Whether private endpoint is enabled for the Kubernetes API server"
  value       = var.enable_private_endpoint
}

output "private_nodes_enabled" {
  description = "Whether private nodes are enabled (no public IP addresses)"
  value       = var.enable_private_nodes
}

# ---------------------------------------------------------------------------------------------------------------------
# ADDON OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "addons_enabled" {
  description = "Map of enabled addons for the cluster"
  value       = {
    monitoring                = var.enable_monitoring
    logging                   = var.enable_logging
    http_load_balancing       = var.enable_http_load_balancing
    horizontal_pod_autoscaler = var.enable_horizontal_pod_autoscaler
    network_policy            = var.enable_network_policy
    pod_security_policy       = var.enable_pod_security_policy
    dns_cache                 = var.enable_dns_cache
    config_connector          = var.enable_config_connector
    gce_persistent_disk_csi   = var.enable_gce_persistent_disk_csi_driver
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# ENVIRONMENT OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "environment" {
  description = "Deployment environment (development, staging, production)"
  value       = var.environment
}

output "environment_specific_config" {
  description = "Environment-specific configuration values"
  value       = {
    node_count    = local.node_count
    machine_type  = local.machine_type
  }
}