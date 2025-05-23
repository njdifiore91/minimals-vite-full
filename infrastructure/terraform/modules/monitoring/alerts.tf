# Terraform configuration for alerting rules and notification channels
# This file defines critical alerts for system health, application performance, and business metrics

# Alert severity levels and response times
# P1 - Critical: Service outage or severe degradation - Immediate response (24/7)
# P2 - High: Partial service degradation - <30 minutes response (24/7)
# P3 - Medium: Non-critical component issue - Business hours response
# P4 - Low: Potential issue, no user impact - Next sprint

# Variables for alert thresholds
locals {
  # SLA thresholds
  application_processing_time_threshold = 300 # 5 minutes in seconds
  ocr_accuracy_threshold               = 99   # 99% accuracy
  api_response_time_threshold          = 500  # 500ms
  
  # Queue depth thresholds
  queue_depth_critical                 = 1000 # Critical threshold for queue depth
  queue_depth_warning                  = 500  # Warning threshold for queue depth
  
  # Error rate thresholds
  error_rate_critical                  = 0.05 # 5% error rate
  error_rate_warning                   = 0.02 # 2% error rate
  
  # Resource utilization thresholds
  cpu_utilization_critical             = 90   # 90% CPU utilization
  memory_utilization_critical          = 90   # 90% memory utilization
  disk_utilization_critical            = 85   # 85% disk utilization
  
  # Notification channels
  pagerduty_service_key                = var.pagerduty_service_key
  slack_channel_alerts_urgent          = var.slack_channel_alerts_urgent
  slack_channel_alerts_general         = var.slack_channel_alerts_general
  email_alerts_critical                = var.email_alerts_critical
}

# Datadog provider configuration
provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
}

# PagerDuty integration for critical alerts
resource "datadog_integration_pagerduty" "mca_pagerduty" {
  count             = var.enable_datadog ? 1 : 0
  schedules = {
    "critical" = local.pagerduty_service_key
  }
}

# Slack integration for alerts
resource "datadog_integration_slack" "mca_slack" {
  count             = var.enable_datadog ? 1 : 0
  account_name      = "dollarfunding"
  channels = {
    "urgent"  = local.slack_channel_alerts_urgent
    "general" = local.slack_channel_alerts_general
  }
}

# Email notification configuration
resource "datadog_monitor_notification_channel" "email_notifications" {
  count             = var.enable_datadog ? 1 : 0
  name              = "MCA Email Notifications"
  email_recipients  = local.email_alerts_critical
}

#######################
# Application Monitors
#######################

# Application Processing Time SLA Monitor
resource "datadog_monitor" "application_processing_time" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P1][MCA] Application Processing Time Exceeds SLA"
  type              = "metric alert"
  message           = <<-EOT
    Application processing time has exceeded the SLA threshold of 5 minutes.
    
    This is a critical alert that requires immediate attention as it impacts our core SLA.
    
    Troubleshooting steps:
    1. Check the OCR service for processing delays
    2. Verify document service classification performance
    3. Check RabbitMQ queue depths for bottlenecks
    4. Verify database performance metrics
    
    @pagerduty-critical @slack-urgent
  EOT
  
  query             = "avg(last_5m):avg:mca.application.processing_time{*} > ${local.application_processing_time_threshold}"
  thresholds = {
    critical        = local.application_processing_time_threshold
    warning         = local.application_processing_time_threshold * 0.8
  }
  
  notify_no_data    = true
  no_data_timeframe = 10
  evaluation_delay  = 60
  include_tags      = true
  priority          = 1
  
  tags = [
    "service:data-service",
    "sla:processing-time",
    "severity:critical",
    "team:operations"
  ]
}

