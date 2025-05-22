# infrastructure/terraform/modules/monitoring/prometheus.tf

# This file contains Prometheus and Grafana resources and configurations
# It is used when monitoring_type is set to "prometheus"

# Deploy Prometheus using Helm chart
resource "helm_release" "prometheus" {
  count = local.use_prometheus ? 1 : 0
  
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "45.0.0"
  namespace  = var.kubernetes_namespace
  
  create_namespace = true
  
  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "${var.prometheus_retention_days}d"
  }
  
  set {
    name  = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName"
    value = var.storage_class_name
  }
  
  set {
    name  = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage"
    value = var.prometheus_storage_size
  }
  
  set {
    name  = "grafana.persistence.enabled"
    value = "true"
  }
  
  set {
    name  = "grafana.persistence.storageClassName"
    value = var.storage_class_name
  }
  
  set {
    name  = "grafana.persistence.size"
    value = var.grafana_storage_size
  }
  
  set {
    name  = "grafana.adminPassword"
    value = "prom-operator" # In production, use a secret or external secret management
  }
  
  # Add common labels to all resources
  values = [
    <<-EOT
    commonLabels:
      app.kubernetes.io/managed-by: terraform
      app.kubernetes.io/part-of: ${var.project_name}
      app.kubernetes.io/environment: ${var.environment}
    EOT
  ]
}

# Deploy Loki for log aggregation
resource "helm_release" "loki" {
  count = local.use_prometheus ? 1 : 0
  
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki-stack"
  version    = "2.9.0"
  namespace  = var.kubernetes_namespace
  
  depends_on = [helm_release.prometheus]
  
  set {
    name  = "loki.persistence.enabled"
    value = "true"
  }
  
  set {
    name  = "loki.persistence.storageClassName"
    value = var.storage_class_name
  }
  
  set {
    name  = "loki.persistence.size"
    value = "10Gi"
  }
  
  set {
    name  = "promtail.enabled"
    value = "true"
  }
  
  # Add common labels to all resources
  values = [
    <<-EOT
    commonLabels:
      app.kubernetes.io/managed-by: terraform
      app.kubernetes.io/part-of: ${var.project_name}
      app.kubernetes.io/environment: ${var.environment}
    EOT
  ]
}

# Deploy Tempo for distributed tracing
resource "helm_release" "tempo" {
  count = local.use_prometheus ? 1 : 0
  
  name       = "tempo"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "tempo"
  version    = "1.0.0"
  namespace  = var.kubernetes_namespace
  
  depends_on = [helm_release.prometheus]
  
  set {
    name  = "persistence.enabled"
    value = "true"
  }
  
  set {
    name  = "persistence.storageClassName"
    value = var.storage_class_name
  }
  
  set {
    name  = "persistence.size"
    value = "10Gi"
  }
  
  # Add common labels to all resources
  values = [
    <<-EOT
    commonLabels:
      app.kubernetes.io/managed-by: terraform
      app.kubernetes.io/part-of: ${var.project_name}
      app.kubernetes.io/environment: ${var.environment}
    EOT
  ]
}

