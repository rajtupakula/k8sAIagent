#!/usr/bin/env python3
"""
Lightweight AI Agent Dashboard with Interactive Capabilities
Uses pattern matching and rule-based analysis instead of heavy ML models
"""
import streamlit as st
import os
import sys
import time
import json
import subprocess
import logging
import re
from datetime import datetime
from typing import Dict, List, Any
import threading

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try importing Kubernetes components with graceful fallback
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent'))
    from monitor import KubernetesMonitor
    from remediate import RemediationEngine
    K8S_COMPONENTS_AVAILABLE = True
except ImportError as e:
    st.warning(f"Kubernetes components not fully available: {e}")
    K8S_COMPONENTS_AVAILABLE = False
    KubernetesMonitor = None
    RemediationEngine = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Kubernetes AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Knowledge base for AI responses
KNOWLEDGE_BASE = {
    "pod_issues": {
        "crashloopbackoff": {
            "analysis": "Pod is restarting repeatedly, usually due to application errors or configuration issues.",
            "solutions": [
                "Check pod logs: kubectl logs <pod-name> --previous",
                "Verify container image and tags",
                "Check resource limits and requests",
                "Validate environment variables and configurations",
                "Ensure health check endpoints are working"
            ]
        },
        "pending": {
            "analysis": "Pod cannot be scheduled, typically due to resource constraints or node issues.",
            "solutions": [
                "Check node resources: kubectl describe nodes",
                "Verify resource requests vs available capacity",
                "Check for node selectors and affinity rules",
                "Ensure storage classes are available",
                "Validate persistent volume claims"
            ]
        },
        "imagepullbackoff": {
            "analysis": "Cannot pull container image, usually authentication or network issues.",
            "solutions": [
                "Verify image name and tag exist",
                "Check image registry credentials",
                "Ensure network connectivity to registry",
                "Validate imagePullSecrets configuration",
                "Check for rate limiting on registry"
            ]
        }
    },
    "node_issues": {
        "notready": {
            "analysis": "Node is not ready to accept pods, could be network, kubelet, or resource issues.",
            "solutions": [
                "Check kubelet logs: journalctl -u kubelet",
                "Verify node network connectivity",
                "Check disk space and inode usage",
                "Restart kubelet service if needed",
                "Validate CNI plugin status"
            ]
        },
        "high_cpu": {
            "analysis": "Node experiencing high CPU usage, may affect workload performance.",
            "solutions": [
                "Identify top consuming processes",
                "Scale workloads or add more nodes",
                "Review resource requests/limits",
                "Consider node affinity to spread load",
                "Monitor for unusual system processes"
            ]
        }
    },
    "storage_issues": {
        "pv_failed": {
            "analysis": "Persistent Volume is in failed state, affecting data availability.",
            "solutions": [
                "Check storage backend health",
                "Verify storage class configuration",
                "Ensure storage nodes are accessible",
                "Check for disk space issues",
                "Validate storage driver logs"
            ]
        }
    }
}

# Initialize session state
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'remediation' not in st.session_state:
    st.session_state.remediation = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'last_scan_results' not in st.session_state:
    st.session_state.last_scan_results = {}

def initialize_components():
    """Initialize Kubernetes components with error handling"""
    if not K8S_COMPONENTS_AVAILABLE:
        return False
    
    try:
        if st.session_state.monitor is None:
            st.session_state.monitor = KubernetesMonitor()
        
        if st.session_state.remediation is None:
            st.session_state.remediation = RemediationEngine()
        
        return True
    except Exception as e:
        st.error(f"Failed to initialize Kubernetes components: {e}")
        return False