# OCR Accuracy Monitor
resource "datadog_monitor" "ocr_accuracy" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P1][MCA] OCR Accuracy Below Threshold"
  type              = "metric alert"
  message           = <<-EOT
    OCR accuracy has fallen below the required 99% threshold.
    
    This is a critical alert that requires immediate attention as it impacts data extraction quality.
    
    Troubleshooting steps:
    1. Check recent model performance metrics
    2. Verify if there are new document types causing issues
    3. Check for changes in document quality or format
    4. Verify GPU resource availability for OCR processing
    
    @pagerduty-critical @slack-urgent
  EOT
  
  query             = "avg(last_15m):avg:mca.ocr.accuracy{*} < ${local.ocr_accuracy_threshold}"
  thresholds = {
    critical        = local.ocr_accuracy_threshold
    warning         = local.ocr_accuracy_threshold + 0.5
  }
  
  notify_no_data    = true
  no_data_timeframe = 10
  evaluation_delay  = 60
  include_tags      = true
  priority          = 1
  
  tags = [
    "service:ocr-service",
    "sla:accuracy",
    "severity:critical",
    "team:data-science"
  ]
}

# Queue Depth Monitor
resource "datadog_monitor" "queue_depth" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] RabbitMQ Queue Depth High"
  type              = "metric alert"
  message           = <<-EOT
    RabbitMQ queue depth is abnormally high, indicating potential processing bottlenecks.
    
    This alert requires attention within 30 minutes as it may lead to processing delays.
    
    Troubleshooting steps:
    1. Check consumer service health and scaling
    2. Verify if there's an unusual influx of documents
    3. Check for errors in processing services
    4. Consider scaling up consumer services
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "max(last_10m):max:rabbitmq.queue.messages{queue:document-processing} > ${local.queue_depth_critical} OR max:rabbitmq.queue.messages{queue:data-extraction} > ${local.queue_depth_critical} OR max:rabbitmq.queue.messages{queue:notification} > ${local.queue_depth_critical}"
  thresholds = {
    critical        = local.queue_depth_critical
    warning         = local.queue_depth_warning
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "service:rabbitmq",
    "component:queue",
    "severity:high",
    "team:operations"
  ]
}

# API Response Time Monitor
resource "datadog_monitor" "api_response_time" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] API Gateway Response Time High"
  type              = "metric alert"
  message           = <<-EOT
    API Gateway response time is exceeding the threshold of 500ms.
    
    This alert requires attention within 30 minutes as it impacts user experience.
    
    Troubleshooting steps:
    1. Check API Gateway logs for slow endpoints
    2. Verify backend service performance
    3. Check for network latency issues
    4. Verify database query performance
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "avg(last_5m):avg:kong.request.latency{*} > ${local.api_response_time_threshold}"
  thresholds = {
    critical        = local.api_response_time_threshold
    warning         = local.api_response_time_threshold * 0.8
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "service:api-gateway",
    "component:kong",
    "severity:high",
    "team:operations"
  ]
}

# Error Rate Monitor
resource "datadog_monitor" "error_rate" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P1][MCA] High Error Rate Detected"
  type              = "metric alert"
  message           = <<-EOT
    Error rate has exceeded the critical threshold of 5%.
    
    This is a critical alert that requires immediate attention as it indicates system failures.
    
    Troubleshooting steps:
    1. Check application logs for error patterns
    2. Verify recent deployments or changes
    3. Check external dependencies and services
    4. Verify infrastructure health
    
    @pagerduty-critical @slack-urgent
  EOT
  
  query             = "sum(last_5m):sum:mca.errors.count{*}.as_count() / sum:mca.requests.count{*}.as_count() > ${local.error_rate_critical}"
  thresholds = {
    critical        = local.error_rate_critical
    warning         = local.error_rate_warning
  }
  
  notify_no_data    = true
  no_data_timeframe = 10
  evaluation_delay  = 30
  include_tags      = true
  priority          = 1
  
  tags = [
    "service:all",
    "component:errors",
    "severity:critical",
    "team:operations"
  ]
}

