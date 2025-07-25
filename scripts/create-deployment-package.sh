#!/bin/bash

# Generate K8s Deployment Package for Jenkins
# This script creates a deployment package with all necessary files

set -e

# Default values
IMAGE_TAG="${IMAGE_TAG:-latest}"
VERSION="${VERSION:-1.0.0}"
BUILD_NUMBER="${BUILD_NUMBER:-1}"
IMAGE_REGISTRY="${IMAGE_REGISTRY:-dockerhub.cisco.com}"
IMAGE_REPO="${IMAGE_REPO:-robot-dockerprod}"
IMAGE_NAME="${IMAGE_NAME:-k8s-ai-agent}"

# Create deployment package directory
PACKAGE_DIR="k8s-ai-agent-deployment-${VERSION}-${BUILD_NUMBER}"
mkdir -p "$PACKAGE_DIR"

echo "Creating K8s AI Agent deployment package..."
echo "Package: $PACKAGE_DIR"
echo "Image: ${IMAGE_REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

# Copy deployment script
cp scripts/easy-deploy.sh "$PACKAGE_DIR/"
chmod +x "$PACKAGE_DIR/easy-deploy.sh"

# Copy existing k8s manifests
if [ -d "k8s" ]; then
    cp -r k8s "$PACKAGE_DIR/"
fi

# Generate environment-specific deployment packages
ENVIRONMENTS=("local" "dev" "staging" "prod")

for env in "${ENVIRONMENTS[@]}"; do
    echo "Generating $env deployment package..."
    
    # Run easy-deploy script to generate manifests for each environment
    ./scripts/easy-deploy.sh \
        --environment "$env" \
        --tag "$IMAGE_TAG" \
        --registry "$IMAGE_REGISTRY" \
        --repo "$IMAGE_REPO" \
        --image-name "$IMAGE_NAME" \
        --no-apply
    
    # Move generated directory to package
    if [ -d "deploy-${env}-${IMAGE_TAG}" ]; then
        mv "deploy-${env}-${IMAGE_TAG}" "$PACKAGE_DIR/"
    fi
done

# Create deployment guide
cat > "$PACKAGE_DIR/DEPLOYMENT_GUIDE.md" << EOF
# K8s AI Agent Deployment Package