# Create ConfigMap for Prometheus alert rules
resource "kubernetes_config_map" "prometheus_alert_rules" {
  count = local.use_prometheus ? 1 : 0
  
  metadata {
    name      = "prometheus-alert-rules"
    namespace = var.kubernetes_namespace
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "app.kubernetes.io/part-of"    = var.project_name
      "app.kubernetes.io/environment" = var.environment
      "role"                        = "alert-rules"
    }
  }
  
  data = {
    "application-alerts.yaml" = <<-EOT
groups:
- name: application-alerts
  rules:
  - alert: ApplicationProcessingTimeTooHigh
    expr: avg(app_processing_time{environment="${var.environment}"}) by (service) > ${local.alert_thresholds.app_processing_time_critical}
    for: 5m
    labels:
      severity: critical
      environment: ${var.environment}
    annotations:
      summary: "Application processing time too high"
      description: "Application processing time for {{ $labels.service }} is {{ $value }} seconds, which is above the critical threshold of ${local.alert_thresholds.app_processing_time_critical} seconds."

  - alert: ApplicationProcessingTimeWarning
    expr: avg(app_processing_time{environment="${var.environment}"}) by (service) > ${local.alert_thresholds.app_processing_time_warning}
    for: 5m
    labels:
      severity: warning
      environment: ${var.environment}
    annotations:
      summary: "Application processing time warning"
      description: "Application processing time for {{ $labels.service }} is {{ $value }} seconds, which is above the warning threshold of ${local.alert_thresholds.app_processing_time_warning} seconds."

  - alert: OCRAccuracyTooLow
    expr: avg(ocr_accuracy{environment="${var.environment}"}) by (document_type) < ${local.alert_thresholds.ocr_accuracy_critical}
    for: 5m
    labels:
      severity: critical
      environment: ${var.environment}
    annotations:
      summary: "OCR accuracy too low"
      description: "OCR accuracy for {{ $labels.document_type }} is {{ $value }}%, which is below the critical threshold of ${local.alert_thresholds.ocr_accuracy_critical}%."

  - alert: OCRAccuracyWarning
    expr: avg(ocr_accuracy{environment="${var.environment}"}) by (document_type) < ${local.alert_thresholds.ocr_accuracy_warning}
    for: 5m
    labels:
      severity: warning
      environment: ${var.environment}
    annotations:
      summary: "OCR accuracy warning"
      description: "OCR accuracy for {{ $labels.document_type }} is {{ $value }}%, which is below the warning threshold of ${local.alert_thresholds.ocr_accuracy_warning}%."

  - alert: QueueDepthTooHigh
    expr: avg(rabbitmq_queue_messages{environment="${var.environment}"}) by (queue_name) > ${local.alert_thresholds.queue_depth_critical}
    for: 5m
    labels:
      severity: critical
      environment: ${var.environment}
    annotations:
      summary: "Queue depth too high"
      description: "Queue depth for {{ $labels.queue_name }} is {{ $value }} messages, which is above the critical threshold of ${local.alert_thresholds.queue_depth_critical} messages."

  - alert: QueueDepthWarning
    expr: avg(rabbitmq_queue_messages{environment="${var.environment}"}) by (queue_name) > ${local.alert_thresholds.queue_depth_warning}
    for: 5m
    labels:
      severity: warning
      environment: ${var.environment}
    annotations:
      summary: "Queue depth warning"
      description: "Queue depth for {{ $labels.queue_name }} is {{ $value }} messages, which is above the warning threshold of ${local.alert_thresholds.queue_depth_warning} messages."

  - alert: APIResponseTimeTooHigh
    expr: avg(api_response_time{environment="${var.environment}"}) by (endpoint) > ${local.alert_thresholds.api_response_time_critical}
    for: 5m
    labels:
      severity: critical
      environment: ${var.environment}
    annotations:
      summary: "API response time too high"
      description: "API response time for {{ $labels.endpoint }} is {{ $value }} ms, which is above the critical threshold of ${local.alert_thresholds.api_response_time_critical} ms."

  - alert: APIResponseTimeWarning
    expr: avg(api_response_time{environment="${var.environment}"}) by (endpoint) > ${local.alert_thresholds.api_response_time_warning}
    for: 5m
    labels:
      severity: warning
      environment: ${var.environment}
    annotations:
      summary: "API response time warning"
      description: "API response time for {{ $labels.endpoint }} is {{ $value }} ms, which is above the warning threshold of ${local.alert_thresholds.api_response_time_warning} ms."
    EOT
  }
  
  depends_on = [helm_release.prometheus]
}