# Document Classification Confidence Monitor
resource "datadog_monitor" "classification_confidence" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P3][MCA] Document Classification Confidence Low"
  type              = "metric alert"
  message           = <<-EOT
    Document classification confidence is below expected levels.
    
    This alert requires attention during business hours as it may impact classification accuracy.
    
    Troubleshooting steps:
    1. Check recent document types being processed
    2. Verify classification model performance
    3. Consider model retraining with recent examples
    4. Check for data drift in document formats
    
    @slack-general
  EOT
  
  query             = "avg(last_30m):avg:mca.document.classification.confidence{*} < 75"
  thresholds = {
    critical        = 70
    warning         = 75
  }
  
  notify_no_data    = false
  evaluation_delay  = 60
  include_tags      = true
  priority          = 3
  
  tags = [
    "service:document-service",
    "component:classification",
    "severity:medium",
    "team:data-science"
  ]
}

# Email Processing Delay Monitor
resource "datadog_monitor" "email_processing_delay" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] Email Processing Delay Detected"
  type              = "metric alert"
  message           = <<-EOT
    Delay in email processing has been detected.
    
    This alert requires attention within 30 minutes as it may impact application ingestion.
    
    Troubleshooting steps:
    1. Check email service logs for connectivity issues
    2. Verify IMAP server health and connectivity
    3. Check for large attachments causing processing delays
    4. Verify message queue performance
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "avg(last_10m):avg:mca.email.processing_delay{*} > 300"
  thresholds = {
    critical        = 300
    warning         = 180
  }
  
  notify_no_data    = true
  no_data_timeframe = 30
  evaluation_delay  = 60
  include_tags      = true
  priority          = 2
  
  tags = [
    "service:email-service",
    "component:email-processing",
    "severity:high",
    "team:operations"
  ]
}

# Database Replication Lag Monitor
resource "datadog_monitor" "db_replication_lag" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] PostgreSQL Replication Lag High"
  type              = "metric alert"
  message           = <<-EOT
    PostgreSQL replication lag is higher than expected.
    
    This alert requires attention within 30 minutes as it may impact data consistency.
    
    Troubleshooting steps:
    1. Check database load and performance
    2. Verify network connectivity between primary and replicas
    3. Check for long-running transactions blocking replication
    4. Verify disk I/O performance on replicas
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "max(last_5m):max:postgresql.replication_delay{*} > 300"
  thresholds = {
    critical        = 300
    warning         = 120
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "service:postgresql",
    "component:replication",
    "severity:high",
    "team:dba"
  ]
}

# Redis Cache Hit Rate Monitor
resource "datadog_monitor" "redis_hit_rate" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P3][MCA] Redis Cache Hit Rate Low"
  type              = "metric alert"
  message           = <<-EOT
    Redis cache hit rate is below expected levels.
    
    This alert requires attention during business hours as it may impact application performance.
    
    Troubleshooting steps:
    1. Check cache key patterns and expiration policies
    2. Verify memory usage and eviction rates
    3. Review application caching strategy
    4. Consider increasing cache size if consistently low
    
    @slack-general
  EOT
  
  query             = "avg(last_15m):avg:redis.stats.keyspace_hits{*} / (avg:redis.stats.keyspace_hits{*} + avg:redis.stats.keyspace_misses{*}) < 0.7"
  thresholds = {
    critical        = 0.5
    warning         = 0.7
  }
  
  notify_no_data    = false
  evaluation_delay  = 60
  include_tags      = true
  priority          = 3
  
  tags = [
    "service:redis",
    "component:cache",
    "severity:medium",
    "team:operations"
  ]
}

