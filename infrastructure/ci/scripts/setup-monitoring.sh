#!/bin/bash
# setup-monitoring.sh
# Configures monitoring and logging for deployed services with Datadog integration

set -e

# Default values
DEFAULT_ENV="development"
DATADOG_SITE="datadoghq.com"
DATADOG_API_KEY=""
DATADOG_APP_KEY=""
CLUSTER_NAME="mca-cluster"

# Service names
SERVICES=("email-service" "document-service" "ocr-service" "data-service" "notification-service" "api-gateway")

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --api-key)
      DATADOG_API_KEY="$2"
      shift
      shift
      ;;
    --app-key)
      DATADOG_APP_KEY="$2"
      shift
      shift
      ;;
    --site)
      DATADOG_SITE="$2"
      shift
      shift
      ;;
    --env)
      ENV="$2"
      shift
      shift
      ;;
    --cluster-name)
      CLUSTER_NAME="$2"
      shift
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --api-key KEY       Datadog API key"
      echo "  --app-key KEY       Datadog application key"
      echo "  --site SITE         Datadog site (default: datadoghq.com)"
      echo "  --env ENV           Environment (development, staging, production)"
      echo "  --cluster-name NAME Kubernetes cluster name (default: mca-cluster)"
      echo "  --help              Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Set environment if not provided
ENV=${ENV:-$DEFAULT_ENV}

# Validate required parameters
if [ -z "$DATADOG_API_KEY" ]; then
  echo "Error: Datadog API key is required. Use --api-key to provide it."
  exit 1
fi

if [ -z "$DATADOG_APP_KEY" ]; then
  echo "Error: Datadog application key is required. Use --app-key to provide it."
  exit 1
fi

echo "=== Setting up Datadog monitoring for MCA Application ==="
echo "Environment: $ENV"
echo "Cluster: $CLUSTER_NAME"

# Create Kubernetes secret for Datadog API and APP keys
echo "Creating Kubernetes secret for Datadog credentials..."
kubectl create secret generic datadog-secret \
  --from-literal=api-key=$DATADOG_API_KEY \
  --from-literal=app-key=$DATADOG_APP_KEY \
  --namespace=default \
  --dry-run=client -o yaml | kubectl apply -f -

# Function to set environment-specific thresholds
function get_threshold() {
  local metric=$1
  local env=$2
  
  case $env in
    production)
      case $metric in
        cpu) echo "80" ;;
        memory) echo "80" ;;
        error_rate) echo "1" ;;
        latency) echo "2000" ;; # 2 seconds in ms
        *) echo "75" ;;
      esac
      ;;
    staging)
      case $metric in
        cpu) echo "85" ;;
        memory) echo "85" ;;
        error_rate) echo "5" ;;
        latency) echo "5000" ;; # 5 seconds in ms
        *) echo "80" ;;
      esac
      ;;
    *) # development
      case $metric in
        cpu) echo "90" ;;
        memory) echo "90" ;;
        error_rate) echo "10" ;;
        latency) echo "10000" ;; # 10 seconds in ms
        *) echo "85" ;;
      esac
      ;;
  esac
}

# Install Datadog Operator using Helm
echo "Installing Datadog Operator..."
helm repo add datadog https://helm.datadoghq.com
helm repo update

helm upgrade --install datadog-operator datadog/datadog-operator \
  --namespace default \
  --set image.tag=latest

# Wait for the operator to be ready
echo "Waiting for Datadog Operator to be ready..."
kubectl rollout status deployment/datadog-operator -n default --timeout=120s

# Create DatadogAgent custom resource
echo "Creating DatadogAgent custom resource..."
cat <<EOF | kubectl apply -f -
apiVersion: datadoghq.com/v2alpha1
kind: DatadogAgent
metadata:
  name: datadog
