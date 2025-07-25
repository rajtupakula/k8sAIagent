#!/usr/bin/env python3
"""
SMART INTERACTIVE KUBERNETES AI DASHBOARD
Real-time cluster analysis with intelligent troubleshooting
"""
import streamlit as st
import os
import sys
import time
import json
import subprocess
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import threading

# Configure Streamlit page FIRST
st.set_page_config(
    page_title="🧠 Smart Kubernetes AI - Live Cluster Assistant",
    page_icon="🧠",
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

# Initialize session state
if 'live_cluster_data' not in st.session_state:
    st.session_state.live_cluster_data = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = None
if 'auto_scan' not in st.session_state:
    st.session_state.auto_scan = False

class SmartClusterAnalyzer:
    """Real-time cluster analysis and intelligent troubleshooting"""
    
    def __init__(self):
        self.kubectl_available = self._check_kubectl()
        
    def _check_kubectl(self) -> bool:
        """Check if kubectl is available and configured"""
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def get_live_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive real-time cluster status"""
        if not self.kubectl_available:
            return {"status": "kubectl_unavailable", "message": "kubectl not found or not configured"}
        
        try:
            cluster_data = {
                "timestamp": datetime.now().isoformat(),
                "status": "connected",
                "pods": self._get_pod_status(),
                "nodes": self._get_node_status(),
                "services": self._get_service_status(),
                "events": self._get_recent_events(),
                "namespaces": self._get_namespaces(),
                "resource_usage": self._get_resource_usage(),
                "health_summary": {}
            }
            
            # Generate health summary
            cluster_data["health_summary"] = self._analyze_cluster_health(cluster_data)
            
            return cluster_data
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _get_pod_status(self) -> Dict[str, Any]:
        """Get detailed pod status across all namespaces"""
        try:
            result = subprocess.run(['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json'], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                pods_data = json.loads(result.stdout)
                pod_summary = {
                    "total": 0,
                    "running": 0,
                    "pending": 0,
                    "failed": 0,
                    "succeeded": 0,
                    "crashloop": 0,
                    "imagepull_issues": 0,
                    "by_namespace": {},
                    "problem_pods": []
                }
                
                for pod in pods_data.get('items', []):
                    namespace = pod['metadata']['namespace']
                    name = pod['metadata']['name']
                    status = pod['status']['phase']
                    
                    # Count by namespace
                    if namespace not in pod_summary["by_namespace"]:
                        pod_summary["by_namespace"][namespace] = {"total": 0, "running": 0, "issues": 0}
                    
                    pod_summary["by_namespace"][namespace]["total"] += 1
                    pod_summary["total"] += 1
                    
                    # Analyze pod status
                    if status == "Running":
                        pod_summary["running"] += 1
                        pod_summary["by_namespace"][namespace]["running"] += 1
                    elif status == "Pending":
                        pod_summary["pending"] += 1
                        pod_summary["by_namespace"][namespace]["issues"] += 1
                    elif status == "Failed":
                        pod_summary["failed"] += 1
                        pod_summary["by_namespace"][namespace]["issues"] += 1
                    elif status == "Succeeded":
                        pod_summary["succeeded"] += 1
                    
                    # Check for specific issues
                    container_statuses = pod['status'].get('containerStatuses', [])
                    for container in container_statuses:
                        waiting = container.get('state', {}).get('waiting', {})
                        if waiting:
                            reason = waiting.get('reason', '')
                            if 'CrashLoopBackOff' in reason:
                                pod_summary["crashloop"] += 1
                                pod_summary["problem_pods"].append({
                                    "name": name,
                                    "namespace": namespace,
                                    "issue": "CrashLoopBackOff",
                                    "message": waiting.get('message', '')
                                })
                            elif 'ImagePullBackOff' in reason or 'ErrImagePull' in reason:
                                pod_summary["imagepull_issues"] += 1
                                pod_summary["problem_pods"].append({
                                    "name": name,
                                    "namespace": namespace,
                                    "issue": "ImagePullBackOff",
                                    "message": waiting.get('message', '')
                                })
                
                return pod_summary
            else:
                return {"error": "Failed to get pod status"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _get_node_status(self) -> Dict[str, Any]:
        """Get detailed node status and resource information"""
        try:
            result = subprocess.run(['kubectl', 'get', 'nodes', '-o', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                nodes_data = json.loads(result.stdout)
                node_summary = {
                    "total": 0,
                    "ready": 0,
                    "not_ready": 0,
                    "nodes": [],
                    "resource_capacity": {"cpu": 0, "memory": 0},
                    "resource_allocatable": {"cpu": 0, "memory": 0}
                }
                
                for node in nodes_data.get('items', []):
                    name = node['metadata']['name']
                    conditions = node['status'].get('conditions', [])
                    
                    # Check node readiness
                    is_ready = False
                    for condition in conditions:
                        if condition['type'] == 'Ready' and condition['status'] == 'True':
                            is_ready = True
                            break
                    
                    node_info = {
                        "name": name,
                        "ready": is_ready,
                        "roles": list(node['metadata'].get('labels', {}).keys()),
                        "version": node['status']['nodeInfo']['kubeletVersion'],
                        "capacity": node['status']['capacity'],
                        "allocatable": node['status']['allocatable'],
                        "conditions": [{"type": c['type'], "status": c['status'], "reason": c.get('reason', '')} for c in conditions]
                    }
                    
                    node_summary["nodes"].append(node_info)
                    node_summary["total"] += 1
                    
                    if is_ready:
                        node_summary["ready"] += 1
                    else:
                        node_summary["not_ready"] += 1
                    
                    # Aggregate resource capacity
                    try:
                        cpu_capacity = node['status']['capacity'].get('cpu', '0')
                        memory_capacity = node['status']['capacity'].get('memory', '0Ki')
                        
                        # Convert CPU (can be in millicores)
                        if 'm' in cpu_capacity:
                            cpu_val = float(cpu_capacity.replace('m', '')) / 1000
                        else:
                            cpu_val = float(cpu_capacity)
                        node_summary["resource_capacity"]["cpu"] += cpu_val
                        
                        # Convert memory (remove unit and convert to GB)
                        memory_val = self._convert_memory_to_gb(memory_capacity)
                        node_summary["resource_capacity"]["memory"] += memory_val
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse resources for node {name}: {e}")
                
                return node_summary
            else:
                return {"error": "Failed to get node status"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _convert_memory_to_gb(self, memory_str: str) -> float:
        """Convert memory string to GB"""
        try:
            if 'Ki' in memory_str:
                return float(memory_str.replace('Ki', '')) / (1024 * 1024)
            elif 'Mi' in memory_str:
                return float(memory_str.replace('Mi', '')) / 1024
            elif 'Gi' in memory_str:
                return float(memory_str.replace('Gi', ''))
            elif 'Ti' in memory_str:
                return float(memory_str.replace('Ti', '')) * 1024
            else:
                return float(memory_str) / (1024**3)  # Assume bytes
        except:
            return 0.0
    
    def _get_service_status(self) -> Dict[str, Any]:
        """Get service and endpoint status"""
        try:
            result = subprocess.run(['kubectl', 'get', 'services', '--all-namespaces', '-o', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                service_summary = {
                    "total": 0,
                    "by_type": {"ClusterIP": 0, "NodePort": 0, "LoadBalancer": 0, "ExternalName": 0},
                    "services": []
                }
                
                for svc in services_data.get('items', []):
                    name = svc['metadata']['name']
                    namespace = svc['metadata']['namespace']
                    svc_type = svc['spec'].get('type', 'ClusterIP')
                    
                    service_summary["total"] += 1
                    service_summary["by_type"][svc_type] = service_summary["by_type"].get(svc_type, 0) + 1
                    
                    service_summary["services"].append({
                        "name": name,
                        "namespace": namespace,
                        "type": svc_type,
                        "cluster_ip": svc['spec'].get('clusterIP', ''),
                        "ports": svc['spec'].get('ports', [])
                    })
                
                return service_summary
            else:
                return {"error": "Failed to get service status"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Get recent cluster events for troubleshooting"""
        try:
            result = subprocess.run(['kubectl', 'get', 'events', '--all-namespaces', 
                                   '--sort-by=.metadata.creationTimestamp', '-o', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                events_data = json.loads(result.stdout)
                recent_events = []
                
                # Get events from last hour
                now = datetime.now()
                one_hour_ago = now - timedelta(hours=1)
                
                for event in events_data.get('items', [])[-50:]:  # Last 50 events
                    try:
                        event_time = datetime.fromisoformat(
                            event['metadata']['creationTimestamp'].replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                        
                        if event_time > one_hour_ago:
                            recent_events.append({
                                "time": event_time.isoformat(),
                                "namespace": event['metadata']['namespace'],
                                "type": event.get('type', 'Normal'),
                                "reason": event.get('reason', ''),
                                "message": event.get('message', ''),
                                "object": event['involvedObject'].get('name', ''),
                                "kind": event['involvedObject'].get('kind', '')
                            })
                    except Exception as e:
                        continue
                
                return recent_events
            else:
                return []
                
        except Exception as e:
            return []
    
    def _get_namespaces(self) -> List[str]:
        """Get list of namespaces"""
        try:
            result = subprocess.run(['kubectl', 'get', 'namespaces', '-o', 'name'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return [ns.replace('namespace/', '') for ns in result.stdout.strip().split('\n')]
            else:
                return []
                
        except Exception as e:
            return []
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get resource usage if metrics server is available"""
        try:
            # Try to get node metrics
            result = subprocess.run(['kubectl', 'top', 'nodes'], 
                                  capture_output=True, text=True, timeout=10)
            
            usage_data = {"nodes_available": False, "pods_available": False}
            
            if result.returncode == 0:
                usage_data["nodes_available"] = True
                usage_data["node_usage"] = result.stdout
            
            # Try to get pod metrics
            result = subprocess.run(['kubectl', 'top', 'pods', '--all-namespaces'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                usage_data["pods_available"] = True
                usage_data["pod_usage"] = result.stdout
            
            return usage_data
            
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_cluster_health(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall cluster health and identify issues"""
        health = {
            "overall_status": "healthy",
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Check pod health
        pods = cluster_data.get("pods", {})
        if pods.get("failed", 0) > 0:
            health["overall_status"] = "degraded"
            health["issues"].append(f"{pods['failed']} pods are in failed state")
        
        if pods.get("crashloop", 0) > 0:
            health["overall_status"] = "degraded"
            health["issues"].append(f"{pods['crashloop']} pods are crash looping")
        
        if pods.get("imagepull_issues", 0) > 0:
            health["overall_status"] = "warning"
            health["warnings"].append(f"{pods['imagepull_issues']} pods have image pull issues")
        
        # Check node health
        nodes = cluster_data.get("nodes", {})
        if nodes.get("not_ready", 0) > 0:
            health["overall_status"] = "critical"
            health["issues"].append(f"{nodes['not_ready']} nodes are not ready")
        
        # Check for recent error events
        events = cluster_data.get("events", [])
        error_events = [e for e in events if e.get("type") == "Warning"]
        if len(error_events) > 5:
            health["warnings"].append(f"{len(error_events)} warning events in the last hour")
        
        # Generate recommendations
        if health["issues"]:
            health["recommendations"].append("Immediate attention required for failed components")
        if health["warnings"]:
            health["recommendations"].append("Monitor warning conditions for potential issues")
        if not health["issues"] and not health["warnings"]:
            health["recommendations"].append("Cluster is healthy - continue monitoring")
        
        return health
    
    def intelligent_analysis(self, user_query: str, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide intelligent analysis based on user query and live cluster data"""
        query_lower = user_query.lower()
        
        analysis = {
            "query": user_query,
            "analysis_type": "general",
            "confidence": 0.0,
            "live_data_insights": [],
            "specific_issues": [],
            "recommended_actions": [],
            "kubectl_commands": [],
            "auto_fix_available": False
        }
        
        # Check if we have live data
        if cluster_data.get("status") != "connected":
            analysis["live_data_insights"] = ["❌ Cannot connect to cluster - kubectl not available"]
            analysis["recommended_actions"] = ["Configure kubectl access to your cluster"]
            return analysis
        
        # Analyze based on query intent and live data
        pods = cluster_data.get("pods", {})
        nodes = cluster_data.get("nodes", {})
        events = cluster_data.get("events", [])
        
        # Pod health queries
        if any(word in query_lower for word in ["pod", "pods", "container"]):
            analysis["analysis_type"] = "pod_analysis"
            analysis["confidence"] = 0.95
            
            # Live pod insights
            total_pods = pods.get("total", 0)
            running_pods = pods.get("running", 0)
            failed_pods = pods.get("failed", 0)
            crashloop_pods = pods.get("crashloop", 0)
            
            analysis["live_data_insights"] = [
                f"📊 **Live Status**: {running_pods}/{total_pods} pods running",
                f"🚨 **Issues**: {failed_pods} failed, {crashloop_pods} crash looping"
            ]
            
            if failed_pods > 0 or crashloop_pods > 0:
                analysis["specific_issues"] = []
                for problem_pod in pods.get("problem_pods", []):
                    analysis["specific_issues"].append(
                        f"❌ **{problem_pod['name']}** in {problem_pod['namespace']}: {problem_pod['issue']}"
                    )
                
                analysis["recommended_actions"] = [
                    f"Check failing pods: kubectl get pods --all-namespaces | grep -E '(Error|CrashLoop|Failed)'",
                    f"Get detailed pod info: kubectl describe pod <pod-name> -n <namespace>",
                    f"Check pod logs: kubectl logs <pod-name> -n <namespace> --previous"
                ]
                
                analysis["kubectl_commands"] = [
                    "kubectl get pods --all-namespaces",
                    "kubectl get events --sort-by=.metadata.creationTimestamp"
                ]
                analysis["auto_fix_available"] = True
            else:
                analysis["live_data_insights"].append("✅ All pods are healthy!")
        
        # Node health queries
        elif any(word in query_lower for word in ["node", "nodes", "cluster"]):
            analysis["analysis_type"] = "node_analysis"
            analysis["confidence"] = 0.95
            
            total_nodes = nodes.get("total", 0)
            ready_nodes = nodes.get("ready", 0)
            not_ready_nodes = nodes.get("not_ready", 0)
            
            analysis["live_data_insights"] = [
                f"🖥️ **Live Status**: {ready_nodes}/{total_nodes} nodes ready",
                f"💾 **Capacity**: {nodes.get('resource_capacity', {}).get('cpu', 0):.1f} CPU cores, {nodes.get('resource_capacity', {}).get('memory', 0):.1f}GB memory"
            ]
            
            if not_ready_nodes > 0:
                analysis["specific_issues"] = [f"❌ {not_ready_nodes} nodes are not ready"]
                
                # Find which nodes are not ready
                for node in nodes.get("nodes", []):
                    if not node["ready"]:
                        analysis["specific_issues"].append(f"❌ **{node['name']}** is not ready")
                
                analysis["recommended_actions"] = [
                    "Check node status: kubectl get nodes",
                    "Describe problem nodes: kubectl describe node <node-name>",
                    "Check kubelet logs on the node",
                    "Verify node network connectivity"
                ]
                analysis["kubectl_commands"] = [
                    "kubectl get nodes",
                    "kubectl describe nodes"
                ]
            else:
                analysis["live_data_insights"].append("✅ All nodes are ready!")
        
        # Service/networking queries
        elif any(word in query_lower for word in ["service", "network", "connection", "endpoint"]):
            analysis["analysis_type"] = "service_analysis"
            analysis["confidence"] = 0.90
            
            services = cluster_data.get("services", {})
            total_services = services.get("total", 0)
            
            analysis["live_data_insights"] = [
                f"🌐 **Live Status**: {total_services} services running",
                f"📊 **Types**: {services.get('by_type', {})}"
            ]
            
            analysis["recommended_actions"] = [
                "Check services: kubectl get svc --all-namespaces",
                "Check endpoints: kubectl get ep --all-namespaces",
                "Test service connectivity: kubectl run test-pod --image=busybox -it --rm -- nslookup <service-name>"
            ]
            
            analysis["kubectl_commands"] = [
                "kubectl get svc,ep --all-namespaces",
                "kubectl describe svc <service-name>"
            ]
        
        # Event-based troubleshooting
        elif any(word in query_lower for word in ["event", "error", "warning", "issue"]):
            analysis["analysis_type"] = "event_analysis"
            analysis["confidence"] = 0.85
            
            warning_events = [e for e in events if e.get("type") == "Warning"]
            recent_events = events[-10:] if events else []
            
            analysis["live_data_insights"] = [
                f"📋 **Recent Events**: {len(events)} events in last hour",
                f"⚠️ **Warnings**: {len(warning_events)} warning events"
            ]
            
            if warning_events:
                analysis["specific_issues"] = []
                for event in warning_events[-5:]:  # Last 5 warnings
                    analysis["specific_issues"].append(
                        f"⚠️ **{event['object']}**: {event['reason']} - {event['message'][:100]}..."
                    )
            
            analysis["recommended_actions"] = [
                "Check recent events: kubectl get events --sort-by=.metadata.creationTimestamp",
                "Filter warning events: kubectl get events --field-selector type=Warning",
                "Monitor specific objects: kubectl describe <resource-type> <resource-name>"
            ]
            
            analysis["kubectl_commands"] = [
                "kubectl get events --sort-by=.metadata.creationTimestamp",
                "kubectl get events --field-selector type=Warning"
            ]
        
        # General health check
        else:
            analysis["analysis_type"] = "health_check"
            analysis["confidence"] = 0.80
            
            health = cluster_data.get("health_summary", {})
            overall_status = health.get("overall_status", "unknown")
            
            analysis["live_data_insights"] = [
                f"🏥 **Cluster Health**: {overall_status.upper()}",
                f"📊 **Summary**: {pods.get('running', 0)}/{pods.get('total', 0)} pods running, {nodes.get('ready', 0)}/{nodes.get('total', 0)} nodes ready"
            ]
            
            if health.get("issues"):
                analysis["specific_issues"] = [f"❌ {issue}" for issue in health["issues"]]
            
            if health.get("warnings"):
                analysis["specific_issues"].extend([f"⚠️ {warning}" for warning in health["warnings"]])
            
            analysis["recommended_actions"] = health.get("recommendations", [
                "Run comprehensive health check: kubectl get all --all-namespaces",
                "Check cluster events: kubectl get events --sort-by=.metadata.creationTimestamp",
                "Monitor resource usage: kubectl top nodes && kubectl top pods --all-namespaces"
            ])
        
        return analysis

# Initialize the smart analyzer
@st.cache_resource
def get_smart_analyzer():
    return SmartClusterAnalyzer()

def scan_cluster():
    """Scan cluster and update session state"""
    analyzer = get_smart_analyzer()
    
    with st.spinner("🔍 Scanning cluster..."):
        cluster_data = analyzer.get_live_cluster_status()
        st.session_state.live_cluster_data = cluster_data
        st.session_state.last_scan_time = datetime.now()
    
    return cluster_data

def ask_smart_ai(query: str):
    """Ask the smart AI with live cluster context"""
    analyzer = get_smart_analyzer()
    
    # Get latest cluster data
    cluster_data = st.session_state.live_cluster_data
    if not cluster_data or (datetime.now() - st.session_state.last_scan_time).seconds > 300:
        cluster_data = scan_cluster()
    
    # Get intelligent analysis
    with st.spinner("🧠 Analyzing with live cluster data..."):
        analysis = analyzer.intelligent_analysis(query, cluster_data)
    
    # Add to chat history
    chat_entry = {
        "query": query,
        "analysis": analysis,
        "timestamp": datetime.now().isoformat(),
        "cluster_timestamp": cluster_data.get("timestamp")
    }
    
    st.session_state.chat_history.append(chat_entry)

def main():
    """Main smart dashboard"""
    
    # Header
    st.title("🧠 Smart Kubernetes AI - Live Cluster Assistant")
    st.caption("🔴 **LIVE** • Real-time cluster analysis • Intelligent troubleshooting • Interactive fixes")
    
    # Check cluster connectivity
    analyzer = get_smart_analyzer()
    if analyzer.kubectl_available:
        st.success("✅ **Connected to Kubernetes cluster** - Real-time analysis enabled")
    else:
        st.error("❌ **kubectl not available** - Configure kubectl to enable live analysis")
        st.stop()
    
    # Auto-scan setup
    if st.session_state.auto_scan and (
        not st.session_state.last_scan_time or 
        (datetime.now() - st.session_state.last_scan_time).seconds > 30
    ):
        scan_cluster()
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Smart Controls")
        
        st.session_state.auto_scan = st.checkbox("🔄 Auto-scan (30s)", value=st.session_state.auto_scan)
        
        if st.button("🔍 Scan Cluster Now"):
            scan_cluster()
            st.rerun()
        
        if st.button("🧹 Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        
        # Show last scan time
        if st.session_state.last_scan_time:
            st.write(f"Last scan: {st.session_state.last_scan_time.strftime('%H:%M:%S')}")
    
    # Main tabs
    tab1, tab2 = st.tabs(["💬 AI Chat", "📊 System Info"])
    
    with tab1:
        ai_chat_tab()
    
    with tab2:
        system_info_tab()

def ai_chat_tab():
    """Enhanced AI Chat with live cluster integration"""
    st.header("💬 Chat with Smart AI")
    st.write("Ask me anything about your cluster - I'll analyze live data and provide intelligent solutions!")
    
    # Display chat history
    for i, chat in enumerate(st.session_state.chat_history):
        with st.container():
            # User query
            st.markdown(f"**🙋 You:** {chat['query']}")
            
            # AI analysis
            analysis = chat['analysis']
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**🧠 Smart AI:** Analysis Type: **{analysis['analysis_type'].replace('_', ' ').title()}**")
            with col2:
                confidence_color = "🟢" if analysis['confidence'] > 0.8 else "🟡" if analysis['confidence'] > 0.6 else "🔴"
                st.metric("Confidence", f"{confidence_color} {analysis['confidence']:.0%}")
            
            # Live insights
            if analysis.get('live_data_insights'):
                st.markdown("**📊 Live Cluster Insights:**")
                for insight in analysis['live_data_insights']:
                    st.markdown(f"• {insight}")
            
            # Specific issues
            if analysis.get('specific_issues'):
                st.markdown("**🚨 Issues Detected:**")
                for issue in analysis['specific_issues']:
                    st.markdown(f"• {issue}")
            
            # Recommended actions
            if analysis.get('recommended_actions'):
                st.markdown("**💡 Recommended Actions:**")
                for i, action in enumerate(analysis['recommended_actions'], 1):
                    st.markdown(f"{i}. {action}")
            
            # kubectl commands
            if analysis.get('kubectl_commands'):
                with st.expander("🔧 kubectl Commands"):
                    for cmd in analysis['kubectl_commands']:
                        st.code(cmd, language="bash")
            
            # Auto-fix option
            if analysis.get('auto_fix_available'):
                if st.button(f"🔧 Auto-fix Issues", key=f"fix_{i}"):
                    st.info("🔧 Auto-fix functionality would execute remediation steps here")
            
            st.divider()
    
    # Chat input
    query = st.text_area(
        "💭 Ask your question:",
        placeholder="Examples:\n• 'Are all my pods healthy?'\n• 'What's wrong with my cluster?'\n• 'Check node status'\n• 'Why is my service failing?'",
        height=100
    )
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🚀 Ask Smart AI", disabled=not query.strip(), type="primary"):
            ask_smart_ai(query.strip())
            st.rerun()
    
    with col2:
        if st.button("🔍 Quick Health Check"):
            ask_smart_ai("What's the overall health of my cluster?")
            st.rerun()

def system_info_tab():
    """Enhanced System Info with live cluster data"""
    st.header("📊 Live System Information")
    
    # Get latest cluster data
    cluster_data = st.session_state.live_cluster_data
    
    if not cluster_data:
        st.info("No cluster data available. Click 'Scan Cluster Now' to get live information.")
        return
    
    if cluster_data.get("status") != "connected":
        st.error(f"Cannot connect to cluster: {cluster_data.get('message', 'Unknown error')}")
        return
    
    # Cluster overview
    st.subheader("🏥 Cluster Health Overview")
    
    health = cluster_data.get("health_summary", {})
    status = health.get("overall_status", "unknown")
    
    if status == "healthy":
        st.success(f"🟢 **HEALTHY** - Cluster is operating normally")
    elif status == "warning":
        st.warning(f"🟡 **WARNING** - Some issues detected")
    elif status == "degraded":
        st.error(f"🟠 **DEGRADED** - Multiple issues require attention")
    elif status == "critical":
        st.error(f"🔴 **CRITICAL** - Immediate action required")
    
    # Metrics overview
    col1, col2, col3, col4 = st.columns(4)
    
    pods = cluster_data.get("pods", {})
    nodes = cluster_data.get("nodes", {})
    services = cluster_data.get("services", {})
    
    with col1:
        st.metric(
            "Pods Running", 
            f"{pods.get('running', 0)}/{pods.get('total', 0)}",
            delta=f"-{pods.get('failed', 0)}" if pods.get('failed', 0) > 0 else None
        )
    
    with col2:
        st.metric(
            "Nodes Ready", 
            f"{nodes.get('ready', 0)}/{nodes.get('total', 0)}",
            delta=f"-{nodes.get('not_ready', 0)}" if nodes.get('not_ready', 0) > 0 else None
        )
    
    with col3:
        st.metric("Services", services.get('total', 0))
    
    with col4:
        st.metric("Namespaces", len(cluster_data.get('namespaces', [])))
    
    # Detailed sections
    col1, col2 = st.columns(2)
    
    with col1:
        # Pod details
        st.subheader("🚀 Pod Status")
        if pods.get("by_namespace"):
            for namespace, ns_data in pods["by_namespace"].items():
                issues = ns_data.get("issues", 0)
                status_icon = "✅" if issues == 0 else "⚠️"
                st.write(f"{status_icon} **{namespace}**: {ns_data['running']}/{ns_data['total']} running")
        
        # Problem pods
        if pods.get("problem_pods"):
            st.subheader("🚨 Problem Pods")
            for pod in pods["problem_pods"]:
                st.error(f"❌ **{pod['name']}** ({pod['namespace']}): {pod['issue']}")
    
    with col2:
        # Node details
        st.subheader("🖥️ Node Information")
        for node in nodes.get("nodes", []):
            status_icon = "✅" if node["ready"] else "❌"
            st.write(f"{status_icon} **{node['name']}** - {node['version']}")
        
        # Resource capacity
        st.subheader("💾 Cluster Resources")
        cpu_capacity = nodes.get('resource_capacity', {}).get('cpu', 0)
        memory_capacity = nodes.get('resource_capacity', {}).get('memory', 0)
        st.write(f"**CPU**: {cpu_capacity:.1f} cores")
        st.write(f"**Memory**: {memory_capacity:.1f} GB")
    
    # Recent events
    st.subheader("📋 Recent Events")
    events = cluster_data.get("events", [])
    
    if events:
        # Show last 10 events
        for event in events[-10:]:
            time_str = datetime.fromisoformat(event['time']).strftime('%H:%M:%S')
            type_icon = "⚠️" if event['type'] == "Warning" else "ℹ️"
            st.write(f"{type_icon} **{time_str}** - {event['object']} ({event['kind']}): {event['reason']}")
    else:
        st.info("No recent events")
    
    # Resource usage (if available)
    resource_usage = cluster_data.get("resource_usage", {})
    if resource_usage.get("nodes_available"):
        st.subheader("📊 Resource Usage")
        st.text("Node Usage:")
        st.code(resource_usage["node_usage"])
        
        if resource_usage.get("pods_available"):
            with st.expander("Pod Resource Usage"):
                st.code(resource_usage["pod_usage"])
    
    # Raw data section
    with st.expander("🔍 Raw Cluster Data (JSON)"):
        st.json(cluster_data)

if __name__ == "__main__":
    main()
