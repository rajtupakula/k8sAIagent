"""
Expert Remediation Agent for Ubuntu OS, Kubernetes, and GlusterFS Issues

This agent acts as an expert system engineer/developer capable of:
1. Detecting and diagnosing complex system issues
2. Providing expert-level remediation strategies
3. Working within existing system constraints (no external binaries)
4. Automated issue resolution with safety checks
5. Continuous learning from issue history and log patterns
6. Root cause prediction based on historical analysis
"""

import os
import re
import json
import subprocess
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Import the Issue History Manager for continuous learning
try:
    from .issue_history_manager import IssueHistoryManager
except ImportError:
    try:
        from issue_history_manager import IssueHistoryManager
    except ImportError:
        IssueHistoryManager = None
        print("Warning: Issue History Manager not available - running without continuous learning")

class ExpertRemediationAgent:
    """Expert-level remediation agent for comprehensive system troubleshooting."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.expertise_areas = ["ubuntu_os", "kubernetes", "glusterfs"]
        self.remediation_history = []
        self.safety_mode = True
        
        # Initialize Issue History Manager for continuous learning
        self.history_manager = None
        if IssueHistoryManager:
            try:
                self.history_manager = IssueHistoryManager()
                print("✅ Issue History Manager initialized - continuous learning enabled")
            except Exception as e:
                print(f"⚠️ Could not initialize Issue History Manager: {e}")
        
        # Expert knowledge base for issue patterns and solutions
        self.expert_knowledge = self._load_expert_knowledge()
        
        # System analysis tools (using only built-in commands)
        self.system_tools = {
            "ubuntu": ["systemctl", "journalctl", "ps", "top", "df", "free", "lsof", "netstat", "ss", "dmesg"],
            "kubernetes": ["kubectl", "crictl", "docker"],
            "glusterfs": ["gluster", "mount", "umount", "findmnt"]
        }
    
    def _load_expert_knowledge(self) -> Dict[str, Any]:
        """Load comprehensive expert knowledge base."""
        return {
            "ubuntu_os": {
                "patterns": {
                    "disk_full": {
                        "symptoms": ["No space left on device", "disk.*full", "filesystem.*full"],
                        "commands": ["df -h", "du -sh /*", "find /var/log -type f -size +100M"],
                        "remediation": [
                            "Clean log files: journalctl --vacuum-time=7d",
                            "Remove old kernels: apt autoremove --purge",
                            "Clear apt cache: apt clean",
                            "Find large files: find / -type f -size +1G 2>/dev/null",
                            "Clean Docker if present: docker system prune -f"
                        ],
                        "severity": "high"
                    },
                    "memory_pressure": {
                        "symptoms": ["Out of memory", "OOM", "memory.*pressure", "killed.*process"],
                        "commands": ["free -h", "ps aux --sort=-%mem", "dmesg | grep -i 'killed process'"],
                        "remediation": [
                            "Identify memory hogs: ps aux --sort=-%mem | head -20",
                            "Check swap usage: swapon --show",
                            "Enable swap if needed: swapon -a",
                            "Kill problematic processes if safe",
                            "Restart services consuming excessive memory"
                        ],
                        "severity": "critical"
                    },
                    "service_failures": {
                        "symptoms": ["failed.*start", "service.*failed", "unit.*failed"],
                        "commands": ["systemctl --failed", "journalctl -xe", "systemctl status"],
                        "remediation": [
                            "Check failed services: systemctl --failed",
                            "Restart failed services: systemctl restart <service>",
                            "Check logs: journalctl -u <service> --since today",
                            "Reset failed state: systemctl reset-failed",
                            "Reload systemd: systemctl daemon-reload"
                        ],
                        "severity": "medium"
                    },
                    "network_issues": {
                        "symptoms": ["network.*unreachable", "connection.*refused", "timeout"],
                        "commands": ["ip addr", "ip route", "ss -tuln", "ping -c 3", "nslookup"],
                        "remediation": [
                            "Check interfaces: ip addr show",
                            "Check routing: ip route show",
                            "Restart networking: systemctl restart networking",
                            "Check DNS: cat /etc/resolv.conf",
                            "Test connectivity: ping 8.8.8.8"
                        ],
                        "severity": "high"
                    },
                    "cpu_issues": {
                        "symptoms": ["high.*load", "cpu.*usage", "load.*average"],
                        "commands": ["top", "htop", "ps aux --sort=-%cpu", "vmstat"],
                        "remediation": [
                            "Find CPU hogs: ps aux --sort=-%cpu | head -20",
                            "Check load average: uptime",
                            "Analyze processes: top -p $(pgrep -d, process_name)",
                            "Kill runaway processes if safe",
                            "Check for infinite loops or stuck processes"
                        ],
                        "severity": "medium"
                    }
                }
            },
            "kubernetes": {
                "patterns": {
                    "pod_crashloop": {
                        "symptoms": ["CrashLoopBackOff", "crash.*loop", "restarting.*continuously"],
                        "commands": ["kubectl get pods", "kubectl describe pod", "kubectl logs"],
                        "remediation": [
                            "Check pod logs: kubectl logs <pod> --previous",
                            "Describe pod: kubectl describe pod <pod>",
                            "Check resource limits: kubectl get pod <pod> -o yaml | grep -A10 resources",
                            "Verify image exists: kubectl describe pod <pod> | grep -i image",
                            "Check liveness/readiness probes",
                            "Scale down and up: kubectl scale deployment <name> --replicas=0 && kubectl scale deployment <name> --replicas=1"
                        ],
                        "severity": "high"
                    },
                    "pod_pending": {
                        "symptoms": ["Pending", "pod.*pending", "not.*scheduled"],
                        "commands": ["kubectl describe pod", "kubectl get nodes", "kubectl top nodes"],
                        "remediation": [
                            "Check node resources: kubectl top nodes",
                            "Describe pod for events: kubectl describe pod <pod>",
                            "Check node selectors: kubectl get pod <pod> -o yaml | grep nodeSelector",
                            "Verify taints/tolerations: kubectl describe nodes",
                            "Check PVC status: kubectl get pvc",
                            "Ensure nodes are ready: kubectl get nodes"
                        ],
                        "severity": "medium"
                    },
                    "node_notready": {
                        "symptoms": ["NotReady", "node.*not.*ready", "kubelet.*stopped"],
                        "commands": ["kubectl get nodes", "kubectl describe node", "systemctl status kubelet"],
                        "remediation": [
                            "Check kubelet status: systemctl status kubelet",
                            "Restart kubelet: systemctl restart kubelet",
                            "Check kubelet logs: journalctl -u kubelet --since '1 hour ago'",
                            "Verify node resources: df -h && free -h",
                            "Check container runtime: systemctl status docker || systemctl status containerd",
                            "Uncordon if needed: kubectl uncordon <node>"
                        ],
                        "severity": "critical"
                    },
                    "service_unavailable": {
                        "symptoms": ["service.*unavailable", "endpoint.*not.*found", "connection.*refused"],
                        "commands": ["kubectl get svc", "kubectl get endpoints", "kubectl describe svc"],
                        "remediation": [
                            "Check service endpoints: kubectl get endpoints <service>",
                            "Verify pod labels match service selector",
                            "Check if pods are ready: kubectl get pods -l <selector>",
                            "Test service connectivity: kubectl run test-pod --image=busybox -it --rm",
                            "Verify network policies: kubectl get networkpolicy",
                            "Check ingress controller if using ingress"
                        ],
                        "severity": "high"
                    },
                    "volume_issues": {
                        "symptoms": ["volume.*mount.*failed", "pv.*not.*available", "pvc.*pending"],
                        "commands": ["kubectl get pv", "kubectl get pvc", "kubectl describe pvc"],
                        "remediation": [
                            "Check PVC status: kubectl get pvc",
                            "Describe PVC for events: kubectl describe pvc <pvc>",
                            "Verify storage class: kubectl get storageclass",
                            "Check PV availability: kubectl get pv",
                            "Ensure storage backend is healthy",
                            "Check node disk space: kubectl top nodes"
                        ],
                        "severity": "medium"
                    }
                }
            },
            "glusterfs": {
                "patterns": {
                    "volume_offline": {
                        "symptoms": ["volume.*offline", "brick.*down", "peer.*disconnected"],
                        "commands": ["gluster volume status", "gluster peer status", "gluster volume info"],
                        "remediation": [
                            "Check volume status: gluster volume status <volume>",
                            "Start volume if stopped: gluster volume start <volume>",
                            "Check peer connectivity: gluster peer status",
                            "Restart glusterd: systemctl restart glusterd",
                            "Check brick processes: ps aux | grep gluster",
                            "Verify mount points: findmnt -t fuse.glusterfs"
                        ],
                        "severity": "critical"
                    },
                    "split_brain": {
                        "symptoms": ["split.*brain", "conflicting.*data", "heal.*pending"],
                        "commands": ["gluster volume heal", "gluster volume status", "find /mnt -name '*.gfid'"],
                        "remediation": [
                            "Check heal status: gluster volume heal <volume> info",
                            "List split-brain files: gluster volume heal <volume> info split-brain",
                            "Heal volume: gluster volume heal <volume>",
                            "Force heal if needed: gluster volume heal <volume> full",
                            "Resolve split-brain manually for critical files",
                            "Monitor heal progress: watch 'gluster volume heal <volume> info'"
                        ],
                        "severity": "high"
                    },
                    "quota_exceeded": {
                        "symptoms": ["quota.*exceeded", "disk.*quota", "no.*space.*quota"],
                        "commands": ["gluster volume quota", "df -h", "du -sh"],
                        "remediation": [
                            "Check quota status: gluster volume quota <volume> list",
                            "Increase quota: gluster volume quota <volume> limit-usage / <size>",
                            "Remove unnecessary files from volume",
                            "Check actual disk usage: du -sh /mnt/<volume>/*",
                            "Disable quota temporarily if needed: gluster volume quota <volume> disable"
                        ],
                        "severity": "medium"
                    },
                    "brick_failures": {
                        "symptoms": ["brick.*failed", "brick.*offline", "brick.*disconnected"],
                        "commands": ["gluster volume status", "df -h", "mount | grep gluster"],
                        "remediation": [
                            "Check brick status: gluster volume status <volume>",
                            "Verify brick mount points: df -h | grep brick",
                            "Check disk space on brick: df -h <brick_path>",
                            "Restart brick: gluster volume stop <volume> && gluster volume start <volume>",
                            "Replace brick if hardware failure: gluster volume replace-brick",
                            "Check filesystem errors: dmesg | grep -i error"
                        ],
                        "severity": "high"
                    }
                }
            }
        }
    
    def analyze_system_comprehensive(self) -> Dict[str, Any]:
        """Perform comprehensive system analysis with historical learning and root cause prediction."""
        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "system_metrics": {},
            "detailed_analysis": {},
            "historical_insights": {},
            "predictive_analysis": {}
        }
        
        try:
            # Perform continuous learning scan if history manager is available
            if self.history_manager:
                try:
                    learning_scan = self.history_manager.continuous_learning_scan()
                    analysis_results["learning_scan"] = {
                        "issues_detected": learning_scan["issues_detected"],
                        "total_historical": learning_scan["total_historical_issues"],
                        "scan_timestamp": learning_scan["scan_timestamp"]
                    }
                    
                    # Get trend analysis
                    trends = self.history_manager.get_issue_trend_analysis()
                    analysis_results["historical_insights"] = trends
                    
                except Exception as e:
                    print(f"Warning: Learning scan failed: {e}")
            
            # Analyze each system component
            for area in self.expertise_areas:
                area_analysis = self._analyze_area(area)
                analysis_results["detailed_analysis"][area] = area_analysis
                
                # Aggregate issues
                analysis_results["critical_issues"].extend(area_analysis.get("critical_issues", []))
                analysis_results["warnings"].extend(area_analysis.get("warnings", []))
                analysis_results["recommendations"].extend(area_analysis.get("recommendations", []))
                
                # Add historical predictions for detected issues
                if self.history_manager and area_analysis.get("critical_issues"):
                    for issue in area_analysis["critical_issues"]:
                        prediction = self.history_manager.get_predictive_analysis(issue)
                        if prediction["confidence"] > 0.0:
                            if area not in analysis_results["predictive_analysis"]:
                                analysis_results["predictive_analysis"][area] = []
                            analysis_results["predictive_analysis"][area].append({
                                "issue": issue,
                                "prediction": prediction
                            })
            
            # Determine overall health
            critical_count = len(analysis_results["critical_issues"])
            warning_count = len(analysis_results["warnings"])
            
            if critical_count > 0:
                analysis_results["overall_health"] = "critical"
            elif warning_count > 3:
                analysis_results["overall_health"] = "degraded"
            elif warning_count > 0:
                analysis_results["overall_health"] = "warning"
            else:
                analysis_results["overall_health"] = "healthy"
            
            # Prioritize recommendations based on historical success rates
            if self.history_manager:
                analysis_results["recommendations"] = self._prioritize_recommendations_with_history(
                    analysis_results["recommendations"]
                )
            analysis_results["recommendations"] = self._prioritize_recommendations(
                analysis_results["recommendations"]
            )
            
        except Exception as e:
            self.logger.error(f"Error during comprehensive analysis: {e}")
            analysis_results["overall_health"] = "error"
            analysis_results["critical_issues"].append(f"Analysis failed: {e}")
        
        return analysis_results
    
    def _analyze_area(self, area: str) -> Dict[str, Any]:
        """Analyze specific system area."""
        area_result = {
            "status": "unknown",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "metrics": {}
        }
        
        try:
            if area == "ubuntu_os":
                area_result = self._analyze_ubuntu_os()
            elif area == "kubernetes":
                area_result = self._analyze_kubernetes()
            elif area == "glusterfs":
                area_result = self._analyze_glusterfs()
        
        except Exception as e:
            self.logger.error(f"Error analyzing {area}: {e}")
            area_result["status"] = "error"
            area_result["critical_issues"].append(f"Analysis failed: {e}")
        
        return area_result
    
    def _analyze_ubuntu_os(self) -> Dict[str, Any]:
        """Expert-level Ubuntu OS analysis."""
        result = {
            "status": "healthy",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "metrics": {}
        }
        
        try:
            # System resource analysis
            resource_metrics = self._get_system_resources()
            result["metrics"]["resources"] = resource_metrics
            
            # Disk space check
            if resource_metrics.get("disk_usage_percent", 0) > 90:
                result["critical_issues"].append("Disk space critically low")
                result["recommendations"].extend(self.expert_knowledge["ubuntu_os"]["patterns"]["disk_full"]["remediation"])
            elif resource_metrics.get("disk_usage_percent", 0) > 80:
                result["warnings"].append("Disk space getting low")
            
            # Memory analysis
            if resource_metrics.get("memory_usage_percent", 0) > 95:
                result["critical_issues"].append("Memory critically low")
                result["recommendations"].extend(self.expert_knowledge["ubuntu_os"]["patterns"]["memory_pressure"]["remediation"])
            elif resource_metrics.get("memory_usage_percent", 0) > 85:
                result["warnings"].append("High memory usage")
            
            # Service health check
            failed_services = self._check_failed_services()
            if failed_services:
                if len(failed_services) > 5:
                    result["critical_issues"].append(f"Multiple services failed: {', '.join(failed_services[:5])}")
                else:
                    result["warnings"].append(f"Failed services: {', '.join(failed_services)}")
                result["recommendations"].extend(self.expert_knowledge["ubuntu_os"]["patterns"]["service_failures"]["remediation"])
            
            # System load analysis
            load_avg = self._get_load_average()
            cpu_count = resource_metrics.get("cpu_count", 1)
            if load_avg > cpu_count * 2:
                result["critical_issues"].append(f"Very high system load: {load_avg}")
                result["recommendations"].extend(self.expert_knowledge["ubuntu_os"]["patterns"]["cpu_issues"]["remediation"])
            elif load_avg > cpu_count * 1.5:
                result["warnings"].append(f"High system load: {load_avg}")
            
            # Network connectivity check
            network_issues = self._check_network_connectivity()
            if network_issues:
                result["critical_issues"].extend(network_issues)
                result["recommendations"].extend(self.expert_knowledge["ubuntu_os"]["patterns"]["network_issues"]["remediation"])
            
            # Determine overall status
            if result["critical_issues"]:
                result["status"] = "critical"
            elif len(result["warnings"]) > 3:
                result["status"] = "degraded"
            elif result["warnings"]:
                result["status"] = "warning"
            else:
                result["status"] = "healthy"
                
        except Exception as e:
            result["status"] = "error"
            result["critical_issues"].append(f"Ubuntu analysis failed: {e}")
        
        return result
    
    def _analyze_kubernetes(self) -> Dict[str, Any]:
        """Expert-level Kubernetes analysis."""
        result = {
            "status": "healthy",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "metrics": {}
        }
        
        try:
            # Check if kubectl is available
            if not self._command_exists("kubectl"):
                result["status"] = "unavailable"
                result["warnings"].append("kubectl not available")
                return result
            
            # Node health check
            node_issues = self._check_node_health()
            if node_issues["critical"]:
                result["critical_issues"].extend(node_issues["critical"])
                result["recommendations"].extend(self.expert_knowledge["kubernetes"]["patterns"]["node_notready"]["remediation"])
            if node_issues["warnings"]:
                result["warnings"].extend(node_issues["warnings"])
            
            # Pod health analysis
            pod_issues = self._check_pod_health()
            result["metrics"]["pods"] = pod_issues["metrics"]
            
            if pod_issues["crashloop_pods"]:
                result["critical_issues"].append(f"Pods in CrashLoopBackOff: {', '.join(pod_issues['crashloop_pods'][:5])}")
                result["recommendations"].extend(self.expert_knowledge["kubernetes"]["patterns"]["pod_crashloop"]["remediation"])
            
            if pod_issues["pending_pods"]:
                result["warnings"].append(f"Pending pods: {', '.join(pod_issues['pending_pods'][:5])}")
                result["recommendations"].extend(self.expert_knowledge["kubernetes"]["patterns"]["pod_pending"]["remediation"])
            
            # Service connectivity check
            service_issues = self._check_service_health()
            if service_issues:
                result["warnings"].extend(service_issues)
                result["recommendations"].extend(self.expert_knowledge["kubernetes"]["patterns"]["service_unavailable"]["remediation"])
            
            # Volume health check
            volume_issues = self._check_volume_health()
            if volume_issues:
                result["warnings"].extend(volume_issues)
                result["recommendations"].extend(self.expert_knowledge["kubernetes"]["patterns"]["volume_issues"]["remediation"])
            
            # Determine overall status
            if result["critical_issues"]:
                result["status"] = "critical"
            elif len(result["warnings"]) > 3:
                result["status"] = "degraded"
            elif result["warnings"]:
                result["status"] = "warning"
            else:
                result["status"] = "healthy"
                
        except Exception as e:
            result["status"] = "error"
            result["critical_issues"].append(f"Kubernetes analysis failed: {e}")
        
        return result
    
    def _analyze_glusterfs(self) -> Dict[str, Any]:
        """Expert-level GlusterFS analysis."""
        result = {
            "status": "healthy",
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "metrics": {}
        }
        
        try:
            # Check if gluster is available
            if not self._command_exists("gluster"):
                result["status"] = "unavailable"
                result["warnings"].append("GlusterFS not available")
                return result
            
            # Volume status check
            volume_issues = self._check_gluster_volumes()
            if volume_issues["offline_volumes"]:
                result["critical_issues"].append(f"Offline volumes: {', '.join(volume_issues['offline_volumes'])}")
                result["recommendations"].extend(self.expert_knowledge["glusterfs"]["patterns"]["volume_offline"]["remediation"])
            
            if volume_issues["degraded_volumes"]:
                result["warnings"].append(f"Degraded volumes: {', '.join(volume_issues['degraded_volumes'])}")
            
            # Heal status check
            heal_issues = self._check_gluster_heal()
            if heal_issues["split_brain_files"] > 0:
                result["critical_issues"].append(f"Split-brain files detected: {heal_issues['split_brain_files']}")
                result["recommendations"].extend(self.expert_knowledge["glusterfs"]["patterns"]["split_brain"]["remediation"])
            
            if heal_issues["heal_pending"] > 100:
                result["warnings"].append(f"Many files pending heal: {heal_issues['heal_pending']}")
            
            # Peer connectivity check
            peer_issues = self._check_gluster_peers()
            if peer_issues["disconnected_peers"]:
                result["critical_issues"].append(f"Disconnected peers: {', '.join(peer_issues['disconnected_peers'])}")
            
            # Brick health check
            brick_issues = self._check_gluster_bricks()
            if brick_issues["failed_bricks"]:
                result["critical_issues"].append(f"Failed bricks: {', '.join(brick_issues['failed_bricks'][:3])}")
                result["recommendations"].extend(self.expert_knowledge["glusterfs"]["patterns"]["brick_failures"]["remediation"])
            
            # Quota check
            quota_issues = self._check_gluster_quota()
            if quota_issues:
                result["warnings"].extend(quota_issues)
                result["recommendations"].extend(self.expert_knowledge["glusterfs"]["patterns"]["quota_exceeded"]["remediation"])
            
            # Determine overall status
            if result["critical_issues"]:
                result["status"] = "critical"
            elif len(result["warnings"]) > 2:
                result["status"] = "degraded"
            elif result["warnings"]:
                result["status"] = "warning"
            else:
                result["status"] = "healthy"
                
        except Exception as e:
            result["status"] = "error"
            result["critical_issues"].append(f"GlusterFS analysis failed: {e}")
        
        return result
    
    def expert_remediate(self, issue_description: str, auto_execute: bool = False) -> Dict[str, Any]:
        """Expert-level issue remediation with intelligent pattern matching."""
        remediation_result = {
            "issue_analysis": {},
            "remediation_plan": [],
            "executed_actions": [],
            "safety_checks": [],
            "success": False,
            "message": ""
        }
        
        try:
            # Analyze the issue using expert knowledge
            issue_analysis = self._analyze_issue_pattern(issue_description)
            remediation_result["issue_analysis"] = issue_analysis
            
            if not issue_analysis["pattern_matched"]:
                remediation_result["message"] = "No expert pattern matched for this issue"
                return remediation_result
            
            # Generate remediation plan
            remediation_plan = self._generate_remediation_plan(issue_analysis)
            remediation_result["remediation_plan"] = remediation_plan
            
            # Perform safety checks
            safety_checks = self._perform_safety_checks(remediation_plan)
            remediation_result["safety_checks"] = safety_checks
            
            if not safety_checks["safe_to_proceed"]:
                remediation_result["message"] = f"Safety check failed: {safety_checks['reason']}"
                return remediation_result
            
            # Execute remediation if requested
            if auto_execute and remediation_plan:
                execution_results = self._execute_remediation_plan(remediation_plan)
                remediation_result["executed_actions"] = execution_results
                
                # Verify remediation success
                verification = self._verify_remediation(issue_analysis, execution_results)
                remediation_result["success"] = verification["success"]
                remediation_result["message"] = verification["message"]
            else:
                remediation_result["message"] = "Remediation plan generated. Set auto_execute=True to execute."
            
            # Log the remediation attempt
            self._log_remediation_attempt(issue_description, remediation_result)
            
        except Exception as e:
            self.logger.error(f"Error during expert remediation: {e}")
            remediation_result["message"] = f"Remediation failed: {e}"
        
        return remediation_result
    
    def _analyze_issue_pattern(self, issue_description: str) -> Dict[str, Any]:
        """Analyze issue using expert pattern matching."""
        analysis = {
            "pattern_matched": False,
            "confidence": 0.0,
            "area": "unknown",
            "issue_type": "unknown",
            "severity": "unknown",
            "symptoms": [],
            "likely_causes": [],
            "related_patterns": []
        }
        
        issue_lower = issue_description.lower()
        best_match = {"confidence": 0.0, "area": None, "pattern": None}
        
        # Analyze against all expert patterns
        for area, area_data in self.expert_knowledge.items():
            for pattern_name, pattern_data in area_data["patterns"].items():
                confidence = self._calculate_pattern_confidence(issue_lower, pattern_data["symptoms"])
                
                if confidence > best_match["confidence"]:
                    best_match = {
                        "confidence": confidence,
                        "area": area,
                        "pattern": pattern_name,
                        "data": pattern_data
                    }
        
        if best_match["confidence"] > 0.5:  # Threshold for pattern match
            analysis.update({
                "pattern_matched": True,
                "confidence": best_match["confidence"],
                "area": best_match["area"],
                "issue_type": best_match["pattern"],
                "severity": best_match["data"]["severity"],
                "symptoms": best_match["data"]["symptoms"],
                "commands": best_match["data"]["commands"],
                "remediation": best_match["data"]["remediation"]
            })
        
        return analysis
    
    def _calculate_pattern_confidence(self, issue_text: str, symptoms: List[str]) -> float:
        """Calculate confidence score for pattern matching."""
        matches = 0
        total_symptoms = len(symptoms)
        
        for symptom in symptoms:
            if re.search(symptom.lower(), issue_text):
                matches += 1
        
        return matches / total_symptoms if total_symptoms > 0 else 0.0
    
    def _generate_remediation_plan(self, issue_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate step-by-step remediation plan."""
        plan = []
        
        if not issue_analysis["pattern_matched"]:
            return plan
        
        # Diagnostic phase
        plan.append({
            "phase": "diagnosis",
            "step": "gather_diagnostics",
            "description": "Gather diagnostic information",
            "commands": issue_analysis.get("commands", []),
            "safety_level": "safe"
        })
        
        # Remediation phase
        for i, remediation_step in enumerate(issue_analysis.get("remediation", []), 1):
            safety_level = self._assess_command_safety(remediation_step)
            
            plan.append({
                "phase": "remediation",
                "step": f"remediation_{i}",
                "description": remediation_step,
                "command": self._extract_command(remediation_step),
                "safety_level": safety_level,
                "requires_confirmation": safety_level in ["medium", "high"]
            })
        
        # Verification phase
        plan.append({
            "phase": "verification",
            "step": "verify_fix",
            "description": "Verify that the issue has been resolved",
            "commands": issue_analysis.get("commands", []),
            "safety_level": "safe"
        })
        
        return plan
    
    def _assess_command_safety(self, command_desc: str) -> str:
        """Assess the safety level of a command."""
        high_risk_patterns = [
            r"rm\s+-rf", r"delete.*--force", r"kill.*-9", r"shutdown", r"reboot",
            r"format", r"mkfs", r"dd\s+if", r">/dev/"
        ]
        
        medium_risk_patterns = [
            r"restart", r"stop", r"kill", r"delete", r"remove", r"purge"
        ]
        
        command_lower = command_desc.lower()
        
        for pattern in high_risk_patterns:
            if re.search(pattern, command_lower):
                return "high"
        
        for pattern in medium_risk_patterns:
            if re.search(pattern, command_lower):
                return "medium"
        
        return "safe"
    
    def _extract_command(self, step_description: str) -> Optional[str]:
        """Extract executable command from step description."""
        # Look for command patterns in the description
        command_patterns = [
            r"`([^`]+)`",  # Commands in backticks
            r":\s*([a-zA-Z][a-zA-Z0-9\s\-\.\/]+)",  # Commands after colon
            r"^([a-zA-Z][a-zA-Z0-9\s\-\.\/]+)$"  # Simple commands
        ]
        
        for pattern in command_patterns:
            match = re.search(pattern, step_description)
            if match:
                command = match.group(1).strip()
                # Validate it looks like a valid command
                if self._is_valid_command(command):
                    return command
        
        return None
    
    def _is_valid_command(self, command: str) -> bool:
        """Check if a string looks like a valid command."""
        if not command:
            return False
        
        # Should start with a command name
        first_word = command.split()[0]
        
        # Common system commands we allow
        allowed_commands = [
            "systemctl", "journalctl", "ps", "top", "df", "free", "ls", "cat", "grep",
            "find", "which", "kubectl", "docker", "gluster", "mount", "umount",
            "ping", "curl", "wget", "ssh", "scp", "rsync", "tar", "gzip"
        ]
        
        return first_word in allowed_commands
    
    def _perform_safety_checks(self, remediation_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive safety checks before execution."""
        safety_result = {
            "safe_to_proceed": True,
            "reason": "",
            "warnings": [],
            "blocking_issues": []
        }
        
        try:
            # Check if we're in safety mode
            if self.safety_mode:
                high_risk_actions = [step for step in remediation_plan if step.get("safety_level") == "high"]
                if high_risk_actions:
                    safety_result["safe_to_proceed"] = False
                    safety_result["reason"] = "High-risk actions detected in safety mode"
                    safety_result["blocking_issues"] = [step["description"] for step in high_risk_actions]
                    return safety_result
            
            # Check system resources before making changes
            resources = self._get_system_resources()
            if resources.get("disk_usage_percent", 0) > 95:
                safety_result["warnings"].append("Critical disk space - some operations may fail")
            
            if resources.get("memory_usage_percent", 0) > 95:
                safety_result["warnings"].append("Critical memory usage - system may be unstable")
            
            # Check for concurrent operations
            if self._check_concurrent_operations():
                safety_result["warnings"].append("Other system operations in progress")
            
            # Validate all commands exist
            missing_commands = []
            for step in remediation_plan:
                if step.get("command"):
                    command_name = step["command"].split()[0]
                    if not self._command_exists(command_name):
                        missing_commands.append(command_name)
            
            if missing_commands:
                safety_result["safe_to_proceed"] = False
                safety_result["reason"] = f"Required commands not available: {', '.join(missing_commands)}"
                return safety_result
            
        except Exception as e:
            safety_result["safe_to_proceed"] = False
            safety_result["reason"] = f"Safety check failed: {e}"
        
        return safety_result
    
    def _execute_remediation_plan(self, remediation_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute the remediation plan with proper error handling."""
        execution_results = []
        
        for step in remediation_plan:
            step_result = {
                "step": step["step"],
                "description": step["description"],
                "executed": False,
                "success": False,
                "output": "",
                "error": "",
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                if step.get("command") and step["safety_level"] != "high":
                    # Execute the command
                    result = self._execute_command_safely(step["command"])
                    step_result.update({
                        "executed": True,
                        "success": result["success"],
                        "output": result["output"],
                        "error": result["error"]
                    })
                    
                    # If command failed, stop execution
                    if not result["success"] and step["phase"] == "remediation":
                        step_result["error"] += " (Stopping remediation due to failure)"
                        execution_results.append(step_result)
                        break
                
                elif step["phase"] == "diagnosis":
                    # For diagnostic steps, execute multiple commands
                    diagnostic_output = []
                    for cmd in step.get("commands", []):
                        result = self._execute_command_safely(cmd)
                        diagnostic_output.append(f"$ {cmd}\n{result['output']}")
                    
                    step_result.update({
                        "executed": True,
                        "success": True,
                        "output": "\n\n".join(diagnostic_output)
                    })
                
            except Exception as e:
                step_result.update({
                    "executed": True,
                    "success": False,
                    "error": f"Execution failed: {e}"
                })
            
            execution_results.append(step_result)
        
        return execution_results
    
    def _execute_command_safely(self, command: str) -> Dict[str, Any]:
        """Execute a command with safety measures."""
        result = {
            "success": False,
            "output": "",
            "error": "",
            "return_code": -1
        }
        
        try:
            # Add timeout for safety
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            stdout, stderr = process.communicate()
            result.update({
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr,
                "return_code": process.returncode
            })
            
        except subprocess.TimeoutExpired:
            result["error"] = "Command timed out after 60 seconds"
        except FileNotFoundError:
            result["error"] = f"Command not found: {command.split()[0]}"
        except Exception as e:
            result["error"] = f"Execution error: {e}"
        
        return result
    
    def _verify_remediation(self, issue_analysis: Dict[str, Any], execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify that the remediation was successful."""
        verification = {
            "success": False,
            "message": "",
            "evidence": []
        }
        
        try:
            # Check if all remediation steps succeeded
            remediation_steps = [r for r in execution_results if r.get("step", "").startswith("remediation_")]
            failed_steps = [r for r in remediation_steps if not r.get("success", False)]
            
            if failed_steps:
                verification["message"] = f"Remediation failed at step: {failed_steps[0]['description']}"
                return verification
            
            # Re-run diagnostic commands to check if issue is resolved
            if issue_analysis.get("commands"):
                verification_results = []
                for cmd in issue_analysis["commands"][:3]:  # Limit to first 3 commands
                    result = self._execute_command_safely(cmd)
                    verification_results.append({
                        "command": cmd,
                        "output": result["output"],
                        "success": result["success"]
                    })
                
                verification["evidence"] = verification_results
                
                # Simple heuristic: if diagnostic commands run successfully, consider it fixed
                successful_diagnostics = sum(1 for r in verification_results if r["success"])
                if successful_diagnostics >= len(verification_results) * 0.7:  # 70% success rate
                    verification["success"] = True
                    verification["message"] = "Remediation appears successful based on diagnostic verification"
                else:
                    verification["message"] = "Remediation may not have been successful - diagnostic checks failed"
            else:
                verification["success"] = True
                verification["message"] = "Remediation completed - manual verification recommended"
            
        except Exception as e:
            verification["message"] = f"Verification failed: {e}"
        
        return verification
    
    # Helper methods for system analysis
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        resources = {}
        
        try:
            # Disk usage
            result = self._execute_command_safely("df -h /")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        usage_str = parts[4].rstrip('%')
                        resources["disk_usage_percent"] = int(usage_str)
            
            # Memory usage
            result = self._execute_command_safely("free -m")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        total = int(parts[1])
                        used = int(parts[2])
                        resources["memory_usage_percent"] = (used / total) * 100
            
            # CPU count
            result = self._execute_command_safely("nproc")
            if result["success"]:
                resources["cpu_count"] = int(result["output"].strip())
            
        except Exception as e:
            self.logger.warning(f"Error getting system resources: {e}")
        
        return resources
    
    def _check_failed_services(self) -> List[str]:
        """Check for failed systemd services."""
        failed_services = []
        
        try:
            result = self._execute_command_safely("systemctl --failed --no-pager")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                for line in lines[1:]:  # Skip header
                    if line.strip() and not line.startswith('0 loaded'):
                        parts = line.split()
                        if parts:
                            failed_services.append(parts[0])
        except Exception as e:
            self.logger.warning(f"Error checking failed services: {e}")
        
        return failed_services
    
    def _get_load_average(self) -> float:
        """Get current system load average."""
        try:
            result = self._execute_command_safely("uptime")
            if result["success"]:
                # Extract load average from uptime output
                match = re.search(r'load average:\s*([0-9.]+)', result["output"])
                if match:
                    return float(match.group(1))
        except Exception as e:
            self.logger.warning(f"Error getting load average: {e}")
        
        return 0.0
    
    def _check_network_connectivity(self) -> List[str]:
        """Check basic network connectivity."""
        issues = []
        
        try:
            # Test basic connectivity
            result = self._execute_command_safely("ping -c 1 -W 3 8.8.8.8")
            if not result["success"]:
                issues.append("External network connectivity failed")
            
            # Check if basic networking is up
            result = self._execute_command_safely("ip route show default")
            if not result["success"] or not result["output"].strip():
                issues.append("No default route configured")
            
        except Exception as e:
            self.logger.warning(f"Error checking network connectivity: {e}")
            issues.append(f"Network check failed: {e}")
        
        return issues
    
    def _check_node_health(self) -> Dict[str, Any]:
        """Check Kubernetes node health."""
        node_issues = {"critical": [], "warnings": []}
        
        try:
            result = self._execute_command_safely("kubectl get nodes --no-headers")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            node_name, status = parts[0], parts[1]
                            if status != "Ready":
                                node_issues["critical"].append(f"Node {node_name} is {status}")
        except Exception as e:
            self.logger.warning(f"Error checking node health: {e}")
        
        return node_issues
    
    def _check_pod_health(self) -> Dict[str, Any]:
        """Check Kubernetes pod health."""
        pod_status = {
            "metrics": {},
            "crashloop_pods": [],
            "pending_pods": [],
            "error_pods": []
        }
        
        try:
            result = self._execute_command_safely("kubectl get pods --all-namespaces --no-headers")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                total_pods = 0
                running_pods = 0
                
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            namespace, pod_name, ready, status = parts[0], parts[1], parts[2], parts[3]
                            total_pods += 1
                            
                            if status == "Running":
                                running_pods += 1
                            elif status == "CrashLoopBackOff":
                                pod_status["crashloop_pods"].append(f"{namespace}/{pod_name}")
                            elif status == "Pending":
                                pod_status["pending_pods"].append(f"{namespace}/{pod_name}")
                            elif status in ["Error", "Failed"]:
                                pod_status["error_pods"].append(f"{namespace}/{pod_name}")
                
                pod_status["metrics"] = {
                    "total_pods": total_pods,
                    "running_pods": running_pods,
                    "pod_health_percent": (running_pods / total_pods * 100) if total_pods > 0 else 0
                }
        except Exception as e:
            self.logger.warning(f"Error checking pod health: {e}")
        
        return pod_status
    
    def _check_service_health(self) -> List[str]:
        """Check Kubernetes service health."""
        service_issues = []
        
        try:
            result = self._execute_command_safely("kubectl get endpoints --all-namespaces --no-headers")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            namespace, service_name, endpoints = parts[0], parts[1], parts[2]
                            if endpoints == "<none>":
                                service_issues.append(f"Service {namespace}/{service_name} has no endpoints")
        except Exception as e:
            self.logger.warning(f"Error checking service health: {e}")
        
        return service_issues
    
    def _check_volume_health(self) -> List[str]:
        """Check Kubernetes volume health."""
        volume_issues = []
        
        try:
            result = self._execute_command_safely("kubectl get pvc --all-namespaces --no-headers")
            if result["success"]:
                lines = result["output"].strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            namespace, pvc_name, status = parts[0], parts[1], parts[2]
                            if status != "Bound":
                                volume_issues.append(f"PVC {namespace}/{pvc_name} is {status}")
        except Exception as e:
            self.logger.warning(f"Error checking volume health: {e}")
        
        return volume_issues
    
    def _check_gluster_volumes(self) -> Dict[str, Any]:
        """Check GlusterFS volume status."""
        volume_status = {
            "offline_volumes": [],
            "degraded_volumes": [],
            "healthy_volumes": []
        }
        
        try:
            result = self._execute_command_safely("gluster volume info")
            if result["success"]:
                # Parse volume info output
                current_volume = None
                for line in result["output"].split('\n'):
                    if line.startswith('Volume Name:'):
                        current_volume = line.split(':', 1)[1].strip()
                    elif line.startswith('Status:') and current_volume:
                        status = line.split(':', 1)[1].strip()
                        if status == "Started":
                            volume_status["healthy_volumes"].append(current_volume)
                        else:
                            volume_status["offline_volumes"].append(current_volume)
        except Exception as e:
            self.logger.warning(f"Error checking GlusterFS volumes: {e}")
        
        return volume_status
    
    def _check_gluster_heal(self) -> Dict[str, Any]:
        """Check GlusterFS heal status."""
        heal_status = {
            "split_brain_files": 0,
            "heal_pending": 0
        }
        
        try:
            # Get list of volumes first
            result = self._execute_command_safely("gluster volume list")
            if result["success"]:
                volumes = result["output"].strip().split('\n')
                for volume in volumes:
                    if volume.strip():
                        # Check heal status for each volume
                        heal_result = self._execute_command_safely(f"gluster volume heal {volume.strip()} info")
                        if heal_result["success"]:
                            # Count heal entries (simplified)
                            heal_lines = heal_result["output"].count('\n')
                            heal_status["heal_pending"] += max(0, heal_lines - 5)  # Rough estimate
        except Exception as e:
            self.logger.warning(f"Error checking GlusterFS heal status: {e}")
        
        return heal_status
    
    def _check_gluster_peers(self) -> Dict[str, Any]:
        """Check GlusterFS peer status."""
        peer_status = {
            "connected_peers": [],
            "disconnected_peers": []
        }
        
        try:
            result = self._execute_command_safely("gluster peer status")
            if result["success"]:
                current_peer = None
                for line in result["output"].split('\n'):
                    if line.startswith('Hostname:'):
                        current_peer = line.split(':', 1)[1].strip()
                    elif line.startswith('State:') and current_peer:
                        state = line.split(':', 1)[1].strip()
                        if "Connected" in state:
                            peer_status["connected_peers"].append(current_peer)
                        else:
                            peer_status["disconnected_peers"].append(current_peer)
        except Exception as e:
            self.logger.warning(f"Error checking GlusterFS peers: {e}")
        
        return peer_status
    
    def _check_gluster_bricks(self) -> Dict[str, Any]:
        """Check GlusterFS brick status."""
        brick_status = {
            "healthy_bricks": [],
            "failed_bricks": []
        }
        
        try:
            result = self._execute_command_safely("gluster volume status")
            if result["success"]:
                lines = result["output"].split('\n')
                for line in lines:
                    if "Brick" in line and ":" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            brick_path = parts[1]
                            status = parts[2] if len(parts) > 2 else "Unknown"
                            if status == "Y":  # Online
                                brick_status["healthy_bricks"].append(brick_path)
                            else:
                                brick_status["failed_bricks"].append(brick_path)
        except Exception as e:
            self.logger.warning(f"Error checking GlusterFS bricks: {e}")
        
        return brick_status
    
    def _check_gluster_quota(self) -> List[str]:
        """Check GlusterFS quota issues."""
        quota_issues = []
        
        try:
            result = self._execute_command_safely("gluster volume list")
            if result["success"]:
                volumes = result["output"].strip().split('\n')
                for volume in volumes:
                    if volume.strip():
                        quota_result = self._execute_command_safely(f"gluster volume quota {volume.strip()} list")
                        if quota_result["success"] and "limit set" in quota_result["output"]:
                            # Check if quota is being exceeded (simplified check)
                            if "100%" in quota_result["output"] or "exceeded" in quota_result["output"].lower():
                                quota_issues.append(f"Quota exceeded on volume {volume.strip()}")
        except Exception as e:
            self.logger.warning(f"Error checking GlusterFS quota: {e}")
        
        return quota_issues
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists on the system."""
        try:
            result = self._execute_command_safely(f"which {command}")
            return result["success"]
        except:
            return False
    
    def _check_concurrent_operations(self) -> bool:
        """Check if other potentially conflicting operations are running."""
        try:
            # Check for package managers
            for cmd in ["apt", "yum", "dnf", "zypper"]:
                result = self._execute_command_safely(f"pgrep {cmd}")
                if result["success"] and result["output"].strip():
                    return True
            
            # Check for system updates
            result = self._execute_command_safely("pgrep -f update")
            if result["success"] and result["output"].strip():
                return True
                
        except Exception:
            pass
        
        return False
    
    def _prioritize_recommendations(self, recommendations: List[str]) -> List[str]:
        """Prioritize recommendations by safety and impact."""
        # Simple prioritization based on keywords
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for rec in recommendations:
            rec_lower = rec.lower()
            if any(word in rec_lower for word in ["restart", "kill", "delete", "remove"]):
                high_priority.append(rec)
            elif any(word in rec_lower for word in ["check", "verify", "monitor"]):
                low_priority.append(rec)
            else:
                medium_priority.append(rec)
        
        return low_priority + medium_priority + high_priority
    
    def _log_remediation_attempt(self, issue_description: str, result: Dict[str, Any]):
        """Log remediation attempt for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "issue_description": issue_description,
            "pattern_matched": result["issue_analysis"].get("pattern_matched", False),
            "confidence": result["issue_analysis"].get("confidence", 0.0),
            "area": result["issue_analysis"].get("area", "unknown"),
            "executed": len(result.get("executed_actions", [])) > 0,
            "success": result.get("success", False),
            "message": result.get("message", "")
        }
        
        self.remediation_history.append(log_entry)
        
        # Keep only last 100 entries
        if len(self.remediation_history) > 100:
            self.remediation_history = self.remediation_history[-100:]
    
    def _prioritize_recommendations_with_history(self, recommendations: List[str]) -> List[str]:
        """Prioritize recommendations based on historical success rates."""
        if not self.history_manager:
            return recommendations
        
        # For now, return as-is - can be enhanced with specific success rate tracking
        return recommendations
    
    def get_historical_issue_analysis(self, issue_description: str) -> Dict[str, Any]:
        """Get historical analysis and prediction for a specific issue."""
        if not self.history_manager:
            return {"message": "Historical analysis not available"}
        
        try:
            prediction = self.history_manager.get_predictive_analysis(issue_description)
            trends = self.history_manager.get_issue_trend_analysis()
            
            return {
                "prediction": prediction,
                "trends": trends,
                "learning_report": self.history_manager.generate_learning_report()
            }
        except Exception as e:
            return {"error": f"Historical analysis failed: {e}"}
    
    def perform_continuous_learning_update(self) -> Dict[str, Any]:
        """Perform a manual continuous learning update."""
        if not self.history_manager:
            return {"message": "Continuous learning not available"}
        
        try:
            scan_result = self.history_manager.continuous_learning_scan()
            return {
                "success": True,
                "scan_result": scan_result,
                "learning_report": self.history_manager.generate_learning_report()
            }
        except Exception as e:
            return {"success": False, "error": f"Learning update failed: {e}"}
    
    def get_remediation_history(self) -> List[Dict[str, Any]]:
        """Get remediation history for audit purposes."""
        return self.remediation_history.copy()
    
    def set_safety_mode(self, enabled: bool):
        """Enable or disable safety mode."""
        self.safety_mode = enabled
        self.logger.info(f"Safety mode {'enabled' if enabled else 'disabled'}")
    
    def get_system_health_summary(self) -> str:
        """Get a comprehensive system health summary with historical insights."""
        analysis = self.analyze_system_comprehensive()
        
        summary_parts = []
        
        # Overall health
        health_status = analysis["overall_health"]
        if health_status == "healthy":
            summary_parts.append("🟢 **System Status: HEALTHY** - All monitored components are operating normally.")
        elif health_status == "warning":
            summary_parts.append("🟡 **System Status: WARNING** - Some issues detected that require attention.")
        elif health_status == "degraded":
            summary_parts.append("🟠 **System Status: DEGRADED** - Multiple issues affecting system performance.")
        elif health_status == "critical":
            summary_parts.append("🔴 **System Status: CRITICAL** - Immediate attention required!")
        
        # Add historical insights
        if "historical_insights" in analysis and analysis["historical_insights"]:
            insights = analysis["historical_insights"]
            summary_parts.append(f"\n📊 **Historical Analysis:**")
            summary_parts.append(f"• Recent Issues (24h): {insights.get('recent_issues_24h', 0)}")
            summary_parts.append(f"• Trend Direction: {insights.get('trend_direction', 'unknown').title()}")
            if insights.get('most_frequent_type'):
                most_frequent = insights['most_frequent_type']
                summary_parts.append(f"• Most Frequent Issue: {most_frequent[0]} ({most_frequent[1]} occurrences)")
        
        # Add predictive analysis
        if "predictive_analysis" in analysis and analysis["predictive_analysis"]:
            summary_parts.append(f"\n🔮 **Predictive Analysis:**")
            for area, predictions in analysis["predictive_analysis"].items():
                for pred_data in predictions[:2]:  # Show top 2 predictions per area
                    pred = pred_data["prediction"]
                    if pred["confidence"] > 0.5:
                        summary_parts.append(f"• {area.title()}: {pred['predicted_cause']} (confidence: {pred['confidence']:.1%})")
        
        # Add learning scan results
        if "learning_scan" in analysis:
            scan = analysis["learning_scan"]
            summary_parts.append(f"\n🧠 **Continuous Learning:**")
            summary_parts.append(f"• New Issues Detected: {scan['issues_detected']}")
            summary_parts.append(f"• Total Historical Issues: {scan['total_historical']}")
            summary_parts.append(f"• Last Scan: {scan['scan_timestamp'][:19]}")
    
        # Overall health
        else:
            summary_parts.append("⚪ **System Status: UNKNOWN** - Unable to determine system health.")
        
        # Critical issues
        if analysis["critical_issues"]:
            summary_parts.append(f"\n**🚨 Critical Issues ({len(analysis['critical_issues'])}):**")
            for issue in analysis["critical_issues"][:5]:  # Limit to first 5
                summary_parts.append(f"• {issue}")
            if len(analysis["critical_issues"]) > 5:
                summary_parts.append(f"• ... and {len(analysis['critical_issues']) - 5} more")
        
        # Warnings
        if analysis["warnings"]:
            summary_parts.append(f"\n**⚠️ Warnings ({len(analysis['warnings'])}):**")
            for warning in analysis["warnings"][:3]:  # Limit to first 3
                summary_parts.append(f"• {warning}")
            if len(analysis["warnings"]) > 3:
                summary_parts.append(f"• ... and {len(analysis['warnings']) - 3} more")
        
        # Component status
        summary_parts.append("\n**📊 Component Status:**")
        for area, area_data in analysis["detailed_analysis"].items():
            status = area_data["status"]
            emoji = {"healthy": "✅", "warning": "⚠️", "degraded": "🟠", "critical": "🔴", "unavailable": "⚫", "error": "❌"}.get(status, "❓")
            area_name = area.replace("_", " ").title()
            summary_parts.append(f"• {emoji} {area_name}: {status.upper()}")
        
        # Top recommendations
        if analysis["recommendations"]:
            summary_parts.append(f"\n**💡 Top Recommendations:**")
            for rec in analysis["recommendations"][:3]:  # Top 3 recommendations
                summary_parts.append(f"• {rec}")
        
        return "\n".join(summary_parts)