spec:
  global:
    credentials:
      apiSecret:
        secretName: datadog-secret
        keyName: api-key
      appSecret:
        secretName: datadog-secret
        keyName: app-key
    clusterName: ${CLUSTER_NAME}
    site: ${DATADOG_SITE}
    tags:
      - "env:${ENV}"
      - "service:mca-application"
    kubernetesCriEnabled: true
  features:
    logCollection:
      enabled: true
    apm:
      enabled: true
      hostPortEnabled: true
    processCollection:
      enabled: true
    eventCollection:
      collectKubernetesEvents: true
    npm:
      enabled: true
  override:
    clusterAgent:
      image:
        name: gcr.io/datadoghq/cluster-agent:latest
      replicas: 2
    nodeAgent:
      image:
        name: gcr.io/datadoghq/agent:latest
      tolerations:
      - operator: Exists
      resources:
        requests:
          cpu: 200m
          memory: 256Mi
        limits:
          cpu: 500m
          memory: 512Mi
      env:
        - name: DD_ENV
          value: "${ENV}"
        - name: DD_LOGS_ENABLED
          value: "true"
        - name: DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL
          value: "true"
        - name: DD_APM_ENABLED
          value: "true"
        - name: DD_PROCESS_AGENT_ENABLED
          value: "true"
        - name: DD_RUNTIME_METRICS_ENABLED
          value: "true"
EOF

# Wait for the Datadog agent to be deployed
echo "Waiting for Datadog Agent to be deployed..."
sleep 30

# Configure service-specific monitoring
echo "Configuring service-specific monitoring..."

# Email Service (Node.js/Nodemailer)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-email-service-config
data:
  conf.yaml: |
    logs:
      - type: docker
        source: nodejs
        service: email-service
        tags:
          - "env:${ENV}"
          - "service:email-service"
        log_processing_rules:
          - type: multi_line
            name: nodejs_stack_traces
            pattern: ^\s*at .*\(.*\)$
    apm_config:
      enabled: true
      service: email-service
      env: ${ENV}
    metrics:
      - name: "email_service.inbox_check_time"
        type: gauge
        description: "Time taken to check inbox for new emails"
      - name: "email_service.emails_processed"
        type: count
        description: "Number of emails processed"
      - name: "email_service.processing_errors"
        type: count
        description: "Number of email processing errors"
      - name: "email_service.attachment_size"
        type: gauge
        description: "Size of email attachments in bytes"
      - name: "email_service.queue_depth"
        type: gauge
        description: "Number of emails waiting to be processed"
EOF

# Document Service (Python/scikit-learn)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-document-service-config
data:
  conf.yaml: |
    logs:
      - type: docker
        source: python
        service: document-service
        tags:
          - "env:${ENV}"
          - "service:document-service"
        log_processing_rules:
          - type: multi_line
            name: python_traceback
            pattern: ^Traceback \(most recent call last\):$|^[\t ]+File "/.*\.py"
    apm_config:
      enabled: true
      service: document-service
      env: ${ENV}
    metrics:
      - name: "document_service.classification_time"
        type: gauge
        description: "Time taken to classify a document"
      - name: "document_service.documents_processed"
        type: count
        description: "Number of documents processed"
      - name: "document_service.classification_accuracy"
        type: gauge
        description: "Accuracy of document classification"
      - name: "document_service.model_prediction_time"
        type: gauge
        description: "Time taken for model prediction"
      - name: "document_service.queue_depth"
        type: gauge
        description: "Number of documents waiting to be processed"
EOF

# OCR Service (Python/TensorFlow)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-ocr-service-config
data:
  conf.yaml: |
    logs:
      - type: docker
        source: python
        service: ocr-service
        tags:
          - "env:${ENV}"
          - "service:ocr-service"
        log_processing_rules:
          - type: multi_line
            name: python_traceback
            pattern: ^Traceback \(most recent call last\):$|^[\t ]+File "/.*\.py"
    apm_config:
      enabled: true
      service: ocr-service
      env: ${ENV}
    metrics:
      - name: "ocr_service.processing_time"
        type: gauge
        description: "Time taken to process OCR on a document"
      - name: "ocr_service.documents_processed"
        type: count
        description: "Number of documents processed with OCR"
      - name: "ocr_service.extraction_accuracy"
        type: gauge
        description: "Accuracy of text extraction"
      - name: "ocr_service.gpu_utilization"
        type: gauge
        description: "GPU utilization percentage"
      - name: "ocr_service.queue_depth"
        type: gauge
        description: "Number of documents waiting for OCR processing"
EOF

