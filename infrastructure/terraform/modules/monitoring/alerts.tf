# Merchant Cash Advance (MCA) Application Processing System - Alerts Configuration
# This file configures alerting rules and notification channels for both Datadog and Prometheus/Grafana

# Local variables for alert configuration
locals {
  # Alert severity levels with response times
  severity_levels = {
    p1_critical = {
      description = "Service outage or severe degradation"
      response_time = "Immediate (24/7)"
      example = ">20% error rate, service unavailable"
      datadog_priority = 1
      pagerduty_severity = "critical"
    },
    p2_high = {
      description = "Partial service degradation"
      response_time = "<30 minutes (24/7)"
      example = "Performance degradation, approaching resource limits"
      datadog_priority = 2
      pagerduty_severity = "error"
    },
    p3_medium = {
      description = "Non-critical component issue"
      response_time = "Business hours"
      example = "Elevated error rates, performance anomalies"
      datadog_priority = 3
      pagerduty_severity = "warning"
    },
    p4_low = {
      description = "Potential issue, no user impact"
      response_time = "Next sprint"
      example = "Slow degradation, maintenance needed"
      datadog_priority = 4
      pagerduty_severity = "info"
    }
  }

  # Service Level Objectives (SLOs) for critical metrics
  slos = {
    application_processing_time = {
      description = "Application Processing Time"
      threshold = 300 # 5 minutes in seconds
      warning_threshold = 240 # 4 minutes in seconds
      critical_severity = "p1_critical"
      warning_severity = "p2_high"
    },
    ocr_accuracy = {
      description = "OCR Data Extraction Accuracy"
      threshold = 99.0 # 99% accuracy
      warning_threshold = 99.5 # 99.5% accuracy
      critical_severity = "p2_high"
      warning_severity = "p3_medium"
    },
    queue_depth = {
      description = "Message Queue Depth"
      threshold = 1000 # Maximum number of messages in queue
      warning_threshold = 750 # Warning threshold for queue depth
      critical_severity = "p2_high"
      warning_severity = "p3_medium"
    },
    api_response_time = {
      description = "API Response Time"
      threshold = 500 # 500ms
      warning_threshold = 300 # 300ms
      critical_severity = "p2_high"
      warning_severity = "p3_medium"
    },
    automation_rate = {
      description = "Application Automation Rate"
      threshold = 93.0 # 93% automation rate
      warning_threshold = 95.0 # 95% automation rate
      critical_severity = "p2_high"
      warning_severity = "p3_medium"
    },
    system_uptime = {
      description = "System Uptime"
      threshold = 99.9 # 99.9% uptime
      warning_threshold = 99.95 # 99.95% uptime
      critical_severity = "p1_critical"
      warning_severity = "p2_high"
    }
  }

  # Notification channels
  notification_channels = {
    pagerduty = {
      name = "PagerDuty"
      description = "PagerDuty for immediate response (24/7)"
      severity_levels = ["p1_critical", "p2_high"]
    },
    slack_urgent = {
      name = "Slack #alerts-urgent"
      description = "Slack channel for urgent alerts"
      severity_levels = ["p2_high"]
    },
    slack_general = {
      name = "Slack #alerts-general"
      description = "Slack channel for general alerts"
      severity_levels = ["p3_medium"]
    },
    jira = {
      name = "Jira Tickets"
      description = "Jira tickets for planned response"
      severity_levels = ["p4_low"]
    },
    email = {
      name = "Email Notifications"
      description = "Email notifications for alerts"
      severity_levels = ["p3_medium", "p4_low"]
    }
  }
}

# Datadog provider configuration is expected to be in datadog.tf

