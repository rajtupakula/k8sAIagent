#!/bin/bash
# Runtime Configuration Management Script for Kubernetes AI Assistant
# This script demonstrates how to modify the AI assistant configuration at runtime

set -e

NAMESPACE="${NAMESPACE:-default}"
CONFIGMAP_NAME="k8s-ai-runtime-config"
DEPLOYMENT_NAME="k8s-ai-assistant"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎛️ Kubernetes AI Assistant Runtime Configuration Manager${NC}"
echo "=================================================="

# Function to update configuration
update_config() {
    local key=$1
    local value=$2
    
    echo -e "${YELLOW}Updating ${key} to ${value}...${NC}"
    
    # Update ConfigMap
    kubectl patch configmap $CONFIGMAP_NAME -n $NAMESPACE \
        --type merge -p "{\"data\":{\"$key\":\"$value\"}}"
    
    echo -e "${GREEN}✅ ConfigMap updated${NC}"
    
    # Restart pods to pick up environment variable changes
    kubectl rollout restart deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    
    echo -e "${GREEN}✅ Deployment restarted to pick up new configuration${NC}"
    echo "⏳ Waiting for rollout to complete..."
    
    kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    
    echo -e "${GREEN}✅ Configuration update complete!${NC}"
    echo ""
}

# Function to show current configuration
show_config() {
    echo -e "${BLUE}📊 Current Configuration:${NC}"
    echo "========================="
    
    # Get current config from ConfigMap
    echo -e "${YELLOW}ConfigMap Data:${NC}"
    kubectl get configmap $CONFIGMAP_NAME -n $NAMESPACE -o jsonpath='{.data}' | jq .
    
    echo ""
    echo -e "${YELLOW}Pod Environment Variables:${NC}"
    kubectl get pods -l app=k8s-ai-assistant -n $NAMESPACE -o jsonpath='{.items[0].spec.containers[0].env[*]}' | jq .
    
    echo ""
}

# Function to apply predefined configuration modes
apply_mode() {
    local mode=$1
    
    echo -e "${BLUE}🎯 Applying $mode mode configuration...${NC}"
    
    case $mode in
        "debug")
            update_config "mode" "debug"
            update_config "automation_level" "manual"
            update_config "backend_auto_remediation" "false"
            update_config "confidence_threshold" "95"
            ;;
        "remediation")
            update_config "mode" "remediation"
            update_config "automation_level" "full_auto"
            update_config "backend_auto_remediation" "true"
            update_config "confidence_threshold" "85"
            update_config "continuous_monitoring" "true"
            ;;
        "interactive")
            update_config "mode" "interactive"
            update_config "automation_level" "semi_auto"
            update_config "backend_auto_remediation" "false"
            update_config "confidence_threshold" "75"
            ;;
        "monitoring")
            update_config "mode" "monitoring"
            update_config "automation_level" "semi_auto"
            update_config "backend_auto_remediation" "false"
            update_config "continuous_monitoring" "true"
            update_config "predictive_analysis" "true"
            ;;
        "hybrid")
            update_config "mode" "hybrid"
            update_config "automation_level" "semi_auto"
            update_config "backend_auto_remediation" "true"
            update_config "confidence_threshold" "80"
            update_config "continuous_monitoring" "true"
            update_config "predictive_analysis" "true"
            ;;
        *)
            echo -e "${RED}❌ Unknown mode: $mode${NC}"
            echo "Available modes: debug, remediation, interactive, monitoring, hybrid"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}🎉 $mode mode configuration applied successfully!${NC}"
}

# Function to enable/disable features
toggle_feature() {
    local feature=$1
    local enabled=$2
    
    case $feature in
        "auto-remediation")
            update_config "backend_auto_remediation" "$enabled"
            ;;
        "historical-learning")
            update_config "historical_learning" "$enabled"
            ;;
        "predictive-analysis")
            update_config "predictive_analysis" "$enabled"
            ;;
        "continuous-monitoring")
            update_config "continuous_monitoring" "$enabled"
            ;;
        "safety-checks")
            update_config "safety_checks" "$enabled"
            ;;
        *)
            echo -e "${RED}❌ Unknown feature: $feature${NC}"
            echo "Available features: auto-remediation, historical-learning, predictive-analysis, continuous-monitoring, safety-checks"
            exit 1
            ;;
    esac
}