# Data Service (Java/Spring Boot)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-data-service-config
data:
  conf.yaml: |
    logs:
      - type: docker
        source: java
        service: data-service
        tags:
          - "env:${ENV}"
          - "service:data-service"
        log_processing_rules:
          - type: multi_line
            name: java_stack_traces
            pattern: ^[\t ]*at .*\(.*\)$
    apm_config:
      enabled: true
      service: data-service
      env: ${ENV}
    metrics:
      - name: "data_service.request_time"
        type: gauge
        description: "Time taken to process API requests"
      - name: "data_service.requests_processed"
        type: count
        description: "Number of API requests processed"
      - name: "data_service.database_query_time"
        type: gauge
        description: "Time taken for database queries"
      - name: "data_service.active_connections"
        type: gauge
        description: "Number of active database connections"
      - name: "data_service.jvm_memory_used"
        type: gauge
        description: "JVM memory usage"
EOF

# Notification Service (Node.js)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-notification-service-config
data:
  conf.yaml: |
    logs:
      - type: docker
        source: nodejs
        service: notification-service
        tags:
          - "env:${ENV}"
          - "service:notification-service"
        log_processing_rules:
          - type: multi_line
            name: nodejs_stack_traces
            pattern: ^\s*at .*\(.*\)$
    apm_config:
      enabled: true
      service: notification-service
      env: ${ENV}
    metrics:
      - name: "notification_service.delivery_time"
        type: gauge
        description: "Time taken to deliver notifications"
      - name: "notification_service.notifications_sent"
        type: count
        description: "Number of notifications sent"
      - name: "notification_service.delivery_failures"
        type: count
        description: "Number of notification delivery failures"
      - name: "notification_service.webhook_response_time"
        type: gauge
        description: "Response time of webhook endpoints"
      - name: "notification_service.queue_depth"
        type: gauge
        description: "Number of notifications waiting to be sent"
EOF

# API Gateway (Kong)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-api-gateway-config
data:
  conf.yaml: |
    logs:
      - type: docker
        source: kong
        service: api-gateway
        tags:
          - "env:${ENV}"
          - "service:api-gateway"
    apm_config:
      enabled: true
      service: api-gateway
      env: ${ENV}
    metrics:
      - name: "api_gateway.request_time"
        type: gauge
        description: "Time taken to process API requests"
      - name: "api_gateway.requests_processed"
        type: count
        description: "Number of API requests processed"
      - name: "api_gateway.error_count"
        type: count
        description: "Number of API errors"
      - name: "api_gateway.upstream_latency"
        type: gauge
        description: "Latency of upstream services"
      - name: "api_gateway.rate_limit_hits"
        type: count
        description: "Number of rate limit hits"
EOF

# Set up Datadog monitors for critical service metrics
echo "Setting up Datadog monitors for critical service metrics..."

