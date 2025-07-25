#!/usr/bin/env python3
"""
🚀 RUNTIME-ERROR-FREE KUBERNETES AI AGENT DASHBOARD
Fixed version with proper LLaMA integration, error handling, and real-time data
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import sys
import json
import subprocess
import re
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config FIRST
st.set_page_config(
    page_title="🚀 Expert Kubernetes AI Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'llama_status' not in st.session_state:
    st.session_state.llama_status = "Unknown"
if 'k8s_status' not in st.session_state:
    st.session_state.k8s_status = "Unknown"

# Real Kubernetes integration with proper error handling
KUBERNETES_AVAILABLE = False
K8S_CONFIG_LOADED = False
K8S_MODE = "none"
v1 = None
apps_v1 = None

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
    
    # Try to load Kubernetes config
    try:
        # First try in-cluster config (for running inside K8s)
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        K8S_CONFIG_LOADED = True
        K8S_MODE = "in-cluster"
        st.session_state.k8s_status = "Connected (In-Cluster)"
    except:
        try:
            # Fall back to local kubeconfig
            config.load_kube_config()
            v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()
            K8S_CONFIG_LOADED = True
            K8S_MODE = "kubeconfig"
            st.session_state.k8s_status = "Connected (Kubeconfig)"
        except Exception as e:
            K8S_CONFIG_LOADED = False
            K8S_MODE = "none"
            st.session_state.k8s_status = f"Disconnected: {str(e)[:50]}"
            
except ImportError as e:
    KUBERNETES_AVAILABLE = False
    st.session_state.k8s_status = f"Library Missing: {str(e)[:50]}"

# LLaMA Server Integration with multiple endpoints
LLAMA_ENDPOINTS = [
    {"url": "http://localhost:8080", "name": "llama-cpp-python", "type": "completion"},
    {"url": "http://localhost:11434", "name": "Ollama", "type": "generate"},
]

LLAMA_AVAILABLE = False
ACTIVE_LLAMA_ENDPOINT = None

def test_llama_server(endpoint_url: str, endpoint_type: str = "completion") -> bool:
    """Test if LLaMA server is available at the given endpoint"""
    try:
        # Test health endpoint first
        health_response = requests.get(f"{endpoint_url}/health", timeout=2)
        if health_response.status_code == 200:
            return True
            
        # If no health endpoint, test completion endpoint
        if endpoint_type == "completion":
            test_payload = {
                "prompt": "Hello",
                "max_tokens": 5,
                "temperature": 0.1
            }
            response = requests.post(f"{endpoint_url}/completion", json=test_payload, timeout=5)
            return response.status_code == 200
        elif endpoint_type == "generate":
            test_payload = {
                "model": "llama2",
                "prompt": "Hello",
                "stream": False
            }
            response = requests.post(f"{endpoint_url}/api/generate", json=test_payload, timeout=5)
            return response.status_code == 200
            
    except Exception as e:
        logger.debug(f"LLaMA test failed for {endpoint_url}: {e}")
        return False
    
    return False

# Test LLaMA endpoints and find working one
for endpoint in LLAMA_ENDPOINTS:
    if test_llama_server(endpoint["url"], endpoint["type"]):
        LLAMA_AVAILABLE = True
        ACTIVE_LLAMA_ENDPOINT = endpoint
        st.session_state.llama_status = f"Online ({endpoint['name']})"
        break

if not LLAMA_AVAILABLE:
    st.session_state.llama_status = "Offline - No endpoints responding"

# Plotting with fallback
try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

# Enhanced CSS with better error styling
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    margin: 10px 0;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.status-good { color: #4CAF50; font-weight: bold; }
.status-warning { color: #FF9800; font-weight: bold; }
.status-critical { color: #F44336; font-weight: bold; }
.status-offline { color: #9E9E9E; font-weight: bold; }
.chat-user {
    background-color: #e3f2fd;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
    border-left: 4px solid #2196f3;
}
.chat-ai {
    background-color: #f3e5f5;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
    border-left: 4px solid #9c27b0;
}
.error-box {
    background-color: #ffebee;
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #f44336;
    margin: 10px 0;
}
.success-box {
    background-color: #e8f5e8;
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #4caf50;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

def safe_query_llama_server(prompt: str, **kwargs) -> Dict[str, Any]:
    """Query LLaMA server with comprehensive error handling"""
    if not LLAMA_AVAILABLE or not ACTIVE_LLAMA_ENDPOINT:
        return {
            "success": False,
            "message": "LLaMA server not available",
            "response": "AI analysis unavailable. Please ensure LLaMA server is running on port 8080 or 11434.",
            "fallback": True
        }
    
    try:
        endpoint = ACTIVE_LLAMA_ENDPOINT
        
        if endpoint["type"] == "completion":
            # llama-cpp-python format
            payload = {
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 500),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "stop": kwargs.get("stop", ["\n\n", "###"]),
                "stream": False
            }
            
            response = requests.post(
                f"{endpoint['url']}/completion",
                json=payload,
                timeout=15
            )
            
        elif endpoint["type"] == "generate":
            # Ollama format
            payload = {
                "model": "llama2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 500)
                }
            }
            
            response = requests.post(
                f"{endpoint['url']}/api/generate",
                json=payload,
                timeout=15
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract response based on endpoint type
            if endpoint["type"] == "completion":
                ai_response = result.get("content", result.get("choices", [{}])[0].get("text", "")).strip()
            else:  # Ollama
                ai_response = result.get("response", "").strip()
            
            return {
                "success": True,
                "response": ai_response,
                "tokens": result.get("tokens_predicted", result.get("eval_count", 0)),
                "message": f"AI analysis completed via {endpoint['name']}",
                "fallback": False
            }
        else:
            return {
                "success": False,
                "message": f"LLaMA server error: {response.status_code} - {response.text[:100]}",
                "response": "AI analysis failed due to server error.",
                "fallback": True
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "LLaMA server timeout",
            "response": "AI analysis timed out. Server may be overloaded.",
            "fallback": True
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to query LLaMA server: {str(e)}",
            "response": f"AI analysis error: {str(e)[:100]}",
            "fallback": True
        }

def get_real_kubernetes_data():
    """Get real-time Kubernetes cluster data with error handling"""
    if not K8S_CONFIG_LOADED:
        return {
            "pods": [],
            "nodes": [],
            "deployments": [],
            "services": [],
            "events": [],
            "error": "Kubernetes API not available"
        }
    
    try:
        # Get pods
        pods_data = []
        pods = v1.list_pod_for_all_namespaces(limit=100)
        for pod in pods.items:
            pod_status = "Unknown"
            if pod.status.phase:
                pod_status = pod.status.phase
            
            # Check for container statuses
            if pod.status.container_statuses:
                for container in pod.status.container_statuses:
                    if container.state.waiting:
                        pod_status = f"Waiting: {container.state.waiting.reason}"
                    elif container.state.terminated:
                        pod_status = f"Terminated: {container.state.terminated.reason}"
            
            pods_data.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod_status,
                "node": pod.spec.node_name or "Unscheduled",
                "age": str(datetime.now(pod.metadata.creation_timestamp.tzinfo) - pod.metadata.creation_timestamp).split('.')[0],
                "restarts": sum([container.restart_count for container in (pod.status.container_statuses or [])]),
                "ready": f"{sum([1 for container in (pod.status.container_statuses or []) if container.ready])}/{len(pod.status.container_statuses or [])}"
            })
        
        # Get nodes
        nodes_data = []
        nodes = v1.list_node()
        for node in nodes.items:
            node_status = "Unknown"
            for condition in (node.status.conditions or []):
                if condition.type == "Ready":
                    node_status = "Ready" if condition.status == "True" else "NotReady"
                    break
            
            nodes_data.append({
                "name": node.metadata.name,
                "status": node_status,
                "version": node.status.node_info.kubelet_version,
                "os": f"{node.status.node_info.os_image}",
                "arch": node.status.node_info.architecture,
                "age": str(datetime.now(node.metadata.creation_timestamp.tzinfo) - node.metadata.creation_timestamp).split('.')[0]
            })
        
        # Get deployments
        deployments_data = []
        deployments = apps_v1.list_deployment_for_all_namespaces(limit=50)
        for deployment in deployments.items:
            deployments_data.append({
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "ready": f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas or 0}",
                "available": deployment.status.available_replicas or 0,
                "age": str(datetime.now(deployment.metadata.creation_timestamp.tzinfo) - deployment.metadata.creation_timestamp).split('.')[0]
            })
        
        # Get recent events
        events_data = []
        events = v1.list_event_for_all_namespaces(limit=20)
        for event in events.items:
            events_data.append({
                "type": event.type,
                "reason": event.reason,
                "object": f"{event.involved_object.kind}/{event.involved_object.name}",
                "namespace": event.namespace,
                "message": event.message[:100] + "..." if len(event.message) > 100 else event.message,
                "age": str(datetime.now(event.last_timestamp.tzinfo) - event.last_timestamp).split('.')[0] if event.last_timestamp else "Unknown"
            })
        
        return {
            "pods": pods_data,
            "nodes": nodes_data,
            "deployments": deployments_data,
            "events": events_data,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Failed to get Kubernetes data: {e}")
        return {
            "pods": [],
            "nodes": [],
            "deployments": [],
            "events": [],
            "error": str(e)
        }

def render_status_header():
    """Render the status header with real-time connection info"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        k8s_status = st.session_state.get('k8s_status', 'Unknown')
        if 'Connected' in k8s_status:
            st.markdown(f'<p class="status-good">✅ Kubernetes: {k8s_status}</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p class="status-critical">❌ Kubernetes: {k8s_status}</p>', unsafe_allow_html=True)
    
    with col2:
        llama_status = st.session_state.get('llama_status', 'Unknown')
        if 'Online' in llama_status:
            st.markdown(f'<p class="status-good">🤖 LLaMA: {llama_status}</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p class="status-critical">🤖 LLaMA: {llama_status}</p>', unsafe_allow_html=True)
    
    with col3:
        if PLOTTING_AVAILABLE:
            st.markdown('<p class="status-good">📊 Plotting: Available</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-warning">📊 Plotting: Limited</p>', unsafe_allow_html=True)
    
    with col4:
        current_time = datetime.now().strftime("%H:%M:%S")
        st.markdown(f'<p class="status-good">⏰ {current_time}</p>', unsafe_allow_html=True)

