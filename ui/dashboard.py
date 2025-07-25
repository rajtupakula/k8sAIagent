#!/usr/bin/env python3
"""
INTERACTIVE KUBERNETES AI AGENT DASHBOARD
Expert-level troubleshooting assistant with real-time chat capabilities
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

# Configure Streamlit page FIRST
st.set_page_config(
    page_title="🤖 Kubernetes AI Agent - Interactive Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try importing Kubernetes components with graceful fallback
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agent'))
    from monitor import KubernetesMonitor
    from remediate import RemediationEngine
    K8S_COMPONENTS_AVAILABLE = True
except ImportError as e:
    K8S_COMPONENTS_AVAILABLE = False
    KubernetesMonitor = None
    RemediationEngine = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# EXPERT AI KNOWLEDGE BASE - Your personal Kubernetes troubleshooting expert
EXPERT_KNOWLEDGE = {
    "pod_issues": {
        "crashloopbackoff": {
            "analysis": "🔍 **Root Cause Analysis**: Pod is stuck in restart loop - application failing to start properly",
            "confidence": 0.95,
            "urgency": "HIGH",
            "solutions": [
                "🔎 **Immediate**: Check logs: `kubectl logs <pod-name> --previous`",
                "🏷️ **Verify**: Container image and tag are correct and exist",
                "⚙️ **Config**: Validate environment variables and config maps",
                "📊 **Resources**: Check if CPU/memory limits are sufficient",
                "🌐 **Network**: Ensure health check endpoints are responding",
                "🔐 **Security**: Verify service account permissions",
                "💾 **Storage**: Check if required volumes are mounted correctly"
            ],
            "prevention": "Implement proper health checks and resource monitoring",
            "related_issues": ["imagepullbackoff", "oomkilled"]
        },
        "pending": {
            "analysis": "⏳ **Root Cause Analysis**: Pod cannot be scheduled - resource or constraint issues",
            "confidence": 0.90,
            "urgency": "MEDIUM",
            "solutions": [
                "🖥️ **Nodes**: Check node capacity: `kubectl describe nodes`",
                "📈 **Resources**: Verify resource requests vs available capacity",
                "🎯 **Affinity**: Review node selectors and affinity rules", 
                "💾 **Storage**: Ensure PVCs and storage classes are available",
                "🏷️ **Taints**: Check for node taints blocking scheduling",
                "🔒 **Security**: Validate pod security policies"
            ],
            "prevention": "Monitor cluster capacity and set appropriate resource requests",
            "related_issues": ["insufficient_resources", "node_not_ready"]
        },
        "imagepullbackoff": {
            "analysis": "🖼️ **Root Cause Analysis**: Cannot pull container image - registry or auth issues",
            "confidence": 0.92,
            "urgency": "HIGH",
            "solutions": [
                "🔍 **Registry**: Verify image name, tag, and registry accessibility",
                "🔑 **Auth**: Check image pull secrets and registry credentials",
                "🌐 **Network**: Test connectivity to image registry",
                "⏱️ **Rate Limits**: Check for registry rate limiting",
                "🏷️ **Tags**: Ensure image tag exists (avoid 'latest' in production)"
            ],
            "prevention": "Use private registry mirrors and implement proper image management",
            "related_issues": ["authentication_failure"]
        },
        "oomkilled": {
            "analysis": "💥 **Root Cause Analysis**: Container killed due to memory exhaustion",
            "confidence": 0.88,
            "urgency": "HIGH", 
            "solutions": [
                "📊 **Memory**: Increase memory limits in deployment spec",
                "🔍 **Profiling**: Analyze application memory usage patterns",
                "⚙️ **Optimization**: Optimize application memory consumption",
                "📈 **Monitoring**: Implement memory usage alerts",
                "🎯 **Requests**: Set appropriate memory requests for scheduling"
            ],
            "prevention": "Proper load testing and memory profiling before deployment",
            "related_issues": ["resource_exhaustion"]
        }
    },
    "node_issues": {
        "notready": {
            "analysis": "🖥️ **Root Cause Analysis**: Node unavailable for pod scheduling - kubelet or system issues",
            "confidence": 0.85,
            "urgency": "CRITICAL",
            "solutions": [
                "🔧 **Kubelet**: Check kubelet logs: `journalctl -u kubelet`",
                "🌐 **Network**: Verify node network connectivity and CNI",
                "💾 **Disk**: Check disk space and inode usage",
                "🔄 **Restart**: Consider kubelet service restart",
                "🐳 **Runtime**: Verify container runtime status"
            ],
            "prevention": "Implement node monitoring and automated health checks",
            "related_issues": ["network_issues", "disk_pressure"]
        },
        "disk_pressure": {
            "analysis": "💾 **Root Cause Analysis**: Node running out of disk space",
            "confidence": 0.90,
            "urgency": "HIGH",
            "solutions": [
                "🧹 **Cleanup**: Remove unused images: `docker system prune`",
                "📊 **Analysis**: Identify large files and logs",
                "📈 **Monitoring**: Set up disk usage alerts",
                "🔄 **Rotation**: Implement log rotation policies"
            ],
            "prevention": "Proactive disk monitoring and automated cleanup",
            "related_issues": ["log_overflow"]
        }
    },
    "service_issues": {
        "no_endpoints": {
            "analysis": "🌐 **Root Cause Analysis**: Service has no healthy backend pods",
            "confidence": 0.88,
            "urgency": "HIGH",
            "solutions": [
                "🎯 **Selectors**: Verify service selector matches pod labels",
                "❤️ **Health**: Check pod readiness probes",
                "🔍 **Pods**: Ensure pods are running and ready",
                "🌐 **Ports**: Verify service and container port configuration"
            ],
            "prevention": "Implement proper health checks and service monitoring",
            "related_issues": ["pod_not_ready"]
        }
    }
}

# Initialize session state for chat and monitoring
if 'ai_chat_history' not in st.session_state:
    st.session_state.ai_chat_history = []
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'remediation' not in st.session_state:
    st.session_state.remediation = None
if 'last_health_check' not in st.session_state:
    st.session_state.last_health_check = {}
if 'expert_mode' not in st.session_state:
    st.session_state.expert_mode = True

def initialize_components():
    """Initialize Kubernetes components"""
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

def expert_ai_analysis(user_query: str) -> Dict[str, Any]:
    """Advanced AI analysis with expert-level insights"""
    query_lower = user_query.lower()
    
    # Advanced pattern matching with context awareness
    analysis_result = {
        "query": user_query,
        "expert_analysis": "",
        "solutions": [],
        "confidence": 0.0,
        "urgency": "LOW",
        "issue_type": "unknown",
        "prevention": "",
        "related_issues": [],
        "commands": [],
        "next_steps": []
    }
    
    # CrashLoopBackOff Analysis
    if any(word in query_lower for word in ["crashloop", "crash", "restarting", "restart loop", "exit code"]):
        issue_data = EXPERT_KNOWLEDGE["pod_issues"]["crashloopbackoff"]
        analysis_result.update({
            "issue_type": "crashloopbackoff",
            "expert_analysis": issue_data["analysis"],
            "solutions": issue_data["solutions"],
            "confidence": issue_data["confidence"],
            "urgency": issue_data["urgency"],
            "prevention": issue_data["prevention"],
            "related_issues": issue_data["related_issues"],
            "commands": [
                "kubectl get pods -A | grep -E '(CrashLoop|Error)'",
                "kubectl logs <pod-name> --previous",
                "kubectl describe pod <pod-name>"
            ]
        })
    
    # Pending Pod Analysis  
    elif any(word in query_lower for word in ["pending", "scheduling", "unschedulable", "cannot schedule"]):
        issue_data = EXPERT_KNOWLEDGE["pod_issues"]["pending"]
        analysis_result.update({
            "issue_type": "pending",
            "expert_analysis": issue_data["analysis"],
            "solutions": issue_data["solutions"],
            "confidence": issue_data["confidence"],
            "urgency": issue_data["urgency"],
            "prevention": issue_data["prevention"],
            "commands": [
                "kubectl get pods -A | grep Pending",
                "kubectl describe pod <pod-name>",
                "kubectl get nodes -o wide",
                "kubectl top nodes"
            ]
        })
    
    # ImagePullBackOff Analysis
    elif any(word in query_lower for word in ["imagepull", "image", "pull", "registry", "unauthorized"]):
        issue_data = EXPERT_KNOWLEDGE["pod_issues"]["imagepullbackoff"]
        analysis_result.update({
            "issue_type": "imagepullbackoff",
            "expert_analysis": issue_data["analysis"],
            "solutions": issue_data["solutions"],
            "confidence": issue_data["confidence"],
            "urgency": issue_data["urgency"],
            "commands": [
                "kubectl get pods -A | grep ImagePull",
                "kubectl describe pod <pod-name>",
                "kubectl get secrets | grep docker"
            ]
        })
    
    # OOMKilled Analysis
    elif any(word in query_lower for word in ["oom", "memory", "killed", "out of memory"]):
        issue_data = EXPERT_KNOWLEDGE["pod_issues"]["oomkilled"]
        analysis_result.update({
            "issue_type": "oomkilled",
            "expert_analysis": issue_data["analysis"],
            "solutions": issue_data["solutions"],
            "confidence": issue_data["confidence"],
            "urgency": issue_data["urgency"],
            "commands": [
                "kubectl top pods -A --sort-by=memory",
                "kubectl describe pod <pod-name>",
                "kubectl get events --field-selector reason=OOMKilling"
            ]
        })
    
    # Node Issues
    elif any(word in query_lower for word in ["node", "notready", "ready false", "kubelet"]):
        issue_data = EXPERT_KNOWLEDGE["node_issues"]["notready"]
        analysis_result.update({
            "issue_type": "node_notready",
            "expert_analysis": issue_data["analysis"],
            "solutions": issue_data["solutions"],
            "confidence": issue_data["confidence"],
            "urgency": issue_data["urgency"],
            "commands": [
                "kubectl get nodes",
                "kubectl describe node <node-name>",
                "kubectl get events --field-selector involvedObject.kind=Node"
            ]
        })
    
    # Service Issues
    elif any(word in query_lower for word in ["service", "endpoint", "connection refused", "503", "502"]):
        issue_data = EXPERT_KNOWLEDGE["service_issues"]["no_endpoints"]
        analysis_result.update({
            "issue_type": "service_issue",
            "expert_analysis": issue_data["analysis"],
            "solutions": issue_data["solutions"],
            "confidence": issue_data["confidence"],
            "urgency": issue_data["urgency"],
            "commands": [
                "kubectl get svc,ep",
                "kubectl describe svc <service-name>",
                "kubectl get pods --show-labels"
            ]
        })
    
    # Generic troubleshooting
    else:
        analysis_result.update({
            "issue_type": "general",
            "expert_analysis": "🔍 **General Kubernetes Issue Detected** - Applying systematic troubleshooting approach",
            "confidence": 0.6,
            "urgency": "MEDIUM",
            "solutions": [
                "🔍 **Discovery**: Run `kubectl get all -A` to see cluster state",
                "📋 **Events**: Check `kubectl get events --sort-by='.lastTimestamp'`",
                "📊 **Resources**: Monitor with `kubectl top nodes` and `kubectl top pods -A`",
                "🏷️ **Labels**: Verify selectors and labels match",
                "🌐 **Networking**: Test service connectivity and DNS resolution"
            ],
            "commands": [
                "kubectl get all -A",
                "kubectl get events --sort-by='.lastTimestamp'",
                "kubectl top nodes",
                "kubectl top pods -A"
            ]
        })
    
    return analysis_result

def main():
    """Main interactive dashboard"""
    
    # Header with expert branding
    st.title("🤖 Kubernetes AI Agent - Interactive Expert Assistant")
    st.caption("💬 **Chat with your AI expert** • 🔍 **Real-time analysis** • 🛠️ **Automated fixes**")
    
    # Initialize components
    if K8S_COMPONENTS_AVAILABLE:
        init_success = initialize_components()
        if init_success:
            st.success("✅ **AI Agent Online** - Kubernetes cluster connected")
        else:
            st.warning("⚠️ **Limited Mode** - Cluster access restricted")
    else:
        st.info("💡 **Demo Mode** - Interactive AI available, cluster monitoring disabled")
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ **AI Assistant Controls**")
        
        # Expert mode toggle
        st.session_state.expert_mode = st.checkbox("🧠 Expert Mode", value=True, 
                                                  help="Enable advanced AI analysis")
        
        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
        
        # Quick actions
        st.subheader("⚡ **Quick Actions**")
        if st.button("🔍 **Scan Cluster**"):
            if st.session_state.monitor:
                with st.spinner("Scanning cluster for issues..."):
                    issues = st.session_state.monitor.scan_for_issues()
                    st.session_state.last_health_check = {
                        "issues": issues,
                        "timestamp": datetime.now(),
                        "total_issues": len(issues)
                    }
                    st.success(f"Found {len(issues)} issues")
        
        if st.button("🧹 **Clear Chat**"):
            st.session_state.ai_chat_history = []
            st.rerun()
    
    # Main chat interface - The core interactive feature
    st.header("💬 **Chat with Your Kubernetes Expert**")
    st.write("Ask me anything about your Kubernetes cluster - I'll provide expert analysis and solutions!")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for i, chat in enumerate(st.session_state.ai_chat_history):
            # User message
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin: 5px 0;">
                <strong>🧑‍💻 You:</strong> {chat['query']}
            </div>
            """, unsafe_allow_html=True)
            
            # AI response with expert styling
            confidence_color = "🟢" if chat.get('confidence', 0) > 0.8 else "🟡" if chat.get('confidence', 0) > 0.6 else "🔴"
            urgency_color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(chat.get('urgency', 'LOW'), "🟢")
            
            st.markdown(f"""
            <div style="background-color: #f3e5f5; padding: 15px; border-radius: 5px; margin: 5px 0;">
                <strong>🤖 AI Expert:</strong><br>
                <strong>Issue Type:</strong> {chat.get('issue_type', 'unknown').title()}<br>
                <strong>Confidence:</strong> {confidence_color} {chat.get('confidence', 0):.0%} | 
                <strong>Urgency:</strong> {urgency_color} {chat.get('urgency', 'LOW')}<br><br>
                {chat.get('expert_analysis', 'Analysis not available')}
            </div>
            """, unsafe_allow_html=True)
            
            # Solutions
            if chat.get('solutions'):
                st.markdown("**🛠️ Expert Solutions:**")
                for j, solution in enumerate(chat['solutions'], 1):
                    st.markdown(f"{j}. {solution}")
            
            # Diagnostic commands
            if chat.get('commands'):
                with st.expander("📋 **Diagnostic Commands**"):
                    for cmd in chat['commands']:
                        st.code(cmd)
            
            st.divider()
    
    # Chat input
    chat_input = st.text_area(
        "💭 **Describe your issue or ask a question:**",
        placeholder="e.g., 'My pod keeps crashing' or 'Node is not ready' or 'Service returning 503 errors'",
        height=100,
        key="chat_input"
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🚀 **Ask AI Expert**", disabled=not chat_input.strip(), type="primary"):
            if chat_input.strip():
                with st.spinner("🧠 AI Expert analyzing your issue..."):
                    analysis = expert_ai_analysis(chat_input.strip())
                    
                    # Add to chat history
                    st.session_state.ai_chat_history.append({
                        **analysis,
                        "timestamp": datetime.now()
                    })
                    
                    st.rerun()
    
    with col2:
        if st.button("🔧 **Auto-Fix**"):
            if st.session_state.remediation and chat_input.strip():
                st.info("🚧 Auto-remediation feature coming soon!")
    
    with col3:
        if st.button("📊 **Health Check**"):
            if st.session_state.monitor:
                with st.spinner("Running health check..."):
                    try:
                        health = st.session_state.monitor.run_health_check()
                        st.json(health)
                    except Exception as e:
                        st.error(f"Health check failed: {e}")
    
    # Quick troubleshooting section
    st.header("⚡ **Quick Expert Analysis**")
    
    quick_issues = [
        "Pod in CrashLoopBackOff",
        "Pod stuck in Pending state", 
        "ImagePullBackOff error",
        "Node NotReady",
        "Service returning 503",
        "High memory usage",
        "Disk pressure on node"
    ]
    
    cols = st.columns(4)
    for i, issue in enumerate(quick_issues):
        with cols[i % 4]:
            if st.button(f"🔍 {issue}", key=f"quick_{i}"):
                analysis = expert_ai_analysis(issue)
                st.session_state.ai_chat_history.append({
                    **analysis,
                    "timestamp": datetime.now()
                })
                st.rerun()
    
    # Status footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🤖 AI Status", "🟢 Online" if st.session_state.expert_mode else "⚠️ Basic")
    
    with col2:
        st.metric("💬 Chat History", len(st.session_state.ai_chat_history))
    
    with col3:
        st.metric("🕐 Last Update", datetime.now().strftime("%H:%M:%S"))
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()
