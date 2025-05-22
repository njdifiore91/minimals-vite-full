# Variables for the monitoring module
# These variables are used to configure both Prometheus and Datadog monitoring solutions

variable "monitoring_type" {
  description = "Type of monitoring solution to deploy (prometheus or datadog)"
  type        = string
  default     = "prometheus"
  validation {
    condition     = contains(["prometheus", "datadog"], var.monitoring_type)
    error_message = "The monitoring_type must be either 'prometheus' or 'datadog'."
  }
}

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "The environment must be one of: development, staging, production."
  }
}

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "monitoring_namespace" {
  description = "Kubernetes namespace for monitoring resources"
  type        = string
  default     = "monitoring"
}

variable "app_namespace" {
  description = "Kubernetes namespace where application services are deployed"
  type        = string
  default     = "mca"
}

variable "storage_class_name" {
  description = "Storage class name for persistent volumes"
  type        = string
  default     = "standard"
}

# Prometheus Operator variables
variable "prometheus_operator_version" {
  description = "Version of the Prometheus Operator Helm chart"
  type        = string
  default     = "55.5.0" # kube-prometheus-stack chart version
}

# Grafana variables
variable "grafana_admin_password" {
  description = "Admin password for Grafana"
  type        = string
  sensitive   = true
}

variable "grafana_dashboards_configmap" {
  description = "ConfigMap name containing Grafana dashboards"
  type        = string
  default     = "grafana-dashboards"
}

variable "grafana_ingress_enabled" {
  description = "Enable Ingress for Grafana"
  type        = bool
  default     = true
}

variable "grafana_hostname" {
  description = "Hostname for Grafana Ingress"
  type        = string
  default     = "grafana.example.com"
}

variable "ingress_class" {
  description = "Ingress class for Grafana Ingress"
  type        = string
  default     = "nginx"
}

variable "cert_issuer" {
  description = "Certificate issuer for Grafana Ingress TLS"
  type        = string
  default     = "letsencrypt-prod"
}

# PostgreSQL exporter variables
variable "postgres_exporter_version" {
  description = "Version of the PostgreSQL exporter Helm chart"
  type        = string
  default     = "5.0.0"
}

variable "postgres_host" {
  description = "PostgreSQL host address"
  type        = string
}

variable "postgres_port" {
  description = "PostgreSQL port"
  type        = number
  default     = 5432
}

variable "postgres_database" {
  description = "PostgreSQL database name"
  type        = string
  default     = "postgres"
}

variable "postgres_exporter_user" {
  description = "PostgreSQL user for exporter"
  type        = string
  default     = "postgres_exporter"
}

variable "postgres_exporter_password" {
  description = "PostgreSQL password for exporter"
  type        = string
  sensitive   = true
}

variable "postgres_ssl_mode" {
  description = "PostgreSQL SSL mode"
  type        = string
  default     = "disable"
}

# RabbitMQ exporter variables
variable "rabbitmq_exporter_version" {
  description = "Version of the RabbitMQ exporter Helm chart"
  type        = string
  default     = "1.7.0"
}

variable "rabbitmq_url" {
  description = "RabbitMQ URL"
  type        = string
}

variable "rabbitmq_exporter_user" {
  description = "RabbitMQ user for exporter"
  type        = string
  default     = "monitoring"
}

variable "rabbitmq_exporter_password" {
  description = "RabbitMQ password for exporter"
  type        = string
  sensitive   = true
}

# Redis exporter variables
variable "redis_exporter_version" {
  description = "Version of the Redis exporter Helm chart"
  type        = string
  default     = "5.6.0"
}

variable "redis_url" {
  description = "Redis URL including authentication if required (redis://user:password@host:port)"
  type        = string
}

# S3 exporter variables
variable "s3_exporter_image" {
  description = "S3 exporter container image"
  type        = string
  default     = "prometheuscommunity/s3-exporter"
}

variable "s3_exporter_version" {
  description = "S3 exporter container image version"
  type        = string
  default     = "0.6.0"
}

variable "s3_credentials_secret" {
  description = "Kubernetes secret containing S3 credentials"
  type        = string
  default     = "s3-credentials"
}

variable "s3_endpoint" {
  description = "S3 endpoint URL"
  type        = string
}

variable "s3_buckets" {
  description = "List of S3 bucket names to monitor"
  type        = list(string)
  default     = ["mca-documents-production", "mca-documents-staging"]
}