# Datadog Monitors for Application Processing Time SLA
resource "datadog_monitor" "application_processing_time" {
  count   = var.monitoring_type == "datadog" ? 1 : 0
  name    = "[P${local.severity_levels[local.slos.application_processing_time.critical_severity].datadog_priority}] Application Processing Time Exceeded"
  type    = "metric alert"
  message = <<-EOT
    ${local.slos.application_processing_time.description} has exceeded the threshold of ${local.slos.application_processing_time.threshold} seconds.
    
    This is a ${local.severity_levels[local.slos.application_processing_time.critical_severity].description} alert with ${local.severity_levels[local.slos.application_processing_time.critical_severity].response_time} response time required.
    
    ## Impact
    - Applications are taking longer than the SLA to process
    - This may affect customer satisfaction and business operations
    
    ## Troubleshooting
    1. Check the email service for bottlenecks
    2. Verify document classification service performance
    3. Examine OCR service processing times
    4. Check data service response times
    5. Verify message queue health
    
    @pagerduty-${local.notification_channels.pagerduty.name}
    @slack-${local.notification_channels.slack_urgent.name}
  EOT
  query   = "avg(last_5m):avg:mca.application.processing_time{*} > ${local.slos.application_processing_time.threshold}"
  
  thresholds = {
    critical = local.slos.application_processing_time.threshold
    warning  = local.slos.application_processing_time.warning_threshold
  }
  
  notify_no_data    = true
  no_data_timeframe = 10
  evaluation_delay  = 60
  include_tags      = true
  priority          = local.severity_levels[local.slos.application_processing_time.critical_severity].datadog_priority
  
  tags = [
    "service:mca",
    "metric:processing_time",
    "severity:${local.slos.application_processing_time.critical_severity}",
    "owner:operations",
    "environment:${var.environment}"
  ]
}

# Datadog Monitors for OCR Accuracy
resource "datadog_monitor" "ocr_accuracy" {
  count   = var.monitoring_type == "datadog" ? 1 : 0
  name    = "[P${local.severity_levels[local.slos.ocr_accuracy.critical_severity].datadog_priority}] OCR Data Extraction Accuracy Below Threshold"
  type    = "metric alert"
  message = <<-EOT
    ${local.slos.ocr_accuracy.description} has fallen below the threshold of ${local.slos.ocr_accuracy.threshold}%.
    
    This is a ${local.severity_levels[local.slos.ocr_accuracy.critical_severity].description} alert with ${local.severity_levels[local.slos.ocr_accuracy.critical_severity].response_time} response time required.
    
    ## Impact
    - Data extraction accuracy is below the required SLA
    - This may lead to incorrect data in applications
    - Manual verification may be required
    
    ## Troubleshooting
    1. Check OCR service logs for errors
    2. Verify document quality in recent submissions
    3. Check for OCR model issues
    4. Examine recent model training data
    5. Verify if there are new document types causing issues
    
    @pagerduty-${local.notification_channels.pagerduty.name}
    @slack-${local.notification_channels.slack_urgent.name}
  EOT
  query   = "avg(last_15m):avg:mca.ocr.accuracy{*} < ${local.slos.ocr_accuracy.threshold}"
  
  thresholds = {
    critical = local.slos.ocr_accuracy.threshold
    warning  = local.slos.ocr_accuracy.warning_threshold
  }
  
  notify_no_data    = true
  no_data_timeframe = 30
  evaluation_delay  = 300
  include_tags      = true
  priority          = local.severity_levels[local.slos.ocr_accuracy.critical_severity].datadog_priority
  
  tags = [
    "service:ocr",
    "metric:accuracy",
    "severity:${local.slos.ocr_accuracy.critical_severity}",
    "owner:data-science",
    "environment:${var.environment}"
  ]
}

