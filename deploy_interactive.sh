#!/bin/bash

# Deploy Interactive Kubernetes AI Chat
# This script builds and deploys the enhanced interactive UI

set -e

NAMESPACE="default"
APP_NAME="k8s-ai-agent"
IMAGE_NAME="dockerhub.cisco.com/robot-dockerprod/k8s-ai-agent:latest"

echo "🚀 Deploying Interactive Kubernetes AI Chat..."

# Build the Docker image with interactive chat
echo "📦 Building Docker image..."
docker build -t ${IMAGE_NAME} .

# Push the image (if using external registry)
echo "📤 Pushing Docker image..."
docker push ${IMAGE_NAME}

# Apply RBAC first
echo "🔐 Creating ServiceAccount and RBAC..."
kubectl apply -f k8s/02-rbac.yaml

# Apply main application manifest
echo "🚀 Deploying Interactive AI Agent..."
kubectl apply -f k8s/k8s-ai-agent.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s

# Check pod status
echo "📊 Checking pod status..."
kubectl get pods -l app=${APP_NAME} -n ${NAMESPACE}

# Show service information
echo "🌐 Service information:"
kubectl get svc ${APP_NAME} -n ${NAMESPACE}

# Get the NodePort URL
NODE_PORT=$(kubectl get svc ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')
echo ""
echo "✅ Interactive AI Chat deployed successfully!"
echo ""
echo "🌐 Access the Interactive UI at:"
echo "   http://<your-node-ip>:${NODE_PORT}"
echo ""
echo "🔍 To check logs:"
echo "   kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} -f"
echo ""
echo "💬 The interactive chat will allow you to:"
echo "   - Ask 'get all pods' to see real pod information"
echo "   - Ask 'get nodes' to see cluster nodes" 
echo "   - Ask 'cluster status' for comprehensive health check"
echo "   - Type any question about your Kubernetes cluster"
echo ""
echo "🔧 To troubleshoot:"
echo "   kubectl describe pod -l app=${APP_NAME} -n ${NAMESPACE}"