# S3 Storage Error Rate Monitor
resource "datadog_monitor" "s3_error_rate" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] S3 Storage Error Rate High"
  type              = "metric alert"
  message           = <<-EOT
    S3 storage error rate is higher than expected.
    
    This alert requires attention within 30 minutes as it may impact document storage and retrieval.
    
    Troubleshooting steps:
    1. Check S3 service status
    2. Verify IAM permissions and access keys
    3. Check for network connectivity issues
    4. Verify application S3 client configuration
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "sum(last_5m):sum:aws.s3.4xx_errors{*}.as_count() + sum:aws.s3.5xx_errors{*}.as_count() / sum:aws.s3.requests{*}.as_count() > 0.05"
  thresholds = {
    critical        = 0.05
    warning         = 0.02
  }
  
  notify_no_data    = false
  evaluation_delay  = 60
  include_tags      = true
  priority          = 2
  
  tags = [
    "service:s3",
    "component:storage",
    "severity:high",
    "team:operations"
  ]
}

# Webhook Delivery Failure Monitor
resource "datadog_monitor" "webhook_delivery_failure" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] Webhook Delivery Failure Rate High"
  type              = "metric alert"
  message           = <<-EOT
    Webhook delivery failure rate is higher than expected.
    
    This alert requires attention within 30 minutes as it impacts notification delivery to external systems.
    
    Troubleshooting steps:
    1. Check notification service logs for specific errors
    2. Verify webhook endpoint availability
    3. Check for network connectivity issues
    4. Verify webhook payload format and signature
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "sum(last_15m):sum:mca.webhook.delivery.failure{*}.as_count() / sum:mca.webhook.delivery.attempt{*}.as_count() > 0.1"
  thresholds = {
    critical        = 0.1
    warning         = 0.05
  }
  
  notify_no_data    = false
  evaluation_delay  = 60
  include_tags      = true
  priority          = 2
  
  tags = [
    "service:notification-service",
    "component:webhooks",
    "severity:high",
    "team:operations"
  ]
}

#######################
# Resource Monitors
#######################

# CPU Utilization Monitor
resource "datadog_monitor" "cpu_utilization" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] High CPU Utilization"
  type              = "metric alert"
  message           = <<-EOT
    CPU utilization is above ${local.cpu_utilization_critical}% for the specified service.
    
    This alert requires attention within 30 minutes as it may impact service performance.
    
    Troubleshooting steps:
    1. Check for resource-intensive processes
    2. Verify recent deployments or changes
    3. Consider scaling up or out the service
    4. Check for potential memory leaks or runaway processes
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "avg(last_5m):avg:kubernetes.cpu.usage.total{kube_namespace:mca} by {kube_deployment} > ${local.cpu_utilization_critical}"
  thresholds = {
    critical        = local.cpu_utilization_critical
    warning         = local.cpu_utilization_critical - 10
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "resource:cpu",
    "severity:high",
    "team:operations"
  ]
}

# Memory Utilization Monitor
resource "datadog_monitor" "memory_utilization" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] High Memory Utilization"
  type              = "metric alert"
  message           = <<-EOT
    Memory utilization is above ${local.memory_utilization_critical}% for the specified service.
    
    This alert requires attention within 30 minutes as it may lead to OOM kills.
    
    Troubleshooting steps:
    1. Check for memory leaks
    2. Verify heap usage for Java services
    3. Consider scaling up or out the service
    4. Check for large data processing operations
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "avg(last_5m):avg:kubernetes.memory.usage_pct{kube_namespace:mca} by {kube_deployment} > ${local.memory_utilization_critical}"
  thresholds = {
    critical        = local.memory_utilization_critical
    warning         = local.memory_utilization_critical - 10
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "resource:memory",
    "severity:high",
    "team:operations"
  ]
}