# CPU and Memory monitors for all services
for service in "${SERVICES[@]}"; do
  # CPU Usage Monitor
  cpu_threshold=$(get_threshold "cpu" "$ENV")
  curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
    -H "Content-Type: application/json" \
    -H "DD-API-KEY: ${DATADOG_API_KEY}" \
    -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
    -d @- << EOF
{
  "name": "[${ENV}] ${service} - High CPU Usage",
  "type": "metric alert",
  "query": "avg(last_5m):avg:kubernetes.cpu.usage{service:${service},env:${ENV}} by {pod_name} > ${cpu_threshold}",
  "message": "CPU usage for ${service} is above ${cpu_threshold}% for 5 minutes.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:${service}", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": ${cpu_threshold}
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "CPU usage for ${service} is still above ${cpu_threshold}%!"
  }
}
EOF

  # Memory Usage Monitor
  memory_threshold=$(get_threshold "memory" "$ENV")
  curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
    -H "Content-Type: application/json" \
    -H "DD-API-KEY: ${DATADOG_API_KEY}" \
    -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
    -d @- << EOF
{
  "name": "[${ENV}] ${service} - High Memory Usage",
  "type": "metric alert",
  "query": "avg(last_5m):avg:kubernetes.memory.usage_pct{service:${service},env:${ENV}} by {pod_name} > ${memory_threshold}",
  "message": "Memory usage for ${service} is above ${memory_threshold}% for 5 minutes.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:${service}", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": ${memory_threshold}
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "Memory usage for ${service} is still above ${memory_threshold}%!"
  }
}
EOF

  # Error Rate Monitor
  error_threshold=$(get_threshold "error_rate" "$ENV")
  curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
    -H "Content-Type: application/json" \
    -H "DD-API-KEY: ${DATADOG_API_KEY}" \
    -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
    -d @- << EOF
{
  "name": "[${ENV}] ${service} - High Error Rate",
  "type": "metric alert",
  "query": "sum(last_5m):sum:trace.${service}.errors{env:${ENV}} / sum:trace.${service}.hits{env:${ENV}} * 100 > ${error_threshold}",
  "message": "Error rate for ${service} is above ${error_threshold}% for 5 minutes.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:${service}", "env:${ENV}", "team:mca"],
  "priority": 1,
  "options": {
    "thresholds": {
      "critical": ${error_threshold}
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "Error rate for ${service} is still above ${error_threshold}%!"
  }
}
EOF

  # Latency Monitor
  latency_threshold=$(get_threshold "latency" "$ENV")
  curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
    -H "Content-Type: application/json" \
    -H "DD-API-KEY: ${DATADOG_API_KEY}" \
    -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
    -d @- << EOF
{
  "name": "[${ENV}] ${service} - High Latency",
  "type": "metric alert",
  "query": "avg(last_5m):avg:trace.${service}.request.duration{env:${ENV}} > ${latency_threshold}",
  "message": "Latency for ${service} is above ${latency_threshold}ms for 5 minutes.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:${service}", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": ${latency_threshold}
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "Latency for ${service} is still above ${latency_threshold}ms!"
  }
}
EOF
done

# Create service-specific monitors

# Email Service - Inbox Check Monitor
curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] Email Service - Inbox Check Failing",
  "type": "metric alert",
  "query": "min(last_10m):avg:email_service.inbox_check_time{env:${ENV}} < 0",
  "message": "Email Service is unable to check inbox for new emails.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:email-service", "env:${ENV}", "team:mca"],
  "priority": 1,
  "options": {
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": true,
    "no_data_timeframe": 20,
    "new_host_delay": 300,
    "escalation_message": "Email Service is still unable to check inbox!"
  }
}
EOF

# Document Service - Classification Accuracy Monitor
curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] Document Service - Low Classification Accuracy",
  "type": "metric alert",
  "query": "avg(last_15m):avg:document_service.classification_accuracy{env:${ENV}} < 95",
  "message": "Document classification accuracy has dropped below 95%.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:document-service", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": 95,
      "warning": 97
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "Document classification accuracy is still below threshold!"
  }
}
EOF

# OCR Service - Extraction Accuracy Monitor
curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] OCR Service - Low Extraction Accuracy",
  "type": "metric alert",
  "query": "avg(last_15m):avg:ocr_service.extraction_accuracy{env:${ENV}} < 95",
  "message": "OCR extraction accuracy has dropped below 95%.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:ocr-service", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": 95,
      "warning": 97
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "OCR extraction accuracy is still below threshold!"
  }
}
EOF

# Data Service - Database Connection Monitor
curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] Data Service - Database Connection Pool Saturation",
  "type": "metric alert",
  "query": "avg(last_5m):avg:data_service.active_connections{env:${ENV}} / 100 * 100 > 80",
  "message": "Database connection pool is over 80% saturated.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:data-service", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": 80,
      "warning": 70
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "Database connection pool is still highly saturated!"
  }
}
EOF

# Notification Service - Webhook Delivery Monitor
curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] Notification Service - High Webhook Failure Rate",
  "type": "metric alert",
  "query": "sum(last_10m):sum:notification_service.delivery_failures{env:${ENV}} / sum:notification_service.notifications_sent{env:${ENV}} * 100 > 5",
  "message": "Webhook delivery failure rate is above 5%.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:notification-service", "env:${ENV}", "team:mca"],
  "priority": 2,
  "options": {
    "thresholds": {
      "critical": 5,
      "warning": 2
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "Webhook delivery failure rate is still above threshold!"
  }
}
EOF