# Datadog Monitors for Queue Depth
resource "datadog_monitor" "queue_depth" {
  count   = var.monitoring_type == "datadog" ? 1 : 0
  name    = "[P${local.severity_levels[local.slos.queue_depth.critical_severity].datadog_priority}] Message Queue Depth Exceeded"
  type    = "metric alert"
  message = <<-EOT
    ${local.slos.queue_depth.description} has exceeded the threshold of ${local.slos.queue_depth.threshold} messages.
    
    This is a ${local.severity_levels[local.slos.queue_depth.critical_severity].description} alert with ${local.severity_levels[local.slos.queue_depth.critical_severity].response_time} response time required.
    
    ## Impact
    - Message processing is falling behind
    - This may lead to delayed application processing
    - System may become overloaded if not addressed
    
    ## Troubleshooting
    1. Check consumer service logs for errors
    2. Verify consumer service scaling
    3. Examine message processing times
    4. Check for stuck messages
    5. Verify if there's a sudden increase in incoming messages
    
    @pagerduty-${local.notification_channels.pagerduty.name}
    @slack-${local.notification_channels.slack_urgent.name}
  EOT
  query   = "avg(last_5m):avg:rabbitmq.queue.messages{queue:document-processing} > ${local.slos.queue_depth.threshold} OR avg(last_5m):avg:rabbitmq.queue.messages{queue:data-extraction} > ${local.slos.queue_depth.threshold} OR avg(last_5m):avg:rabbitmq.queue.messages{queue:notification} > ${local.slos.queue_depth.threshold}"
  
  thresholds = {
    critical = local.slos.queue_depth.threshold
    warning  = local.slos.queue_depth.warning_threshold
  }
  
  notify_no_data    = false
  evaluation_delay  = 60
  include_tags      = true
  priority          = local.severity_levels[local.slos.queue_depth.critical_severity].datadog_priority
  
  tags = [
    "service:rabbitmq",
    "metric:queue_depth",
    "severity:${local.slos.queue_depth.critical_severity}",
    "owner:operations",
    "environment:${var.environment}"
  ]
}

# Datadog Monitors for API Response Time
resource "datadog_monitor" "api_response_time" {
  count   = var.monitoring_type == "datadog" ? 1 : 0
  name    = "[P${local.severity_levels[local.slos.api_response_time.critical_severity].datadog_priority}] API Response Time Exceeded"
  type    = "metric alert"
  message = <<-EOT
    ${local.slos.api_response_time.description} has exceeded the threshold of ${local.slos.api_response_time.threshold}ms.
    
    This is a ${local.severity_levels[local.slos.api_response_time.critical_severity].description} alert with ${local.severity_levels[local.slos.api_response_time.critical_severity].response_time} response time required.
    
    ## Impact
    - API responses are slower than expected
    - This may affect user experience and frontend performance
    - May indicate backend service issues
    
    ## Troubleshooting
    1. Check API gateway logs for errors
    2. Verify backend service response times
    3. Examine database query performance
    4. Check for network latency issues
    5. Verify if there's a sudden increase in API traffic
    
    @pagerduty-${local.notification_channels.pagerduty.name}
    @slack-${local.notification_channels.slack_urgent.name}
  EOT
  query   = "avg(last_5m):avg:kong.latency.request{*} > ${local.slos.api_response_time.threshold}"
  
  thresholds = {
    critical = local.slos.api_response_time.threshold
    warning  = local.slos.api_response_time.warning_threshold
  }
  
  notify_no_data    = false
  evaluation_delay  = 30
  include_tags      = true
  priority          = local.severity_levels[local.slos.api_response_time.critical_severity].datadog_priority
  
  tags = [
    "service:api-gateway",
    "metric:response_time",
    "severity:${local.slos.api_response_time.critical_severity}",
    "owner:backend",
    "environment:${var.environment}"
  ]
}

# Datadog Monitors for Automation Rate
resource "datadog_monitor" "automation_rate" {
  count   = var.monitoring_type == "datadog" ? 1 : 0
  name    = "[P${local.severity_levels[local.slos.automation_rate.critical_severity].datadog_priority}] Application Automation Rate Below Threshold"
  type    = "metric alert"
  message = <<-EOT
    ${local.slos.automation_rate.description} has fallen below the threshold of ${local.slos.automation_rate.threshold}%.
    
    This is a ${local.severity_levels[local.slos.automation_rate.critical_severity].description} alert with ${local.severity_levels[local.slos.automation_rate.critical_severity].response_time} response time required.
    
    ## Impact
    - More manual intervention is required than expected
    - This may affect operational efficiency
    - May indicate issues with automation components
    
    ## Troubleshooting
    1. Check document classification accuracy
    2. Verify OCR extraction performance
    3. Examine data validation rules
    4. Check for new document types or formats
    5. Verify if there are changes in incoming application formats
    
    @slack-${local.notification_channels.slack_urgent.name}
    @slack-${local.notification_channels.slack_general.name}
  EOT
  query   = "avg(last_1h):avg:mca.application.automation_rate{*} < ${local.slos.automation_rate.threshold}"
  
  thresholds = {
    critical = local.slos.automation_rate.threshold
    warning  = local.slos.automation_rate.warning_threshold
  }
  
  notify_no_data    = true
  no_data_timeframe = 60
  evaluation_delay  = 300
  include_tags      = true
  priority          = local.severity_levels[local.slos.automation_rate.critical_severity].datadog_priority
  
  tags = [
    "service:mca",
    "metric:automation_rate",
    "severity:${local.slos.automation_rate.critical_severity}",
    "owner:operations",
    "environment:${var.environment}"
  ]
}

