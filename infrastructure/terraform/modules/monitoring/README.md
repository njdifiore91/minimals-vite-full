# Monitoring Module

## Overview

This Terraform module deploys a comprehensive monitoring solution for the MCA Application Processing System. It supports two monitoring options:

1. **Prometheus/Grafana Stack** - A self-hosted monitoring solution deployed on Kubernetes
2. **Datadog** - A managed monitoring service (configured in datadog.tf)

The module provisions all necessary components for collecting metrics from the MCA application services and infrastructure components, visualizing them through dashboards, and setting up alerts for critical conditions.

## Features

### Prometheus/Grafana Stack

- Deploys Prometheus Operator using the kube-prometheus-stack Helm chart
- Configures Grafana with pre-built dashboards for MCA application monitoring
- Sets up service monitors for all MCA microservices
- Deploys exporters for infrastructure components:
  - PostgreSQL exporter for database metrics
  - RabbitMQ exporter for message queue metrics
  - Redis exporter for cache metrics
  - S3 exporter for object storage metrics
- Configures node exporter for host-level metrics
- Sets up persistent storage for metrics data
- Configures AlertManager for alert notifications

### Common Features

- Environment-specific configurations (development, staging, production)
- Resource allocation based on environment
- Retention policies based on environment
- Integration with Kubernetes services

## Usage

```hcl
module "monitoring" {
  source = "../modules/monitoring"

  # Common variables
  monitoring_type    = "prometheus"  # or "datadog"
  environment        = "production"
  cluster_name       = "mca-cluster"
  monitoring_namespace = "monitoring"
  app_namespace      = "mca"
  
  # Prometheus-specific variables
  prometheus_operator_version = "55.5.0"
  grafana_admin_password     = var.grafana_admin_password
  grafana_ingress_enabled    = true
  grafana_hostname           = "grafana.example.com"
  
  # Database monitoring
  postgres_host              = module.database.postgres_host
  postgres_port              = module.database.postgres_port
  postgres_exporter_user     = var.postgres_exporter_user
  postgres_exporter_password = var.postgres_exporter_password
  
  # Message queue monitoring
  rabbitmq_url               = module.messaging.rabbitmq_url
  rabbitmq_exporter_user     = var.rabbitmq_exporter_user
  rabbitmq_exporter_password = var.rabbitmq_exporter_password
  
  # Cache monitoring
  redis_url                  = module.cache.redis_url
  
  # Storage monitoring
  s3_endpoint                = module.storage.s3_endpoint
  s3_buckets                 = ["mca-documents-production"]
  s3_credentials_secret      = "s3-credentials"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| monitoring_type | Type of monitoring solution to deploy (prometheus or datadog) | `string` | `"prometheus"` | no |
| environment | Deployment environment (development, staging, production) | `string` | n/a | yes |
| cluster_name | Name of the Kubernetes cluster | `string` | n/a | yes |
| monitoring_namespace | Kubernetes namespace for monitoring resources | `string` | `"monitoring"` | no |
| app_namespace | Kubernetes namespace where application services are deployed | `string` | `"mca"` | no |
| storage_class_name | Storage class name for persistent volumes | `string` | `"standard"` | no |
| prometheus_operator_version | Version of the Prometheus Operator Helm chart | `string` | `"55.5.0"` | no |
| grafana_admin_password | Admin password for Grafana | `string` | n/a | yes |
| grafana_dashboards_configmap | ConfigMap name containing Grafana dashboards | `string` | `"grafana-dashboards"` | no |
| grafana_ingress_enabled | Enable Ingress for Grafana | `bool` | `true` | no |
| grafana_hostname | Hostname for Grafana Ingress | `string` | `"grafana.example.com"` | no |
| ingress_class | Ingress class for Grafana Ingress | `string` | `"nginx"` | no |
| cert_issuer | Certificate issuer for Grafana Ingress TLS | `string` | `"letsencrypt-prod"` | no |
| postgres_exporter_version | Version of the PostgreSQL exporter Helm chart | `string` | `"5.0.0"` | no |
| postgres_host | PostgreSQL host address | `string` | n/a | yes |
| postgres_port | PostgreSQL port | `number` | `5432` | no |
| postgres_database | PostgreSQL database name | `string` | `"postgres"` | no |
| postgres_exporter_user | PostgreSQL user for exporter | `string` | `"postgres_exporter"` | no |
| postgres_exporter_password | PostgreSQL password for exporter | `string` | n/a | yes |
| postgres_ssl_mode | PostgreSQL SSL mode | `string` | `"disable"` | no |
| rabbitmq_exporter_version | Version of the RabbitMQ exporter Helm chart | `string` | `"1.7.0"` | no |
| rabbitmq_url | RabbitMQ URL | `string` | n/a | yes |
| rabbitmq_exporter_user | RabbitMQ user for exporter | `string` | `"monitoring"` | no |
| rabbitmq_exporter_password | RabbitMQ password for exporter | `string` | n/a | yes |
| redis_exporter_version | Version of the Redis exporter Helm chart | `string` | `"5.6.0"` | no |
| redis_url | Redis URL including authentication if required | `string` | n/a | yes |
| s3_exporter_image | S3 exporter container image | `string` | `"prometheuscommunity/s3-exporter"` | no |
| s3_exporter_version | S3 exporter container image version | `string` | `"0.6.0"` | no |
| s3_credentials_secret | Kubernetes secret containing S3 credentials | `string` | `"s3-credentials"` | no |
| s3_endpoint | S3 endpoint URL | `string` | n/a | yes |
| s3_buckets | List of S3 bucket names to monitor | `list(string)` | `["mca-documents-production", "mca-documents-staging"]` | no |

## Outputs

| Name | Description |
|------|-------------|
| prometheus_server_endpoint | Prometheus server endpoint URL |
| prometheus_alertmanager_endpoint | Prometheus AlertManager endpoint URL |
| grafana_endpoint | Grafana endpoint URL |
| grafana_external_url | Grafana external URL (if Ingress is enabled) |
| prometheus_operator_crds | List of CRDs created by Prometheus Operator |
| monitoring_namespace | Kubernetes namespace where monitoring resources are deployed |
| monitoring_type | Type of monitoring solution deployed |
| monitoring_enabled | Whether monitoring is enabled |
| monitoring_labels | Common labels used for monitoring resources |

## Integration with MCA Services

The monitoring module is designed to integrate with all MCA application services. Each service should expose a metrics endpoint that can be scraped by Prometheus. The module configures service monitors for the following services:

- Email Service
- Document Service
- OCR Service
- Data Service
- Notification Service
- API Gateway

## Metrics Collection

The module collects metrics from various sources:

1. **Infrastructure Metrics**:
   - Host-level metrics (CPU, memory, disk, network)
   - Kubernetes metrics (pods, nodes, deployments)

2. **Database Metrics**:
   - Connection pool usage
   - Query performance
   - Replication lag
   - Transaction rates

3. **Message Queue Metrics**:
   - Queue depth
   - Message rates
   - Consumer lag
   - Connection status

4. **Cache Metrics**:
   - Hit/miss rates
   - Memory usage
   - Eviction counts
   - Connection counts

5. **Storage Metrics**:
   - Bucket usage
   - Object counts
   - Request rates
   - Error rates

6. **Application Metrics**:
   - Processing time
   - OCR accuracy
   - API response time
   - Error rates

## Alerting

The module configures alerts for critical conditions based on the collected metrics. Alerts are managed by AlertManager and can be sent to various notification channels:

- PagerDuty for critical alerts (P1)
- Slack for high and medium priority alerts (P2, P3)
- Email for low priority alerts (P4)

## Dashboard Access

Grafana dashboards can be accessed through the Grafana UI. The module provides the following access methods:

1. **Cluster-internal access**: `http://prometheus-operator-grafana.monitoring.svc.cluster.local:80`
2. **External access** (if Ingress is enabled): `https://grafana.example.com`

