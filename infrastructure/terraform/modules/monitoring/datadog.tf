# Datadog Terraform configuration for MCA Application
# This file configures Datadog monitoring resources including:
# - Datadog provider configuration
# - Kubernetes integration
# - APM and log collection
# - Integrations with PostgreSQL, RabbitMQ, Redis, and S3
# - Monitors for application metrics

# Configure the Datadog provider
provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
  api_url = "https://api.${var.datadog_site}"
}

# Only create Datadog resources if monitoring_type is set to "datadog"
locals {
  create_datadog = var.monitoring_type == "datadog" ? 1 : 0
  env_tag        = "env:${var.environment}"
  service_tags   = [
    local.env_tag,
    "cluster:${var.cluster_name}",
    "managed-by:terraform"
  ]
}

# Datadog-Kubernetes integration
resource "kubernetes_namespace" "datadog" {
  count = local.create_datadog

  metadata {
    name = "datadog"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

# Datadog API key secret
resource "kubernetes_secret" "datadog_api_key" {
  count = local.create_datadog

  metadata {
    name      = "datadog-api-key"
    namespace = kubernetes_namespace.datadog[0].metadata[0].name
  }

  data = {
    api-key = var.datadog_api_key
    app-key = var.datadog_app_key
  }
}

# Datadog Helm release
resource "helm_release" "datadog" {
  count = local.create_datadog

  name       = "datadog"
  repository = "https://helm.datadoghq.com"
  chart      = "datadog"
  version    = var.datadog_agent_version
  namespace  = kubernetes_namespace.datadog[0].metadata[0].name

  set {
    name  = "datadog.apiKey"
    value = var.datadog_api_key
  }

  set {
    name  = "datadog.appKey"
    value = var.datadog_app_key
  }

  set {
    name  = "datadog.site"
    value = var.datadog_site
  }

  set {
    name  = "datadog.clusterName"
    value = var.cluster_name
  }

  set {
    name  = "datadog.tags"
    value = "{${join(",", local.service_tags)}}"
  }

  # Enable APM (Application Performance Monitoring)
  set {
    name  = "datadog.apm.enabled"
    value = var.datadog_apm_enabled
  }

  # Configure APM to use socket or hostPort
  set {
    name  = "datadog.apm.socketEnabled"
    value = true
  }

  # Enable logs collection
  set {
    name  = "datadog.logs.enabled"
    value = var.datadog_logs_enabled
  }

  set {
    name  = "datadog.logs.containerCollectAll"
    value = true
  }

  # Enable process collection
  set {
    name  = "datadog.processAgent.enabled"
    value = var.datadog_process_collection_enabled
  }

  # Enable Kubernetes event collection
  set {
    name  = "datadog.leaderElection"
    value = true
  }

  set {
    name  = "datadog.collectEvents"
    value = true
  }

  # Enable Kubernetes state metrics
  set {
    name  = "datadog.kubeStateMetricsEnabled"
    value = true
  }

  # Enable cluster checks
  set {
    name  = "clusterAgent.enabled"
    value = true
  }

  set {
    name  = "clusterAgent.metricsProvider.enabled"
    value = true
  }

  # Configure cluster agent for APM
  set {
    name  = "clusterAgent.admissionController.enabled"
    value = true
  }

  set {
    name  = "clusterAgent.admissionController.mutateUnlabelled"
    value = true
  }

  # Configure security context
  set {
    name  = "agents.podSecurity.securityContext.runAsUser"
    value = 0
  }

  # Configure resources for agents
  set {
    name  = "agents.containers.agent.resources.limits.cpu"
    value = "200m"
  }

  set {
    name  = "agents.containers.agent.resources.limits.memory"
    value = "512Mi"
  }

  set {
    name  = "agents.containers.agent.resources.requests.cpu"
    value = "100m"
  }

  set {
    name  = "agents.containers.agent.resources.requests.memory"
    value = "256Mi"
  }
}

# Create Datadog integrations for PostgreSQL, RabbitMQ, Redis, and S3

# AWS data source for account ID
data "aws_caller_identity" "current" {}

# S3 log collection integration
resource "datadog_integration_aws_log_collection" "s3_logs" {
  count = local.create_datadog
  
  account_id = data.aws_caller_identity.current.account_id
  services   = ["s3"]
}

resource "datadog_integration_postgres" "postgres" {
  count = local.create_datadog
  
  name     = "mca-postgres"
  host     = var.postgres_host
  port     = var.postgres_port
  username = var.postgres_exporter_user
  password = var.postgres_exporter_password
  
  tags = local.service_tags
}

# RabbitMQ integration
resource "datadog_integration_rabbitmq" "rabbitmq" {
  count = local.create_datadog
  
  url      = var.rabbitmq_url
  username = var.rabbitmq_exporter_user
  password = var.rabbitmq_exporter_password
  
  tags = local.service_tags
}

# Create monitors for application metrics

# Monitor for application processing time
resource "datadog_monitor" "application_processing_time" {
  count = local.create_datadog
  
  name               = "[MCA] Application Processing Time Above SLA"
  type               = "metric alert"
  message            = "Application processing time is above the SLA threshold of 5 minutes. Please investigate. @pagerduty-mca-team"
  escalation_message = "Application processing time is still above SLA! Please escalate! @pagerduty-mca-escalation"
  
  query = "avg(last_5m):avg:mca.application.processing_time{${local.env_tag}} by {service} > 300"
  
  monitor_thresholds {
    critical = 300 # 5 minutes in seconds
    warning  = 240 # 4 minutes in seconds
  }
  
  notify_no_data    = false
  renotify_interval = 30
  
  tags = concat(local.service_tags, ["monitor:processing_time", "sla:processing_time"])

  # Set priority based on environment
  priority = var.environment == "production" ? 1 : 3
}

# Monitor for OCR accuracy
resource "datadog_monitor" "ocr_accuracy" {
  count = local.create_datadog
  
  name               = "[MCA] OCR Accuracy Below Threshold"
  type               = "metric alert"
  message            = "OCR accuracy has dropped below the required 99% threshold. Please investigate. @pagerduty-mca-team"
  escalation_message = "OCR accuracy is still below threshold! Please escalate! @pagerduty-mca-escalation"
  
  query = "avg(last_5m):avg:mca.ocr.accuracy{${local.env_tag}} < 99"
  
  monitor_thresholds {
    critical = 99.0
    warning  = 99.5
  }
  
  notify_no_data    = true
  renotify_interval = 60
  
  tags = concat(local.service_tags, ["monitor:ocr_accuracy", "sla:ocr_accuracy"])

  # Set priority based on environment
  priority = var.environment == "production" ? 1 : 3
}

# Monitor for queue depth
resource "datadog_monitor" "queue_depth" {
  count = local.create_datadog
  
  name               = "[MCA] Message Queue Depth Too High"
  type               = "metric alert"
  message            = "Message queue depth is too high, indicating potential processing backlog. Please investigate. @pagerduty-mca-team"
  escalation_message = "Message queue depth is still too high! Please escalate! @pagerduty-mca-escalation"
  
  query = "avg(last_5m):avg:rabbitmq.queue.messages{${local.env_tag},queue:document-processing} > 1000"
  
  monitor_thresholds {
    critical = 1000
    warning  = 500
  }
  
  notify_no_data    = false
  renotify_interval = 30
  
  tags = concat(local.service_tags, ["monitor:queue_depth", "service:rabbitmq"])

  # Set priority based on environment
  priority = var.environment == "production" ? 2 : 3
}

# Monitor for API response time
resource "datadog_monitor" "api_response_time" {
  count = local.create_datadog
  
  name               = "[MCA] API Response Time Too High"
  type               = "metric alert"
  message            = "API response time is too high, affecting user experience. Please investigate. @pagerduty-mca-team"
  escalation_message = "API response time is still too high! Please escalate! @pagerduty-mca-escalation"
  
  query = "avg(last_5m):avg:kong.latency.request{${local.env_tag}} by {service} > 500"
  
  monitor_thresholds {
    critical = 500 # 500ms
    warning  = 300 # 300ms
  }
  
  notify_no_data    = false
  renotify_interval = 30
  
  tags = concat(local.service_tags, ["monitor:api_response_time", "service:kong"])

  # Set priority based on environment
  priority = var.environment == "production" ? 2 : 3
}

# Create Datadog dashboards

# Main MCA Application Dashboard
resource "datadog_dashboard" "mca_application" {
  count = local.create_datadog
  
  title        = "MCA Application Overview"
  description  = "Overview of the Merchant Cash Advance application performance and health"
  layout_type  = "ordered"
  is_read_only = false
  notify_list  = []
  reflow_type  = "fixed"
  
  widget {
    group_definition {
      title       = "Application Processing Metrics"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Application Processing Time"
          request {
            q            = "avg:mca.application.processing_time{${local.env_tag}} by {service}"
            display_type = "line"
          }
          yaxis {
            max = "600" # 10 minutes
          }
          marker {
            display_type = "error dashed"
            value        = "300" # 5 minutes SLA
            label        = "SLA Threshold"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Applications Processed"
          request {
            q            = "sum:mca.application.processed{${local.env_tag}} by {status}.as_count()"
            display_type = "bars"
          }
        }
      }
      
      widget {
        toplist_definition {
          title = "Slowest Application Types"
          request {
            q = "top(avg:mca.application.processing_time{${local.env_tag}} by {application_type}, 10, 'mean', 'desc')"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "OCR Performance"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "OCR Accuracy"
          request {
            q            = "avg:mca.ocr.accuracy{${local.env_tag}}"
            display_type = "line"
          }
          yaxis {
            min = "95"
            max = "100"
          }
          marker {
            display_type = "error dashed"
            value        = "99"
            label        = "Minimum Accuracy"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "OCR Processing Time"
          request {
            q            = "avg:mca.ocr.processing_time{${local.env_tag}} by {document_type}"
            display_type = "line"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "Queue Metrics"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "Queue Depth"
          request {
            q            = "avg:rabbitmq.queue.messages{${local.env_tag}} by {queue}"
            display_type = "line"
          }
          marker {
            display_type = "warning dashed"
            value        = "500"
            label        = "Warning Threshold"
          }
          marker {
            display_type = "error dashed"
            value        = "1000"
            label        = "Critical Threshold"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "Message Processing Rate"
          request {
            q            = "avg:rabbitmq.queue.messages.publish_rate{${local.env_tag}} by {queue}"
            display_type = "line"
          }
        }
      }
    }
  }
  
  widget {
    group_definition {
      title       = "API Performance"
      layout_type = "ordered"
      
      widget {
        timeseries_definition {
          title = "API Response Time"
          request {
            q            = "avg:kong.latency.request{${local.env_tag}} by {service}"
            display_type = "line"
          }
          marker {
            display_type = "warning dashed"
            value        = "300"
            label        = "Warning Threshold"
          }
          marker {
            display_type = "error dashed"
            value        = "500"
            label        = "Critical Threshold"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "API Request Rate"
          request {
            q            = "sum:kong.request.count{${local.env_tag}} by {service}.as_rate()"
            display_type = "line"
          }
        }
      }
      
      widget {
        timeseries_definition {
          title = "API Error Rate"
          request {
            q            = "sum:kong.request.status.count{${local.env_tag},status:5xx} by {service}.as_rate() / sum:kong.request.count{${local.env_tag}} by {service}.as_rate() * 100"
            display_type = "line"
          }
        }
      }
    }
  }
  
  template_variable {
    name    = "env"
    prefix  = "env"
    default = var.environment
  }
  
  template_variable {
    name    = "service"
    prefix  = "service"
    default = "*"
  }
  
  tags = local.service_tags
}

# Create SLO (Service Level Objective) for application processing time
resource "datadog_service_level_objective" "application_processing_time_slo" {
  count = local.create_datadog
  
  name        = "MCA Application Processing Time SLO"
  type        = "metric"
  description = "SLO tracking the percentage of applications processed within the 5-minute SLA"
  
  thresholds {
    timeframe = "7d"
    target    = 93.0 # 93% of applications should be processed within SLA
    warning   = 95.0
  }
  
  thresholds {
    timeframe = "30d"
    target    = 93.0
    warning   = 95.0
  }
  
  query {
    numerator   = "sum:mca.application.processed{${local.env_tag},processing_time:<300} by {service}.as_count()"
    denominator = "sum:mca.application.processed{${local.env_tag}} by {service}.as_count()"
  }
  
  tags = local.service_tags
}

# Create SLO for OCR accuracy
resource "datadog_service_level_objective" "ocr_accuracy_slo" {
  count = local.create_datadog
  
  name        = "MCA OCR Accuracy SLO"
  type        = "metric"
  description = "SLO tracking the percentage of time OCR accuracy is above the 99% threshold"
  
  thresholds {
    timeframe = "7d"
    target    = 99.0 # OCR accuracy should be above 99% threshold 99% of the time
    warning   = 99.5
  }
  
  thresholds {
    timeframe = "30d"
    target    = 99.0
    warning   = 99.5
  }
  
  query {
    numerator   = "sum:mca.ocr.documents{${local.env_tag},accuracy:>=99} by {service}.as_count()"
    denominator = "sum:mca.ocr.documents{${local.env_tag}} by {service}.as_count()"
  }
  
  tags = local.service_tags
}

# Create SLO for API availability
resource "datadog_service_level_objective" "api_availability_slo" {
  count = local.create_datadog
  
  name        = "MCA API Availability SLO"
  type        = "metric"
  description = "SLO tracking the percentage of successful API requests (non-5xx responses)"
  
  thresholds {
    timeframe = "7d"
    target    = 99.9 # 99.9% of API requests should be successful
    warning   = 99.95
  }
  
  thresholds {
    timeframe = "30d"
    target    = 99.9
    warning   = 99.95
  }
  
  query {
    numerator   = "sum:kong.request.count{${local.env_tag}} by {service}.as_count() - sum:kong.request.status.count{${local.env_tag},status:5xx} by {service}.as_count()"
    denominator = "sum:kong.request.count{${local.env_tag}} by {service}.as_count()"
  }
  
  tags = local.service_tags
}