# Datadog Monitors for System Uptime
resource "datadog_monitor" "system_uptime" {
  count   = var.monitoring_type == "datadog" ? 1 : 0
  name    = "[P${local.severity_levels[local.slos.system_uptime.critical_severity].datadog_priority}] System Uptime Below Threshold"
  type    = "service check"
  message = <<-EOT
    ${local.slos.system_uptime.description} has fallen below the threshold of ${local.slos.system_uptime.threshold}%.
    
    This is a ${local.severity_levels[local.slos.system_uptime.critical_severity].description} alert with ${local.severity_levels[local.slos.system_uptime.critical_severity].response_time} response time required.
    
    ## Impact
    - System availability is below the required SLA
    - This affects all users and business operations
    - Immediate action is required
    
    ## Troubleshooting
    1. Check service status in Kubernetes
    2. Verify infrastructure health
    3. Examine application logs for errors
    4. Check for recent deployments or changes
    5. Verify external dependencies
    
    @pagerduty-${local.notification_channels.pagerduty.name}
    @slack-${local.notification_channels.slack_urgent.name}
  EOT
  query   = """"check("datadog.agent.up").by("host").last(5).count_by_status()"""
  
  thresholds = {
    critical = 1 # Number of failing hosts
    warning  = 1
    ok       = 0
  }
  
  notify_no_data    = true
  no_data_timeframe = 10
  new_host_delay    = 300
  include_tags      = true
  priority          = local.severity_levels[local.slos.system_uptime.critical_severity].datadog_priority
  
  tags = [
    "service:infrastructure",
    "metric:uptime",
    "severity:${local.slos.system_uptime.critical_severity}",
    "owner:devops",
    "environment:${var.environment}"
  ]
}