**Version:** ${VERSION}-${BUILD_NUMBER}  
**Image:** ${IMAGE_REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${IMAGE_TAG}  
**Generated:** $(date)

## Contents

This package contains deployment manifests and scripts for the K8s AI Agent across different environments.

### Directory Structure
\`\`\`
k8s-ai-agent-deployment-${VERSION}-${BUILD_NUMBER}/
├── easy-deploy.sh                    # Easy deployment script
├── k8s/                             # Original Kubernetes manifests
├── deploy-local-${IMAGE_TAG}/        # Local environment manifests
├── deploy-dev-${IMAGE_TAG}/          # Development environment manifests
├── deploy-staging-${IMAGE_TAG}/      # Staging environment manifests
├── deploy-prod-${IMAGE_TAG}/         # Production environment manifests
├── DEPLOYMENT_GUIDE.md              # This file
└── quick-start.sh                   # Quick start script
\`\`\`

## Quick Start

### 1. Extract and Navigate
\`\`\`bash
# If downloaded as zip
unzip k8s-ai-agent-deployment-${VERSION}-${BUILD_NUMBER}.zip
cd k8s-ai-agent-deployment-${VERSION}-${BUILD_NUMBER}
\`\`\`

### 2. Choose Your Deployment Method

#### Option A: Use Easy Deploy Script (Recommended)
\`\`\`bash
# Local deployment
./easy-deploy.sh -e local

# Development deployment  
./easy-deploy.sh -e dev -n k8s-ai-agent-dev

# Staging deployment
./easy-deploy.sh -e staging -n k8s-ai-agent-staging -t ${IMAGE_TAG}

# Production deployment (dry-run first)
./easy-deploy.sh -e prod -n k8s-ai-agent-prod -t ${IMAGE_TAG} --dry-run
./easy-deploy.sh -e prod -n k8s-ai-agent-prod -t ${IMAGE_TAG}
\`\`\`

#### Option B: Use Pre-generated Manifests
\`\`\`bash
# Deploy to local environment
kubectl apply -f deploy-local-${IMAGE_TAG}/

# Deploy to staging environment
kubectl apply -f deploy-staging-${IMAGE_TAG}/

# Deploy to production environment
kubectl apply -f deploy-prod-${IMAGE_TAG}/
\`\`\`

#### Option C: Use Original Manifests
\`\`\`bash
# Apply base manifests and update image
kubectl apply -f k8s/
kubectl set image deployment/k8s-ai-agent ai-agent=${IMAGE_REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${IMAGE_TAG} -n default
\`\`\`

## Environment Configurations

| Environment | Replicas | Service Type | Resources | Features |
|-------------|----------|--------------|-----------|----------|
| **Local**   | 1        | NodePort     | Minimal   | Basic monitoring |
| **Dev**     | 1        | ClusterIP    | Standard  | Debug mode, monitoring |
| **Staging** | 2        | LoadBalancer | Enhanced  | Full monitoring, HPA |
| **Prod**    | 3        | LoadBalancer | Maximum   | Full monitoring, HPA, alerts |

## Access Methods

### Local Environment (NodePort)
\`\`\`bash
# Get node port
kubectl get svc k8s-ai-agent-service -n k8s-ai-agent

# Access via any node IP
# UI: http://<NODE-IP>:<NODEPORT>
\`\`\`

### Staging/Production (LoadBalancer)
\`\`\`bash
# Get external IP
kubectl get svc k8s-ai-agent-service -n <namespace>

# Access via LoadBalancer IP
# UI: http://<EXTERNAL-IP>:8501
\`\`\`

### Development (ClusterIP)
\`\`\`bash
# Port forward for access
kubectl port-forward svc/k8s-ai-agent-service 8501:8501 -n <namespace>

# Access locally
# UI: http://localhost:8501
\`\`\`

## Verification

### Check Deployment Status
\`\`\`bash
# Check pods
kubectl get pods -n <namespace> -l app=k8s-ai-agent

# Check deployment
kubectl get deployment k8s-ai-agent -n <namespace>

# Check service
kubectl get service k8s-ai-agent-service -n <namespace>

# View logs
kubectl logs -f deployment/k8s-ai-agent -n <namespace>
\`\`\`

### Health Check
\`\`\`bash
# Direct health check (if port-forwarded)
curl http://localhost:8501/healthz

# Via service (replace with actual service IP/port)
curl http://<SERVICE-IP>:8501/healthz
\`\`\`

## Configuration

### Runtime Configuration
The AI Agent supports runtime configuration through ConfigMaps. Key settings:

- **MODE**: Operation mode (interactive, debug, remediation, monitoring, hybrid)
- **UI_INTERACTIVE**: Always keep UI interactive
- **ENABLE_HISTORICAL_LEARNING**: Enable learning from past issues
- **LOG_LEVEL**: Logging verbosity (DEBUG, INFO, WARN, ERROR)

### Environment Variables
All environments include these configurable options:
- Application behavior settings
- Resource limits and requests
- Monitoring and alerting configuration
- Feature toggles

## Troubleshooting

### Common Issues

1. **Image Pull Errors**
   \`\`\`bash
   # Check image exists
   docker pull ${IMAGE_REGISTRY}/${IMAGE_REPO}/${IMAGE_NAME}:${IMAGE_TAG}
   
   # Check image pull secrets
   kubectl get secrets -n <namespace>
   \`\`\`

2. **Pod Startup Issues**
   \`\`\`bash
   # Describe pod for events
   kubectl describe pod <pod-name> -n <namespace>
   
   # Check resource constraints
   kubectl top pods -n <namespace>
   \`\`\`

3. **Service Access Issues**
   \`\`\`bash
   # Check service endpoints
   kubectl get endpoints -n <namespace>
   
   # Test service connectivity
   kubectl exec -it <pod-name> -n <namespace> -- curl localhost:8501/healthz
   \`\`\`

### Getting Help
- Check pod logs: \`kubectl logs <pod-name> -n <namespace>\`
- Describe resources: \`kubectl describe <resource> <name> -n <namespace>\`
- Check events: \`kubectl get events -n <namespace> --sort-by='.lastTimestamp'\`

## Cleanup

### Remove Specific Environment
\`\`\`bash
# Remove specific deployment
kubectl delete -f deploy-<environment>-${IMAGE_TAG}/

# Or remove by namespace
kubectl delete namespace <namespace>
\`\`\`

### Complete Cleanup
\`\`\`bash
# Remove all environments (if using default namespaces)
kubectl delete -f deploy-local-${IMAGE_TAG}/
kubectl delete -f deploy-dev-${IMAGE_TAG}/
kubectl delete -f deploy-staging-${IMAGE_TAG}/
kubectl delete -f deploy-prod-${IMAGE_TAG}/
\`\`\`

## Support

For issues with deployment:
1. Check the troubleshooting section above
2. Review the generated README.md in each environment directory
3. Examine the easy-deploy.sh script for additional options
4. Contact the development team with specific error messages

---
**Package Generated:** $(date)  
**Jenkins Build:** ${BUILD_NUMBER}  
**Git Branch:** ${GIT_BRANCH:-main}
EOF

# Create quick start script
cat > "$PACKAGE_DIR/quick-start.sh" << 'EOF'
#!/bin/bash

# Quick Start Script for K8s AI Agent

set -e

echo "K8s AI Agent Quick Start"
echo "======================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if connected to cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "ERROR: Not connected to Kubernetes cluster"
    exit 1
fi

echo "Select deployment environment:"
echo "1) Local (single replica, NodePort)"
echo "2) Development (single replica, ClusterIP)" 
echo "3) Staging (2 replicas, LoadBalancer)"
echo "4) Production (3 replicas, LoadBalancer)"
echo "5) Custom (use easy-deploy.sh with options)"

read -p "Choose option [1-5]: " choice

case $choice in
    1)
        echo "Deploying to local environment..."
        ./easy-deploy.sh -e local
        ;;
    2)
        echo "Deploying to development environment..."
        ./easy-deploy.sh -e dev -n k8s-ai-agent-dev
        ;;
    3)
        echo "Deploying to staging environment..."
        ./easy-deploy.sh -e staging -n k8s-ai-agent-staging
        ;;
    4)
        read -p "This will deploy to PRODUCTION. Are you sure? (yes/no): " confirm
        if [[ "$confirm" == "yes" ]]; then
            echo "Deploying to production environment..."
            ./easy-deploy.sh -e prod -n k8s-ai-agent-prod
        else
            echo "Production deployment cancelled."
        fi
        ;;
    5)
        echo "Run: ./easy-deploy.sh --help for all options"
        echo "Example: ./easy-deploy.sh -e staging -n my-namespace -t latest"
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo "Quick start completed!"
EOF

chmod +x "$PACKAGE_DIR/quick-start.sh"

# Create zip file
ZIP_FILE="${PACKAGE_DIR}.zip"
echo "Creating zip file: $ZIP_FILE"
zip -r "$ZIP_FILE" "$PACKAGE_DIR/" -x "*.DS_Store"

# Create checksum
echo "Generating checksum..."
if command -v sha256sum &> /dev/null; then
    sha256sum "$ZIP_FILE" > "${ZIP_FILE}.sha256"
elif command -v shasum &> /dev/null; then
    shasum -a 256 "$ZIP_FILE" > "${ZIP_FILE}.sha256"
fi

echo "Deployment package created successfully!"
echo "Package: $ZIP_FILE"
echo "Size: $(du -h "$ZIP_FILE" | cut -f1)"

# List contents
echo ""
echo "Package contents:"
unzip -l "$ZIP_FILE" | head -20

# Keep the directory for Jenkins artifacts
echo ""
echo "Directory $PACKAGE_DIR kept for Jenkins artifacts"