def main():
    """Main dashboard application"""
    
    # Header
    st.title("🚀 Expert Kubernetes AI Agent")
    st.markdown("**Real-time cluster monitoring with AI-powered analysis and remediation**")
    
    # Status header
    render_status_header()
    
    # Sidebar navigation
    st.sidebar.title("🔧 Navigation")
    page = st.sidebar.selectbox("Choose a page:", [
        "🏠 Overview",
        "🗨️ AI Chat Assistant", 
        "📊 Cluster Resources",
        "🔍 Troubleshooting",
        "⚡ Auto-Remediation",
        "📈 Analytics",
        "⚙️ Settings"
    ])
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
    if auto_refresh:
        time.sleep(1)
        st.rerun()
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now"):
        st.rerun()
    
    # Page content
    if page == "🏠 Overview":
        render_overview_page()
    elif page == "🗨️ AI Chat Assistant":
        render_chat_page()
    elif page == "📊 Cluster Resources":
        render_resources_page()
    elif page == "🔍 Troubleshooting":
        render_troubleshooting_page()
    elif page == "⚡ Auto-Remediation":
        render_remediation_page()
    elif page == "📈 Analytics":
        render_analytics_page()
    elif page == "⚙️ Settings":
        render_settings_page()

def render_overview_page():
    """Render the overview page with cluster status"""
    st.header("🏠 Cluster Overview")
    
    # Get real-time data
    with st.spinner("Loading real-time cluster data..."):
        k8s_data = get_real_kubernetes_data()
    
    if k8s_data.get("error"):
        st.error(f"❌ Failed to connect to Kubernetes: {k8s_data['error']}")
        st.info("💡 Make sure you're running inside a Kubernetes cluster or have valid kubeconfig")
        return
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pods = len(k8s_data["pods"])
        running_pods = len([p for p in k8s_data["pods"] if p["status"] == "Running"])
        st.metric("Total Pods", total_pods, f"{running_pods} running")
    
    with col2:
        total_nodes = len(k8s_data["nodes"])
        ready_nodes = len([n for n in k8s_data["nodes"] if n["status"] == "Ready"])
        st.metric("Cluster Nodes", total_nodes, f"{ready_nodes} ready")
    
    with col3:
        total_deployments = len(k8s_data["deployments"])
        st.metric("Deployments", total_deployments)
    
    with col4:
        recent_events = len([e for e in k8s_data["events"] if e["type"] == "Warning"])
        st.metric("Recent Warnings", recent_events)
    
    # Recent events
    st.subheader("🔔 Recent Cluster Events")
    if k8s_data["events"]:
        events_df = pd.DataFrame(k8s_data["events"])
        st.dataframe(events_df, use_container_width=True)
    else:
        st.info("No recent events found")

