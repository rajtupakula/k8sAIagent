#!/bin/bash

# K8s AI Agent Simple Deployment Script
# Following etcd/kafka deployment pattern

set -e

NAMESPACE="default"
APP_NAME="k8s-ai-agent"

echo "Deploying K8s AI Agent..."

# Apply RBAC first
echo "Creating ServiceAccount and RBAC..."
kubectl apply -f 02-rbac.yaml

# Apply main application manifest
echo "Deploying K8s AI Agent application..."
kubectl apply -f k8s-ai-agent.yaml

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s

# Check pod status
echo "Checking pod status..."
kubectl get pods -l app=${APP_NAME} -n ${NAMESPACE}

# Show service information
echo "Service information:"
kubectl get svc ${APP_NAME} -n ${NAMESPACE}

echo "K8s AI Agent deployment completed successfully!"
echo ""
echo "To check logs:"
echo "  kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} -f"
echo ""
echo "To get service endpoint:"
echo "  kubectl get svc ${APP_NAME} -n ${NAMESPACE}"
