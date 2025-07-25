#!/bin/bash

# K8s AI Agent Easy Deployment Script
# This script simplifies the deployment process for different environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

# Default configuration
ENVIRONMENT="local"
IMAGE_TAG="latest"
NAMESPACE="k8s-ai-agent"
IMAGE_REGISTRY="dockerhub.cisco.com"
IMAGE_REPO="robot-dockerprod"
IMAGE_NAME="k8s-ai-agent"
DRY_RUN=false
APPLY_MANIFESTS=true
CREATE_NAMESPACE=true

# Show usage
show_usage() {
    cat << EOF
K8s AI Agent Easy Deployment Script
==================================

Usage: $0 [OPTIONS]

OPTIONS:
    -e, --environment ENV     Environment: local, dev, staging, prod (default: local)
    -t, --tag TAG            Image tag to deploy (default: latest)
    -n, --namespace NS       Kubernetes namespace (default: k8s-ai-agent)
    -r, --registry REG       Docker registry (default: dockerhub.cisco.com)
    --repo REPO              Repository name (default: robot-dockerprod)
    --image-name NAME        Image name (default: k8s-ai-agent)
    --dry-run               Show what would be deployed without applying
    --no-apply              Generate manifests only, don't apply
    --no-namespace          Don't create namespace
    -h, --help              Show this help

EXAMPLES:
    # Local deployment
    $0 -e local

    # Staging deployment with specific tag
    $0 -e staging -t v1.2.3-45 -n ai-staging

    # Production deployment (dry run first)
    $0 -e prod -t v1.2.3 --dry-run

    # Generate manifests only
    $0 -e prod -t v1.2.3 --no-apply

ENVIRONMENT CONFIGURATIONS:
    local:    Single replica, NodePort service, minimal resources
    dev:      Single replica, ClusterIP service, debug enabled
    staging:  2 replicas, LoadBalancer service, monitoring enabled
    prod:     3 replicas, LoadBalancer service, full monitoring, resource limits

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--registry)
                IMAGE_REGISTRY="$2"
                shift 2
                ;;
            --repo)
                IMAGE_REPO="$2"
                shift 2
                ;;
            --image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-apply)
                APPLY_MANIFESTS=false
                shift
                ;;
            --no-namespace)
                CREATE_NAMESPACE=false
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Validate environment
validate_environment() {
    case $ENVIRONMENT in
        local|dev|staging|prod)
            log "Deploying to $ENVIRONMENT environment"
            ;;
        *)
            error "Invalid environment: $ENVIRONMENT. Must be one of: local, dev, staging, prod"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log "Prerequisites check completed"
}

# Set environment-specific configuration
set_env_config() {
    case $ENVIRONMENT in
        local)
            REPLICAS=1
            SERVICE_TYPE="NodePort"
            CPU_REQUEST="100m"
            CPU_LIMIT="1000m"
            MEMORY_REQUEST="512Mi"
            MEMORY_LIMIT="2Gi"
            ENABLE_MONITORING="false"
            LOG_LEVEL="INFO"
            ;;
        dev)
            REPLICAS=1
            SERVICE_TYPE="ClusterIP"
            CPU_REQUEST="200m"
            CPU_LIMIT="1000m"
            MEMORY_REQUEST="1Gi"
            MEMORY_LIMIT="4Gi"
            ENABLE_MONITORING="true"
            LOG_LEVEL="DEBUG"
            ;;
        staging)
            REPLICAS=2
            SERVICE_TYPE="LoadBalancer"
            CPU_REQUEST="500m"
            CPU_LIMIT="2000m"
            MEMORY_REQUEST="2Gi"
            MEMORY_LIMIT="8Gi"
            ENABLE_MONITORING="true"
            LOG_LEVEL="INFO"
            ;;
        prod)
            REPLICAS=3
            SERVICE_TYPE="LoadBalancer"
            CPU_REQUEST="1000m"
            CPU_LIMIT="4000m"
            MEMORY_REQUEST="4Gi"
            MEMORY_LIMIT="16Gi"
            ENABLE_MONITORING="true"
            LOG_LEVEL="WARN"
            ;;
    esac

    FULL_IMAGE="${IMAGE_REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"
    
    info "Environment: $ENVIRONMENT"
    info "Image: $FULL_IMAGE"
    info "Namespace: $NAMESPACE"
    info "Replicas: $REPLICAS"
    info "Service Type: $SERVICE_TYPE"
}

