#!/usr/bin/env python3
"""
Enhanced AI Agent Dashboard with Interactive Capabilities
"""
import streamlit as st
import os
import sys
import time
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Any
import threading

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try importing AI components with graceful fallback
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent'))
    from monitor import KubernetesMonitor
    from rag_agent import RAGAgent
    from remediate import RemediationEngine
    AI_COMPONENTS_AVAILABLE = True
except ImportError as e:
    st.warning(f"AI components not fully available: {e}")
    AI_COMPONENTS_AVAILABLE = False
    KubernetesMonitor = None
    RAGAgent = None
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

# Initialize session state
if 'ai_agent' not in st.session_state:
    st.session_state.ai_agent = None
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'remediation' not in st.session_state:
    st.session_state.remediation = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'last_scan_results' not in st.session_state:
    st.session_state.last_scan_results = {}

def initialize_ai_components():
    """Initialize AI components with error handling"""
    if not AI_COMPONENTS_AVAILABLE:
        return False
    
    try:
        if st.session_state.monitor is None:
            st.session_state.monitor = KubernetesMonitor()
        
        if st.session_state.ai_agent is None:
            st.session_state.ai_agent = RAGAgent(offline_mode=True)
        
        if st.session_state.remediation is None:
            st.session_state.remediation = RemediationEngine()
        
        return True
    except Exception as e:
        st.error(f"Failed to initialize AI components: {e}")
        return False

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
    st.title("🤖 Kubernetes AI Agent Dashboard")
    
    # Initialize components
    if AI_COMPONENTS_AVAILABLE:
        init_success = initialize_ai_components()
        if init_success:
            st.success("✅ AI Agent components initialized successfully!")
        else:
            st.error("❌ Failed to initialize AI components")
    else:
        st.warning("⚠️ Running in limited mode - AI components not available")
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        
        # Manual refresh button
        if st.button("🔄 Refresh Now"):
            st.rerun()
        
        # AI Agent Mode
        st.subheader("🎯 AI Agent Mode")
        if AI_COMPONENTS_AVAILABLE and st.session_state.ai_agent:
            ai_mode = st.selectbox("Select Mode", 
                                 ["Interactive", "Monitor Only", "Auto-Remediate"])
        else:
            st.info("AI Agent not available")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview", 
        "🤖 AI Chat", 
        "📊 Cluster Health", 
        "🔧 Remediation", 
        "📈 Metrics"
    ])
    
    with tab1:
        overview_tab()
    
    with tab2:
        ai_chat_tab()
    
    with tab3:
        cluster_health_tab()
    
    with tab4:
        remediation_tab()
    
    with tab5:
        metrics_tab()
    
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
        st.metric("AI Agent", "✅ Online" if AI_COMPONENTS_AVAILABLE else "❌ Offline")
    
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
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Scan for Issues"):
            if st.session_state.monitor:
                with st.spinner("Scanning cluster..."):
                    issues = st.session_state.monitor.scan_for_issues()
                    st.session_state.last_scan_results = {
                        "issues": issues,
                        "timestamp": datetime.now().isoformat()
                    }
                    if issues:
                        st.error(f"Found {len(issues)} issues")
                    else:
                        st.success("No issues found")
            else:
                st.error("Monitor not available")
    
    with col2:
        if st.button("🤖 AI Health Check"):
            if st.session_state.ai_agent:
                with st.spinner("Running AI health check..."):
                    try:
                        response = st.session_state.ai_agent.get_system_health_report()
                        st.text_area("Health Report", response, height=200)
                    except Exception as e:
                        st.error(f"Health check failed: {e}")
            else:
                st.error("AI Agent not available")
    
    with col3:
        if st.button("📊 Generate Report"):
            if st.session_state.monitor:
                with st.spinner("Generating report..."):
                    try:
                        report = st.session_state.monitor.generate_report()
                        st.download_button(
                            label="Download Report",
                            data=report,
                            file_name=f"cluster_report_{int(time.time())}.json",
                            mime="application/json"
                        )
                    except Exception as e:
                        st.error(f"Report generation failed: {e}")
            else:
                st.error("Monitor not available")

def ai_chat_tab():
    """AI Chat interface tab"""
    st.header("🤖 AI Assistant Chat")
    
    if not AI_COMPONENTS_AVAILABLE or not st.session_state.ai_agent:
        st.error("AI Agent not available. Please check the installation.")
        return
    
    # Chat interface
    st.subheader("💬 Ask the AI Agent")
    
    # Display chat history
    for i, chat in enumerate(st.session_state.chat_history):
        with st.container():
            st.markdown(f"**You:** {chat['query']}")
            st.markdown(f"**AI:** {chat['response']}")
            if chat.get('confidence'):
                st.markdown(f"*Confidence: {chat['confidence']:.0%}*")
            st.divider()
    
    # New query input
    query = st.text_area("Enter your question or issue description:", 
                        placeholder="e.g., 'Why is my pod in CrashLoopBackOff?' or 'How do I scale my deployment?'",
                        height=100)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🚀 Ask AI Agent", disabled=not query.strip()):
            ask_ai_agent(query.strip())
    
    with col2:
        auto_remediate = st.checkbox("Enable Auto-Remediation", help="Allow AI to automatically fix safe issues")
    
    with col3:
        if st.button("🔧 Expert Analysis", disabled=not query.strip()):
            expert_analysis(query.strip(), auto_remediate)