# Function to set confidence threshold
set_confidence() {
    local threshold=$1
    
    if [[ $threshold -lt 0 || $threshold -gt 100 ]]; then
        echo -e "${RED}❌ Confidence threshold must be between 0 and 100${NC}"
        exit 1
    fi
    
    update_config "confidence_threshold" "$threshold"
}

# Function to check if resources exist
check_resources() {
    echo -e "${BLUE}🔍 Checking Kubernetes resources...${NC}"
    
    # Check if ConfigMap exists
    if kubectl get configmap $CONFIGMAP_NAME -n $NAMESPACE >/dev/null 2>&1; then
        echo -e "${GREEN}✅ ConfigMap $CONFIGMAP_NAME exists${NC}"
    else
        echo -e "${RED}❌ ConfigMap $CONFIGMAP_NAME not found${NC}"
        echo "Please deploy the ConfigMap first using: kubectl apply -f k8s/runtime-configmap.yaml"
        exit 1
    fi
    
    # Check if Deployment exists
    if kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Deployment $DEPLOYMENT_NAME exists${NC}"
    else
        echo -e "${RED}❌ Deployment $DEPLOYMENT_NAME not found${NC}"
        echo "Please deploy the application first"
        exit 1
    fi
    
    echo ""
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  show-config                     Show current configuration"
    echo "  apply-mode <mode>              Apply predefined mode configuration"
    echo "  set-confidence <threshold>     Set confidence threshold (0-100)"
    echo "  enable-feature <feature>       Enable a specific feature"
    echo "  disable-feature <feature>      Disable a specific feature"
    echo "  update <key> <value>           Update specific configuration key"
    echo ""
    echo "Modes:"
    echo "  debug                          Root cause analysis only"
    echo "  remediation                    Auto-remediation with high confidence"
    echo "  interactive                    User-guided operations"
    echo "  monitoring                     Real-time monitoring and alerts"
    echo "  hybrid                         Adaptive combination of modes"
    echo ""
    echo "Features:"
    echo "  auto-remediation               Backend automatic remediation"
    echo "  historical-learning            Learn from past incidents"
    echo "  predictive-analysis            Predict potential issues"
    echo "  continuous-monitoring          Real-time cluster monitoring"
    echo "  safety-checks                  Enhanced safety validations"
    echo ""
    echo "Examples:"
    echo "  $0 show-config"
    echo "  $0 apply-mode remediation"
    echo "  $0 set-confidence 90"
    echo "  $0 enable-feature auto-remediation"
    echo "  $0 disable-feature predictive-analysis"
    echo "  $0 update mode debug"
    echo ""
    echo "Environment Variables:"
    echo "  NAMESPACE                      Kubernetes namespace (default: default)"
}

# Main script logic
case "${1:-help}" in
    "show-config")
        check_resources
        show_config
        ;;
    "apply-mode")
        if [[ -z "$2" ]]; then
            echo -e "${RED}❌ Mode required${NC}"
            echo "Usage: $0 apply-mode <mode>"
            exit 1
        fi
        check_resources
        apply_mode "$2"
        ;;
    "set-confidence")
        if [[ -z "$2" ]]; then
            echo -e "${RED}❌ Confidence threshold required${NC}"
            echo "Usage: $0 set-confidence <threshold>"
            exit 1
        fi
        check_resources
        set_confidence "$2"
        ;;
    "enable-feature")
        if [[ -z "$2" ]]; then
            echo -e "${RED}❌ Feature name required${NC}"
            echo "Usage: $0 enable-feature <feature>"
            exit 1
        fi
        check_resources
        toggle_feature "$2" "true"
        ;;
    "disable-feature")
        if [[ -z "$2" ]]; then
            echo -e "${RED}❌ Feature name required${NC}"
            echo "Usage: $0 disable-feature <feature>"
            exit 1
        fi
        check_resources
        toggle_feature "$2" "false"
        ;;
    "update")
        if [[ -z "$2" || -z "$3" ]]; then
            echo -e "${RED}❌ Key and value required${NC}"
            echo "Usage: $0 update <key> <value>"
            exit 1
        fi
        check_resources
        update_config "$2" "$3"
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
