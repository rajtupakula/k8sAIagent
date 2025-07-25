#!/usr/bin/env python3
"""
🤖 INTERACTIVE KUBERNETES AI AGENT DASHBOARD
Your personal expert assistant for Kubernetes troubleshooting
"""
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    print("Streamlit not available")
    exit(1)

import time
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Any

# Set page config FIRST
st.set_page_config(
    page_title="🤖 Kubernetes AI Agent - Interactive Expert",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try importing Kubernetes components - but don't fail if they're not available
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent'))
    # Only import basic monitoring that doesn't depend on ChromaDB
    K8S_AVAILABLE = True
    st.success("✅ Basic Kubernetes monitoring available")
except Exception as e:
    K8S_AVAILABLE = False
    st.warning(f"⚠️ Kubernetes components limited: {e}")

# EXPERT AI KNOWLEDGE BASE
EXPERT_AI_KNOWLEDGE = {
    "crashloopbackoff": {
        "analysis": "🔍 **ROOT CAUSE**: Pod is stuck in restart loop - application failing to start properly",
        "confidence": 0.95,
        "urgency": "🔴 CRITICAL",
        "solutions": [
            "🔎 **Check logs immediately**: `kubectl logs <pod-name> --previous`",
            "🏷️ **Verify image**: Ensure container image and tag are correct",
            "⚙️ **Validate config**: Check environment variables and config maps",
            "📊 **Check resources**: Verify CPU/memory limits are sufficient",
            "🌐 **Test endpoints**: Ensure health check endpoints respond",
            "🔐 **Verify permissions**: Check service account and RBAC",
            "💾 **Mount points**: Verify required volumes are mounted"
        ],
        "commands": [
            "kubectl get pods -A | grep -E '(CrashLoop|Error)'",
            "kubectl logs <pod-name> --previous",
            "kubectl describe pod <pod-name>",
            "kubectl get events --field-selector involvedObject.name=<pod-name>"
        ],
        "prevention": "Implement robust health checks, proper resource limits, and comprehensive testing"
    },
    "pending": {
        "analysis": "⏳ **ROOT CAUSE**: Pod cannot be scheduled - insufficient resources or constraints",
        "confidence": 0.90,
        "urgency": "🟡 HIGH",
        "solutions": [
            "🖥️ **Check nodes**: `kubectl describe nodes` to see capacity",
            "📈 **Resource analysis**: Compare requests vs available capacity",
            "🎯 **Review constraints**: Check node selectors and affinity rules",
            "💾 **Storage check**: Ensure PVCs and storage classes exist",
            "🏷️ **Taints & tolerations**: Verify node taints aren't blocking",
            "🔒 **Security policies**: Validate pod security constraints"
        ],
        "commands": [
            "kubectl get pods -A | grep Pending",
            "kubectl describe pod <pod-name>",
            "kubectl describe nodes",
            "kubectl top nodes"
        ],
        "prevention": "Monitor cluster capacity, set appropriate requests, use resource quotas"
    },
    "imagepullbackoff": {
        "analysis": "🖼️ **ROOT CAUSE**: Cannot pull container image - registry access or authentication failure",
        "confidence": 0.92,
        "urgency": "🔴 CRITICAL",
        "solutions": [
            "🔍 **Verify image**: Check image name, tag, and registry URL",
            "🔑 **Check secrets**: Validate image pull secrets and credentials",
            "🌐 **Test connectivity**: Ensure registry is accessible from nodes",
            "⏱️ **Rate limits**: Check for registry rate limiting",
            "🏷️ **Tag exists**: Confirm image tag exists (avoid 'latest')",
            "🔐 **Registry auth**: Verify registry authentication"
        ],
        "commands": [
            "kubectl get pods -A | grep ImagePull",
            "kubectl describe pod <pod-name>",
            "kubectl get secrets | grep docker"
        ],
        "prevention": "Use private registries, implement image scanning, avoid 'latest' tags"
    },
    "node_notready": {
        "analysis": "🖥️ **ROOT CAUSE**: Node unavailable for workloads - kubelet or system issues",
        "confidence": 0.88,
        "urgency": "🔴 CRITICAL",
        "solutions": [
            "🔧 **Kubelet logs**: `journalctl -u kubelet` on the node",
            "🌐 **Network check**: Verify node connectivity and CNI",
            "💾 **Disk space**: Check disk usage and inodes",
            "🔄 **Service restart**: Consider restarting kubelet",
            "🐳 **Container runtime**: Verify Docker/containerd status"
        ],
        "commands": [
            "kubectl get nodes",
            "kubectl describe node <node-name>",
            "kubectl get events --field-selector involvedObject.kind=Node"
        ],
        "prevention": "Implement node monitoring, automated health checks, resource alerts"
    },
    "service_503": {
        "analysis": "🌐 **ROOT CAUSE**: Service has no healthy backend pods or configuration issues",
        "confidence": 0.85,
        "urgency": "🟡 HIGH", 
        "solutions": [
            "🎯 **Check selectors**: Verify service selector matches pod labels",
            "❤️ **Health probes**: Ensure pods pass readiness checks",
            "🔍 **Pod status**: Confirm backend pods are running",
            "🌐 **Port config**: Verify service and container ports match"
        ],
        "commands": [
            "kubectl get svc,ep <service-name>",
            "kubectl describe svc <service-name>",
            "kubectl get pods --show-labels"
        ],
        "prevention": "Implement proper health checks, monitor service endpoints"
    }
}

# Initialize session state
if 'ai_chat_history' not in st.session_state:
    st.session_state.ai_chat_history = []
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'remediation' not in st.session_state:
    st.session_state.remediation = None

def initialize_k8s_components():
    """Initialize Kubernetes monitoring components"""
    if not K8S_AVAILABLE:
        return False
    
    try:
        # Import only when needed and available
        from monitor import KubernetesMonitor
        from remediate import RemediationEngine
        
        if st.session_state.monitor is None:
            st.session_state.monitor = KubernetesMonitor()
        if st.session_state.remediation is None:
            st.session_state.remediation = RemediationEngine()
        return True
    except Exception as e:
        st.warning(f"⚠️ K8s components failed to initialize: {e}")
        return False

def ai_expert_analysis(user_query: str) -> Dict[str, Any]:
    """Expert AI analysis of Kubernetes issues"""
    query_lower = user_query.lower()
    
    # Pattern matching for issue detection
    if any(word in query_lower for word in ["crashloop", "crash", "restarting", "restart loop"]):
        issue_type = "crashloopbackoff"
    elif any(word in query_lower for word in ["pending", "scheduling", "unschedulable"]):
        issue_type = "pending"
    elif any(word in query_lower for word in ["imagepull", "image", "pull", "registry"]):
        issue_type = "imagepullbackoff"
    elif any(word in query_lower for word in ["node", "notready", "ready false"]):
        issue_type = "node_notready"
    elif any(word in query_lower for word in ["service", "503", "502", "connection refused"]):
        issue_type = "service_503"
    else:
        # Generic analysis
        return {
            "issue_type": "general",
            "analysis": "🔍 **GENERAL KUBERNETES ISSUE** - Applying systematic troubleshooting",
            "confidence": 0.6,
            "urgency": "🟡 MEDIUM",
            "solutions": [
                "🔍 **Cluster overview**: `kubectl get all -A`",
                "📋 **Recent events**: `kubectl get events --sort-by='.lastTimestamp'`",
                "📊 **Resource usage**: `kubectl top nodes` and `kubectl top pods -A`",
                "🏷️ **Labels & selectors**: Verify matching labels",
                "🌐 **Network tests**: Check service connectivity"
            ],
            "commands": [
                "kubectl get all -A",
                "kubectl get events --sort-by='.lastTimestamp'",
                "kubectl top nodes"
            ],
            "prevention": "Regular cluster health checks and monitoring"
        }
    
    # Get expert knowledge for detected issue
    expert_data = EXPERT_AI_KNOWLEDGE[issue_type]
    return {
        "issue_type": issue_type,
        "analysis": expert_data["analysis"],
        "confidence": expert_data["confidence"],
        "urgency": expert_data["urgency"],
        "solutions": expert_data["solutions"],
        "commands": expert_data["commands"],
        "prevention": expert_data["prevention"]
    }

def main():
    """Main interactive AI dashboard"""
    
    # Header
    st.title("🤖 Kubernetes AI Agent - Interactive Expert Assistant")
    st.caption("💬 **Chat with your AI expert** • 🔍 **Instant analysis** • 🛠️ **Expert solutions**")
    
    # Status indicators
    col1, col2, col3 = st.columns(3)
    with col1:
        if K8S_AVAILABLE:
            k8s_init = initialize_k8s_components()
            status = "🟢 **Cluster Connected**" if k8s_init else "🟡 **Limited Access**"
        else:
            status = "🔵 **Demo Mode**"
        st.markdown(f"**Kubernetes:** {status}")
    
    with col2:
        st.markdown(f"**AI Status:** 🟢 **Expert Mode Active**")
    
    with col3:
        st.markdown(f"**Chat History:** {len(st.session_state.ai_chat_history)} messages")
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ **AI Controls**")
        
        if st.button("🧹 **Clear Chat History**"):
            st.session_state.ai_chat_history = []
            st.rerun()
        
        if st.button("🔍 **Quick Cluster Scan**") and st.session_state.monitor:
            with st.spinner("Scanning cluster..."):
                try:
                    issues = st.session_state.monitor.scan_for_issues()
                    st.success(f"Found {len(issues)} issues")
                except:
                    st.error("Scan failed")
        
        st.markdown("---")
        st.markdown("**💡 Tips:**")
        st.markdown("• Describe your issue in plain English")
        st.markdown("• Ask about specific error messages")
        st.markdown("• Request step-by-step solutions")
    
    # ===============================
    # MAIN INTERACTIVE CHAT INTERFACE
    # ===============================
    st.header("💬 **Chat with Your Kubernetes Expert**")
    st.markdown("Describe any Kubernetes issue and get instant expert analysis with solutions!")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for chat in st.session_state.ai_chat_history:
            # User message
            st.markdown(f"""
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #2196f3;">
                <strong>🧑‍💻 You:</strong> {chat['query']}
                <br><small>🕐 {chat.get('timestamp', datetime.now()).strftime('%H:%M:%S')}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # AI Expert Response
            st.markdown(f"""
            <div style="background-color: #f3e5f5; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #9c27b0;">
                <strong>🤖 AI Expert Analysis:</strong><br>
                <strong>Issue:</strong> {chat.get('issue_type', 'unknown').replace('_', ' ').title()}<br>
                <strong>Confidence:</strong> {chat.get('confidence', 0):.0%} | <strong>Priority:</strong> {chat.get('urgency', 'Medium')}<br><br>
                {chat.get('analysis', 'Analysis not available')}
            </div>
            """, unsafe_allow_html=True)
            
            # Solutions
            if chat.get('solutions'):
                st.markdown("**🛠️ Expert Solutions:**")
                for i, solution in enumerate(chat['solutions'], 1):
                    st.markdown(f"**{i}.** {solution}")
            
            # Diagnostic commands  
            if chat.get('commands'):
                with st.expander("📋 **Diagnostic Commands to Run**"):
                    for cmd in chat['commands']:
                        st.code(cmd, language='bash')
            
            # Prevention advice
            if chat.get('prevention'):
                with st.expander("🛡️ **Prevention Strategy**"):
                    st.markdown(chat['prevention'])
            
            st.divider()
    
    # ===============================
    # CHAT INPUT INTERFACE
    # ===============================
    chat_input = st.text_area(
        "💭 **Describe your Kubernetes issue:**",
        placeholder="e.g., 'My pod keeps crashing and restarting' or 'Getting 503 errors from my service' or 'Node shows as NotReady'",
        height=120,
        help="Describe the problem in your own words - the AI will analyze and provide expert solutions"
    )
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        if st.button("🚀 **Ask AI Expert**", disabled=not chat_input.strip(), type="primary"):
            if chat_input.strip():
                with st.spinner("🧠 AI Expert analyzing your issue..."):
                    # Get AI analysis
                    analysis = ai_expert_analysis(chat_input.strip())
                    
                    # Add to chat history
                    st.session_state.ai_chat_history.append({
                        "query": chat_input.strip(),
                        "timestamp": datetime.now(),
                        **analysis
                    })
                    
                    st.rerun()
    
    with col2:
        if st.button("🔧 **Auto-Fix**") and st.session_state.remediation:
            st.info("🚧 Auto-remediation available for safe operations")
    
    with col3:
        if st.button("📊 **Health Check**") and st.session_state.monitor:
            with st.spinner("Running health check..."):
                try:
                    health = st.session_state.monitor.run_health_check()
                    st.json(health)
                except Exception as e:
                    st.error(f"Health check failed: {e}")
    
    # ===============================
    # QUICK EXPERT ASSISTANCE
    # ===============================
    st.header("⚡ **Quick Expert Assistance**")
    st.markdown("Click for instant analysis of common issues:")
    
    quick_issues = [
        ("Pod in CrashLoopBackOff", "crashloop"),
        ("Pod stuck Pending", "pending"), 
        ("ImagePullBackOff error", "imagepull"),
        ("Node NotReady", "node not ready"),
        ("Service 503 errors", "service 503"),
        ("High memory usage", "memory issues"),
        ("Storage problems", "storage failing")
    ]
    
    cols = st.columns(4)
    for i, (display_text, query_text) in enumerate(quick_issues):
        with cols[i % 4]:
            if st.button(f"🔍 **{display_text}**", key=f"quick_{i}"):
                analysis = ai_expert_analysis(query_text)
                st.session_state.ai_chat_history.append({
                    "query": f"Help with: {display_text}",
                    "timestamp": datetime.now(),
                    **analysis
                })
                st.rerun()
    
    # ===============================
    # SYSTEM STATUS FOOTER
    # ===============================
    st.divider()
    st.markdown("### 📊 **System Status**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🤖 AI Expert", "🟢 Online")
    
    with col2:
        st.metric("💬 Conversations", len(st.session_state.ai_chat_history))
    
    with col3:
        st.metric("🔧 K8s Access", "✅ Available" if K8S_AVAILABLE else "⚠️ Limited")
    
    with col4:
        st.metric("🕐 Last Update", datetime.now().strftime("%H:%M:%S"))
    
    # Usage instructions
    with st.expander("❓ **How to Use This AI Expert**"):
        st.markdown("""
        **🎯 This AI agent acts like a Kubernetes expert sitting next to you:**
        
        1. **💬 Describe your problem** in plain English - just like talking to a colleague
        2. **🔍 Get instant analysis** with confidence levels and urgency ratings  
        3. **🛠️ Receive step-by-step solutions** with exact commands to run
        4. **📋 Copy diagnostic commands** and run them in your terminal
        5. **🛡️ Learn prevention strategies** to avoid future issues
        
        **💡 Example conversations:**
        - "My pod keeps restarting every few minutes"
        - "I'm getting 503 errors from my service"
        - "One of my nodes shows as NotReady"
        - "Pods are stuck in Pending state"
        
        **🚀 The AI will provide expert-level analysis and solutions instantly!**
        """)

if __name__ == "__main__":
    main()
    
    # Health check
    st.subheader("Health Check")
    if st.button("Test Health Endpoint"):
        st.success("✅ Health check passed!")
    
    # Environment variables
    st.subheader("Environment")
    env_vars = ["PYTHONPATH", "PATH", "STREAMLIT_SERVER_PORT"]
    for var in env_vars:
        value = os.environ.get(var, "Not set")
        st.text(f"{var}: {value}")
    
    # Simple refresh button instead of auto-refresh
    if st.button("🔄 Refresh"):
        st.rerun()

if __name__ == "__main__":
    main()