# Prometheus Alerting Rules (when Prometheus/Grafana is selected)
resource "kubernetes_config_map" "prometheus_alerts" {
  count = var.monitoring_type == "prometheus" ? 1 : 0
  
  metadata {
    name      = "mca-prometheus-alerts"
    namespace = var.monitoring_namespace
    labels = {
      "app.kubernetes.io/name"       = "prometheus"
      "app.kubernetes.io/component"  = "alerting-rules"
      "app.kubernetes.io/part-of"    = "mca"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  
  data = {
    "mca-alerts.yaml" = <<-EOT
      groups:
      - name: mca-sla-alerts
        rules:
        # Application Processing Time Alert
        - alert: ApplicationProcessingTimeExceeded
          expr: avg_over_time(mca_application_processing_time_seconds[5m]) > ${local.slos.application_processing_time.threshold}
          for: 5m
          labels:
            severity: ${local.slos.application_processing_time.critical_severity}
            service: mca
            metric: processing_time
            owner: operations
            environment: ${var.environment}
          annotations:
            summary: "Application Processing Time Exceeded"
            description: "Application Processing Time has exceeded the threshold of ${local.slos.application_processing_time.threshold} seconds."
            impact: "Applications are taking longer than the SLA to process. This may affect customer satisfaction and business operations."
            troubleshooting: "1. Check the email service for bottlenecks. 2. Verify document classification service performance. 3. Examine OCR service processing times. 4. Check data service response times. 5. Verify message queue health."
            response_time: "${local.severity_levels[local.slos.application_processing_time.critical_severity].response_time}"
            dashboard: "${var.grafana_url}/d/mca-application-processing/mca-application-processing"
            runbook: "${var.runbook_url}/application-processing-time"
        
        # OCR Accuracy Alert
        - alert: OCRAccuracyBelowThreshold
          expr: avg_over_time(mca_ocr_accuracy_percent[15m]) < ${local.slos.ocr_accuracy.threshold}
          for: 15m
          labels:
            severity: ${local.slos.ocr_accuracy.critical_severity}
            service: ocr
            metric: accuracy
            owner: data-science
            environment: ${var.environment}
          annotations:
            summary: "OCR Data Extraction Accuracy Below Threshold"
            description: "OCR Data Extraction Accuracy has fallen below the threshold of ${local.slos.ocr_accuracy.threshold}%."
            impact: "Data extraction accuracy is below the required SLA. This may lead to incorrect data in applications. Manual verification may be required."
            troubleshooting: "1. Check OCR service logs for errors. 2. Verify document quality in recent submissions. 3. Check for OCR model issues. 4. Examine recent model training data. 5. Verify if there are new document types causing issues."
            response_time: "${local.severity_levels[local.slos.ocr_accuracy.critical_severity].response_time}"
            dashboard: "${var.grafana_url}/d/mca-ocr-performance/mca-ocr-performance"
            runbook: "${var.runbook_url}/ocr-accuracy"
        
        # Queue Depth Alert
        - alert: MessageQueueDepthExceeded
          expr: rabbitmq_queue_messages{queue=~"document-processing|data-extraction|notification"} > ${local.slos.queue_depth.threshold}
          for: 5m
          labels:
            severity: ${local.slos.queue_depth.critical_severity}
            service: rabbitmq
            metric: queue_depth
            owner: operations
            environment: ${var.environment}
          annotations:
            summary: "Message Queue Depth Exceeded"
            description: "Message Queue Depth has exceeded the threshold of ${local.slos.queue_depth.threshold} messages."
            impact: "Message processing is falling behind. This may lead to delayed application processing. System may become overloaded if not addressed."
            troubleshooting: "1. Check consumer service logs for errors. 2. Verify consumer service scaling. 3. Examine message processing times. 4. Check for stuck messages. 5. Verify if there's a sudden increase in incoming messages."
            response_time: "${local.severity_levels[local.slos.queue_depth.critical_severity].response_time}"
            dashboard: "${var.grafana_url}/d/rabbitmq-overview/rabbitmq-overview"
            runbook: "${var.runbook_url}/queue-depth"
        
        # API Response Time Alert
        - alert: APIResponseTimeExceeded
          expr: avg_over_time(kong_latency_request_seconds[5m]) > ${local.slos.api_response_time.threshold / 1000}
          for: 5m
          labels:
            severity: ${local.slos.api_response_time.critical_severity}
            service: api-gateway
            metric: response_time
            owner: backend
            environment: ${var.environment}
          annotations:
            summary: "API Response Time Exceeded"
            description: "API Response Time has exceeded the threshold of ${local.slos.api_response_time.threshold}ms."
            impact: "API responses are slower than expected. This may affect user experience and frontend performance. May indicate backend service issues."
            troubleshooting: "1. Check API gateway logs for errors. 2. Verify backend service response times. 3. Examine database query performance. 4. Check for network latency issues. 5. Verify if there's a sudden increase in API traffic."
            response_time: "${local.severity_levels[local.slos.api_response_time.critical_severity].response_time}"
            dashboard: "${var.grafana_url}/d/kong-overview/kong-overview"
            runbook: "${var.runbook_url}/api-response-time"
        
        # Automation Rate Alert
        - alert: AutomationRateBelowThreshold
          expr: avg_over_time(mca_application_automation_rate_percent[1h]) < ${local.slos.automation_rate.threshold}
          for: 1h
          labels:
            severity: ${local.slos.automation_rate.critical_severity}
            service: mca
            metric: automation_rate
            owner: operations
            environment: ${var.environment}
          annotations:
            summary: "Application Automation Rate Below Threshold"
            description: "Application Automation Rate has fallen below the threshold of ${local.slos.automation_rate.threshold}%."
            impact: "More manual intervention is required than expected. This may affect operational efficiency. May indicate issues with automation components."
            troubleshooting: "1. Check document classification accuracy. 2. Verify OCR extraction performance. 3. Examine data validation rules. 4. Check for new document types or formats. 5. Verify if there are changes in incoming application formats."
            response_time: "${local.severity_levels[local.slos.automation_rate.critical_severity].response_time}"
            dashboard: "${var.grafana_url}/d/mca-automation/mca-automation"
            runbook: "${var.runbook_url}/automation-rate"
        
        # System Uptime Alert
        - alert: SystemUptimeBelowThreshold
          expr: up{job="kubernetes-nodes"} == 0
          for: 5m
          labels:
            severity: ${local.slos.system_uptime.critical_severity}
            service: infrastructure
            metric: uptime
            owner: devops
            environment: ${var.environment}
          annotations:
            summary: "System Uptime Below Threshold"
            description: "System Uptime has fallen below the threshold of ${local.slos.system_uptime.threshold}%."
            impact: "System availability is below the required SLA. This affects all users and business operations. Immediate action is required."
            troubleshooting: "1. Check service status in Kubernetes. 2. Verify infrastructure health. 3. Examine application logs for errors. 4. Check for recent deployments or changes. 5. Verify external dependencies."
            response_time: "${local.severity_levels[local.slos.system_uptime.critical_severity].response_time}"
            dashboard: "${var.grafana_url}/d/node-exporter/node-exporter"
            runbook: "${var.runbook_url}/system-uptime"
    EOT
  }
}

# PagerDuty Integration for Prometheus Alertmanager
resource "kubernetes_secret" "alertmanager_pagerduty" {
  count = var.monitoring_type == "prometheus" && var.pagerduty_integration_key != "" ? 1 : 0
  
  metadata {
    name      = "alertmanager-pagerduty"
    namespace = var.monitoring_namespace
  }
  
  data = {
    "pagerduty_api_key" = var.pagerduty_integration_key
  }
}

# Prometheus Alertmanager Configuration
resource "kubernetes_config_map" "alertmanager_config" {
  count = var.monitoring_type == "prometheus" ? 1 : 0
  
  metadata {
    name      = "alertmanager-config"
    namespace = var.monitoring_namespace
    labels = {
      "app.kubernetes.io/name"       = "alertmanager"
      "app.kubernetes.io/component"  = "config"
      "app.kubernetes.io/part-of"    = "mca"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  
  data = {
    "alertmanager.yaml" = <<-EOT
      global:
        resolve_timeout: 5m
        ${var.pagerduty_integration_key != "" ? "pagerduty_url: https://events.pagerduty.com/v2/enqueue" : ""}
        ${var.slack_webhook_url != "" ? "slack_api_url: ${var.slack_webhook_url}" : ""}
        ${var.smtp_smarthost != "" ? "smtp_smarthost: ${var.smtp_smarthost}" : ""}
        ${var.smtp_from != "" ? "smtp_from: ${var.smtp_from}" : ""}
        ${var.smtp_auth_username != "" ? "smtp_auth_username: ${var.smtp_auth_username}" : ""}
        ${var.smtp_auth_password != "" ? "smtp_auth_password: ${var.smtp_auth_password}" : ""}
      
      route:
        group_by: ['alertname', 'severity']
        group_wait: 30s
        group_interval: 5m
        repeat_interval: 4h
        receiver: 'default'
        routes:
        - match:
            severity: p1_critical
          receiver: 'pagerduty'
          continue: true
        - match:
            severity: p2_high
          receiver: 'slack-urgent'
          continue: true
        - match:
            severity: p3_medium
          receiver: 'slack-general'
          continue: true
        - match:
            severity: p4_low
          receiver: 'email'
      
      receivers:
      - name: 'default'
        ${var.slack_webhook_url != "" ? "slack_configs:
        - channel: '#alerts-general'
          send_resolved: true
          title: '[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .CommonLabels.alertname }}'
          text: >-
            {{ range .Alerts }}
            *Alert:* {{ .Annotations.summary }}
            *Description:* {{ .Annotations.description }}
            *Severity:* {{ .Labels.severity }}
            *Response Time:* {{ .Annotations.response_time }}
            *Impact:* {{ .Annotations.impact }}
            *Troubleshooting:* {{ .Annotations.troubleshooting }}
            *Dashboard:* {{ .Annotations.dashboard }}
            *Runbook:* {{ .Annotations.runbook }}
            {{ end }}
        " : ""}
      
      - name: 'pagerduty'
        ${var.pagerduty_integration_key != "" ? "pagerduty_configs:
        - service_key: ${var.pagerduty_integration_key}
          send_resolved: true
          description: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
          details:
            summary: '{{ .CommonAnnotations.summary }}'
            description: '{{ .CommonAnnotations.description }}'
            impact: '{{ .CommonAnnotations.impact }}'
            troubleshooting: '{{ .CommonAnnotations.troubleshooting }}'
            response_time: '{{ .CommonAnnotations.response_time }}'
            dashboard: '{{ .CommonAnnotations.dashboard }}'
            runbook: '{{ .CommonAnnotations.runbook }}'
        " : ""}
      
      - name: 'slack-urgent'
        ${var.slack_webhook_url != "" ? "slack_configs:
        - channel: '#alerts-urgent'
          send_resolved: true
          title: '[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .CommonLabels.alertname }}'
          text: >-
            {{ range .Alerts }}
            *Alert:* {{ .Annotations.summary }}
            *Description:* {{ .Annotations.description }}
            *Severity:* {{ .Labels.severity }}
            *Response Time:* {{ .Annotations.response_time }}
            *Impact:* {{ .Annotations.impact }}
            *Troubleshooting:* {{ .Annotations.troubleshooting }}
            *Dashboard:* {{ .Annotations.dashboard }}
            *Runbook:* {{ .Annotations.runbook }}
            {{ end }}
        " : ""}
      
      - name: 'slack-general'
        ${var.slack_webhook_url != "" ? "slack_configs:
        - channel: '#alerts-general'
          send_resolved: true
          title: '[{{ .Status | toUpper }}{{ if eq .Status "firing" }}:{{ .Alerts.Firing | len }}{{ end }}] {{ .CommonLabels.alertname }}'
          text: >-
            {{ range .Alerts }}
            *Alert:* {{ .Annotations.summary }}
            *Description:* {{ .Annotations.description }}
            *Severity:* {{ .Labels.severity }}
            *Response Time:* {{ .Annotations.response_time }}
            *Impact:* {{ .Annotations.impact }}
            *Troubleshooting:* {{ .Annotations.troubleshooting }}
            *Dashboard:* {{ .Annotations.dashboard }}
            *Runbook:* {{ .Annotations.runbook }}
            {{ end }}
        " : ""}
      
      - name: 'email'
        ${var.smtp_smarthost != "" ? "email_configs:
        - to: '${var.alert_email_to}'
          send_resolved: true
          headers:
            subject: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
          html: |
            <h2>{{ .CommonLabels.alertname }}</h2>
            <p><strong>Status:</strong> {{ .Status | toUpper }}</p>
            <p><strong>Severity:</strong> {{ .CommonLabels.severity }}</p>
            <p><strong>Description:</strong> {{ .CommonAnnotations.description }}</p>
            <p><strong>Impact:</strong> {{ .CommonAnnotations.impact }}</p>
            <p><strong>Response Time:</strong> {{ .CommonAnnotations.response_time }}</p>
            <p><strong>Troubleshooting:</strong> {{ .CommonAnnotations.troubleshooting }}</p>
            <p><strong>Dashboard:</strong> <a href='{{ .CommonAnnotations.dashboard }}'>{{ .CommonAnnotations.dashboard }}</a></p>
            <p><strong>Runbook:</strong> <a href='{{ .CommonAnnotations.runbook }}'>{{ .CommonAnnotations.runbook }}</a></p>
        " : ""}
    EOT
  }
}