# API Gateway - Rate Limit Monitor
curl -X POST "https://api.${DATADOG_SITE}/api/v1/monitor" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] API Gateway - High Rate Limit Hits",
  "type": "metric alert",
  "query": "sum(last_5m):sum:api_gateway.rate_limit_hits{env:${ENV}} > 100",
  "message": "API Gateway is experiencing a high number of rate limit hits.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": ["service:api-gateway", "env:${ENV}", "team:mca"],
  "priority": 3,
  "options": {
    "thresholds": {
      "critical": 100,
      "warning": 50
    },
    "notify_audit": true,
    "include_tags": true,
    "notify_no_data": false,
    "require_full_window": false,
    "new_host_delay": 300,
    "escalation_message": "API Gateway is still experiencing a high number of rate limit hits!"
  }
}
EOF

# Create a dashboard for MCA Application monitoring
echo "Creating dashboard for MCA Application monitoring..."
curl -X POST "https://api.${DATADOG_SITE}/api/v1/dashboard" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "title": "MCA Application Dashboard - ${ENV}",
  "description": "Comprehensive monitoring dashboard for the MCA Application in ${ENV} environment",
  "widgets": [
    {
      "definition": {
        "type": "group",
        "title": "Application Overview",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Service Status",
              "type": "servicemap",
              "service": "mca-application",
              "filters": ["env:${ENV}"],
              "size": "xl"
            }
          },
          {
            "definition": {
              "title": "Error Rates by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:trace.errors{env:${ENV}} by {service} / sum:trace.hits{env:${ENV}} by {service} * 100",
                  "display_type": "line"
                }
              ],
              "yaxis": {
                "label": "Error Rate (%)",
                "min": "0",
                "scale": "linear"
              }
            }
          },
          {
            "definition": {
              "title": "Request Latency by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:trace.http.request.duration{env:${ENV}} by {service}",
                  "display_type": "line"
                }
              ],
              "yaxis": {
                "label": "Latency (ms)",
                "min": "0",
                "scale": "linear"
              }
            }
          },
          {
            "definition": {
              "title": "Request Volume by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:trace.http.hits{env:${ENV}} by {service}.as_count()",
                  "display_type": "bars"
                }
              ],
              "yaxis": {
                "label": "Requests",
                "min": "0",
                "scale": "linear"
              }
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "Email Service",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Emails Processed",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:email_service.emails_processed{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Inbox Check Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:email_service.inbox_check_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Processing Errors",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:email_service.processing_errors{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Queue Depth",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:email_service.queue_depth{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "Document Service",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Documents Processed",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:document_service.documents_processed{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Classification Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:document_service.classification_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Classification Accuracy",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:document_service.classification_accuracy{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Queue Depth",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:document_service.queue_depth{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "OCR Service",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Documents Processed",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:ocr_service.documents_processed{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Processing Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:ocr_service.processing_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Extraction Accuracy",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:ocr_service.extraction_accuracy{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "GPU Utilization",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:ocr_service.gpu_utilization{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "Data Service",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Requests Processed",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:data_service.requests_processed{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Request Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:data_service.request_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Database Query Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:data_service.database_query_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Active Connections",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:data_service.active_connections{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "Notification Service",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Notifications Sent",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:notification_service.notifications_sent{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Delivery Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:notification_service.delivery_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Delivery Failures",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:notification_service.delivery_failures{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Webhook Response Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:notification_service.webhook_response_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "API Gateway",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "Requests Processed",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:api_gateway.requests_processed{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Request Time",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:api_gateway.request_time{env:${ENV}}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Error Count",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:api_gateway.error_count{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Rate Limit Hits",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:api_gateway.rate_limit_hits{env:${ENV}}.as_count()",
                  "display_type": "bars"
                }
              ]
            }
          }
        ]
      }
    },
    {
      "definition": {
        "type": "group",
        "title": "Infrastructure",
        "layout_type": "ordered",
        "widgets": [
          {
            "definition": {
              "title": "CPU Usage by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:kubernetes.cpu.usage{env:${ENV}} by {service}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Memory Usage by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:kubernetes.memory.usage_pct{env:${ENV}} by {service}",
                  "display_type": "line"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Network Traffic by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "sum:kubernetes.network.rx_bytes{env:${ENV}} by {service}.as_count()",
                  "display_type": "line",
                  "name": "Received"
                },
                {
                  "q": "sum:kubernetes.network.tx_bytes{env:${ENV}} by {service}.as_count()",
                  "display_type": "line",
                  "name": "Transmitted"
                }
              ]
            }
          },
          {
            "definition": {
              "title": "Disk Usage by Service",
              "type": "timeseries",
              "requests": [
                {
                  "q": "avg:kubernetes.filesystem.usage_pct{env:${ENV}} by {service}",
                  "display_type": "line"
                }
              ]
            }
          }
        ]
      }
    }
  ],
  "template_variables": [
    {
      "name": "service",
      "prefix": "service",
      "default": "*"
    },
    {
      "name": "env",
      "prefix": "env",
      "default": "${ENV}"
    }
  ],
  "layout_type": "ordered",
  "is_read_only": false,
  "notify_list": []
}
EOF