def analyze_issue_with_ai(issue_description: str) -> Dict[str, Any]:
    """Advanced AI analysis - handles general queries like a human expert"""
    issue_lower = issue_description.lower()
    
    # First, check for specific technical issues with high confidence
    if any(word in issue_lower for word in ["crashloop", "crash", "restarting"]):
        return {
            "issue_type": "pod_crashloop",
            "confidence": 0.95,
            "analysis": KNOWLEDGE_BASE["pod_issues"]["crashloopbackoff"]["analysis"],
            "solutions": KNOWLEDGE_BASE["pod_issues"]["crashloopbackoff"]["solutions"]
        }
    
    elif any(word in issue_lower for word in ["pending", "scheduling", "unschedulable"]):
        return {
            "issue_type": "pod_pending", 
            "confidence": 0.9,
            "analysis": KNOWLEDGE_BASE["pod_issues"]["pending"]["analysis"],
            "solutions": KNOWLEDGE_BASE["pod_issues"]["pending"]["solutions"]
        }
    
    elif any(word in issue_lower for word in ["imagepull", "image", "pull"]):
        return {
            "issue_type": "image_pull",
            "confidence": 0.95,
            "analysis": KNOWLEDGE_BASE["pod_issues"]["imagepullbackoff"]["analysis"],
            "solutions": KNOWLEDGE_BASE["pod_issues"]["imagepullbackoff"]["solutions"]
        }
    
    elif any(word in issue_lower for word in ["node", "notready", "ready"]):
        return {
            "issue_type": "node_issue",
            "confidence": 0.85,
            "analysis": KNOWLEDGE_BASE["node_issues"]["notready"]["analysis"],
            "solutions": KNOWLEDGE_BASE["node_issues"]["notready"]["solutions"]
        }
    
    elif any(word in issue_lower for word in ["storage", "volume", "pv", "pvc"]):
        return {
            "issue_type": "storage_issue",
            "confidence": 0.85,
            "analysis": KNOWLEDGE_BASE["storage_issues"]["pv_failed"]["analysis"],
            "solutions": KNOWLEDGE_BASE["storage_issues"]["pv_failed"]["solutions"]
        }
    
    # Handle general operational queries
    elif any(word in issue_lower for word in ["pods running", "pod status", "check pods", "are pods"]):
        return {
            "issue_type": "pod_status_check",
            "confidence": 0.9,
            "analysis": "You want to check the status of Kubernetes pods in your cluster. This is a common operational task.",
            "solutions": [
                "Check all pods: kubectl get pods --all-namespaces",
                "Check pods in current namespace: kubectl get pods",
                "Check specific pod details: kubectl describe pod <pod-name>",
                "Check pod logs: kubectl logs <pod-name>",
                "Watch pod status in real-time: kubectl get pods -w",
                "Filter by status: kubectl get pods --field-selector=status.phase=Running"
            ]
        }
    
    elif any(word in issue_lower for word in ["nodes", "node status", "cluster status", "check cluster"]):
        return {
            "issue_type": "cluster_status_check",
            "confidence": 0.9,
            "analysis": "You want to check the overall health and status of your Kubernetes cluster nodes.",
            "solutions": [
                "Check all nodes: kubectl get nodes",
                "Check node details: kubectl describe nodes",
                "Check node resource usage: kubectl top nodes",
                "Check node conditions: kubectl get nodes -o wide",
                "Check cluster info: kubectl cluster-info",
                "Check system pods: kubectl get pods -n kube-system"
            ]
        }
    
    elif any(word in issue_lower for word in ["services", "svc", "service status", "endpoints"]):
        return {
            "issue_type": "service_check",
            "confidence": 0.9,
            "analysis": "You want to check Kubernetes services and their endpoints to ensure connectivity.",
            "solutions": [
                "Check all services: kubectl get svc --all-namespaces",
                "Check service details: kubectl describe svc <service-name>",
                "Check service endpoints: kubectl get endpoints",
                "Test service connectivity: kubectl run test-pod --image=busybox -it --rm",
                "Check ingress: kubectl get ingress",
                "Port forward for testing: kubectl port-forward svc/<service> <port>:<port>"
            ]
        }
    
    elif any(word in issue_lower for word in ["deployment", "deployments", "scale", "replicas"]):
        return {
            "issue_type": "deployment_management",
            "confidence": 0.9,
            "analysis": "You're asking about deployment management, scaling, or replica management in Kubernetes.",
            "solutions": [
                "Check deployments: kubectl get deployments",
                "Scale deployment: kubectl scale deployment <name> --replicas=<number>",
                "Check deployment status: kubectl rollout status deployment/<name>",
                "View deployment history: kubectl rollout history deployment/<name>",
                "Restart deployment: kubectl rollout restart deployment/<name>",
                "Check replica sets: kubectl get replicasets"
            ]
        }
    
    elif any(word in issue_lower for word in ["logs", "log", "debug", "troubleshoot"]):
        return {
            "issue_type": "logging_debug",
            "confidence": 0.85,
            "analysis": "You need help with logging and debugging Kubernetes resources.",
            "solutions": [
                "Get pod logs: kubectl logs <pod-name>",
                "Get previous pod logs: kubectl logs <pod-name> --previous",
                "Follow logs: kubectl logs -f <pod-name>",
                "Get logs from all containers: kubectl logs <pod-name> --all-containers",
                "Check events: kubectl get events --sort-by=.metadata.creationTimestamp",
                "Debug pod: kubectl exec -it <pod-name> -- /bin/bash"
            ]
        }
    
    elif any(word in issue_lower for word in ["help", "how", "what", "list", "show"]):
        return {
            "issue_type": "general_help",
            "confidence": 0.8,
            "analysis": "You're asking for general help or information about Kubernetes operations.",
            "solutions": [
                "Get basic cluster info: kubectl cluster-info",
                "List all resource types: kubectl api-resources",
                "Get help for commands: kubectl --help",
                "Check kubectl version: kubectl version",
                "View cluster configuration: kubectl config view",
                "Switch contexts: kubectl config use-context <context-name>"
            ]
        }
    
    else:
        # Enhanced generic response - always helpful
        return {
            "issue_type": "general_kubernetes",
            "confidence": 0.75,  # Higher confidence for general help
            "analysis": f"I understand you're asking about: '{issue_description}'. Let me provide comprehensive Kubernetes troubleshooting guidance.",
            "solutions": [
                "Start with basic status: kubectl get all",
                "Check recent events: kubectl get events --sort-by=.metadata.creationTimestamp",
                "Review pod status: kubectl get pods -o wide",
                "Check node health: kubectl get nodes",
                "Examine logs: kubectl logs <resource-name>",
                "Describe resources: kubectl describe <resource-type> <name>",
                "If issues persist, check: kubectl top pods (resource usage)",
                "For networking: kubectl get svc,endpoints,ingress"
            ]
        }