def render_chat_page():
    """Render the AI chat assistant page"""
    st.header("🗨️ AI Chat Assistant")
    
    # LLaMA status check
    if not LLAMA_AVAILABLE:
        st.error("🤖 LLaMA server is not available")
        st.info("💡 Start LLaMA server on port 8080 or 11434 to enable AI chat")
        
        with st.expander("🔧 Quick LLaMA Setup"):
            st.code("""
# Option 1: llama-cpp-python
pip install llama-cpp-python[server]
python -m llama_cpp.server --model path/to/model.gguf --host 0.0.0.0 --port 8080

# Option 2: Ollama
ollama serve
ollama pull llama2
            """)
        return
    
    # Chat interface
    st.success(f"🤖 AI Assistant Online - {ACTIVE_LLAMA_ENDPOINT['name']}")
    
    # Chat input
    user_input = st.text_input("💬 Ask me anything about your Kubernetes cluster:", 
                              placeholder="e.g., Why is my pod failing? How to scale my deployment?")
    
    if st.button("Send") and user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "type": "user",
            "message": user_input,
            "timestamp": datetime.now()
        })
        
        # Get AI response
        with st.spinner("🤖 AI is analyzing..."):
            # Get current cluster context
            k8s_data = get_real_kubernetes_data()
            context = f"Current cluster status: {len(k8s_data.get('pods', []))} pods, {len(k8s_data.get('nodes', []))} nodes"
            
            prompt = f"""You are a Kubernetes expert assistant. 
Context: {context}
User question: {user_input}
Provide helpful, accurate advice:"""
            
            ai_response = safe_query_llama_server(prompt, max_tokens=300)
            
            # Add AI response to history
            st.session_state.chat_history.append({
                "type": "ai", 
                "message": ai_response["response"],
                "success": ai_response["success"],
                "timestamp": datetime.now()
            })
    
    # Display chat history
    for chat in reversed(st.session_state.chat_history[-10:]):  # Show last 10 messages
        if chat["type"] == "user":
            st.markdown(f'<div class="chat-user">👤 <strong>You:</strong><br>{chat["message"]}</div>', 
                       unsafe_allow_html=True)
        else:
            status_icon = "🤖" if chat.get("success", True) else "⚠️"
            st.markdown(f'<div class="chat-ai">{status_icon} <strong>AI Assistant:</strong><br>{chat["message"]}</div>', 
                       unsafe_allow_html=True)