# Create Grafana dashboards for application metrics
resource "kubernetes_config_map" "grafana_dashboards" {
  count = local.use_prometheus ? 1 : 0
  
  metadata {
    name      = "grafana-dashboards"
    namespace = var.kubernetes_namespace
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "app.kubernetes.io/part-of"    = var.project_name
      "app.kubernetes.io/environment" = var.environment
      "grafana_dashboard"           = "1"
    }
  }
  
  data = {
    "mca-application-dashboard.json" = <<-EOT
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "gnetId": null,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "panels": [
    {
      "collapsed": false,
      "datasource": null,
      "gridPos": {
        "h": 1,
        "w": 24,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "panels": [],
      "title": "Application Processing",
      "type": "row"
    },
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "custom": {}
        },
        "overrides": []
      },
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 1
      },
      "hiddenSeries": false,
      "id": 2,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "alertThreshold": true
      },
      "percentage": false,
      "pluginVersion": "7.3.7",
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "seriesOverrides": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "avg(app_processing_time{environment=\"${var.environment}\"}) by (service)",
          "interval": "",
          "legendFormat": "{{service}}",
          "refId": "A"
        }
      ],
      "thresholds": [
        {
          "colorMode": "critical",
          "fill": true,
          "line": true,
          "op": "gt",
          "value": ${local.alert_thresholds.app_processing_time_critical},
          "yaxis": "left"
        },
        {
          "colorMode": "warning",
          "fill": true,
          "line": true,
          "op": "gt",
          "value": ${local.alert_thresholds.app_processing_time_warning},
          "yaxis": "left"
        }
      ],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "Application Processing Time (seconds)",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "s",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": "0",
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    },
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "custom": {}
        },
        "overrides": []
      },
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 1
      },
      "hiddenSeries": false,
      "id": 3,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "alertThreshold": true
      },
      "percentage": false,
      "pluginVersion": "7.3.7",
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "seriesOverrides": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "avg(ocr_accuracy{environment=\"${var.environment}\"}) by (document_type)",
          "interval": "",
          "legendFormat": "{{document_type}}",
          "refId": "A"
        }
      ],
      "thresholds": [
        {
          "colorMode": "critical",
          "fill": true,
          "line": true,
          "op": "lt",
          "value": ${local.alert_thresholds.ocr_accuracy_critical},
          "yaxis": "left"
        },
        {
          "colorMode": "warning",
          "fill": true,
          "line": true,
          "op": "lt",
          "value": ${local.alert_thresholds.ocr_accuracy_warning},
          "yaxis": "left"
        }
      ],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "OCR Accuracy (%)",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "percent",
          "label": null,
          "logBase": 1,
          "max": "100",
          "min": "0",
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    },
    {
      "collapsed": false,
      "datasource": null,
      "gridPos": {
        "h": 1,
        "w": 24,
        "x": 0,
        "y": 9
      },
      "id": 4,
      "panels": [],
      "title": "Queue and API",
      "type": "row"
    },
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "custom": {}
        },
        "overrides": []
      },
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 10
      },
      "hiddenSeries": false,
      "id": 5,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "alertThreshold": true
      },
      "percentage": false,
      "pluginVersion": "7.3.7",
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "seriesOverrides": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "avg(rabbitmq_queue_messages{environment=\"${var.environment}\"}) by (queue_name)",
          "interval": "",
          "legendFormat": "{{queue_name}}",
          "refId": "A"
        }
      ],
      "thresholds": [
        {
          "colorMode": "critical",
          "fill": true,
          "line": true,
          "op": "gt",
          "value": ${local.alert_thresholds.queue_depth_critical},
          "yaxis": "left"
        },
        {
          "colorMode": "warning",
          "fill": true,
          "line": true,
          "op": "gt",
          "value": ${local.alert_thresholds.queue_depth_warning},
          "yaxis": "left"
        }
      ],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "Queue Depth",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": "0",
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    },
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "custom": {}
        },
        "overrides": []
      },
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 10
      },
      "hiddenSeries": false,
      "id": 6,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "alertThreshold": true
      },
      "percentage": false,
      "pluginVersion": "7.3.7",
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "seriesOverrides": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "avg(api_response_time{environment=\"${var.environment}\"}) by (endpoint)",
          "interval": "",
          "legendFormat": "{{endpoint}}",
          "refId": "A"
        }
      ],
      "thresholds": [
        {
          "colorMode": "critical",
          "fill": true,
          "line": true,
          "op": "gt",
          "value": ${local.alert_thresholds.api_response_time_critical},
          "yaxis": "left"
        },
        {
          "colorMode": "warning",
          "fill": true,
          "line": true,
          "op": "gt",
          "value": ${local.alert_thresholds.api_response_time_warning},
          "yaxis": "left"
        }
      ],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "API Response Time (ms)",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "ms",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": "0",
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    }
  ],
  "refresh": "10s",
  "schemaVersion": 26,
  "style": "dark",
  "tags": [
    "mca",
    "application",
    "${var.environment}"
  ],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-6h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "MCA Application Processing - ${title(var.environment)}",
  "uid": "mca-application-${var.environment}",
  "version": 1
}
    EOT
  }
  
  depends_on = [helm_release.prometheus]
}