def ask_ai_agent(query: str):
    """Ask the AI agent a question"""
    with st.spinner("AI Agent is thinking..."):
        try:
            response = st.session_state.ai_agent.query(query)
            
            chat_entry = {
                "query": query,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            st.session_state.chat_history.append(chat_entry)
            st.rerun()
            
        except Exception as e:
            st.error(f"AI Agent error: {e}")

def expert_analysis(query: str, auto_remediate: bool = False):
    """Get expert analysis from AI agent"""
    with st.spinner("Running expert analysis..."):
        try:
            # Use expert query if available
            if hasattr(st.session_state.ai_agent, 'expert_query'):
                result = st.session_state.ai_agent.expert_query(query, auto_remediate=auto_remediate)
                
                chat_entry = {
                    "query": query,
                    "response": result.get("expert_response", result.get("standard_response", "No response")),
                    "confidence": result.get("confidence", 0),
                    "timestamp": datetime.now().isoformat(),
                    "expert_analysis": result.get("expert_analysis", {}),
                    "recommendations": result.get("recommendations", [])
                }
                
                st.session_state.chat_history.append(chat_entry)
                
                # Show additional expert details
                if result.get("recommendations"):
                    st.subheader("🎯 Recommendations")
                    for rec in result["recommendations"]:
                        st.markdown(f"• {rec}")
                
                if result.get("remediation_plan"):
                    st.subheader("🔧 Remediation Plan")
                    for step in result["remediation_plan"]:
                        st.markdown(f"• {step}")
                
            else:
                # Fallback to regular query
                ask_ai_agent(query)
                
        except Exception as e:
            st.error(f"Expert analysis failed: {e}")

def cluster_health_tab():
    """Cluster health monitoring tab"""
    st.header("📊 Cluster Health Dashboard")
    
    if not st.session_state.monitor:
        st.error("Kubernetes monitor not available")
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
                    if st.session_state.ai_agent:
                        analysis_query = f"Analyze this Kubernetes issue: {issue.get('title', '')} - {issue.get('description', '')}"
                        ask_ai_agent(analysis_query)
    else:
        st.success("🎉 No issues detected!")
    
    # Cluster metrics
    if health_data.get("metrics"):
        st.subheader("📈 Cluster Metrics")
        metrics = health_data["metrics"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("CPU Usage", f"{metrics.get('cpu_usage', 0):.1f}%")
        with col2:
            st.metric("Memory Usage", f"{metrics.get('memory_usage', 0):.1f}%")
        with col3:
            st.metric("Pod Count", metrics.get('pod_count', 0))
        with col4:
            st.metric("Node Count", metrics.get('node_count', 0))

def remediation_tab():
    """Remediation actions tab"""
    st.header("🔧 Remediation Center")
    
    if not st.session_state.remediation:
        st.error("Remediation engine not available")
        return
    
    st.subheader("🚀 Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Restart Failed Pods"):
            try:
                result = st.session_state.remediation.restart_failed_pods()
                if result.get('success'):
                    st.success(f"✅ Restarted {result.get('count', 0)} failed pods")
                else:
                    st.error(f"❌ Failed to restart pods: {result.get('message', 'Unknown error')}")
            except Exception as e:
                st.error(f"Remediation failed: {e}")
    
    with col2:
        if st.button("🧹 Clean Up Completed Jobs"):
            try:
                # This would need to be implemented in remediation engine
                st.info("Job cleanup functionality not yet implemented")
            except Exception as e:
                st.error(f"Cleanup failed: {e}")
    
    # Auto-remediation
    st.subheader("🤖 AI Auto-Remediation")
    
    if st.button("🚀 Run Auto-Remediation"):
        if st.session_state.ai_agent and hasattr(st.session_state.ai_agent, 'auto_remediate_system_issues'):
            with st.spinner("Running auto-remediation..."):
                try:
                    result = st.session_state.ai_agent.auto_remediate_system_issues()
                    
                    if result.get('success'):
                        st.success(f"✅ Auto-remediation completed!")
                        st.json(result)
                    else:
                        st.warning(f"⚠️ Auto-remediation result: {result.get('message', 'No issues found')}")
                except Exception as e:
                    st.error(f"Auto-remediation failed: {e}")
        else:
            st.error("Auto-remediation not available")

def metrics_tab():
    """System metrics and monitoring tab"""
    st.header("📈 System Metrics")
    
    # Basic system info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    with col2:
        st.metric("Working Directory", os.getcwd())
    
    with col3:
        st.metric("Current Time", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # Package status
    st.subheader("📦 Package Status")
    packages = ["streamlit", "pandas", "numpy", "requests", "kubernetes"]
    
    for pkg in packages:
        try:
            __import__(pkg)
            st.success(f"✅ {pkg} - Available")
        except ImportError:
            st.error(f"❌ {pkg} - Not Available")
    
    # Environment variables
    st.subheader("🌍 Environment")
    important_vars = ["PYTHONPATH", "PATH", "KUBERNETES_SERVICE_HOST", "KUBERNETES_SERVICE_PORT"]
    
    for var in important_vars:
        value = os.environ.get(var, "Not set")
        if len(value) > 100:
            value = value[:100] + "..."
        st.text(f"{var}: {value}")

if __name__ == "__main__":
    main()