def render_resources_page():
    """Render cluster resources page"""
    st.header("📊 Cluster Resources")
    
    # Get real-time data
    with st.spinner("Loading cluster resources..."):
        k8s_data = get_real_kubernetes_data()
    
    if k8s_data.get("error"):
        st.error(f"❌ Failed to load resources: {k8s_data['error']}")
        return
    
    # Tabs for different resources
    tab1, tab2, tab3 = st.tabs(["🏃 Pods", "🖥️ Nodes", "🚀 Deployments"])
    
    with tab1:
        st.subheader("Pod Status")
        if k8s_data["pods"]:
            pods_df = pd.DataFrame(k8s_data["pods"])
            st.dataframe(pods_df, use_container_width=True)
            
            # Pod status chart
            if PLOTTING_AVAILABLE:
                status_counts = pods_df['status'].value_counts()
                fig = px.pie(values=status_counts.values, names=status_counts.index, 
                           title="Pod Status Distribution")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pods found")
    
    with tab2:
        st.subheader("Node Information") 
        if k8s_data["nodes"]:
            nodes_df = pd.DataFrame(k8s_data["nodes"])
            st.dataframe(nodes_df, use_container_width=True)
        else:
            st.info("No nodes found")
    
    with tab3:
        st.subheader("Deployment Status")
        if k8s_data["deployments"]:
            deployments_df = pd.DataFrame(k8s_data["deployments"])
            st.dataframe(deployments_df, use_container_width=True)
        else:
            st.info("No deployments found")