Default credentials:
- Username: `admin`
- Password: Specified by the `grafana_admin_password` variable

## Maintenance and Troubleshooting

### Storage Management

The module configures persistent storage for Prometheus and Grafana. The storage size is determined based on the environment:

- **Development**: 10Gi for Prometheus, 5Gi for Grafana
- **Staging**: 20Gi for Prometheus, 10Gi for Grafana
- **Production**: 50Gi for Prometheus, 20Gi for Grafana

If storage needs to be expanded, update the corresponding variables and apply the changes.

### Retention Management

Metrics retention is configured based on the environment:

- **Development**: 7 days
- **Staging**: 15 days
- **Production**: 30 days

To modify retention periods, update the `prometheus_retention` local variable in the module.

### Common Issues

1. **Prometheus not scraping metrics**: Check service monitor configurations and ensure that services expose metrics on the correct port and path.

2. **Grafana dashboards not loading**: Verify that the dashboard ConfigMap exists and is properly formatted.

3. **Alerts not firing**: Check AlertManager configuration and ensure that notification channels are properly configured.

4. **High resource usage**: Adjust resource requests and limits based on actual usage patterns.

## Security Considerations

The module implements several security measures:

1. **Authentication**: Grafana is protected with admin credentials.

2. **TLS**: Ingress resources are configured with TLS when enabled.

3. **RBAC**: Service accounts have minimal required permissions.

4. **Secrets**: Sensitive information is stored in Kubernetes secrets.

5. **Network Policies**: Access to monitoring services is restricted to necessary components.

## Cost Optimization

To optimize costs, consider the following:

1. **Resource Allocation**: Adjust CPU and memory requests based on actual usage.

2. **Retention Period**: Reduce retention periods for non-critical metrics.

3. **Scrape Interval**: Increase scrape intervals for stable metrics.

4. **Storage Class**: Use cost-effective storage classes for persistent volumes.

5. **Environment Sizing**: Use minimal resources in development and staging environments.