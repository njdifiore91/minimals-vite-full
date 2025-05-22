# Dashboards.tf - Defines monitoring dashboards for both Datadog and Prometheus/Grafana
# This file creates dashboards for different stakeholders to monitor system performance,
# troubleshoot issues, and track business metrics.

# ---------------------------------------------------------------------------------------------------------------------
# TERRAFORM PROVIDERS
# ---------------------------------------------------------------------------------------------------------------------

# Datadog provider configuration
# The actual provider configuration should be in the root module
# This is just a reference to the provider that will be used
terraform {
  required_providers {
    datadog = {
      source  = "DataDog/datadog"
      version = ">= 3.20.0"
    }
    grafana = {
      source  = "grafana/grafana"
      version = ">= 2.9.0"
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# LOCAL VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

locals {
  # Common dashboard settings
  common_datadog_settings = {
    layout_type    = "ordered"
    is_read_only   = false
    notify_list    = []
    template_variable_presets = []
  }

  # Dashboard tags for organization
  dashboard_tags = [
    "service:mca-application",
    "env:${var.environment}",
    "terraform:true"
  ]

  # Time windows for widgets
  time_windows = {
    short  = "1h"
    medium = "4h"
    long   = "24h"
    week   = "1w"
  }

  # Common colors for consistency
  colors = {
    normal     = "#4CAF50"
    warning    = "#FF9800"
    critical   = "#F44336"
    info       = "#2196F3"
    background = "#424242"
  }

  # Service names for monitoring
  services = [
    "email-service",
    "document-service",
    "ocr-service",
    "data-service",
    "notification-service",
    "api-gateway"
  ]

  # Infrastructure components
  infrastructure = [
    "postgresql",
    "rabbitmq",
    "redis",
    "s3"
  ]
}

# ---------------------------------------------------------------------------------------------------------------------
# DATADOG DASHBOARDS
# ---------------------------------------------------------------------------------------------------------------------

# 1. Executive Summary Dashboard for Management
resource "datadog_dashboard" "executive_summary" {
  title       = "MCA Application - Executive Summary"
  description = "High-level overview of system health, SLA compliance, and key business metrics for management"
  layout_type = local.common_datadog_settings.layout_type
  is_read_only = local.common_datadog_settings.is_read_only
  notify_list = local.common_datadog_settings.notify_list
  
  widget {
    group_definition {
      title = "SLA Compliance"
      widget {
        note_definition {
          content = "### Service Level Objectives\nTarget: 99.9% uptime\nTarget: 93% automation rate\nTarget: 99% data extraction accuracy"
          background_color = local.colors.background
          font_size = "14"
          text_align = "center"
        }
      }
      widget {
        query_value_definition {
          title = "System Uptime (30d)"
          precision = 2
          request {
            q = "avg:system.uptime{service:mca-application} by {host}.fill(last, 30)"
            aggregator = "avg"
            conditional_formats {
              comparator = ">"
              value = 99.9
              palette = "white_on_green"
            }
            conditional_formats {
              comparator = "<="
              value = 99.9
              palette = "white_on_yellow"
            }
            conditional_formats {
              comparator = "<="
              value = 99
              palette = "white_on_red"
            }
          }
        }
      }
      widget {
        query_value_definition {
          title = "Automation Rate"
          precision = 2
          request {
            q = "avg:mca.application.automation_rate{*}"
            aggregator = "avg"
            conditional_formats {
              comparator = ">="
              value = 93
              palette = "white_on_green"
            }
            conditional_formats {
              comparator = "<"
              value = 93
              palette = "white_on_yellow"
            }
            conditional_formats {
              comparator = "<"
              value = 90
              palette = "white_on_red"
            }
          }
        }
      }
      widget {
        query_value_definition {
          title = "Data Extraction Accuracy"
          precision = 2
          request {
            q = "avg:mca.ocr.extraction_accuracy{*}"
            aggregator = "avg"
            conditional_formats {
              comparator = ">="
              value = 99
              palette = "white_on_green"
            }
            conditional_formats {
              comparator = "<"
              value = 99
              palette = "white_on_yellow"
            }
            conditional_formats {
              comparator = "<"
              value = 95
              palette = "white_on_red"
            }
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "Business KPIs"
      widget {
        timeseries_definition {
          title = "Applications Processed (Daily)"
          request {
            q = "sum:mca.application.processed{*}.as_count()"
            display_type = "bars"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Processing Time (Minutes)"
          request {
            q = "avg:mca.application.processing_time{*} by {status}"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "Minutes"
          }
        }
      }
      widget {
        query_value_definition {
          title = "Avg. Processing Time"
          precision = 2
          request {
            q = "avg:mca.application.processing_time{*}"
            aggregator = "avg"
            conditional_formats {
              comparator = "<="
              value = 5
              palette = "white_on_green"
            }
            conditional_formats {
              comparator = ">"
              value = 5
              palette = "white_on_yellow"
            }
            conditional_formats {
              comparator = ">"
              value = 10
              palette = "white_on_red"
            }
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "System Health"
      widget {
        hostmap_definition {
          title = "Host Status"
          request {
            fill {
              q = "avg:system.cpu.user{*} by {host}"
            }
          }
          node_type = "host"
          no_metric_hosts = true
          no_group_hosts = true
          style {
            palette = "green_to_orange"
            palette_flip = false
          }
        }
      }
      widget {
        alert_graph_definition {
          title = "Critical Alerts"
          alert_id = "system-generated-id" # This should be replaced with actual alert ID
          viz_type = "timeseries"
        }
      }
    }
  }

  widget {
    note_definition {
      content = "Dashboard automatically generated by Terraform. Last updated: ${timestamp()}
For support, contact: operations@dollarfunding.com"
      background_color = "transparent"
      font_size = "12"
      text_align = "center"
      show_tick = false
      tick_pos = "bottom"
      tick_edge = "bottom"
    }
  }

  tags = local.dashboard_tags
}

# 2. Service Overview Dashboard for Operations
resource "datadog_dashboard" "service_overview" {
  title       = "MCA Application - Service Overview"
  description = "Service-level monitoring for operations teams with error rates, latency, throughput, and resource utilization"
  layout_type = local.common_datadog_settings.layout_type
  is_read_only = local.common_datadog_settings.is_read_only
  notify_list = local.common_datadog_settings.notify_list

  widget {
    group_definition {
      title = "Service Health Overview"
      widget {
        servicemap_definition {
          service = "mca-application"
          filters = ["env:${var.environment}"]
          title = "Service Map"
        }
      }
    }
  }

  # Create a service health widget for each service
  dynamic "widget" {
    for_each = local.services
    content {
      group_definition {
        title = "${title(replace(widget.value, "-", " "))} Health"
        widget {
          query_value_definition {
            title = "Error Rate"
            precision = 2
            request {
              q = "sum:trace.${widget.value}.errors{env:${var.environment}}.as_count() / sum:trace.${widget.value}.hits{env:${var.environment}}.as_count() * 100"
              aggregator = "avg"
              conditional_formats {
                comparator = "<="
                value = 1
                palette = "white_on_green"
              }
              conditional_formats {
                comparator = ">"
                value = 1
                palette = "white_on_yellow"
              }
              conditional_formats {
                comparator = ">"
                value = 5
                palette = "white_on_red"
              }
            }
          }
        }
        widget {
          timeseries_definition {
            title = "Latency (p95)"
            request {
              q = "p95:trace.${widget.value}.duration{env:${var.environment}}"
              display_type = "line"
            }
            yaxis {
              min = "0"
              max = "auto"
              scale = "linear"
              include_zero = true
              label = "ms"
            }
          }
        }
        widget {
          timeseries_definition {
            title = "Throughput (req/s)"
            request {
              q = "sum:trace.${widget.value}.hits{env:${var.environment}}.as_rate()"
              display_type = "line"
            }
            yaxis {
              min = "0"
              max = "auto"
              scale = "linear"
              include_zero = true
              label = "req/s"
            }
          }
        }
      }
    }
  }

  widget {
    toplist_definition {
      title = "Top Endpoints by Latency (p95)"
      request {
        q = "top(avg:trace.http.request.duration.by.resource{env:${var.environment}} by {resource_name}, 10, 'mean', 'desc')"
      }
    }
  }

  widget {
    toplist_definition {
      title = "Top Endpoints by Error Rate"
      request {
        q = "top(sum:trace.http.errors.by.resource{env:${var.environment}}.as_count() / sum:trace.http.hits.by.resource{env:${var.environment}}.as_count() * 100 by {resource_name}, 10, 'mean', 'desc')"
      }
    }
  }

  widget {
    note_definition {
      content = "Dashboard automatically generated by Terraform. Last updated: ${timestamp()}
For support, contact: operations@dollarfunding.com"
      background_color = "transparent"
      font_size = "12"
      text_align = "center"
      show_tick = false
      tick_pos = "bottom"
      tick_edge = "bottom"
    }
  }

  tags = local.dashboard_tags
}

# 3. Infrastructure Dashboard for DevOps/SRE
resource "datadog_dashboard" "infrastructure" {
  title       = "MCA Application - Infrastructure"
  description = "Infrastructure health monitoring for DevOps/SRE teams with node status, resource usage, and network metrics"
  layout_type = local.common_datadog_settings.layout_type
  is_read_only = local.common_datadog_settings.is_read_only
  notify_list = local.common_datadog_settings.notify_list

  widget {
    group_definition {
      title = "Kubernetes Overview"
      widget {
        hostmap_definition {
          title = "Node Status"
          request {
            fill {
              q = "avg:kubernetes.cpu.usage.total{*} by {host}"
            }
          }
          node_type = "host"
          no_metric_hosts = true
          no_group_hosts = true
          style {
            palette = "green_to_orange"
            palette_flip = false
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Pod Status by Namespace"
          request {
            q = "sum:kubernetes.pods.running{*} by {kube_namespace}"
            display_type = "area"
          }
        }
      }
    }
  }

  # Create infrastructure component widgets
  dynamic "widget" {
    for_each = local.infrastructure
    content {
      group_definition {
        title = "${title(widget.value)} Metrics"
        
        # Different metrics based on infrastructure component
        dynamic "widget" {
          for_each = widget.value == "postgresql" ? [1] : []
          content {
            timeseries_definition {
              title = "Database Connections"
              request {
                q = "avg:postgresql.connections{*} by {db}"
                display_type = "line"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "postgresql" ? [1] : []
          content {
            timeseries_definition {
              title = "Query Execution Time"
              request {
                q = "avg:postgresql.query_time{*}"
                display_type = "line"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "rabbitmq" ? [1] : []
          content {
            timeseries_definition {
              title = "Queue Depth"
              request {
                q = "avg:rabbitmq.queue.messages{*} by {queue}"
                display_type = "line"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "rabbitmq" ? [1] : []
          content {
            timeseries_definition {
              title = "Message Rate"
              request {
                q = "avg:rabbitmq.queue.messages.rate{*} by {queue}"
                display_type = "line"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "redis" ? [1] : []
          content {
            timeseries_definition {
              title = "Memory Usage"
              request {
                q = "avg:redis.mem.used{*} by {redis_host}"
                display_type = "line"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "redis" ? [1] : []
          content {
            timeseries_definition {
              title = "Hit Rate"
              request {
                q = "avg:redis.stats.keyspace_hits{*} / (avg:redis.stats.keyspace_hits{*} + avg:redis.stats.keyspace_misses{*}) * 100"
                display_type = "line"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "s3" ? [1] : []
          content {
            timeseries_definition {
              title = "S3 Request Count"
              request {
                q = "sum:aws.s3.requests{*} by {bucket_name}.as_count()"
                display_type = "bars"
              }
            }
          }
        }
        
        dynamic "widget" {
          for_each = widget.value == "s3" ? [1] : []
          content {
            timeseries_definition {
              title = "S3 Error Count"
              request {
                q = "sum:aws.s3.errors{*} by {bucket_name}.as_count()"
                display_type = "bars"
              }
            }
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "Resource Utilization"
      widget {
        timeseries_definition {
          title = "CPU Usage by Service"
          request {
            q = "avg:kubernetes.cpu.usage.total{*} by {kube_service}"
            display_type = "line"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Memory Usage by Service"
          request {
            q = "avg:kubernetes.memory.usage{*} by {kube_service}"
            display_type = "line"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Network Traffic by Service"
          request {
            q = "sum:kubernetes.network.rx_bytes{*} by {kube_service}.as_rate()"
            display_type = "area"
            style = {
              palette = "cool"
              line_type = "solid"
              line_width = "normal"
            }
          }
          request {
            q = "sum:kubernetes.network.tx_bytes{*} by {kube_service}.as_rate()"
            display_type = "area"
            style = {
              palette = "warm"
              line_type = "solid"
              line_width = "normal"
            }
          }
        }
      }
    }
  }

  widget {
    note_definition {
      content = "Dashboard automatically generated by Terraform. Last updated: ${timestamp()}
For support, contact: operations@dollarfunding.com"
      background_color = "transparent"
      font_size = "12"
      text_align = "center"
      show_tick = false
      tick_pos = "bottom"
      tick_edge = "bottom"
    }
  }

  tags = local.dashboard_tags
}

# 4. Developer Dashboard for Engineering
resource "datadog_dashboard" "developer" {
  title       = "MCA Application - Developer"
  description = "Development-focused metrics for engineering teams with build health, test coverage, and deployment frequency"
  layout_type = local.common_datadog_settings.layout_type
  is_read_only = local.common_datadog_settings.is_read_only
  notify_list = local.common_datadog_settings.notify_list

  widget {
    group_definition {
      title = "CI/CD Metrics"
      widget {
        timeseries_definition {
          title = "Build Duration"
          request {
            q = "avg:ci.build.duration{*} by {service}"
            display_type = "line"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Build Success Rate"
          request {
            q = "sum:ci.build.success{*}.as_count() / sum:ci.build.total{*}.as_count() * 100"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "100"
            scale = "linear"
            include_zero = true
            label = "%"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Deployment Frequency"
          request {
            q = "sum:ci.deploy.count{*} by {service}.as_count()"
            display_type = "bars"
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "Code Quality"
      widget {
        timeseries_definition {
          title = "Test Coverage"
          request {
            q = "avg:ci.test.coverage{*} by {service}"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "100"
            scale = "linear"
            include_zero = true
            label = "%"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Code Smells"
          request {
            q = "avg:sonarqube.code_smells{*} by {service}"
            display_type = "line"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Technical Debt Ratio"
          request {
            q = "avg:sonarqube.tech_debt_ratio{*} by {service}"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "%"
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "Application Performance"
      widget {
        timeseries_definition {
          title = "Error Rate by Service"
          request {
            q = "sum:trace.errors{*} by {service}.as_count() / sum:trace.hits{*} by {service}.as_count() * 100"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "%"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Latency by Service (p95)"
          request {
            q = "p95:trace.duration{*} by {service}"
            display_type = "line"
          }
        }
      }
      widget {
        toplist_definition {
          title = "Top Slowest Endpoints"
          request {
            q = "top(avg:trace.http.request.duration.by.resource{*} by {resource_name}, 10, 'mean', 'desc')"
          }
        }
      }
    }
  }

  widget {
    note_definition {
      content = "Dashboard automatically generated by Terraform. Last updated: ${timestamp()}
For support, contact: engineering@dollarfunding.com"
      background_color = "transparent"
      font_size = "12"
      text_align = "center"
      show_tick = false
      tick_pos = "bottom"
      tick_edge = "bottom"
    }
  }

  tags = local.dashboard_tags
}

# 5. User Experience Dashboard for Product Teams
resource "datadog_dashboard" "user_experience" {
  title       = "MCA Application - User Experience"
  description = "User-centric metrics for product teams with Web Vitals, user journeys, and conversion rates"
  layout_type = local.common_datadog_settings.layout_type
  is_read_only = local.common_datadog_settings.is_read_only
  notify_list = local.common_datadog_settings.notify_list

  widget {
    group_definition {
      title = "Web Vitals"
      widget {
        timeseries_definition {
          title = "Largest Contentful Paint (LCP)"
          request {
            q = "avg:rum.performance.largest_contentful_paint{*} by {browser}"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "ms"
          }
          marker {
            display_type = "error dashed"
            value = "2500"
            label = "Poor"
          }
          marker {
            display_type = "warning dashed"
            value = "1000"
            label = "Needs Improvement"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "First Input Delay (FID)"
          request {
            q = "avg:rum.performance.first_input_delay{*} by {browser}"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "ms"
          }
          marker {
            display_type = "error dashed"
            value = "300"
            label = "Poor"
          }
          marker {
            display_type = "warning dashed"
            value = "100"
            label = "Needs Improvement"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Cumulative Layout Shift (CLS)"
          request {
            q = "avg:rum.performance.cumulative_layout_shift{*} by {browser}"
            display_type = "line"
          }
          marker {
            display_type = "error dashed"
            value = "0.25"
            label = "Poor"
          }
          marker {
            display_type = "warning dashed"
            value = "0.1"
            label = "Needs Improvement"
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "User Journeys"
      widget {
        timeseries_definition {
          title = "Application Funnel Conversion"
          request {
            q = "sum:mca.application.step.started{step:email_received}.as_count(), sum:mca.application.step.started{step:document_classified}.as_count(), sum:mca.application.step.started{step:data_extracted}.as_count(), sum:mca.application.step.started{step:application_processed}.as_count(), sum:mca.application.step.started{step:notification_sent}.as_count()"
            display_type = "bars"
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Step Completion Time"
          request {
            q = "avg:mca.application.step.duration{*} by {step}"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "seconds"
          }
        }
      }
    }
  }

  widget {
    group_definition {
      title = "User Satisfaction"
      widget {
        query_value_definition {
          title = "Apdex Score"
          precision = 2
          request {
            q = "avg:rum.performance.apdex{*}"
            aggregator = "avg"
            conditional_formats {
              comparator = ">="
              value = 0.9
              palette = "white_on_green"
            }
            conditional_formats {
              comparator = ">="
              value = 0.7
              palette = "white_on_yellow"
            }
            conditional_formats {
              comparator = "<"
              value = 0.7
              palette = "white_on_red"
            }
          }
        }
      }
      widget {
        timeseries_definition {
          title = "Error Rate by Page"
          request {
            q = "sum:rum.errors{*} by {page}.as_count() / sum:rum.page_views{*} by {page}.as_count() * 100"
            display_type = "line"
          }
          yaxis {
            min = "0"
            max = "auto"
            scale = "linear"
            include_zero = true
            label = "%"
          }
        }
      }
      widget {
        toplist_definition {
          title = "Slowest Pages"
          request {
            q = "top(avg:rum.page_load_time{*} by {page}, 10, 'mean', 'desc')"
          }
        }
      }
    }
  }

  widget {
    note_definition {
      content = "Dashboard automatically generated by Terraform. Last updated: ${timestamp()}
For support, contact: product@dollarfunding.com"
      background_color = "transparent"
      font_size = "12"
      text_align = "center"
      show_tick = false
      tick_pos = "bottom"
      tick_edge = "bottom"
    }
  }

  tags = local.dashboard_tags
}

# ---------------------------------------------------------------------------------------------------------------------
# GRAFANA DASHBOARDS
# ---------------------------------------------------------------------------------------------------------------------

# 1. Executive Summary Dashboard for Grafana
resource "grafana_dashboard" "executive_summary" {
  config_json = jsonencode({
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
        "title": "SLA Compliance",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 99
                },
                {
                  "color": "green",
                  "value": 99.9
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 0,
          "y": 1
        },
        "id": 2,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "avg(up{job=~\"mca-.*\"}) by (job)",
            "interval": "",
            "legendFormat": "",
            "refId": "A"
          }
        ],
        "title": "System Uptime",
        "type": "gauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 90
                },
                {
                  "color": "green",
                  "value": 93
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 8,
          "y": 1
        },
        "id": 3,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "mca_application_automation_rate",
            "interval": "",
            "legendFormat": "",
            "refId": "A"
          }
        ],
        "title": "Automation Rate",
        "type": "gauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 95
                },
                {
                  "color": "green",
                  "value": 99
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 16,
          "y": 1
        },
        "id": 4,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "mca_ocr_extraction_accuracy",
            "interval": "",
            "legendFormat": "",
            "refId": "A"
          }
        ],
        "title": "Data Extraction Accuracy",
        "type": "gauge"
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
        "id": 5,
        "panels": [],
        "title": "Business KPIs",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "bars",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 10
        },
        "id": 6,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(increase(mca_application_processed_total[1d]))",
            "interval": "",
            "legendFormat": "Applications Processed",
            "refId": "A"
          }
        ],
        "title": "Applications Processed (Daily)",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "Minutes",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 5
                },
                {
                  "color": "red",
                  "value": 10
                }
              ]
            },
            "unit": "m"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 10
        },
        "id": 7,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "avg(mca_application_processing_time_minutes) by (status)",
            "interval": "",
            "legendFormat": "{{status}}",
            "refId": "A"
          }
        ],
        "title": "Processing Time (Minutes)",
        "type": "timeseries"
      }
    ],
    "refresh": "5s",
    "schemaVersion": 30,
    "style": "dark",
    "tags": ["mca-application", "executive", "terraform"],
    "templating": {
      "list": []
    },
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "timepicker": {},
    "timezone": "",
    "title": "MCA Application - Executive Summary",
    "uid": "mca-exec-summary",
    "version": 1
  })

  folder = var.grafana_folder_id
}

# 2. Service Overview Dashboard for Grafana
resource "grafana_dashboard" "service_overview" {
  config_json = jsonencode({
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
        "title": "Service Health Overview",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 1
                },
                {
                  "color": "red",
                  "value": 5
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 1
        },
        "id": 2,
        "options": {
          "displayMode": "gradient",
          "orientation": "horizontal",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showUnfilled": true,
          "text": {}
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(increase(http_server_requests_errors_total[5m])) by (service) / sum(increase(http_server_requests_total[5m])) by (service)",
            "interval": "",
            "legendFormat": "{{service}}",
            "refId": "A"
          }
        ],
        "title": "Error Rate by Service",
        "type": "bargauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "ms"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 1
        },
        "id": 3,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, service))",
            "interval": "",
            "legendFormat": "{{service}}",
            "refId": "A"
          }
        ],
        "title": "Latency by Service (p95)",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "reqps"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 24,
          "x": 0,
          "y": 9
        },
        "id": 4,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(rate(http_server_requests_total[5m])) by (service)",
            "interval": "",
            "legendFormat": "{{service}}",
            "refId": "A"
          }
        ],
        "title": "Throughput by Service (req/s)",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 200
                },
                {
                  "color": "red",
                  "value": 500
                }
              ]
            },
            "unit": "ms"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 17
        },
        "id": 5,
        "options": {
          "displayMode": "gradient",
          "orientation": "horizontal",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showUnfilled": true,
          "text": {}
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "topk(10, histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, endpoint)))",
            "interval": "",
            "legendFormat": "{{endpoint}}",
            "refId": "A"
          }
        ],
        "title": "Top 10 Endpoints by Latency (p95)",
        "type": "bargauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 0.01
                },
                {
                  "color": "red",
                  "value": 0.05
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 17
        },
        "id": 6,
        "options": {
          "displayMode": "gradient",
          "orientation": "horizontal",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showUnfilled": true,
          "text": {}
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "topk(10, sum(increase(http_server_requests_errors_total[5m])) by (endpoint) / sum(increase(http_server_requests_total[5m])) by (endpoint))",
            "interval": "",
            "legendFormat": "{{endpoint}}",
            "refId": "A"
          }
        ],
        "title": "Top 10 Endpoints by Error Rate",
        "type": "bargauge"
      }
    ],
    "refresh": "5s",
    "schemaVersion": 30,
    "style": "dark",
    "tags": ["mca-application", "service", "operations", "terraform"],
    "templating": {
      "list": []
    },
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "timepicker": {},
    "timezone": "",
    "title": "MCA Application - Service Overview",
    "uid": "mca-service-overview",
    "version": 1
  })

  folder = var.grafana_folder_id
}

# 3. Infrastructure Dashboard for Grafana
resource "grafana_dashboard" "infrastructure" {
  config_json = jsonencode({
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
        "title": "Kubernetes Overview",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 0.7
                },
                {
                  "color": "red",
                  "value": 0.85
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 1
        },
        "id": 2,
        "options": {
          "displayMode": "gradient",
          "orientation": "horizontal",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showUnfilled": true,
          "text": {}
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(rate(node_cpu_seconds_total{mode!='idle'}[5m])) by (instance) / on(instance) count(node_cpu_seconds_total) by (instance)",
            "interval": "",
            "legendFormat": "{{instance}}",
            "refId": "A"
          }
        ],
        "title": "CPU Usage by Node",
        "type": "bargauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 0.7
                },
                {
                  "color": "red",
                  "value": 0.85
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 1
        },
        "id": 3,
        "options": {
          "displayMode": "gradient",
          "orientation": "horizontal",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showUnfilled": true,
          "text": {}
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes",
            "interval": "",
            "legendFormat": "{{instance}}",
            "refId": "A"
          }
        ],
        "title": "Memory Usage by Node",
        "type": "bargauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 24,
          "x": 0,
          "y": 9
        },
        "id": 4,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(kube_pod_status_phase{phase=\"Running\"}) by (namespace)",
            "interval": "",
            "legendFormat": "{{namespace}}",
            "refId": "A"
          }
        ],
        "title": "Running Pods by Namespace",
        "type": "timeseries"
      },
      {
        "collapsed": false,
        "datasource": null,
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 17
        },
        "id": 5,
        "panels": [],
        "title": "Database Metrics",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 18
        },
        "id": 6,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "pg_stat_activity_count{datname=~\"mca.*\"}",
            "interval": "",
            "legendFormat": "{{datname}}",
            "refId": "A"
          }
        ],
        "title": "PostgreSQL Connections",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "ms"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 18
        },
        "id": 7,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "rate(pg_stat_activity_max_tx_duration{datname=~\"mca.*\"}[5m])",
            "interval": "",
            "legendFormat": "{{datname}}",
            "refId": "A"
          }
        ],
        "title": "PostgreSQL Query Duration",
        "type": "timeseries"
      },
      {
        "collapsed": false,
        "datasource": null,
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 26
        },
        "id": 8,
        "panels": [],
        "title": "Message Queue Metrics",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 27
        },
        "id": 9,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "rabbitmq_queue_messages{queue=~\"mca.*\"}",
            "interval": "",
            "legendFormat": "{{queue}}",
            "refId": "A"
          }
        ],
        "title": "RabbitMQ Queue Depth",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "ops"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 27
        },
        "id": 10,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "rate(rabbitmq_queue_messages_published_total{queue=~\"mca.*\"}[5m])",
            "interval": "",
            "legendFormat": "{{queue}}",
            "refId": "A"
          }
        ],
        "title": "RabbitMQ Message Rate",
        "type": "timeseries"
      }
    ],
    "refresh": "5s",
    "schemaVersion": 30,
    "style": "dark",
    "tags": ["mca-application", "infrastructure", "devops", "terraform"],
    "templating": {
      "list": []
    },
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "timepicker": {},
    "timezone": "",
    "title": "MCA Application - Infrastructure",
    "uid": "mca-infrastructure",
    "version": 1
  })

  folder = var.grafana_folder_id
}