def render_troubleshooting_page():
    """Render troubleshooting page"""
    st.header("🔍 Kubernetes Troubleshooting")
    
    # Quick diagnostics
    st.subheader("🩺 Quick Diagnostics")
    
    if st.button("🔍 Run Full Cluster Health Check"):
        with st.spinner("Running health checks..."):
            k8s_data = get_real_kubernetes_data()
            
            # Analyze issues
            issues = []
            
            # Check for failed pods
            failed_pods = [p for p in k8s_data.get("pods", []) if p["status"] not in ["Running", "Succeeded"]]
            if failed_pods:
                issues.append(f"❌ {len(failed_pods)} pods not running")
            
            # Check for unready nodes
            unready_nodes = [n for n in k8s_data.get("nodes", []) if n["status"] != "Ready"]
            if unready_nodes:
                issues.append(f"❌ {len(unready_nodes)} nodes not ready")
            
            # Check for recent warnings
            warnings = [e for e in k8s_data.get("events", []) if e["type"] == "Warning"]
            if warnings:
                issues.append(f"⚠️ {len(warnings)} recent warning events")
            
            if issues:
                st.error("Issues detected:")
                for issue in issues:
                    st.write(f"• {issue}")
                
                # AI Analysis
                if LLAMA_AVAILABLE:
                    st.subheader("🤖 AI Root Cause Analysis")
                    with st.spinner("AI analyzing issues..."):
                        prompt = f"""Analyze these Kubernetes issues and provide remediation steps:
                        Issues: {', '.join(issues)}
                        Failed pods: {[p['name'] + ':' + p['status'] for p in failed_pods[:3]]}
                        Recent warnings: {[e['reason'] + ':' + e['message'][:50] for e in warnings[:3]]}
                        
                        Provide specific remediation steps:"""
                        
                        ai_result = safe_query_llama_server(prompt, max_tokens=500)
                        if ai_result["success"]:
                            st.success("🤖 AI Analysis:")
                            st.write(ai_result["response"])
                        else:
                            st.warning(f"AI analysis failed: {ai_result['message']}")
            else:
                st.success("✅ No issues detected - cluster appears healthy!")

def render_remediation_page():
    """Render auto-remediation page"""
    st.header("⚡ Auto-Remediation")
    
    st.warning("🚨 Auto-remediation executes real kubectl commands. Use with caution!")
    
    # Common remediation actions
    st.subheader("🔧 Quick Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Restart Failed Pods"):
            with st.spinner("Finding failed pods..."):
                k8s_data = get_real_kubernetes_data()
                failed_pods = [p for p in k8s_data.get("pods", []) if p["status"] in ["CrashLoopBackOff", "Error", "Failed"]]
                
                if failed_pods:
                    st.write(f"Found {len(failed_pods)} failed pods:")
                    for pod in failed_pods[:5]:  # Limit to 5
                        st.write(f"• {pod['namespace']}/{pod['name']} - {pod['status']}")
                    
                    if st.button("⚠️ Confirm Restart"):
                        for pod in failed_pods[:5]:
                            try:
                                cmd = f"kubectl delete pod {pod['name']} -n {pod['namespace']}"
                                result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
                                if result.returncode == 0:
                                    st.success(f"✅ Restarted {pod['name']}")
                                else:
                                    st.error(f"❌ Failed to restart {pod['name']}: {result.stderr}")
                            except Exception as e:
                                st.error(f"❌ Error restarting {pod['name']}: {e}")
                else:
                    st.info("No failed pods found")
    
    with col2:
        if st.button("📊 Scale Deployment"):
            namespace = st.text_input("Namespace:", value="default")
            deployment = st.text_input("Deployment name:")
            replicas = st.number_input("Target replicas:", min_value=0, max_value=50, value=3)
            
            if st.button("🚀 Scale Now") and deployment:
                try:
                    cmd = f"kubectl scale deployment {deployment} --replicas={replicas} -n {namespace}"
                    result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        st.success(f"✅ Scaled {deployment} to {replicas} replicas")
                    else:
                        st.error(f"❌ Scaling failed: {result.stderr}")
                except Exception as e:
                    st.error(f"❌ Error scaling: {e}")