# Set up synthetic tests for critical endpoints
echo "Setting up synthetic tests for critical endpoints..."

# API Gateway health check
curl -X POST "https://api.${DATADOG_SITE}/api/v1/synthetics/tests" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] API Gateway Health Check",
  "type": "api",
  "subtype": "http",
  "request": {
    "method": "GET",
    "url": "https://api.${ENV}.dollarfunding.com/health",
    "timeout": 30,
    "headers": {
      "Content-Type": "application/json"
    }
  },
  "assertions": [
    {
      "type": "statusCode",
      "operator": "is",
      "target": 200
    },
    {
      "type": "responseTime",
      "operator": "lessThan",
      "target": 1000
    }
  ],
  "locations": [
    "aws:us-east-1",
    "aws:us-west-1"
  ],
  "options": {
    "tick_every": 60,
    "min_failure_duration": 300,
    "min_location_failed": 1,
    "follow_redirects": true
  },
  "message": "The API Gateway health check is failing. Please investigate.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": [
    "env:${ENV}",
    "service:api-gateway",
    "team:mca"
  ],
  "status": "live"
}
EOF

# Data Service API check
curl -X POST "https://api.${DATADOG_SITE}/api/v1/synthetics/tests" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "name": "[${ENV}] Data Service API Check",
  "type": "api",
  "subtype": "http",
  "request": {
    "method": "GET",
    "url": "https://api.${ENV}.dollarfunding.com/api/v1/applications/status",
    "timeout": 30,
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer {{SYNTHETIC_TEST_TOKEN}}"
    }
  },
  "assertions": [
    {
      "type": "statusCode",
      "operator": "is",
      "target": 200
    },
    {
      "type": "responseTime",
      "operator": "lessThan",
      "target": 2000
    },
    {
      "type": "body",
      "operator": "contains",
      "target": "status"
    }
  ],
  "locations": [
    "aws:us-east-1",
    "aws:us-west-1"
  ],
  "options": {
    "tick_every": 300,
    "min_failure_duration": 300,
    "min_location_failed": 1,
    "follow_redirects": true
  },
  "message": "The Data Service API check is failing. Please investigate.\n\n@slack-mca-alerts\n@pagerduty-MCA-${ENV}",
  "tags": [
    "env:${ENV}",
    "service:data-service",
    "team:mca"
  ],
  "status": "live"
}
EOF

# Configure APM for service tracing
echo "Configuring APM for service tracing..."

# Create a service map dashboard
curl -X POST "https://api.${DATADOG_SITE}/api/v1/dashboard" \
  -H "Content-Type: application/json" \
  -H "DD-API-KEY: ${DATADOG_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DATADOG_APP_KEY}" \
  -d @- << EOF
{
  "title": "MCA Application Service Map - ${ENV}",
  "description": "Service map showing dependencies between MCA Application services",
  "widgets": [
    {
      "definition": {
        "type": "servicemap",
        "service": "mca-application",
        "filters": ["env:${ENV}"],
        "title": "MCA Application Service Map"
      }
    }
  ],
  "template_variables": [
    {
      "name": "env",
      "prefix": "env",
      "default": "${ENV}"
    }
  ],
  "layout_type": "ordered",
  "is_read_only": false,
  "notify_list": []
}
EOF

echo "=== Datadog monitoring setup complete ==="
echo "Dashboards, monitors, and synthetic tests have been created."
echo "APM and log collection have been configured for all services."
echo "Environment-specific thresholds have been set for ${ENV}."