# 4. Developer Dashboard for Grafana
resource "grafana_dashboard" "developer" {
  config_json = jsonencode({
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
        "title": "CI/CD Metrics",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "s"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 1
        },
        "id": 2,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "ci_build_duration_seconds{job=~\"mca-.*\"}",
            "interval": "",
            "legendFormat": "{{job}}",
            "refId": "A"
          }
        ],
        "title": "Build Duration",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 80
                },
                {
                  "color": "green",
                  "value": 90
                }
              ]
            },
            "unit": "percent"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 1
        },
        "id": 3,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(ci_build_success{job=~\"mca-.*\"}) / count(ci_build_success{job=~\"mca-.*\"}) * 100",
            "interval": "",
            "legendFormat": "Success Rate",
            "refId": "A"
          }
        ],
        "title": "Build Success Rate",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "bars",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 24,
          "x": 0,
          "y": 9
        },
        "id": 4,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(increase(ci_deploy_count{job=~\"mca-.*\"}[1d])) by (job)",
            "interval": "",
            "legendFormat": "{{job}}",
            "refId": "A"
          }
        ],
        "title": "Deployment Frequency (Daily)",
        "type": "timeseries"
      },
      {
        "collapsed": false,
        "datasource": null,
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 17
        },
        "id": 5,
        "panels": [],
        "title": "Code Quality",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 70
                },
                {
                  "color": "green",
                  "value": 80
                }
              ]
            },
            "unit": "percent"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 18
        },
        "id": 6,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "code_coverage_percent{job=~\"mca-.*\"}",
            "interval": "",
            "legendFormat": "{{job}}",
            "refId": "A"
          }
        ],
        "title": "Test Coverage",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 18
        },
        "id": 7,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "code_smells_total{job=~\"mca-.*\"}",
            "interval": "",
            "legendFormat": "{{job}}",
            "refId": "A"
          }
        ],
        "title": "Code Smells",
        "type": "timeseries"
      }
    ],
    "refresh": "5s",
    "schemaVersion": 30,
    "style": "dark",
    "tags": ["mca-application", "developer", "engineering", "terraform"],
    "templating": {
      "list": []
    },
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "timepicker": {},
    "timezone": "",
    "title": "MCA Application - Developer",
    "uid": "mca-developer",
    "version": 1
  })

  folder = var.grafana_folder_id
}

