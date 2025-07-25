import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import threading
import time
import queue
import os

# Import host system monitor if available
try:
    from .host_system_monitor import HostSystemMonitor
    HOST_MONITORING_AVAILABLE = True
except ImportError:
    HOST_MONITORING_AVAILABLE = False

class KubernetesMonitor:
    """Monitor Kubernetes cluster for logs, metrics, and issues."""
    
    def __init__(self, config_file: str = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file
        self.v1 = None
        self.apps_v1 = None
        self.metrics_v1 = None
        self.connected = False
        self.issues = []
        self.metrics_cache = {}
        self.log_queue = queue.Queue(maxsize=1000)
        self.monitoring_active = False
        
        # Initialize host system monitor if in privileged mode
        self.host_monitor = None
        if HOST_MONITORING_AVAILABLE and os.path.exists("/usr/local/bin/host-exec"):
            try:
                self.host_monitor = HostSystemMonitor()
                self.logger.info("Host system monitoring enabled")
            except Exception as e:
                self.logger.warning(f"Failed to initialize host system monitor: {e}")
        
        self.connect()
    
    def connect(self) -> bool:
        """Connect to Kubernetes cluster."""
        try:
            if self.config_file:
                config.load_kube_config(config_file=self.config_file)
                self.logger.info("Using specified kubeconfig file")
            else:
                try:
                    # Try in-cluster config first (when running in pod)
                    config.load_incluster_config()
                    self.logger.info("Using in-cluster Kubernetes configuration")
                except config.ConfigException:
                    # Fallback to kubeconfig file (development/local)
                    try:
                        config.load_kube_config()
                        self.logger.info("Using kubeconfig file for Kubernetes connection")
                    except config.ConfigException as e:
                        self.logger.warning(f"No valid Kubernetes configuration found: {e}")
                        self.connected = False
                        return False
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.metrics_v1 = client.CustomObjectsApi()
            
            # Test connection
            self.v1.list_namespace(limit=1)
            self.connected = True
            self.logger.info("Successfully connected to Kubernetes cluster")
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to connect to Kubernetes: {e}")
            self.logger.warning("Monitor will run with limited functionality")
            self.connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to cluster."""
        return self.connected
    
    def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get current cluster metrics."""
        if not self.connected:
            return {}
        
        try:
            nodes = self.v1.list_node()
            pods = self.v1.list_pod_for_all_namespaces()
            
            # Calculate basic metrics
            total_cpu = 0
            total_memory = 0
            used_cpu = 0
            used_memory = 0
            
            for node in nodes.items:
                if node.status.allocatable:
                    cpu_allocatable = self._parse_cpu(node.status.allocatable.get('cpu', '0'))
                    memory_allocatable = self._parse_memory(node.status.allocatable.get('memory', '0'))
                    total_cpu += cpu_allocatable
                    total_memory += memory_allocatable
            
            # Get pod resource requests/usage
            running_pods = [p for p in pods.items if p.status.phase == 'Running']
            
            self.metrics_cache = {
                'cpu_usage': (used_cpu / total_cpu * 100) if total_cpu > 0 else 0,
                'memory_usage': (used_memory / total_memory * 100) if total_memory > 0 else 0,
                'pod_count': len(running_pods),
                'node_count': len(nodes.items),
                'total_pods': len(pods.items),
                'timestamp': datetime.now().isoformat()
            }
            
            return self.metrics_cache
            
        except Exception as e:
            self.logger.error(f"Error getting cluster metrics: {e}")
            return {}
    
    def scan_for_issues(self) -> List[Dict[str, Any]]:
        """Scan cluster for issues and problems."""
        if not self.connected:
            return []
        
        issues = []
        
        try:
            # Check pod issues
            pods = self.v1.list_pod_for_all_namespaces()
            for pod in pods.items:
                pod_issues = self._check_pod_issues(pod)
                issues.extend(pod_issues)
            
            # Check node issues
            try:
                nodes = self.v1.list_node()
                for node in nodes.items:
                    node_issues = self._check_node_issues(node)
                    issues.extend(node_issues)
            except ApiException as e:
                if e.status == 403:
                    self.logger.warning("Insufficient permissions to list nodes, skipping node health checks")
                else:
                    self.logger.error(f"Error checking nodes: {e}")
            
            # Check persistent volume issues
            try:
                pvs = self.v1.list_persistent_volume()
                for pv in pvs.items:
                    pv_issues = self._check_pv_issues(pv)
                    issues.extend(pv_issues)
            except ApiException as e:
                if e.status == 403:
                    self.logger.warning("Insufficient permissions to list persistent volumes, skipping PV health checks")
                else:
                    self.logger.error(f"Error checking persistent volumes: {e}")
            
            self.issues = issues
            return issues
            
        except Exception as e:
            self.logger.error(f"Error scanning for issues: {e}")
            return []
    
    def get_recent_issues(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent issues from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_issues = []
        
        for issue in self.issues:
            issue_time = datetime.fromisoformat(issue.get('timestamp', ''))
            if issue_time > cutoff_time:
                recent_issues.append(issue)
        
        return sorted(recent_issues, key=lambda x: x['timestamp'], reverse=True)
    
    def get_live_logs(self, namespace: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get live logs from pods."""
        logs = []
        
        try:
            # Get recent log entries from queue
            recent_logs = []
            while not self.log_queue.empty() and len(recent_logs) < limit:
                try:
                    recent_logs.append(self.log_queue.get_nowait())
                except queue.Empty:
                    break
            
            return recent_logs[-limit:]
            
        except Exception as e:
            self.logger.error(f"Error getting live logs: {e}")
            return []
    
    def start_log_monitoring(self):
        """Start background log monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        thread = threading.Thread(target=self._monitor_logs, daemon=True)
        thread.start()
    
    def stop_log_monitoring(self):
        """Stop background log monitoring."""
        self.monitoring_active = False
    
    def get_deployments(self) -> List[str]:
        """Get list of deployments."""
        if not self.connected:
            return []
        
        try:
            deployments = self.apps_v1.list_deployment_for_all_namespaces()
            return [f"{d.metadata.namespace}/{d.metadata.name}" for d in deployments.items]
        except Exception as e:
            self.logger.error(f"Error getting deployments: {e}")
            return []
    
    def get_nodes(self) -> List[str]:
        """Get list of node names."""
        if not self.connected:
            return []
        
        try:
            nodes = self.v1.list_node()
            return [node.metadata.name for node in nodes.items]
        except Exception as e:
            self.logger.error(f"Error getting nodes: {e}")
            return []
    
    def analyze_storage_usage(self) -> Dict[str, Any]:
        """Analyze storage usage across the cluster."""
        if not self.connected:
            return {'volumes': []}
        
        try:
            pvs = []
            pvcs = []
            
            # Try to get persistent volumes with error handling
            try:
                pvs = self.v1.list_persistent_volume().items
            except ApiException as e:
                if e.status == 403:
                    self.logger.warning("Insufficient permissions to list persistent volumes")
                else:
                    self.logger.error(f"Error listing persistent volumes: {e}")
            
            # Try to get persistent volume claims with error handling  
            try:
                pvcs = self.v1.list_persistent_volume_claim_for_all_namespaces().items
            except ApiException as e:
                if e.status == 403:
                    self.logger.warning("Insufficient permissions to list persistent volume claims")
                else:
                    self.logger.error(f"Error listing persistent volume claims: {e}")
            
            volumes = []
            for pv in pvs:
                volume_info = {
                    'name': pv.metadata.name,
                    'capacity': pv.spec.capacity.get('storage', 'Unknown'),
                    'storage_class': pv.spec.storage_class_name or 'default',
                    'status': pv.status.phase,
                    'access_modes': pv.spec.access_modes,
                    'used_gb': 0,  # Would need metrics server for actual usage
                    'available_gb': self._parse_storage(pv.spec.capacity.get('storage', '0')),
                    'usage_percent': 0
                }
                volumes.append(volume_info)
            
            return {'volumes': volumes, 'total_pvcs': len(pvcs.items)}
            
        except Exception as e:
            self.logger.error(f"Error analyzing storage: {e}")
            return {'volumes': []}
    
    def check_volume_health(self) -> Dict[str, Any]:
        """Check health of persistent volumes."""
        if not self.connected:
            return {'volumes': []}
        
        try:
            pvs = []
            try:
                pvs = self.v1.list_persistent_volume().items
            except ApiException as e:
                if e.status == 403:
                    self.logger.warning("Insufficient permissions to list persistent volumes for health check")
                    return {'volumes': []}
                else:
                    self.logger.error(f"Error listing persistent volumes for health check: {e}")
                    return {'volumes': []}
            
            volumes = []
            
            for pv in pvs:
                issues = []
                healthy = True
                
                if pv.status.phase != 'Bound':
                    issues.append(f"Volume not bound (status: {pv.status.phase})")
                    healthy = False
                
                if pv.spec.claim is None:
                    issues.append("No claim associated")
                    healthy = False
                
                volume_info = {
                    'name': pv.metadata.name,
                    'healthy': healthy,
                    'status': pv.status.phase,
                    'phase': pv.status.phase,
                    'issues': issues
                }
                volumes.append(volume_info)
            
            return {'volumes': volumes}
            
        except Exception as e:
            self.logger.error(f"Error checking volume health: {e}")
            return {'volumes': []}
    
    def generate_report(self) -> str:
        """Generate comprehensive cluster report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'cluster_metrics': self.get_cluster_metrics(),
            'issues': self.get_recent_issues(),
            'storage_analysis': self.analyze_storage_usage(),
            'volume_health': self.check_volume_health(),
            'node_count': len(self.get_nodes()),
            'deployment_count': len(self.get_deployments())
        }
        
        return json.dumps(report, indent=2)
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        issues = self.scan_for_issues()
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        warning_issues = [i for i in issues if i.get('severity') == 'warning']
        
        overall_status = 'healthy'
        if critical_issues:
            overall_status = 'critical'
        elif warning_issues:
            overall_status = 'warning'
        
        return {
            'overall_status': overall_status,
            'issues_count': len(issues),
            'critical_count': len(critical_issues),
            'warning_count': len(warning_issues),
            'timestamp': datetime.now().isoformat()
        }
    
    def _check_pod_issues(self, pod) -> List[Dict[str, Any]]:
        """Check for issues in a specific pod."""
        issues = []
        
        # Check pod status
        if pod.status.phase in ['Failed', 'Pending']:
            issues.append({
                'id': f"pod-{pod.metadata.namespace}-{pod.metadata.name}",
                'title': f"Pod {pod.metadata.name} in {pod.status.phase} state",
                'severity': 'critical' if pod.status.phase == 'Failed' else 'warning',
                'resource': f"Pod/{pod.metadata.name}",
                'namespace': pod.metadata.namespace,
                'description': f"Pod is in {pod.status.phase} phase",
                'timestamp': datetime.now().isoformat()
            })
        
        # Check container statuses
        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                if not container.ready:
                    issues.append({
                        'id': f"container-{pod.metadata.namespace}-{pod.metadata.name}-{container.name}",
                        'title': f"Container {container.name} not ready",
                        'severity': 'warning',
                        'resource': f"Pod/{pod.metadata.name}",
                        'namespace': pod.metadata.namespace,
                        'description': f"Container {container.name} is not ready",
                        'timestamp': datetime.now().isoformat()
                    })
                
                if container.restart_count > 5:
                    issues.append({
                        'id': f"restarts-{pod.metadata.namespace}-{pod.metadata.name}-{container.name}",
                        'title': f"High restart count for {container.name}",
                        'severity': 'warning',
                        'resource': f"Pod/{pod.metadata.name}",
                        'namespace': pod.metadata.namespace,
                        'description': f"Container has restarted {container.restart_count} times",
                        'timestamp': datetime.now().isoformat()
                    })
        
        return issues
    
    def _check_node_issues(self, node) -> List[Dict[str, Any]]:
        """Check for issues in a specific node."""
        issues = []
        
        # Check node conditions
        if node.status.conditions:
            for condition in node.status.conditions:
                if condition.type == 'Ready' and condition.status != 'True':
                    issues.append({
                        'id': f"node-{node.metadata.name}-notready",
                        'title': f"Node {node.metadata.name} not ready",
                        'severity': 'critical',
                        'resource': f"Node/{node.metadata.name}",
                        'namespace': 'cluster',
                        'description': f"Node is not ready: {condition.message}",
                        'timestamp': datetime.now().isoformat()
                    })
                
                elif condition.type in ['DiskPressure', 'MemoryPressure', 'PIDPressure'] and condition.status == 'True':
                    issues.append({
                        'id': f"node-{node.metadata.name}-{condition.type.lower()}",
                        'title': f"Node {node.metadata.name} has {condition.type}",
                        'severity': 'warning',
                        'resource': f"Node/{node.metadata.name}",
                        'namespace': 'cluster',
                        'description': f"Node experiencing {condition.type}: {condition.message}",
                        'timestamp': datetime.now().isoformat()
                    })
        
        return issues
    
    def _check_pv_issues(self, pv) -> List[Dict[str, Any]]:
        """Check for issues in persistent volumes."""
        issues = []
        
        if pv.status.phase == 'Failed':
            issues.append({
                'id': f"pv-{pv.metadata.name}-failed",
                'title': f"PersistentVolume {pv.metadata.name} failed",
                'severity': 'critical',
                'resource': f"PersistentVolume/{pv.metadata.name}",
                'namespace': 'cluster',
                'description': f"PersistentVolume is in Failed state",
                'timestamp': datetime.now().isoformat()
            })
        
        return issues
    
    def _monitor_logs(self):
        """Background thread to monitor pod logs."""
        while self.monitoring_active:
            try:
                pods = self.v1.list_pod_for_all_namespaces()
                for pod in pods.items[:5]:  # Monitor first 5 pods to avoid overwhelming
                    if pod.status.phase == 'Running':
                        try:
                            logs = self.v1.read_namespaced_pod_log(
                                name=pod.metadata.name,
                                namespace=pod.metadata.namespace,
                                tail_lines=1,
                                since_seconds=60
                            )
                            
                            if logs.strip():
                                log_entry = {
                                    'timestamp': datetime.now().isoformat(),
                                    'pod': f"{pod.metadata.namespace}/{pod.metadata.name}",
                                    'message': logs.strip()[-200:]  # Last 200 chars
                                }
                                
                                if not self.log_queue.full():
                                    self.log_queue.put(log_entry)
                                
                        except:
                            pass  # Skip pods we can't read logs from
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in log monitoring: {e}")
                time.sleep(30)
    
    def _parse_cpu(self, cpu_str: str) -> float:
        """Parse CPU string to float value."""
        if cpu_str.endswith('m'):
            return float(cpu_str[:-1]) / 1000
        return float(cpu_str)
    
    def _parse_memory(self, memory_str: str) -> float:
        """Parse memory string to bytes."""
        multipliers = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4}
        
        for suffix, multiplier in multipliers.items():
            if memory_str.endswith(suffix):
                return float(memory_str[:-2]) * multiplier
        
        return float(memory_str)
    
    def _parse_storage(self, storage_str: str) -> float:
        """Parse storage string to GB."""
        multipliers = {'Ki': 1024/1e9, 'Mi': 1024**2/1e9, 'Gi': 1024**3/1e9, 'Ti': 1024**4/1e9}
        
        for suffix, multiplier in multipliers.items():
            if storage_str.endswith(suffix):
                return float(storage_str[:-2]) * multiplier
        
        # Assume GB if no suffix
        return float(storage_str.rstrip('G'))
    
    def get_host_system_stats(self) -> Dict[str, Any]:
        """Get host system and GlusterFS statistics if available."""
        if self.host_monitor:
            try:
                return self.host_monitor.collect_all_stats()
            except Exception as e:
                self.logger.error(f"Error collecting host system stats: {e}")
                return {}
        else:
            self.logger.debug("Host system monitoring not available")
            return {}
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics including Kubernetes and host system data."""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'kubernetes': {
                'cluster_info': self.get_cluster_info(),
                'node_metrics': self.get_node_metrics(),
                'pod_metrics': self.get_pod_metrics(),
                'persistent_volumes': self.get_persistent_volume_info()
            }
        }
        
        # Add host system stats if available
        host_stats = self.get_host_system_stats()
        if host_stats:
            stats['host_system'] = host_stats
        
        return stats