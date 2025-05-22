# Infrastructure Monitoring Module

## Overview

This Terraform module provisions and configures a comprehensive monitoring infrastructure for the Merchant Cash Advance (MCA) Application Processing System. It supports both Datadog and Prometheus/Grafana as monitoring solutions, providing complete observability across frontend applications, backend microservices, and infrastructure components.

The monitoring infrastructure combines metrics collection, log aggregation, distributed tracing, and alerting to ensure comprehensive visibility into system health, performance, and security.

## Architecture

The monitoring module implements a multi-layered observability stack:

```
┌─────────────────────────────────────────────────────────────────┐
│                      Visualization Layer                         │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │
│  │   Dashboards  │  │  Log Explorer │  │   Trace Viewer    │    │
│  └───────────────┘  └───────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                        Storage Layer                            │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │
│  │  Time Series  │  │  Log Storage  │  │   Trace Storage   │    │
│  │   Database    │  │               │  │                   │    │
│  └───────────────┘  └───────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Instrumentation Layer                        │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │
│  │    Metrics    │  │      Log      │  │    Distributed    │    │
│  │   Collection  │  │   Collection  │  │      Tracing      │    │
│  └───────────────┘  └───────────────┘  └───────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│                                                                 │
│  ┌───────────┐ ┌────────────┐ ┌───────────┐ ┌────────────┐      │
│  │  Frontend │ │ Microservices │ Databases │ │ Message Queues │  │
│  └───────────┘ └────────────┘ └───────────┘ └────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **Metrics Collection**
   - Infrastructure metrics (CPU, memory, disk, network)
   - Container metrics (resource usage, restart count)
   - Application metrics (custom business metrics)
   - Database metrics (query performance, connections)
   - Message queue metrics (queue depth, consumer lag)

2. **Log Aggregation**
   - Centralized logging pipeline
   - Structured logging format
   - Log correlation through trace IDs
   - Log retention policies

3. **Distributed Tracing**
   - Request tracing across services
   - Performance bottleneck identification
   - Error correlation

4. **Alerting Framework**
   - Multi-level severity classification
   - Multiple notification channels
   - Alert deduplication and grouping
   - Escalation policies

## Prerequisites

- Terraform >= 1.0.0
- AWS provider >= 4.0.0 (if using AWS)
- Kubernetes provider >= 2.10.0 (if using Kubernetes)
- Datadog provider >= 3.20.0 (if using Datadog)
- Helm provider >= 2.5.0 (if using Prometheus/Grafana)

## Usage

### Basic Usage with Datadog

```hcl
module "monitoring" {
  source = "../modules/monitoring"

  environment         = "production"
  monitoring_solution = "datadog"
  
  datadog_api_key     = var.datadog_api_key
  datadog_app_key     = var.datadog_app_key
  
  services = [
    "email-service",
    "document-service",
    "ocr-service",
    "data-service",
    "notification-service"
  ]
  
  infrastructure_components = [
    "postgresql",
    "rabbitmq",
    "redis",
    "s3"
  ]
  
  alert_notification_channels = {
    email     = ["alerts@dollarfunding.com"],
    slack     = ["#alerts-production"],
    pagerduty = ["mca-oncall"],
  }
}
```

### Basic Usage with Prometheus/Grafana

```hcl
module "monitoring" {
  source = "../modules/monitoring"

  environment         = "staging"
  monitoring_solution = "prometheus"
  
  prometheus_retention_days = 15
  grafana_admin_password    = var.grafana_admin_password
  
  services = [
    "email-service",
    "document-service",
    "ocr-service",
    "data-service",
    "notification-service"
  ]
  
  infrastructure_components = [
    "postgresql",
    "rabbitmq",
    "redis",
    "s3"
  ]
  
  alert_notification_channels = {
    email = ["dev-alerts@dollarfunding.com"],
    slack = ["#alerts-staging"],
  }
}
```

## Module Configuration

### Input Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | Environment name (e.g., development, staging, production) | `string` | n/a | yes |
| monitoring_solution | Monitoring solution to use ("datadog" or "prometheus") | `string` | `"datadog"` | no |
| services | List of services to monitor | `list(string)` | `[]` | yes |
| infrastructure_components | List of infrastructure components to monitor | `list(string)` | `[]` | yes |
| alert_notification_channels | Map of notification channels and their targets | `map(list(string))` | `{}` | yes |
| datadog_api_key | Datadog API key (required if using Datadog) | `string` | `""` | no |
| datadog_app_key | Datadog application key (required if using Datadog) | `string` | `""` | no |
| prometheus_retention_days | Number of days to retain Prometheus metrics | `number` | `15` | no |
| grafana_admin_password | Grafana admin password (required if using Prometheus) | `string` | `""` | no |
| log_retention_days | Number of days to retain logs | `number` | `30` | no |
| enable_tracing | Whether to enable distributed tracing | `bool` | `true` | no |
| metrics_scrape_interval | Interval for scraping metrics in seconds | `number` | `30` | no |
| high_availability | Whether to deploy monitoring components in HA mode | `bool` | `false` | no |
| namespace | Kubernetes namespace for monitoring components | `string` | `"monitoring"` | no |

### Output Values

| Name | Description |
|------|-------------|
| monitoring_dashboard_url | URL to access the monitoring dashboard |
| alerting_webhook_url | Webhook URL for sending custom alerts |
| metrics_endpoint | Endpoint for pushing custom metrics |
| log_endpoint | Endpoint for sending logs |
| trace_endpoint | Endpoint for sending traces |

## Integration with Other Infrastructure Components

### Database Monitoring Integration

This module automatically integrates with the PostgreSQL database module to collect metrics such as:

- Query performance
- Connection pool usage
- Replication lag
- Transaction rates
- Cache hit ratios

Example integration with the database module:

```hcl
module "database" {
  source = "../modules/database"
  