# 5. User Experience Dashboard for Grafana
resource "grafana_dashboard" "user_experience" {
  config_json = jsonencode({
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
        "title": "Web Vitals",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 1000
                },
                {
                  "color": "red",
                  "value": 2500
                }
              ]
            },
            "unit": "ms"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 0,
          "y": 1
        },
        "id": 2,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "web_vitals_largest_contentful_paint_ms{app=\"mca-frontend\"}",
            "interval": "",
            "legendFormat": "LCP",
            "refId": "A"
          }
        ],
        "title": "Largest Contentful Paint (LCP)",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 100
                },
                {
                  "color": "red",
                  "value": 300
                }
              ]
            },
            "unit": "ms"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 8,
          "y": 1
        },
        "id": 3,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "web_vitals_first_input_delay_ms{app=\"mca-frontend\"}",
            "interval": "",
            "legendFormat": "FID",
            "refId": "A"
          }
        ],
        "title": "First Input Delay (FID)",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "line"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 0.1
                },
                {
                  "color": "red",
                  "value": 0.25
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 16,
          "y": 1
        },
        "id": 4,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "web_vitals_cumulative_layout_shift{app=\"mca-frontend\"}",
            "interval": "",
            "legendFormat": "CLS",
            "refId": "A"
          }
        ],
        "title": "Cumulative Layout Shift (CLS)",
        "type": "timeseries"
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
        "id": 5,
        "panels": [],
        "title": "User Journeys",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "bars",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 10
        },
        "id": 6,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(mca_application_step_started_total{step=\"email_received\"}) or vector(0), sum(mca_application_step_started_total{step=\"document_classified\"}) or vector(0), sum(mca_application_step_started_total{step=\"data_extracted\"}) or vector(0), sum(mca_application_step_started_total{step=\"application_processed\"}) or vector(0), sum(mca_application_step_started_total{step=\"notification_sent\"}) or vector(0)",
            "interval": "",
            "legendFormat": "{{step}}",
            "refId": "A"
          }
        ],
        "title": "Application Funnel",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "s"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 10
        },
        "id": 7,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "avg(mca_application_step_duration_seconds) by (step)",
            "interval": "",
            "legendFormat": "{{step}}",
            "refId": "A"
          }
        ],
        "title": "Step Completion Time",
        "type": "timeseries"
      },
      {
        "collapsed": false,
        "datasource": null,
        "gridPos": {
          "h": 1,
          "w": 24,
          "x": 0,
          "y": 18
        },
        "id": 8,
        "panels": [],
        "title": "User Satisfaction",
        "type": "row"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 0.7
                },
                {
                  "color": "green",
                  "value": 0.9
                }
              ]
            },
            "unit": "none"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 0,
          "y": 19
        },
        "id": 9,
        "options": {
          "orientation": "auto",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showThresholdLabels": false,
          "showThresholdMarkers": true
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "web_vitals_apdex{app=\"mca-frontend\"}",
            "interval": "",
            "legendFormat": "",
            "refId": "A"
          }
        ],
        "title": "Apdex Score",
        "type": "gauge"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "palette-classic"
            },
            "custom": {
              "axisLabel": "",
              "axisPlacement": "auto",
              "barAlignment": 0,
              "drawStyle": "line",
              "fillOpacity": 10,
              "gradientMode": "none",
              "hideFrom": {
                "legend": false,
                "tooltip": false,
                "viz": false
              },
              "lineInterpolation": "linear",
              "lineWidth": 1,
              "pointSize": 5,
              "scaleDistribution": {
                "type": "linear"
              },
              "showPoints": "never",
              "spanNulls": true,
              "stacking": {
                "group": "A",
                "mode": "none"
              },
              "thresholdsStyle": {
                "mode": "off"
              }
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                }
              ]
            },
            "unit": "percentunit"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 8,
          "y": 19
        },
        "id": 10,
        "options": {
          "legend": {
            "calcs": [],
            "displayMode": "list",
            "placement": "bottom"
          },
          "tooltip": {
            "mode": "single"
          }
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "sum(increase(web_vitals_errors_total{app=\"mca-frontend\"}[5m])) by (page) / sum(increase(web_vitals_page_views_total{app=\"mca-frontend\"}[5m])) by (page)",
            "interval": "",
            "legendFormat": "{{page}}",
            "refId": "A"
          }
        ],
        "title": "Error Rate by Page",
        "type": "timeseries"
      },
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "mappings": [],
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {
                  "color": "green",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 1000
                },
                {
                  "color": "red",
                  "value": 3000
                }
              ]
            },
            "unit": "ms"
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 8,
          "x": 16,
          "y": 19
        },
        "id": 11,
        "options": {
          "displayMode": "gradient",
          "orientation": "horizontal",
          "reduceOptions": {
            "calcs": [
              "lastNotNull"
            ],
            "fields": "",
            "values": false
          },
          "showUnfilled": true,
          "text": {}
        },
        "pluginVersion": "8.0.0",
        "targets": [
          {
            "expr": "topk(5, avg(web_vitals_page_load_time_ms{app=\"mca-frontend\"}) by (page))",
            "interval": "",
            "legendFormat": "{{page}}",
            "refId": "A"
          }
        ],
        "title": "Slowest Pages",
        "type": "bargauge"
      }
    ],
    "refresh": "5s",
    "schemaVersion": 30,
    "style": "dark",
    "tags": ["mca-application", "user-experience", "product", "terraform"],
    "templating": {
      "list": []
    },
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "timepicker": {},
    "timezone": "",
    "title": "MCA Application - User Experience",
    "uid": "mca-user-experience",
    "version": 1
  })

  folder = var.grafana_folder_id
}

# ---------------------------------------------------------------------------------------------------------------------
# VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  default     = "development"
}

variable "grafana_folder_id" {
  description = "Grafana folder ID to store dashboards"
  type        = string
  default     = ""
}