# Configure AlertManager for notifications
resource "kubernetes_config_map" "alertmanager_config" {
  count = local.use_prometheus ? 1 : 0
  
  metadata {
    name      = "alertmanager-config"
    namespace = var.kubernetes_namespace
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "app.kubernetes.io/part-of"    = var.project_name
      "app.kubernetes.io/environment" = var.environment
    }
  }
  
  data = {
    "alertmanager.yaml" = <<-EOT
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/REPLACE_WITH_ACTUAL_SLACK_WEBHOOK_URL'

route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-notifications'
  routes:
  - match:
      severity: critical
    receiver: 'pagerduty-critical'
    continue: true
  - match:
      severity: warning
    receiver: 'slack-notifications'

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '${var.notification_channels.slack.value}'
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: >-
      {{ range .Alerts }}
        *Alert:* {{ .Annotations.summary }}
        *Description:* {{ .Annotations.description }}
        *Severity:* {{ .Labels.severity }}
        *Environment:* {{ .Labels.environment }}
        {{ if ne .Labels.service "" }}*Service:* {{ .Labels.service }}{{ end }}
        {{ if ne .Labels.endpoint "" }}*Endpoint:* {{ .Labels.endpoint }}{{ end }}
        {{ if ne .Labels.queue_name "" }}*Queue:* {{ .Labels.queue_name }}{{ end }}
        {{ if ne .Labels.document_type "" }}*Document Type:* {{ .Labels.document_type }}{{ end }}
      {{ end }}

- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '${var.notification_channels.pagerduty.value}'
    send_resolved: true
    description: '{{ .CommonLabels.alertname }}'
    details:
      summary: '{{ .CommonAnnotations.summary }}'
      description: '{{ .CommonAnnotations.description }}'
      environment: '{{ .CommonLabels.environment }}'
      severity: '{{ .CommonLabels.severity }}'
    EOT
  }
  
  depends_on = [helm_release.prometheus]
}

# Output URLs for Prometheus, Grafana, and Alertmanager
output "prometheus_url" {
  value = "http://prometheus-server.${var.kubernetes_namespace}.svc.cluster.local:9090"
}

output "grafana_url" {
  value = "http://grafana.${var.kubernetes_namespace}.svc.cluster.local:3000"
}

output "alertmanager_url" {
  value = "http://alertmanager.${var.kubernetes_namespace}.svc.cluster.local:9093"
}

output "loki_url" {
  value = "http://loki.${var.kubernetes_namespace}.svc.cluster.local:3100"
}

output "tempo_url" {
  value = "http://tempo.${var.kubernetes_namespace}.svc.cluster.local:3100"
}