  # Database configuration
  name     = "mca-db"
  instance = "db.t3.large"
  # ... other database configuration
}

module "monitoring" {
  source = "../modules/monitoring"
  
  # Monitoring configuration
  infrastructure_components = ["postgresql"]
  
  # Reference database module for integration
  postgresql_host = module.database.host
  postgresql_port = module.database.port
  # ... other monitoring configuration
}
```

### Message Queue Monitoring Integration

Integration with RabbitMQ to monitor:

- Queue depths
- Message rates
- Consumer lag
- Connection status
- Node health

### Cache Monitoring Integration

Integration with Redis to monitor:

- Memory usage
- Hit/miss rates
- Eviction counts
- Connection counts
- Command latency

### Storage Monitoring Integration

Integration with S3-compatible storage to monitor:

- Bucket usage
- Request rates
- Error counts
- Latency metrics
- Bandwidth usage

## Alerting Configuration

The module configures alerts with different severity levels:

| Severity | Description | Response Time | Example Trigger |
|----------|-------------|---------------|----------------|
| P1 - Critical | Service outage or severe degradation | Immediate (24/7) | >20% error rate, service unavailable |
| P2 - High | Partial service degradation | <30 minutes (24/7) | Performance degradation, approaching resource limits |
| P3 - Medium | Non-critical component issue | Business hours | Elevated error rates, performance anomalies |
| P4 - Low | Potential issue, no user impact | Next sprint | Slow degradation, maintenance needed |

Example alert configuration:

```hcl
module "monitoring" {
  source = "../modules/monitoring"
  
  # ... other configuration
  
  custom_alerts = [
    {
      name        = "high_api_error_rate"
      query       = "sum:api.error_rate{*} by {service} > 0.05"
      severity    = "P2"
      message     = "API error rate exceeds 5% for service {{service}}"
      notify      = ["slack", "email"]
      evaluation_period = "5m"
    },
    {
      name        = "database_connection_saturation"
      query       = "avg:postgresql.connections.used{*} / avg:postgresql.connections.max{*} * 100 > 80"
      severity    = "P3"
      message     = "Database connection pool usage above 80%"
      notify      = ["slack"]
      evaluation_period = "10m"
    }
  ]
}
```

## Dashboard Setup

The module creates several pre-configured dashboards:

1. **Executive Summary Dashboard**
   - High-level system health
   - SLA compliance metrics
   - Key business metrics

2. **Service Overview Dashboards**
   - One dashboard per service
   - Error rates, latency, throughput
   - Resource utilization

3. **Infrastructure Dashboards**
   - Node status
   - Resource usage
   - Network metrics

4. **User Experience Dashboard**
   - Web Vitals metrics
   - User journey analytics
   - Conversion rates

Custom dashboards can be created by extending the module:

```hcl
module "monitoring" {
  source = "../modules/monitoring"
  
  # ... other configuration
  
  custom_dashboards = [
    {
      name  = "document_processing_pipeline"
      title = "Document Processing Pipeline"
      description = "End-to-end view of the document processing pipeline"
      widgets = [
        # Widget definitions
      ]
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### Metrics Not Appearing

1. Verify that the service or component is properly labeled/tagged
2. Check that the metrics agent is running on the target host
3. Ensure firewall rules allow metrics traffic
4. Verify service discovery is working correctly

#### Alert Notification Failures

1. Check notification channel configuration
2. Verify API keys and credentials
3. Ensure network connectivity to notification services
4. Check for rate limiting on notification endpoints

#### High Cardinality Issues

1. Review metric labels and reduce high-cardinality dimensions
2. Implement metric aggregation where appropriate
3. Adjust retention policies for high-volume metrics

### Debugging Tools

- Use `kubectl logs` to check monitoring agent logs
- Verify metrics endpoints with `curl` for Prometheus targets
- Use the monitoring solution's API to check configuration

## Best Practices

### Metric Naming and Labeling

- Use consistent naming conventions for metrics
- Follow the pattern: `{component}.{subsystem}.{metric}`
- Keep label cardinality under control
- Use standard labels across all services

### Alert Design

- Create actionable alerts with clear remediation steps
- Avoid alert fatigue by tuning thresholds appropriately
- Include context in alert messages
- Implement proper alert grouping

### Dashboard Design

- Focus on user needs and use cases
- Provide context with thresholds and historical data
- Enable drill-down capabilities
- Keep dashboards focused and purpose-driven

### Resource Optimization

- Adjust retention periods based on metric importance
- Implement downsampling for long-term storage
- Use appropriate instance types for monitoring components
- Scale monitoring infrastructure with the application

## Security Considerations

- Store API keys and credentials securely
- Implement proper access controls for monitoring dashboards
- Encrypt monitoring traffic with TLS
- Regularly audit monitoring access logs
- Ensure monitoring agents run with least privilege

## License

This module is licensed under the [LICENSE NAME] license. See LICENSE.md for full details.