/**
 * Kubernetes Module Outputs
 *
 * This file exports essential output values from the Kubernetes module that are needed by
 * other infrastructure components and application deployments. It provides cluster endpoints,
 * authentication data, and node pool information that downstream modules and services require
 * for connectivity and deployment.
 */

# Cluster Endpoint Outputs
# These outputs provide the necessary information to connect to the Kubernetes cluster

output "cluster_endpoint" {
  description = "The endpoint for the Kubernetes control plane"
  value       = var.cloud_provider == "aws" ? aws_eks_cluster.cluster[0].endpoint : (
                var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].host : (
                var.cloud_provider == "google" ? google_container_cluster.cluster[0].endpoint : null))
  sensitive   = false
}

output "cluster_name" {
  description = "The name of the Kubernetes cluster"
  value       = var.cluster_name
  sensitive   = false
}

# Authentication Outputs
# These outputs provide the necessary authentication information for secure cluster access

output "cluster_ca_certificate" {
  description = "The certificate authority data for the Kubernetes cluster"
  value       = var.cloud_provider == "aws" ? aws_eks_cluster.cluster[0].certificate_authority[0].data : (
                var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].cluster_ca_certificate : (
                var.cloud_provider == "google" ? google_container_cluster.cluster[0].master_auth[0].cluster_ca_certificate : null))
  sensitive   = true
}

output "client_certificate" {
  description = "The client certificate for authenticating to the Kubernetes cluster (Azure and GCP only)"
  value       = var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].client_certificate : (
                var.cloud_provider == "google" ? google_container_cluster.cluster[0].master_auth[0].client_certificate : null)
  sensitive   = true
}

output "client_key" {
  description = "The client key for authenticating to the Kubernetes cluster (Azure and GCP only)"
  value       = var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].client_key : (
                var.cloud_provider == "google" ? google_container_cluster.cluster[0].master_auth[0].client_key : null)
  sensitive   = true
}

output "token" {
  description = "The token for authenticating to the Kubernetes cluster (AWS only)"
  value       = var.cloud_provider == "aws" ? data.aws_eks_cluster_auth.cluster[0].token : null
  sensitive   = true
}

# Kubectl Configuration Outputs
# These outputs provide ready-to-use kubectl configuration for CI/CD systems

output "kubeconfig" {
  description = "Kubernetes configuration file content for accessing the cluster"
  value       = templatefile("${path.module}/templates/kubeconfig.tpl", {
    cluster_name       = var.cluster_name
    cluster_endpoint   = var.cloud_provider == "aws" ? aws_eks_cluster.cluster[0].endpoint : (
                         var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].host : (
                         var.cloud_provider == "google" ? google_container_cluster.cluster[0].endpoint : null))
    cluster_ca_cert    = var.cloud_provider == "aws" ? aws_eks_cluster.cluster[0].certificate_authority[0].data : (
                         var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].cluster_ca_certificate : (
                         var.cloud_provider == "google" ? google_container_cluster.cluster[0].master_auth[0].cluster_ca_certificate : null))
    client_cert        = var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].client_certificate : (
                         var.cloud_provider == "google" ? google_container_cluster.cluster[0].master_auth[0].client_certificate : "")
    client_key         = var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].kube_config[0].client_key : (
                         var.cloud_provider == "google" ? google_container_cluster.cluster[0].master_auth[0].client_key : "")
    token              = var.cloud_provider == "aws" ? data.aws_eks_cluster_auth.cluster[0].token : ""
    auth_provider      = var.cloud_provider
  })
  sensitive   = true
}

# Node Pool Outputs
# These outputs provide information about the node pools in the cluster