# Disk Utilization Monitor
resource "datadog_monitor" "disk_utilization" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] High Disk Utilization"
  type              = "metric alert"
  message           = <<-EOT
    Disk utilization is above ${local.disk_utilization_critical}% for the specified node.
    
    This alert requires attention within 30 minutes as it may impact service stability.
    
    Troubleshooting steps:
    1. Identify large files or logs
    2. Check for disk space leaks
    3. Consider cleaning up temporary files
    4. Verify log rotation policies
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "avg(last_5m):avg:kubernetes.filesystem.usage_pct{kube_namespace:mca} by {host} > ${local.disk_utilization_critical}"
  thresholds = {
    critical        = local.disk_utilization_critical
    warning         = local.disk_utilization_critical - 10
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "resource:disk",
    "severity:high",
    "team:operations"
  ]
}

# Pod Restart Monitor
resource "datadog_monitor" "pod_restarts" {
  count             = var.enable_datadog ? 1 : 0
  name              = "[P2][MCA] Frequent Pod Restarts Detected"
  type              = "metric alert"
  message           = <<-EOT
    Frequent pod restarts detected for the specified deployment.
    
    This alert requires attention within 30 minutes as it indicates service instability.
    
    Troubleshooting steps:
    1. Check pod logs for crash reasons
    2. Verify resource limits and requests
    3. Check for liveness/readiness probe failures
    4. Verify recent deployments or changes
    
    @pagerduty-high @slack-urgent
  EOT
  
  query             = "change(sum(last_10m),last_10m):sum:kubernetes.containers.restarts{kube_namespace:mca} by {kube_deployment} > 3"
  thresholds = {
    critical        = 3
    warning         = 1
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = 2
  
  tags = [
    "component:kubernetes",
    "severity:high",
    "team:operations"
  ]
}

#######################
# Prometheus Alerting Rules (if Prometheus is used instead of Datadog)
#######################

# Prometheus alert rules for application monitoring
resource "kubernetes_config_map" "prometheus_alert_rules" {
  count = var.enable_prometheus ? 1 : 0
  
  metadata {
    name      = "mca-prometheus-alert-rules"
    namespace = "monitoring"
    labels = {
      "app.kubernetes.io/name"       = "prometheus"
      "app.kubernetes.io/component"  = "alert-rules"
      "app.kubernetes.io/part-of"    = "mca"
    }
  }

  data = {
    "mca-alerts.yaml" = <<-EOT
      groups:
      - name: mca-application-alerts
        rules:
        # Application Processing Time SLA Alert
        - alert: ApplicationProcessingTimeSLABreach
          expr: avg(rate(mca_application_processing_time_seconds_sum[5m]) / rate(mca_application_processing_time_seconds_count[5m])) > ${local.application_processing_time_threshold}
          for: 5m
          labels:
            severity: critical
            priority: P1
            team: operations
          annotations:
            summary: "Application processing time exceeds SLA"
            description: "Application processing time has exceeded the SLA threshold of 5 minutes. This requires immediate attention."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/processing-time-sla"
        
        # OCR Accuracy Alert
        - alert: OCRAccuracyBelowThreshold
          expr: avg(mca_ocr_accuracy{job="ocr-service"}[15m]) < ${local.ocr_accuracy_threshold}
          for: 15m
          labels:
            severity: critical
            priority: P1
            team: data-science
          annotations:
            summary: "OCR accuracy below threshold"
            description: "OCR accuracy has fallen below the required 99% threshold. This requires immediate attention."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/ocr-accuracy"
        
        # Queue Depth Alert
        - alert: RabbitMQQueueDepthHigh
          expr: rabbitmq_queue_messages{queue=~"document-processing|data-extraction|notification"} > ${local.queue_depth_warning}
          for: 10m
          labels:
            severity: warning
            priority: P2
            team: operations
          annotations:
            summary: "RabbitMQ queue depth high"
            description: "RabbitMQ queue {{ $labels.queue }} has {{ $value }} messages, which is above the warning threshold of ${local.queue_depth_warning}."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/queue-depth"
        
        # API Response Time Alert
        - alert: APIResponseTimeHigh
          expr: avg(rate(kong_latency_seconds_sum[5m]) / rate(kong_latency_seconds_count[5m])) * 1000 > ${local.api_response_time_threshold}
          for: 5m
          labels:
            severity: warning
            priority: P2
            team: operations
          annotations:
            summary: "API Gateway response time high"
            description: "API Gateway response time is exceeding the threshold of ${local.api_response_time_threshold}ms."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/api-response-time"
        
        # Error Rate Alert
        - alert: HighErrorRate
          expr: sum(rate(mca_errors_total[5m])) / sum(rate(mca_requests_total[5m])) > ${local.error_rate_critical}
          for: 5m
          labels:
            severity: critical
            priority: P1
            team: operations
          annotations:
            summary: "High error rate detected"
            description: "Error rate has exceeded the critical threshold of ${local.error_rate_critical * 100}%."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/error-rate"
      
      - name: mca-resource-alerts
        rules:
        # CPU Utilization Alert
        - alert: HighCPUUtilization
          expr: avg(container_cpu_usage_seconds_total{namespace="mca"}) by (pod) / avg(container_spec_cpu_quota{namespace="mca"}) by (pod) > ${local.cpu_utilization_critical / 100}
          for: 5m
          labels:
            severity: warning
            priority: P2
            team: operations
          annotations:
            summary: "High CPU utilization"
            description: "Pod {{ $labels.pod }} has CPU utilization of {{ $value | humanizePercentage }}, which is above the warning threshold of ${local.cpu_utilization_critical}%."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/cpu-utilization"
        
        # Memory Utilization Alert
        - alert: HighMemoryUtilization
          expr: avg(container_memory_usage_bytes{namespace="mca"}) by (pod) / avg(container_spec_memory_limit_bytes{namespace="mca"}) by (pod) > ${local.memory_utilization_critical / 100}
          for: 5m
          labels:
            severity: warning
            priority: P2
            team: operations
          annotations:
            summary: "High memory utilization"
            description: "Pod {{ $labels.pod }} has memory utilization of {{ $value | humanizePercentage }}, which is above the warning threshold of ${local.memory_utilization_critical}%."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/memory-utilization"
        
        # Disk Utilization Alert
        - alert: HighDiskUtilization
          expr: avg(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_free_bytes{mountpoint="/"}) by (instance) / avg(node_filesystem_size_bytes{mountpoint="/"}) by (instance) > ${local.disk_utilization_critical / 100}
          for: 5m
          labels:
            severity: warning
            priority: P2
            team: operations
          annotations:
            summary: "High disk utilization"
            description: "Node {{ $labels.instance }} has disk utilization of {{ $value | humanizePercentage }}, which is above the warning threshold of ${local.disk_utilization_critical}%."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/disk-utilization"
        
        # Pod Restart Alert
        - alert: FrequentPodRestarts
          expr: increase(kube_pod_container_status_restarts_total{namespace="mca"}[10m]) > 3
          for: 5m
          labels:
            severity: warning
            priority: P2
            team: operations
          annotations:
            summary: "Frequent pod restarts detected"
            description: "Pod {{ $labels.pod }} has restarted {{ $value }} times in the last 10 minutes."
            runbook_url: "https://runbooks.dollarfunding.com/mca/alerts/pod-restarts"
    EOT
  }
}

# Grafana dashboard for alerts visualization
resource "grafana_dashboard" "mca_alerts_dashboard" {
  count       = var.enable_prometheus ? 1 : 0
  config_json = file("${path.module}/dashboards/mca-alerts-dashboard.json")
  folder      = var.grafana_folder_id
}

# Grafana alert notification channels
resource "grafana_alert_notification" "pagerduty" {
  count       = var.enable_prometheus ? 1 : 0
  name        = "MCA PagerDuty"
  type        = "pagerduty"
  is_default  = false
  settings = {
    integrationKey = local.pagerduty_service_key
    autoResolve    = true
  }
}

resource "grafana_alert_notification" "slack_urgent" {
  count       = var.enable_prometheus ? 1 : 0
  name        = "MCA Slack Urgent"
  type        = "slack"
  is_default  = false
  settings = {
    url         = var.slack_webhook_url
    recipient   = local.slack_channel_alerts_urgent
    mention     = "@here"
    mentionUsers = "operations-team"
    mentionGroups = ""
    mentionChannel = "here"
    username    = "Grafana Alerts"
    iconEmoji   = ":rotating_light:"
  }
}

resource "grafana_alert_notification" "slack_general" {
  count       = var.enable_prometheus ? 1 : 0
  name        = "MCA Slack General"
  type        = "slack"
  is_default  = false
  settings = {
    url         = var.slack_webhook_url
    recipient   = local.slack_channel_alerts_general
    mention     = ""
    mentionUsers = ""
    mentionGroups = ""
    mentionChannel = ""
    username    = "Grafana Alerts"
    iconEmoji   = ":warning:"
  }
}

resource "grafana_alert_notification" "email" {
  count       = var.enable_prometheus ? 1 : 0
  name        = "MCA Email Alerts"
  type        = "email"
  is_default  = false
  settings = {
    addresses    = join(",", local.email_alerts_critical)
    singleEmail  = false
  }
}

# Variables for the monitoring module
variable "datadog_api_key" {
  description = "Datadog API key for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "datadog_app_key" {
  description = "Datadog application key for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pagerduty_service_key" {
  description = "PagerDuty service key for alert integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "slack_channel_alerts_urgent" {
  description = "Slack channel for urgent alerts"
  type        = string
  default     = "#alerts-urgent"
}

variable "slack_channel_alerts_general" {
  description = "Slack channel for general alerts"
  type        = string
  default     = "#alerts-general"
}

variable "email_alerts_critical" {
  description = "Email addresses for critical alerts"
  type        = list(string)
  default     = ["ops@dollarfunding.com", "oncall@dollarfunding.com"]
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alert notifications"
  type        = string
  sensitive   = true
  default     = ""
}

variable "enable_datadog" {
  description = "Enable Datadog monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_prometheus" {
  description = "Enable Prometheus monitoring and alerting"
  type        = bool
  default     = false
}

variable "grafana_folder_id" {
  description = "Grafana folder ID for dashboards"
  type        = string
  default     = ""
}

# Outputs for the monitoring module
output "datadog_monitors" {
  description = "List of Datadog monitors created"
  value       = var.enable_datadog ? [
    datadog_monitor.application_processing_time[0].id,
    datadog_monitor.ocr_accuracy[0].id,
    datadog_monitor.queue_depth[0].id,
    datadog_monitor.api_response_time[0].id,
    datadog_monitor.error_rate[0].id,
    datadog_monitor.classification_confidence[0].id,
    datadog_monitor.email_processing_delay[0].id,
    datadog_monitor.db_replication_lag[0].id,
    datadog_monitor.redis_hit_rate[0].id,
    datadog_monitor.s3_error_rate[0].id,
    datadog_monitor.webhook_delivery_failure[0].id,
    datadog_monitor.cpu_utilization[0].id,
    datadog_monitor.memory_utilization[0].id,
    datadog_monitor.disk_utilization[0].id,
    datadog_monitor.pod_restarts[0].id
  ] : []
}

output "prometheus_alert_rules" {
  description = "Prometheus alert rules ConfigMap name"
  value       = var.enable_prometheus ? kubernetes_config_map.prometheus_alert_rules[0].metadata[0].name : ""
}

output "grafana_notification_channels" {
  description = "List of Grafana notification channels created"
  value       = var.enable_prometheus ? [
    grafana_alert_notification.pagerduty[0].id,
    grafana_alert_notification.slack_urgent[0].id,
    grafana_alert_notification.slack_general[0].id,
    grafana_alert_notification.email[0].id
  ] : []
}