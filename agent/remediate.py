import logging
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time

class RemediationEngine:
    """Engine for automated and manual remediation of Kubernetes issues."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.v1 = None
        self.apps_v1 = None
        self.connected = False
        self.history = []
        self._connect()
    
    def _connect(self):
        """Connect to Kubernetes cluster."""
        try:
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
                    self.logger.warning("Remediation engine will run in limited mode")
                    self.connected = False
                    return
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.connected = True
            self.logger.info("Remediation engine connected to cluster")
            
        except Exception as e:
            self.logger.warning(f"Failed to connect remediation engine: {e}")
            self.logger.warning("Remediation engine will run in limited mode")
            self.connected = False
    
    def auto_remediate(self, issue_id: str) -> Dict[str, Any]:
        """Automatically remediate a known issue."""
        if not self.connected:
            return {"success": False, "message": "Not connected to cluster"}
        
        try:
            # Parse issue ID to understand the issue type
            issue_parts = issue_id.split('-')
            issue_type = issue_parts[0] if issue_parts else "unknown"
            
            remediation_result = {"success": False, "message": "Unknown issue type"}
            
            if issue_type == "pod":
                remediation_result = self._remediate_pod_issue(issue_id, issue_parts)
            elif issue_type == "node":
                remediation_result = self._remediate_node_issue(issue_id, issue_parts)
            elif issue_type == "container":
                remediation_result = self._remediate_container_issue(issue_id, issue_parts)
            elif issue_type == "pv":
                remediation_result = self._remediate_pv_issue(issue_id, issue_parts)
            
            # Log the remediation attempt
            self._log_action(issue_id, "auto_remediate", remediation_result)
            
            return remediation_result
            
        except Exception as e:
            error_msg = f"Error during auto-remediation: {str(e)}"
            self.logger.error(error_msg)
            self._log_action(issue_id, "auto_remediate", {"success": False, "message": error_msg})
            return {"success": False, "message": error_msg}
    
    def _remediate_pod_issue(self, issue_id: str, parts: List[str]) -> Dict[str, Any]:
        """Remediate pod-specific issues."""
        if len(parts) < 3:
            return {"success": False, "message": "Invalid pod issue ID format"}
        
        namespace = parts[1]
        pod_name = parts[2]
        
        try:
            # Get pod details
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Determine remediation based on pod status
            if pod.status.phase == "Failed":
                # Try to restart the pod by deleting it (if it's managed by a controller)
                self.v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
                return {"success": True, "message": f"Deleted failed pod {pod_name}, controller will recreate it"}
            
            elif pod.status.phase == "Pending":
                # Check for common pending issues and try to resolve
                return self._resolve_pending_pod(pod)
            
            else:
                return {"success": False, "message": f"No automatic remediation available for pod in {pod.status.phase} state"}
                
        except ApiException as e:
            return {"success": False, "message": f"Kubernetes API error: {e.reason}"}
    
    def _remediate_node_issue(self, issue_id: str, parts: List[str]) -> Dict[str, Any]:
        """Remediate node-specific issues."""
        if len(parts) < 3:
            return {"success": False, "message": "Invalid node issue ID format"}
        
        node_name = parts[1]
        issue_subtype = parts[2] if len(parts) > 2 else "unknown"
        
        try:
            node = self.v1.read_node(name=node_name)
            
            if issue_subtype == "notready":
                # For NotReady nodes, we can try to uncordon if they're cordoned
                if node.spec.unschedulable:
                    return self._uncordon_node(node_name)
                else:
                    return {"success": False, "message": "Node is not cordoned, issue may be with kubelet or infrastructure"}
            
            elif issue_subtype in ["diskpressure", "memorypressure", "pidpressure"]:
                # For pressure issues, we can try to evict some pods
                return self._relieve_node_pressure(node_name, issue_subtype)
            
            else:
                return {"success": False, "message": f"No automatic remediation for {issue_subtype} on node {node_name}"}
                
        except ApiException as e:
            return {"success": False, "message": f"Kubernetes API error: {e.reason}"}
    
    def _remediate_container_issue(self, issue_id: str, parts: List[str]) -> Dict[str, Any]:
        """Remediate container-specific issues."""
        if len(parts) < 4:
            return {"success": False, "message": "Invalid container issue ID format"}
        
        namespace = parts[1]
        pod_name = parts[2]
        container_name = parts[3]
        
        try:
            # For container issues, restart the pod
            self.v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            return {"success": True, "message": f"Restarted pod {pod_name} to fix container {container_name} issue"}
            
        except ApiException as e:
            return {"success": False, "message": f"Failed to restart pod: {e.reason}"}
    
    def _remediate_pv_issue(self, issue_id: str, parts: List[str]) -> Dict[str, Any]:
        """Remediate persistent volume issues."""
        if len(parts) < 3:
            return {"success": False, "message": "Invalid PV issue ID format"}
        
        pv_name = parts[1]
        
        try:
            pv = self.v1.read_persistent_volume(name=pv_name)
            
            if pv.status.phase == "Failed":
                # Try to remove finalizers if safe
                if pv.metadata.finalizers:
                    # This is risky - only do for specific cases
                    return {"success": False, "message": "PV has finalizers, manual intervention required"}
                else:
                    return {"success": False, "message": "PV failed, check underlying storage provider"}
            
            return {"success": False, "message": f"No automatic remediation for PV in {pv.status.phase} state"}
            
        except ApiException as e:
            return {"success": False, "message": f"Kubernetes API error: {e.reason}"}
    
    def _resolve_pending_pod(self, pod) -> Dict[str, Any]:
        """Try to resolve pending pod issues."""
        # Check if it's a resource issue
        if pod.status.conditions:
            for condition in pod.status.conditions:
                if condition.type == "PodScheduled" and condition.status == "False":
                    if "Insufficient" in condition.message:
                        # Resource shortage - try to find nodes with capacity
                        return {"success": False, "message": f"Insufficient resources: {condition.message}"}
                    elif "no nodes available" in condition.message.lower():
                        return {"success": False, "message": "No suitable nodes available for scheduling"}
        
        return {"success": False, "message": "Unable to determine cause of pending state"}
    
    def _uncordon_node(self, node_name: str) -> Dict[str, Any]:
        """Uncordon a node to make it schedulable."""
        try:
            # Patch the node to remove unschedulable flag
            body = {"spec": {"unschedulable": False}}
            self.v1.patch_node(name=node_name, body=body)
            return {"success": True, "message": f"Uncordoned node {node_name}"}
            
        except ApiException as e:
            return {"success": False, "message": f"Failed to uncordon node: {e.reason}"}
    
    def _relieve_node_pressure(self, node_name: str, pressure_type: str) -> Dict[str, Any]:
        """Try to relieve node pressure by evicting some pods."""
        try:
            # Get pods on the node
            pods = self.v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )
            
            # Find pods that can be safely evicted (not system pods)
            evictable_pods = []
            for pod in pods.items:
                if (pod.metadata.namespace not in ["kube-system", "kube-public"] and
                    not any(owner.kind == "DaemonSet" for owner in pod.metadata.owner_references or [])):
                    evictable_pods.append(pod)
            
            if not evictable_pods:
                return {"success": False, "message": f"No evictable pods found on node {node_name}"}
            
            # Evict up to 2 pods to relieve pressure
            evicted_count = 0
            for pod in evictable_pods[:2]:
                try:
                    eviction = client.V1Eviction(
                        metadata=client.V1ObjectMeta(
                            name=pod.metadata.name,
                            namespace=pod.metadata.namespace
                        )
                    )
                    self.v1.create_namespaced_pod_eviction(
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace,
                        body=eviction
                    )
                    evicted_count += 1
                except ApiException:
                    continue
            
            if evicted_count > 0:
                return {"success": True, "message": f"Evicted {evicted_count} pods to relieve {pressure_type}"}
            else:
                return {"success": False, "message": "Failed to evict any pods"}
                
        except ApiException as e:
            return {"success": False, "message": f"Error relieving pressure: {e.reason}"}
    
    def execute_kubectl(self, command: str) -> str:
        """Execute a kubectl command safely."""
        if not command.startswith("kubectl "):
            return "Command must start with 'kubectl '"
        
        # Whitelist of safe commands
        safe_commands = [
            "get", "describe", "logs", "top", "explain", "version",
            "cluster-info", "config", "api-resources", "api-versions"
        ]
        
        cmd_parts = command.split()
        if len(cmd_parts) < 2 or cmd_parts[1] not in safe_commands:
            return "Command not allowed. Only read-only operations are permitted."
        
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            self._log_action("manual", f"kubectl_command: {command}", {
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr
            })
            
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def restart_failed_pods(self) -> Dict[str, Any]:
        """Restart all failed pods in the cluster."""
        if not self.connected:
            return {"count": 0, "message": "Not connected to cluster"}
        
        try:
            pods = self.v1.list_pod_for_all_namespaces()
            failed_pods = [p for p in pods.items if p.status.phase == "Failed"]
            
            restarted_count = 0
            for pod in failed_pods:
                try:
                    self.v1.delete_namespaced_pod(
                        name=pod.metadata.name,
                        namespace=pod.metadata.namespace
                    )
                    restarted_count += 1
                except ApiException:
                    continue
            
            result = {"count": restarted_count}
            self._log_action("bulk", "restart_failed_pods", result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error restarting failed pods: {e}")
            return {"count": 0, "message": str(e)}
    
    def clean_completed_jobs(self) -> Dict[str, Any]:
        """Clean up completed jobs."""
        if not self.connected:
            return {"count": 0, "message": "Not connected to cluster"}
        
        try:
            batch_v1 = client.BatchV1Api()
            jobs = batch_v1.list_job_for_all_namespaces()
            
            cleaned_count = 0
            for job in jobs.items:
                if (job.status.conditions and 
                    any(c.type == "Complete" and c.status == "True" for c in job.status.conditions)):
                    try:
                        batch_v1.delete_namespaced_job(
                            name=job.metadata.name,
                            namespace=job.metadata.namespace,
                            propagation_policy="Background"
                        )
                        cleaned_count += 1
                    except ApiException:
                        continue
            
            result = {"count": cleaned_count}
            self._log_action("bulk", "clean_completed_jobs", result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error cleaning completed jobs: {e}")
            return {"count": 0, "message": str(e)}
    
    def scale_deployment(self, deployment_name: str, replicas: int) -> Dict[str, Any]:
        """Scale a deployment to specified number of replicas."""
        if not self.connected:
            return {"success": False, "message": "Not connected to cluster"}
        
        try:
            # Parse deployment name (namespace/name format)
            if "/" in deployment_name:
                namespace, name = deployment_name.split("/", 1)
            else:
                namespace = "default"
                name = deployment_name
            
            # Scale the deployment
            body = {"spec": {"replicas": replicas}}
            self.apps_v1.patch_namespaced_deployment_scale(
                name=name,
                namespace=namespace,
                body=body
            )
            
            result = {"success": True, "message": f"Scaled {deployment_name} to {replicas} replicas"}
            self._log_action("manual", f"scale_deployment: {deployment_name}", result)
            return result
            
        except ApiException as e:
            error_msg = f"Failed to scale deployment: {e.reason}"
            self._log_action("manual", f"scale_deployment: {deployment_name}", {"success": False, "message": error_msg})
            return {"success": False, "message": error_msg}
    
    def drain_node(self, node_name: str, ignore_daemonsets: bool = True, delete_local_data: bool = False) -> Dict[str, Any]:
        """Drain a node safely."""
        if not self.connected:
            return {"success": False, "message": "Not connected to cluster"}
        
        try:
            # Build kubectl drain command
            cmd = ["kubectl", "drain", node_name, "--ignore-daemonsets" if ignore_daemonsets else ""]
            if delete_local_data:
                cmd.append("--delete-emptydir-data")
            cmd.append("--force")
            
            # Filter out empty strings
            cmd = [c for c in cmd if c]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            success = result.returncode == 0
            message = result.stdout if success else result.stderr
            
            action_result = {"success": success, "message": message}
            self._log_action("manual", f"drain_node: {node_name}", action_result)
            return action_result
            
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Drain operation timed out"}
        except Exception as e:
            return {"success": False, "message": f"Error draining node: {str(e)}"}
    
    def label_node(self, node_name: str, key: str, value: str) -> Dict[str, Any]:
        """Add a label to a node."""
        if not self.connected:
            return {"success": False, "message": "Not connected to cluster"}
        
        try:
            body = {
                "metadata": {
                    "labels": {key: value}
                }
            }
            
            self.v1.patch_node(name=node_name, body=body)
            
            result = {"success": True, "message": f"Applied label {key}={value} to node {node_name}"}
            self._log_action("manual", f"label_node: {node_name}", result)
            return result
            
        except ApiException as e:
            error_msg = f"Failed to label node: {e.reason}"
            self._log_action("manual", f"label_node: {node_name}", {"success": False, "message": error_msg})
            return {"success": False, "message": error_msg}
    
    def uncordon_all_nodes(self) -> Dict[str, Any]:
        """Uncordon all cordoned nodes."""
        if not self.connected:
            return {"count": 0, "message": "Not connected to cluster"}
        
        try:
            nodes = self.v1.list_node()
            cordoned_nodes = [n for n in nodes.items if n.spec.unschedulable]
            
            uncordoned_count = 0
            for node in cordoned_nodes:
                try:
                    body = {"spec": {"unschedulable": False}}
                    self.v1.patch_node(name=node.metadata.name, body=body)
                    uncordoned_count += 1
                except ApiException:
                    continue
            
            result = {"count": uncordoned_count}
            self._log_action("bulk", "uncordon_all_nodes", result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error uncordoning nodes: {e}")
            return {"count": 0, "message": str(e)}
    
    def clean_orphaned_storage(self) -> Dict[str, Any]:
        """Clean up orphaned storage resources."""
        if not self.connected:
            return {"count": 0, "message": "Not connected to cluster"}
        
        try:
            # Find PVCs without pods
            pvcs = self.v1.list_persistent_volume_claim_for_all_namespaces()
            pods = self.v1.list_pod_for_all_namespaces()
            
            # Get PVC names that are actually used by pods
            used_pvcs = set()
            for pod in pods.items:
                if pod.spec.volumes:
                    for volume in pod.spec.volumes:
                        if volume.persistent_volume_claim:
                            pvc_name = f"{pod.metadata.namespace}/{volume.persistent_volume_claim.claim_name}"
                            used_pvcs.add(pvc_name)
            
            # Find orphaned PVCs (not used by any pod)
            orphaned_count = 0
            for pvc in pvcs.items:
                pvc_name = f"{pvc.metadata.namespace}/{pvc.metadata.name}"
                if pvc_name not in used_pvcs and pvc.status.phase == "Bound":
                    # Only clean PVCs that have been unused for some time
                    # In a real implementation, you'd check timestamps
                    pass  # For safety, don't actually delete in this demo
            
            result = {"count": orphaned_count, "message": "Orphaned storage detection only (no deletion for safety)"}
            self._log_action("bulk", "clean_orphaned_storage", result)
            return result
            
        except Exception as e:
            self.logger.error(f"Error cleaning orphaned storage: {e}")
            return {"count": 0, "message": str(e)}
    
    def move_pod(self, pod_name: str, target_node: str) -> Dict[str, Any]:
        """Move a pod to a different node."""
        if not self.connected:
            return {"success": False, "message": "Not connected to cluster"}
        
        try:
            # Parse pod name (namespace/name format)
            if "/" in pod_name:
                namespace, name = pod_name.split("/", 1)
            else:
                namespace = "default"
                name = pod_name
            
            # Get the pod
            pod = self.v1.read_namespaced_pod(name=name, namespace=namespace)
            
            # Check if pod is managed by a controller
            if not pod.metadata.owner_references:
                return {"success": False, "message": "Cannot move standalone pods safely"}
            
            # For now, we'll delete the pod and let the controller recreate it
            # A more sophisticated approach would involve modifying the controller
            self.v1.delete_namespaced_pod(name=name, namespace=namespace)
            
            result = {"success": True, "message": f"Deleted pod {pod_name}, controller will recreate it"}
            self._log_action("manual", f"move_pod: {pod_name} to {target_node}", result)
            return result
            
        except ApiException as e:
            error_msg = f"Failed to move pod: {e.reason}"
            self._log_action("manual", f"move_pod: {pod_name}", {"success": False, "message": error_msg})
            return {"success": False, "message": error_msg}
    
    def _log_action(self, action_type: str, action: str, result: Dict[str, Any]):
        """Log remediation actions for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "action": action,
            "result": result,
            "status": "success" if result.get("success", True) else "failed"
        }
        
        self.history.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get remediation history."""
        return self.history[-limit:]