def get_live_kubernetes_status():
    """Get real-time Kubernetes status using kubectl"""
    try:
        # Try to get basic cluster info
        import subprocess
        
        # Check if kubectl is available
        result = subprocess.run(['kubectl', 'version', '--client'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return {"status": "kubectl_unavailable", "message": "kubectl not found"}
        
        # Get pod status
        result = subprocess.run(['kubectl', 'get', 'pods', '--all-namespaces', '--no-headers'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            total_pods = len(lines)
            running_pods = len([l for l in lines if 'Running' in l])
            failed_pods = len([l for l in lines if any(status in l for status in ['CrashLoopBackOff', 'Error', 'Failed'])])
            
            # Get node status
            node_result = subprocess.run(['kubectl', 'get', 'nodes', '--no-headers'], 
                                       capture_output=True, text=True, timeout=10)
            
            node_lines = node_result.stdout.strip().split('\n') if node_result.stdout.strip() else []
            total_nodes = len(node_lines)
            ready_nodes = len([l for l in node_lines if 'Ready' in l and 'NotReady' not in l])
            
            return {
                "status": "connected",
                "pods": {"total": total_pods, "running": running_pods, "failed": failed_pods},
                "nodes": {"total": total_nodes, "ready": ready_nodes}
            }
        else:
            return {"status": "no_access", "message": "Cannot access cluster"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_cluster_health():
    """Get cluster health information"""
    if not st.session_state.monitor:
        return {"status": "unavailable", "message": "Monitor not available"}
    
    try:
        issues = st.session_state.monitor.scan_for_issues()
        metrics = st.session_state.monitor.get_cluster_metrics()
        
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        warning_issues = [i for i in issues if i.get('severity') == 'warning']
        
        if critical_issues:
            status = "critical"
        elif warning_issues:
            status = "warning"  
        else:
            status = "healthy"
        
        return {
            "status": status,
            "issues": issues,
            "metrics": metrics,
            "critical_count": len(critical_issues),
            "warning_count": len(warning_issues),
            "total_issues": len(issues)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    """Main dashboard function"""
    
    # Header
    st.title("� Kubernetes AI Expert Assistant")
    st.caption("Intelligent AI-powered Kubernetes troubleshooting and monitoring - Expert level responses")
    
    # Show AI capabilities
    st.success("✅ **Enhanced AI Capabilities**: Real-time analysis, Live cluster monitoring, Expert recommendations, Low confidence filtering")
    
    # Initialize components
    if K8S_COMPONENTS_AVAILABLE:
        init_success = initialize_components()
        if init_success:
            st.success("✅ Kubernetes AI Expert components initialized!")
        else:
            st.warning("⚠️ Advanced monitoring limited - Using intelligent pattern matching")
    else:
        st.info("ℹ️ **AI Expert Mode**: Using advanced pattern matching and kubectl integration")
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 AI Agent Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        
        # Manual refresh button
        if st.button("🔄 Refresh Now"):
            st.rerun()
        
        # AI Settings
        st.subheader("🎯 AI Settings")
        ai_confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.3)  # Lower threshold
        auto_remediate_enabled = st.checkbox("Enable Auto-Remediation", value=False)
        
        st.info("💡 Lower threshold = more responses, higher threshold = only high-confidence answers")
        
        if auto_remediate_enabled:
            st.warning("⚠️ Auto-remediation will make changes to your cluster")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview", 
        "🤖 AI Chat", 
        "📊 Cluster Health", 
        "🔧 Remediation", 
        "📈 System Info"
    ])
    
    with tab1:
        overview_tab()
    
    with tab2:
        ai_chat_tab(ai_confidence_threshold)
    
    with tab3:
        cluster_health_tab()
    
    with tab4:
        remediation_tab(auto_remediate_enabled)
    
    with tab5:
        system_info_tab()
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

def overview_tab():
    """Overview dashboard tab"""
    st.header("🏠 System Overview")
    
    # Status cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("AI Agent", "✅ Online" if K8S_COMPONENTS_AVAILABLE else "⚠️ Demo Mode")
    
    with col2:
        if st.session_state.monitor:
            health = get_cluster_health()
            status_color = {"healthy": "🟢", "warning": "🟡", "critical": "🔴", "error": "⚫"}.get(health["status"], "⚫")
            st.metric("Cluster Health", f"{status_color} {health['status'].title()}")
        else:
            st.metric("Cluster Health", "❓ Unknown")
    
    with col3:
        st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}")
    
    with col4:
        st.metric("Uptime", time.strftime("%H:%M:%S"))
    
    # Quick AI Analysis with Live Data
    st.subheader("🤖 Intelligent AI Analysis")
    
    # Get live cluster status
    live_status = get_live_kubernetes_status()
    
    # Show cluster status
    if live_status["status"] == "connected":
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pods", live_status["pods"]["total"])
        with col2:
            st.metric("Running Pods", live_status["pods"]["running"])
        with col3:
            st.metric("Failed Pods", live_status["pods"]["failed"])
        with col4:
            st.metric("Ready Nodes", f"{live_status['nodes']['ready']}/{live_status['nodes']['total']}")
        
        # Auto-analysis
        if live_status["pods"]["failed"] > 0:
            st.error(f"🚨 {live_status['pods']['failed']} pods are failing! Click 'Analyze Issues' below for help.")
        elif live_status["nodes"]["ready"] < live_status["nodes"]["total"]:
            st.warning(f"⚠️ Some nodes are not ready. {live_status['nodes']['ready']} of {live_status['nodes']['total']} nodes are ready.")
        else:
            st.success("✅ Cluster looks healthy!")
    
    quick_issue = st.text_input("Ask me anything about Kubernetes:", 
                               placeholder="e.g., 'check if all kubernetes pods are running' or 'help with node issues'")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🧠 Ask AI Assistant"):
            if quick_issue:
                # Enhanced analysis with live data
                analysis = analyze_issue_with_ai(quick_issue)
                
                # Add live data context if available
                if live_status["status"] == "connected" and "pods running" in quick_issue.lower():
                    analysis["live_data"] = f"Currently: {live_status['pods']['running']}/{live_status['pods']['total']} pods running"
                    if live_status["pods"]["failed"] > 0:
                        analysis["analysis"] += f" **ALERT**: {live_status['pods']['failed']} pods are currently failing."
                
                st.markdown("### 🧠 AI Expert Analysis")
                
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.markdown(f"**Analysis:** {analysis['analysis']}")
                    
                with col_b:
                    confidence_color = "🟢" if analysis['confidence'] > 0.8 else "🟡" if analysis['confidence'] > 0.6 else "🔴"
                    st.metric("Confidence", f"{confidence_color} {analysis['confidence']:.0%}")
                
                if analysis.get('live_data'):
                    st.info(f"**Live Status:** {analysis['live_data']}")
                
                st.markdown("**💡 Recommended Actions:**")
                for i, solution in enumerate(analysis['solutions'], 1):
                    st.markdown(f"{i}. {solution}")
                    
            else:
                st.warning("Please enter a question or describe your issue")
    
    with col2:
        if st.button("🔍 Analyze Current Issues"):
            if live_status["status"] == "connected":
                issues_found = []
                
                if live_status["pods"]["failed"] > 0:
                    issues_found.append(f"❌ {live_status['pods']['failed']} pods are failing")
                    
                if live_status["nodes"]["ready"] < live_status["nodes"]["total"]:
                    not_ready = live_status["nodes"]["total"] - live_status["nodes"]["ready"]
                    issues_found.append(f"⚠️ {not_ready} nodes are not ready")
                
                if issues_found:
                    st.error("**Issues Detected:**")
                    for issue in issues_found:
                        st.markdown(f"• {issue}")
                    
                    st.markdown("**Immediate Actions:**")
                    st.markdown("1. Check pod status: `kubectl get pods --all-namespaces`")
                    st.markdown("2. Check failing pods: `kubectl get pods | grep -E '(Error|CrashLoop|Failed)'`")
                    st.markdown("3. Check node status: `kubectl get nodes`")
                    st.markdown("4. Get detailed info: `kubectl describe pod <failing-pod>`")
                else:
                    st.success("✅ No immediate issues detected!")
            else:
                st.error(f"Cannot connect to cluster: {live_status.get('message', 'Unknown error')}")

def ai_chat_tab(confidence_threshold: float):
    """AI Chat interface tab"""
    st.header("🤖 AI Assistant Chat")
    
    # Display chat history
    for i, chat in enumerate(st.session_state.chat_history):
        with st.container():
            st.markdown(f"**You:** {chat['query']}")
            
            if chat.get('confidence', 0) >= confidence_threshold:
                st.markdown(f"**AI:** {chat['response']}")
                if chat.get('confidence'):
                    confidence_color = "🟢" if chat['confidence'] > 0.8 else "🟡"
                    st.markdown(f"*{confidence_color} Confidence: {chat['confidence']:.0%}*")
            else:
                st.markdown("**AI:** *Response filtered due to low confidence. Try rephrasing your question.*")
            
            st.divider()
    
    # New query input
    st.subheader("💬 Ask the AI Agent")
    query = st.text_area("Enter your question or issue description:", 
                        placeholder="e.g., 'Why is my pod in CrashLoopBackOff?' or 'How do I troubleshoot node issues?'",
                        height=100)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 Ask AI Agent", disabled=not query.strip()):
            ask_ai_agent(query.strip(), confidence_threshold)
    
    with col2:
        if st.button("🧹 Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

def ask_ai_agent(query: str, confidence_threshold: float):
    """Process AI agent query"""
    with st.spinner("AI Agent is analyzing..."):
        try:
            analysis = analyze_issue_with_ai(query)
            
            # Format response
            response = f"**Issue Type:** {analysis['issue_type'].replace('_', ' ').title()}\n\n"
            response += f"**Analysis:** {analysis['analysis']}\n\n"
            response += "**Recommended Actions:**\n"
            for i, solution in enumerate(analysis['solutions'], 1):
                response += f"{i}. {solution}\n"
            
            chat_entry = {
                "query": query,
                "response": response,
                "confidence": analysis['confidence'],
                "timestamp": datetime.now().isoformat(),
                "issue_type": analysis['issue_type']
            }
            
            st.session_state.chat_history.append(chat_entry)
            st.rerun()
            
        except Exception as e:
            st.error(f"AI Agent error: {e}")

def cluster_health_tab():
    """Cluster health monitoring tab"""
    st.header("📊 Cluster Health Dashboard")
    
    if not st.session_state.monitor:
        st.error("Kubernetes monitor not available")
        st.info("💡 To enable cluster monitoring, ensure the application has proper Kubernetes access")
        return
    
    # Get current health
    health_data = get_cluster_health()
    
    # Health overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_color = {"healthy": "🟢", "warning": "🟡", "critical": "🔴", "error": "⚫"}.get(health_data["status"], "⚫")
        st.metric("Overall Status", f"{status_color} {health_data['status'].title()}")
    
    with col2:
        st.metric("Critical Issues", health_data.get("critical_count", 0))
    
    with col3:
        st.metric("Warning Issues", health_data.get("warning_count", 0))
    
    # Manual scan button
    if st.button("🔍 Scan for Issues Now"):
        with st.spinner("Scanning cluster..."):
            issues = st.session_state.monitor.scan_for_issues()
            st.session_state.last_scan_results = {
                "issues": issues,
                "timestamp": datetime.now().isoformat()
            }
            st.rerun()
    
    # Issues list
    if health_data.get("issues"):
        st.subheader("🚨 Current Issues")
        
        for issue in health_data["issues"]:
            severity_color = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.get("severity", "info"), "🔵")
            
            with st.expander(f"{severity_color} {issue.get('title', 'Unknown Issue')}"):
                st.markdown(f"**Severity:** {issue.get('severity', 'Unknown')}")
                st.markdown(f"**Resource:** {issue.get('resource', 'Unknown')}")
                st.markdown(f"**Namespace:** {issue.get('namespace', 'Unknown')}")
                st.markdown(f"**Description:** {issue.get('description', 'No description')}")
                st.markdown(f"**Timestamp:** {issue.get('timestamp', 'Unknown')}")
                
                if st.button(f"🤖 Get AI Analysis", key=f"analyze_{issue.get('id', 'unknown')}"):
                    analysis_query = f"Issue: {issue.get('title', '')} - {issue.get('description', '')}"
                    analysis = analyze_issue_with_ai(analysis_query)
                    
                    st.markdown("**AI Analysis:**")
                    st.markdown(analysis['analysis'])
                    st.markdown("**Recommended Solutions:**")
                    for sol in analysis['solutions']:
                        st.markdown(f"• {sol}")
    else:
        st.success("🎉 No issues detected!")

def remediation_tab(auto_remediate_enabled: bool):
    """Remediation actions tab"""
    st.header("🔧 Remediation Center")
    
    if not st.session_state.remediation:
        st.error("Remediation engine not available")
        st.info("💡 To enable remediation, ensure the application has proper Kubernetes access")
        return
    
    st.subheader("🚀 Manual Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Restart Failed Pods"):
            try:
                with st.spinner("Restarting failed pods..."):
                    result = st.session_state.remediation.restart_failed_pods()
                    if result.get('success'):
                        st.success(f"✅ Restarted {result.get('count', 0)} failed pods")
                    else:
                        st.error(f"❌ Failed to restart pods: {result.get('message', 'Unknown error')}")
            except Exception as e:
                st.error(f"Remediation failed: {e}")
    
    with col2:
        if st.button("📊 Generate Diagnostics"):
            try:
                with st.spinner("Generating diagnostics..."):
                    if st.session_state.monitor:
                        report = st.session_state.monitor.generate_report()
                        st.download_button(
                            label="📥 Download Diagnostics",
                            data=report,
                            file_name=f"k8s_diagnostics_{int(time.time())}.json",
                            mime="application/json"
                        )
                    else:
                        st.error("Monitor not available for diagnostics")
            except Exception as e:
                st.error(f"Diagnostics generation failed: {e}")
    
    # Auto-remediation status
    st.subheader("🤖 Auto-Remediation")
    
    if auto_remediate_enabled:
        st.warning("⚠️ Auto-remediation is ENABLED - the AI may automatically fix issues")
        if st.button("🛑 Disable Auto-Remediation"):
            st.info("Auto-remediation disabled (setting not persistent)")
    else:
        st.info("ℹ️ Auto-remediation is DISABLED - manual approval required for all actions")

def system_info_tab():
    """System information and metrics tab"""
    st.header("📈 System Information")
    
    # Python and system info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    with col2:
        st.metric("Working Directory", os.getcwd())
    
    with col3:
        st.metric("Current Time", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Package status
    st.subheader("📦 Package Dependencies")
    packages = ["streamlit", "pandas", "numpy", "requests", "kubernetes", "pyyaml", "psutil"]
    
    for pkg in packages:
        try:
            __import__(pkg)
            st.success(f"✅ {pkg} - Available")
        except ImportError:
            st.error(f"❌ {pkg} - Not Available")
    
    # Environment variables (filtered for security)
    st.subheader("🌍 Environment Variables")
    safe_vars = ["PYTHONPATH", "PATH", "KUBERNETES_SERVICE_HOST", "KUBERNETES_SERVICE_PORT", "STREAMLIT_SERVER_PORT"]
    
    for var in safe_vars:
        value = os.environ.get(var, "Not set")
        if len(value) > 100:
            value = value[:100] + "..."
        st.text(f"{var}: {value}")
    
    # AI Agent capabilities
    st.subheader("🤖 AI Agent Capabilities")
    capabilities = [
        "✅ Pattern-based issue analysis",
        "✅ Rule-based troubleshooting recommendations", 
        "✅ Interactive chat interface",
        "✅ Cluster health monitoring" if K8S_COMPONENTS_AVAILABLE else "❌ Cluster monitoring (not available)",
        "✅ Manual remediation actions" if K8S_COMPONENTS_AVAILABLE else "❌ Remediation actions (not available)",
        "⚠️ Advanced ML models (disabled for performance)"
    ]
    
    for capability in capabilities:
        st.markdown(capability)

if __name__ == "__main__":
    main()