output "node_pools_ids" {
  description = "The IDs of the node pools in the Kubernetes cluster"
  value = {
    standard = var.cloud_provider == "aws" ? (length(aws_eks_node_group.standard) > 0 ? aws_eks_node_group.standard[0].id : null) : (
              var.cloud_provider == "azure" ? (length(azurerm_kubernetes_cluster_node_pool.standard) > 0 ? azurerm_kubernetes_cluster_node_pool.standard[0].id : null) : (
              var.cloud_provider == "google" ? (length(google_container_node_pool.standard) > 0 ? google_container_node_pool.standard[0].id : null) : null))
    service = var.cloud_provider == "aws" ? (length(aws_eks_node_group.service) > 0 ? aws_eks_node_group.service[0].id : null) : (
              var.cloud_provider == "azure" ? (length(azurerm_kubernetes_cluster_node_pool.service) > 0 ? azurerm_kubernetes_cluster_node_pool.service[0].id : null) : (
              var.cloud_provider == "google" ? (length(google_container_node_pool.service) > 0 ? google_container_node_pool.service[0].id : null) : null))
    gpu = var.cloud_provider == "aws" ? (length(aws_eks_node_group.gpu) > 0 ? aws_eks_node_group.gpu[0].id : null) : (
          var.cloud_provider == "azure" ? (length(azurerm_kubernetes_cluster_node_pool.gpu) > 0 ? azurerm_kubernetes_cluster_node_pool.gpu[0].id : null) : (
          var.cloud_provider == "google" ? (length(google_container_node_pool.gpu) > 0 ? google_container_node_pool.gpu[0].id : null) : null))
  }
}

output "node_pools_instance_types" {
  description = "The instance types used by the node pools"
  value = {
    standard = var.node_pools.standard.machine_type
    service  = var.node_pools.service.machine_type
    gpu      = var.node_pools.gpu.machine_type
  }
}

output "gpu_node_pool_details" {
  description = "Details about the GPU-enabled node pool for the OCR service"
  value = {
    name       = var.node_pools.gpu.name
    gpu_type   = var.node_pools.gpu.gpu_type
    gpu_count  = var.node_pools.gpu.gpu_count
    node_count = var.node_pools.gpu.desired_count
    min_nodes  = var.node_pools.gpu.min_count
    max_nodes  = var.node_pools.gpu.max_count
    labels     = var.node_pools.gpu.labels
    taints     = var.node_pools.gpu.taints
  }
}

# Namespace Outputs
# These outputs provide information about the namespaces created for each service

output "service_namespaces" {
  description = "The namespaces created for each microservice"
  value = {
    email_service        = kubernetes_namespace.email_service.metadata[0].name
    document_service     = kubernetes_namespace.document_service.metadata[0].name
    ocr_service          = kubernetes_namespace.ocr_service.metadata[0].name
    data_service         = kubernetes_namespace.data_service.metadata[0].name
    notification_service = kubernetes_namespace.notification_service.metadata[0].name
  }
}

output "namespace_resource_quotas" {
  description = "Resource quotas applied to each namespace"
  value = {
    standard_services = var.default_resource_quotas
    ocr_service       = var.ocr_resource_quotas
  }
}

# Additional Cluster Information
# These outputs provide additional information about the cluster configuration

output "kubernetes_version" {
  description = "The version of Kubernetes running on the cluster"
  value       = var.kubernetes_version
}

output "cluster_security_group_id" {
  description = "The security group ID attached to the cluster (AWS only)"
  value       = var.cloud_provider == "aws" ? aws_eks_cluster.cluster[0].vpc_config[0].cluster_security_group_id : null
}

output "cluster_network_profile" {
  description = "Network configuration of the cluster"
  value = {
    network_plugin     = var.cloud_provider == "azure" ? azurerm_kubernetes_cluster.cluster[0].network_profile[0].network_plugin : "kubenet"
    service_cidr       = var.service_cidr
    pod_cidr           = var.pod_cidr
    dns_service_ip     = var.dns_service_ip
  }
  sensitive = false
}

# Monitoring and Logging Outputs
# These outputs provide information about monitoring and logging configurations

output "monitoring_enabled" {
  description = "Whether monitoring is enabled for the cluster"
  value       = var.enable_monitoring
}

output "logging_enabled" {
  description = "Whether logging is enabled for the cluster"
  value       = var.enable_logging
}

output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics workspace for cluster logging (Azure only)"
  value       = var.cloud_provider == "azure" && var.enable_logging ? azurerm_log_analytics_workspace.workspace[0].id : null
  sensitive   = true
}