# Generate deployment manifests
generate_manifests() {
    log "Generating Kubernetes manifests for $ENVIRONMENT environment..."

    # Create deployment directory
    local deploy_dir="deploy-${ENVIRONMENT}-${IMAGE_TAG}"
    mkdir -p "$deploy_dir"

    # Generate namespace manifest
    if [[ "$CREATE_NAMESPACE" == "true" ]]; then
        cat > "$deploy_dir/01-namespace.yaml" << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
EOF
    fi

    # Generate ConfigMap
    cat > "$deploy_dir/02-configmap.yaml" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-ai-agent-config
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
data:
  MODE: "interactive"
  UI_INTERACTIVE: "true"
  ENABLE_HISTORICAL_LEARNING: "true"
  ENABLE_RUNTIME_CONFIG: "true"
  LOG_LEVEL: "$LOG_LEVEL"
  ENVIRONMENT: "$ENVIRONMENT"
  ENABLE_MONITORING: "$ENABLE_MONITORING"
EOF

    # Generate RuntimeConfig ConfigMap
    cat > "$deploy_dir/03-runtime-config.yaml" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: runtime-config
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
data:
  config.yaml: |
    mode: interactive
    ui_interactive: true
    enable_debug: $([[ "$ENVIRONMENT" == "dev" ]] && echo "true" || echo "false")
    enable_remediation: true
    enable_monitoring: true
    enable_historical_learning: true
    log_level: $LOG_LEVEL
    
    features:
      auto_remediation: $([[ "$ENVIRONMENT" == "prod" ]] && echo "true" || echo "false")
      continuous_learning: true
      pattern_recognition: true
      
    thresholds:
      cpu_alert: 80
      memory_alert: 85
      disk_alert: 90
EOF

    # Generate Deployment
    cat > "$deploy_dir/04-deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: k8s-ai-agent
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
    version: "$IMAGE_TAG"
spec:
  replicas: $REPLICAS
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  selector:
    matchLabels:
      app: k8s-ai-agent
  template:
    metadata:
      labels:
        app: k8s-ai-agent
        environment: $ENVIRONMENT
        version: "$IMAGE_TAG"
      annotations:
        prometheus.io/scrape: "$ENABLE_MONITORING"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: ai-agent
        image: $FULL_IMAGE
        imagePullPolicy: Always
        ports:
        - containerPort: 8501
          name: ui
        - containerPort: 8080
          name: api
        env:
        - name: MODE
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-agent-config
              key: MODE
        - name: UI_INTERACTIVE
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-agent-config
              key: UI_INTERACTIVE
        - name: ENABLE_HISTORICAL_LEARNING
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-agent-config
              key: ENABLE_HISTORICAL_LEARNING
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-agent-config
              key: LOG_LEVEL
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: k8s-ai-agent-config
              key: ENVIRONMENT
        volumeMounts:
        - name: runtime-config
          mountPath: /app/config
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "$MEMORY_REQUEST"
            cpu: "$CPU_REQUEST"
          limits:
            memory: "$MEMORY_LIMIT"
            cpu: "$CPU_LIMIT"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8501
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
      volumes:
      - name: runtime-config
        configMap:
          name: runtime-config
      - name: logs
        emptyDir: {}
      restartPolicy: Always
      terminationGracePeriodSeconds: 30
EOF

    # Generate Service
    cat > "$deploy_dir/05-service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: k8s-ai-agent-service
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
spec:
  selector:
    app: k8s-ai-agent
  ports:
  - name: ui
    port: 8501
    targetPort: 8501
    protocol: TCP
  - name: api
    port: 8080
    targetPort: 8080
    protocol: TCP
  type: $SERVICE_TYPE
EOF

    # Generate HPA for staging/prod
    if [[ "$ENVIRONMENT" == "staging" || "$ENVIRONMENT" == "prod" ]]; then
        cat > "$deploy_dir/06-hpa.yaml" << EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: k8s-ai-agent-hpa
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: k8s-ai-agent
  minReplicas: $REPLICAS
  maxReplicas: $([[ "$ENVIRONMENT" == "prod" ]] && echo "10" || echo "5")
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF
    fi

    # Generate ServiceMonitor for monitoring
    if [[ "$ENABLE_MONITORING" == "true" ]]; then
        cat > "$deploy_dir/07-servicemonitor.yaml" << EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: k8s-ai-agent-monitor
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
spec:
  selector:
    matchLabels:
      app: k8s-ai-agent
  endpoints:
  - port: api
    path: /metrics
    interval: 30s
EOF
    fi

    # Generate RBAC for the agent
    cat > "$deploy_dir/08-rbac.yaml" << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: k8s-ai-agent
  namespace: $NAMESPACE
  labels:
    app: k8s-ai-agent
    environment: $ENVIRONMENT
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-ai-agent-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints", "events", "nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["pods", "nodes"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: k8s-ai-agent-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: k8s-ai-agent-role
subjects:
- kind: ServiceAccount
  name: k8s-ai-agent
  namespace: $NAMESPACE
EOF

    # Update deployment to use service account
    sed -i.bak 's/terminationGracePeriodSeconds: 30/serviceAccountName: k8s-ai-agent\n      terminationGracePeriodSeconds: 30/' "$deploy_dir/04-deployment.yaml"
    rm -f "$deploy_dir/04-deployment.yaml.bak"

    # Generate deployment instructions
    cat > "$deploy_dir/README.md" << EOF
# K8s AI Agent Deployment - $ENVIRONMENT

## Generated Configuration
- **Environment**: $ENVIRONMENT
- **Image**: $FULL_IMAGE
- **Namespace**: $NAMESPACE
- **Replicas**: $REPLICAS
- **Service Type**: $SERVICE_TYPE

## Deployment Instructions

### 1. Deploy to Kubernetes
\`\`\`bash
# Apply all manifests
kubectl apply -f .

# Or apply in order
kubectl apply -f 01-namespace.yaml
kubectl apply -f 02-configmap.yaml
kubectl apply -f 03-runtime-config.yaml
kubectl apply -f 08-rbac.yaml
kubectl apply -f 04-deployment.yaml
kubectl apply -f 05-service.yaml
$(if [[ -f "$deploy_dir/06-hpa.yaml" ]]; then echo "kubectl apply -f 06-hpa.yaml"; fi)
$(if [[ -f "$deploy_dir/07-servicemonitor.yaml" ]]; then echo "kubectl apply -f 07-servicemonitor.yaml"; fi)
\`\`\`

### 2. Verify Deployment
\`\`\`bash
# Check deployment status
kubectl get deployments -n $NAMESPACE

# Check pods
kubectl get pods -n $NAMESPACE

# Check service
kubectl get services -n $NAMESPACE

# View logs
kubectl logs -f deployment/k8s-ai-agent -n $NAMESPACE
\`\`\`

### 3. Access the Application
$(if [[ "$SERVICE_TYPE" == "NodePort" ]]; then
cat << 'NODEPORT'
```bash
# Get NodePort configuration
kubectl get service k8s-ai-agent -n $NAMESPACE

# Get node IPs
kubectl get nodes -o wide

# Access via NodePort
# Dashboard: http://<NODE-IP>:30080
# Metrics:   http://<NODE-IP>:30090

# Example with specific node IP:
# Dashboard: http://192.168.1.100:30080
# Metrics:   http://192.168.1.100:30090
```
NODEPORT
elif [[ "$SERVICE_TYPE" == "LoadBalancer" ]]; then
cat << 'LB'
```bash
# Get LoadBalancer IP
kubectl get service k8s-ai-agent-service -n $NAMESPACE

# Access via LoadBalancer IP
# UI: http://<EXTERNAL-IP>:8501
```
LB
else
cat << 'CLUSTER'
```bash
# Port forward for local access
kubectl port-forward service/k8s-ai-agent-service 8501:8501 -n $NAMESPACE

# Access locally
# UI: http://localhost:8501
```
CLUSTER
fi)

### 4. Update Deployment
\`\`\`bash
# Update image
kubectl set image deployment/k8s-ai-agent ai-agent=NEW_IMAGE -n $NAMESPACE

# Rolling restart
kubectl rollout restart deployment/k8s-ai-agent -n $NAMESPACE

# Check rollout status
kubectl rollout status deployment/k8s-ai-agent -n $NAMESPACE
\`\`\`

### 5. Cleanup
\`\`\`bash
# Delete all resources
kubectl delete -f .

# Or delete namespace (removes everything)
kubectl delete namespace $NAMESPACE
\`\`\`

## Configuration

The deployment includes:
- **ConfigMaps**: Application and runtime configuration
- **RBAC**: Service account and permissions for Kubernetes access
- **Monitoring**: $(if [[ "$ENABLE_MONITORING" == "true" ]]; then echo "ServiceMonitor for Prometheus"; else echo "Disabled"; fi)
- **Autoscaling**: $(if [[ -f "$deploy_dir/06-hpa.yaml" ]]; then echo "HPA enabled"; else echo "Disabled"; fi)

## Troubleshooting

\`\`\`bash
# Describe deployment
kubectl describe deployment k8s-ai-agent -n $NAMESPACE

# Check events
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n $NAMESPACE
\`\`\`
EOF

    info "Manifests generated in directory: $deploy_dir"
    return 0
}

# Apply manifests to cluster
apply_manifests() {
    local deploy_dir="deploy-${ENVIRONMENT}-${IMAGE_TAG}"
    
    if [[ ! -d "$deploy_dir" ]]; then
        error "Deployment directory $deploy_dir not found"
        return 1
    fi

    log "Applying manifests to Kubernetes cluster..."

    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN - Would apply the following files:"
        ls -la "$deploy_dir"/*.yaml
        return 0
    fi

    # Apply manifests in order
    local files=(
        "01-namespace.yaml"
        "02-configmap.yaml" 
        "03-runtime-config.yaml"
        "08-rbac.yaml"
        "04-deployment.yaml"
        "05-service.yaml"
        "06-hpa.yaml"
        "07-servicemonitor.yaml"
    )

    for file in "${files[@]}"; do
        if [[ -f "$deploy_dir/$file" ]]; then
            info "Applying $file..."
            kubectl apply -f "$deploy_dir/$file" || warn "Failed to apply $file"
        fi
    done

    log "Deployment completed!"
}

# Wait for deployment to be ready
wait_for_deployment() {
    if [[ "$DRY_RUN" == "true" || "$APPLY_MANIFESTS" == "false" ]]; then
        return 0
    fi

    log "Waiting for deployment to be ready..."
    
    kubectl rollout status deployment/k8s-ai-agent -n "$NAMESPACE" --timeout=300s || {
        error "Deployment failed to become ready"
        return 1
    }

    log "Deployment is ready!"
}

# Show deployment status and access information
show_status() {
    if [[ "$DRY_RUN" == "true" || "$APPLY_MANIFESTS" == "false" ]]; then
        return 0
    fi

    log "Deployment Status:"
    echo
    
    info "Pods:"
    kubectl get pods -n "$NAMESPACE" -l app=k8s-ai-agent
    echo
    
    info "Services:"
    kubectl get services -n "$NAMESPACE"
    echo
    
    # Show access information
    local service_type=$(kubectl get service k8s-ai-agent -n "$NAMESPACE" -o jsonpath='{.spec.type}' 2>/dev/null || echo "Unknown")
    
    case $service_type in
        NodePort)
            local dashboard_port=$(kubectl get service k8s-ai-agent -n "$NAMESPACE" -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}' 2>/dev/null || echo "30080")
            local metrics_port=$(kubectl get service k8s-ai-agent -n "$NAMESPACE" -o jsonpath='{.spec.ports[?(@.name=="metrics")].nodePort}' 2>/dev/null || echo "30090")
            
            info "NodePort Access URLs:"
            echo "  📱 Dashboard: http://<NODE-IP>:$dashboard_port"
            echo "  📊 Metrics:   http://<NODE-IP>:$metrics_port"
            echo ""
            info "To get node IPs: kubectl get nodes -o wide"
            
            # Try to get actual node IPs
            local external_ips=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null || echo "")
            local internal_ips=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || echo "")
            
            if [ -n "$external_ips" ]; then
                info "External IP examples:"
                for ip in $external_ips; do
                    echo "  📱 Dashboard: http://$ip:$dashboard_port"
                done
            elif [ -n "$internal_ips" ]; then
                info "Internal IP examples:"
                for ip in $internal_ips; do
                    echo "  📱 Dashboard: http://$ip:$dashboard_port"
                done
            fi
            ;;
        LoadBalancer)
            info "Waiting for LoadBalancer IP..."
            kubectl get service k8s-ai-agent -n "$NAMESPACE" --watch
            ;;
        ClusterIP)
            info "To access the service, use port forwarding:"
            info "kubectl port-forward service/k8s-ai-agent-service 8501:8501 -n $NAMESPACE"
            info "Then access: http://localhost:8501"
            ;;
    esac
}

# Main execution
main() {
    log "K8s AI Agent Easy Deployment Script"
    log "==================================="

    parse_args "$@"
    validate_environment
    check_prerequisites
    set_env_config
    generate_manifests

    if [[ "$APPLY_MANIFESTS" == "true" ]]; then
        apply_manifests
        wait_for_deployment
        show_status
    else
        info "Manifests generated only (--no-apply specified)"
    fi

    local deploy_dir="deploy-${ENVIRONMENT}-${IMAGE_TAG}"
    log "Deployment package ready in: $deploy_dir"
    info "To deploy later: cd $deploy_dir && kubectl apply -f ."
}

# Run main function
main "$@"