def render_analytics_page():
    """Render analytics page"""
    st.header("📈 Cluster Analytics")
    
    if not PLOTTING_AVAILABLE:
        st.warning("📊 Plotting libraries not available. Install plotly for full analytics.")
        return
    
    # Get data for analytics
    k8s_data = get_real_kubernetes_data()
    
    if k8s_data.get("error"):
        st.error(f"❌ Cannot load analytics: {k8s_data['error']}")
        return
    
    # Pod status distribution
    if k8s_data["pods"]:
        pods_df = pd.DataFrame(k8s_data["pods"])
        
        # Status pie chart
        st.subheader("📊 Pod Status Distribution")
        status_counts = pods_df['status'].value_counts()
        fig = px.pie(values=status_counts.values, names=status_counts.index)
        st.plotly_chart(fig, use_container_width=True)
        
        # Namespace distribution
        st.subheader("🏷️ Pods by Namespace") 
        namespace_counts = pods_df['namespace'].value_counts()
        fig = px.bar(x=namespace_counts.index, y=namespace_counts.values)
        fig.update_layout(xaxis_title="Namespace", yaxis_title="Pod Count")
        st.plotly_chart(fig, use_container_width=True)
        
        # Restarts analysis
        st.subheader("🔄 Pod Restart Analysis")
        restart_data = pods_df[pods_df['restarts'] > 0].nlargest(10, 'restarts')
        if not restart_data.empty:
            fig = px.bar(restart_data, x='name', y='restarts', 
                        title="Pods with Most Restarts")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pods with restarts found")

def render_settings_page():
    """Render settings page"""
    st.header("⚙️ Settings & Configuration")
    
    # System status
    st.subheader("🔍 System Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Kubernetes Integration:**")
        if K8S_CONFIG_LOADED:
            st.success(f"✅ Connected ({K8S_MODE})")
        else:
            st.error("❌ Not connected")
        
        st.write("**LLaMA Integration:**")
        if LLAMA_AVAILABLE:
            st.success(f"✅ {ACTIVE_LLAMA_ENDPOINT['name']} on {ACTIVE_LLAMA_ENDPOINT['url']}")
        else:
            st.error("❌ No LLaMA server available")
    
    with col2:
        st.write("**Available Libraries:**")
        st.write(f"• Kubernetes: {'✅' if KUBERNETES_AVAILABLE else '❌'}")
        st.write(f"• Plotly: {'✅' if PLOTTING_AVAILABLE else '❌'}")
        st.write(f"• Requests: ✅")
        st.write(f"• Pandas: ✅")
    
    # Connection testing
    st.subheader("🧪 Connection Testing")
    
    if st.button("Test LLaMA Connection"):
        with st.spinner("Testing LLaMA endpoints..."):
            for endpoint in LLAMA_ENDPOINTS:
                result = test_llama_server(endpoint["url"], endpoint["type"])
                if result:
                    st.success(f"✅ {endpoint['name']} at {endpoint['url']}")
                else:
                    st.error(f"❌ {endpoint['name']} at {endpoint['url']}")
    
    if st.button("Test Kubernetes Connection"):
        with st.spinner("Testing Kubernetes API..."):
            k8s_data = get_real_kubernetes_data()
            if k8s_data.get("error"):
                st.error(f"❌ Kubernetes test failed: {k8s_data['error']}")
            else:
                st.success(f"✅ Kubernetes API working - {len(k8s_data['pods'])} pods found")
    
    # Configuration export
    st.subheader("📄 Configuration")
    config = {
        "kubernetes_available": KUBERNETES_AVAILABLE,
        "kubernetes_connected": K8S_CONFIG_LOADED,
        "kubernetes_mode": K8S_MODE,
        "llama_available": LLAMA_AVAILABLE,
        "llama_endpoint": ACTIVE_LLAMA_ENDPOINT,
        "plotting_available": PLOTTING_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }
    
    st.json(config)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"🚨 Application Error: {str(e)}")
        st.write("Please check the logs and refresh the page.")
        logger.error(f"Dashboard error: {e}", exc_info=True)
