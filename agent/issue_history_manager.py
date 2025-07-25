#!/usr/bin/env python3
"""
Issue History Manager - Tracks, learns from, and predicts system issues
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import hashlib
import re
from collections import defaultdict, deque
import subprocess

class IssueHistoryManager:
    """Manages issue history, pattern learning, and root cause prediction"""
    
    def __init__(self, history_file="/tmp/issue_history.json", max_history=3):
        self.history_file = history_file
        self.max_history = max_history
        self.issue_history = defaultdict(lambda: deque(maxlen=max_history))
        self.pattern_signatures = {}
        self.root_cause_patterns = {}
        self.prediction_accuracy = {}
        
        # Load existing history
        self.load_history()
        
        # Initialize pattern recognition
        self.initialize_patterns()
    
    def initialize_patterns(self):
        """Initialize known issue patterns for learning"""
        self.pattern_signatures = {
            # Kubernetes patterns
            "crashloop_backoff": {
                "keywords": ["crashloopbackoff", "crash", "exit", "failed", "restart"],
                "log_patterns": [
                    r"pod.*crashloopbackoff",
                    r"container.*exit.*code.*[1-9]",
                    r"back-off.*restarting.*failed"
                ],
                "common_causes": ["config_error", "resource_limit", "dependency_failure", "health_check_fail"]
            },
            
            "pod_pending": {
                "keywords": ["pending", "unschedulable", "insufficient", "resources"],
                "log_patterns": [
                    r"pod.*pending",
                    r"insufficient.*resources",
                    r"unschedulable"
                ],
                "common_causes": ["resource_shortage", "node_affinity", "taints_tolerations", "pvc_issues"]
            },
            
            "imagepull_backoff": {
                "keywords": ["imagepullbackoff", "errimagepull", "image", "pull"],
                "log_patterns": [
                    r"imagepullbackoff",
                    r"errimagepull",
                    r"failed.*pull.*image"
                ],
                "common_causes": ["registry_auth", "image_not_found", "network_issue", "registry_down"]
            },
            
            # Ubuntu/System patterns
            "disk_space": {
                "keywords": ["disk", "space", "full", "no space", "inodes"],
                "log_patterns": [
                    r"no space left",
                    r"disk.*full",
                    r"filesystem.*full"
                ],
                "common_causes": ["log_rotation", "tmp_cleanup", "large_files", "inode_exhaustion"]
            },
            
            "memory_pressure": {
                "keywords": ["memory", "oom", "killed", "out of memory"],
                "log_patterns": [
                    r"out of memory",
                    r"oom.*killed",
                    r"memory.*pressure"
                ],
                "common_causes": ["memory_leak", "undersized_limits", "burst_traffic", "swap_disabled"]
            },
            
            "network_connectivity": {
                "keywords": ["network", "connection", "timeout", "unreachable"],
                "log_patterns": [
                    r"connection.*timeout",
                    r"network.*unreachable",
                    r"dns.*resolution.*failed"
                ],
                "common_causes": ["firewall_rules", "dns_config", "route_table", "network_partition"]
            },
            
            # GlusterFS patterns
            "split_brain": {
                "keywords": ["split-brain", "split brain", "heal", "conflict"],
                "log_patterns": [
                    r"split.*brain",
                    r"heal.*pending",
                    r"conflicting.*entries"
                ],
                "common_causes": ["network_partition", "node_failure", "concurrent_writes", "clock_skew"]
            },
            
            "peer_disconnect": {
                "keywords": ["peer", "disconnect", "connection", "offline"],
                "log_patterns": [
                    r"peer.*disconnect",
                    r"connection.*lost",
                    r"peer.*offline"
                ],
                "common_causes": ["network_issue", "node_down", "gluster_service", "firewall_block"]
            }
        }
    
    def capture_system_logs(self) -> Dict[str, List[str]]:
        """Capture current system logs for analysis"""
        logs = {
            "kubernetes": [],
            "system": [],
            "glusterfs": []
        }
        
        try:
            # Kubernetes logs
            k8s_commands = [
                "kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -50",
                "kubectl get pods --all-namespaces | grep -E '(Error|CrashLoop|Pending|ImagePull)' || true",
                "kubectl top nodes 2>/dev/null || true"
            ]
            
            for cmd in k8s_commands:
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.stdout.strip():
                        logs["kubernetes"].extend(result.stdout.strip().split('\n'))
                except:
                    continue
            
            # System logs
            system_commands = [
                "journalctl --since '1 hour ago' --no-pager -n 100 | grep -E '(error|failed|critical)' || true",
                "df -h | grep -E '(9[0-9]%|100%)' || true",
                "free -m | grep -E 'Mem:|Swap:' || true"
            ]
            
            for cmd in system_commands:
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.stdout.strip():
                        logs["system"].extend(result.stdout.strip().split('\n'))
                except:
                    continue
            
            # GlusterFS logs (if available)
            gluster_commands = [
                "gluster volume status 2>/dev/null || true",
                "gluster peer status 2>/dev/null || true",
                "gluster volume heal info 2>/dev/null || true"
            ]
            
            for cmd in gluster_commands:
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.stdout.strip():
                        logs["glusterfs"].extend(result.stdout.strip().split('\n'))
                except:
                    continue
                    
        except Exception as e:
            print(f"Warning: Could not capture some logs: {e}")
        
        return logs
    
    def detect_issues_from_logs(self, logs: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Detect issues from captured logs using pattern matching"""
        detected_issues = []
        
        all_log_text = " ".join([
            " ".join(logs.get("kubernetes", [])),
            " ".join(logs.get("system", [])),
            " ".join(logs.get("glusterfs", []))
        ]).lower()
        
        for issue_type, pattern_info in self.pattern_signatures.items():
            confidence = 0.0
            matched_patterns = []
            evidence = []
            
            # Check keyword matches
            keyword_matches = sum(1 for keyword in pattern_info["keywords"] 
                                if keyword.lower() in all_log_text)
            if keyword_matches > 0:
                confidence += (keyword_matches / len(pattern_info["keywords"])) * 0.6
            
            # Check regex patterns
            pattern_matches = 0
            for pattern in pattern_info["log_patterns"]:
                matches = re.findall(pattern, all_log_text, re.IGNORECASE)
                if matches:
                    pattern_matches += 1
                    matched_patterns.append(pattern)
                    evidence.extend(matches[:3])  # Limit evidence
            
            if pattern_matches > 0:
                confidence += (pattern_matches / len(pattern_info["log_patterns"])) * 0.4
            
            # If we have sufficient confidence, record the issue
            if confidence > 0.3:  # 30% confidence threshold
                issue = {
                    "type": issue_type,
                    "confidence": min(confidence, 1.0),
                    "timestamp": datetime.now().isoformat(),
                    "evidence": evidence[:5],  # Top 5 pieces of evidence
                    "matched_patterns": matched_patterns,
                    "system_context": self.gather_system_context(),
                    "predicted_causes": pattern_info["common_causes"]
                }
                detected_issues.append(issue)
        
        return detected_issues
    
    def gather_system_context(self) -> Dict[str, Any]:
        """Gather current system context for issue analysis"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "system_load": None,
            "memory_usage": None,
            "disk_usage": None,
            "k8s_status": None
        }
        
        try:
            # System load
            result = subprocess.run("uptime", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                context["system_load"] = result.stdout.strip()
        except:
            pass
        
        try:
            # Memory usage
            result = subprocess.run("free -m", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                context["memory_usage"] = result.stdout.strip()
        except:
            pass
        
        try:
            # Disk usage
            result = subprocess.run("df -h /", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                context["disk_usage"] = result.stdout.strip()
        except:
            pass
        
        try:
            # Kubernetes status
            result = subprocess.run("kubectl cluster-info 2>/dev/null", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                context["k8s_status"] = "available"
            else:
                context["k8s_status"] = "unavailable"
        except:
            context["k8s_status"] = "unknown"
        
        return context
    
    def record_issue(self, issue: Dict[str, Any]):
        """Record an issue in the history"""
        issue_type = issue["type"]
        issue_signature = self.generate_issue_signature(issue)
        
        # Add signature to issue
        issue["signature"] = issue_signature
        
        # Record in history
        self.issue_history[issue_type].append(issue)
        
        # Update pattern learning
        self.update_pattern_learning(issue)
        
        # Save to disk
        self.save_history()
        
        print(f"📊 Recorded issue: {issue_type} (confidence: {issue['confidence']:.1%})")
    
    def generate_issue_signature(self, issue: Dict[str, Any]) -> str:
        """Generate a unique signature for an issue"""
        signature_data = {
            "type": issue["type"],
            "evidence": sorted(issue.get("evidence", [])),
            "patterns": sorted(issue.get("matched_patterns", []))
        }
        signature_string = json.dumps(signature_data, sort_keys=True)
        return hashlib.md5(signature_string.encode()).hexdigest()[:12]
    
    def update_pattern_learning(self, issue: Dict[str, Any]):
        """Update pattern learning based on new issue"""
        issue_type = issue["type"]
        
        # Update accuracy tracking
        if issue_type not in self.prediction_accuracy:
            self.prediction_accuracy[issue_type] = {
                "total_predictions": 0,
                "accurate_predictions": 0,
                "accuracy_rate": 0.0
            }
        
        # Learn from evidence patterns
        evidence = issue.get("evidence", [])
        if evidence:
            if issue_type not in self.root_cause_patterns:
                self.root_cause_patterns[issue_type] = defaultdict(int)
            
            for evidence_item in evidence:
                # Extract key patterns from evidence
                words = re.findall(r'\b\w+\b', evidence_item.lower())
                for word in words:
                    if len(word) > 3:  # Skip short words
                        self.root_cause_patterns[issue_type][word] += 1
    
    def predict_root_cause(self, issue_type: str, current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Predict root cause based on historical patterns"""
        if issue_type not in self.issue_history:
            return {"predicted_cause": "unknown", "confidence": 0.0, "recommendations": []}
        
        history = list(self.issue_history[issue_type])
        if not history:
            return {"predicted_cause": "unknown", "confidence": 0.0, "recommendations": []}
        
        # Analyze historical patterns
        cause_frequency = defaultdict(int)
        resolution_patterns = defaultdict(list)
        context_patterns = defaultdict(int)
        
        for past_issue in history:
            # Track causes from evidence
            for evidence in past_issue.get("evidence", []):
                words = re.findall(r'\b\w+\b', evidence.lower())
                for word in words:
                    if len(word) > 3:
                        cause_frequency[word] += 1
            
            # Track resolution patterns if available
            if "resolution" in past_issue:
                resolution_patterns[past_issue["resolution"]["action"]].append(
                    past_issue["resolution"]["success"]
                )
            
            # Track context patterns
            context = past_issue.get("system_context", {})
            for key, value in context.items():
                if value and isinstance(value, str):
                    context_patterns[f"{key}_{value}"] += 1
        
        # Predict most likely cause
        if cause_frequency:
            predicted_cause = max(cause_frequency.items(), key=lambda x: x[1])
            confidence = min(predicted_cause[1] / len(history), 1.0)
        else:
            predicted_cause = ("unknown", 0)
            confidence = 0.0
        
        # Generate recommendations based on successful resolutions
        recommendations = []
        if resolution_patterns:
            for action, successes in resolution_patterns.items():
                success_rate = sum(successes) / len(successes) if successes else 0
                if success_rate > 0.5:  # More than 50% success rate
                    recommendations.append({
                        "action": action,
                        "success_rate": success_rate,
                        "frequency": len(successes)
                    })
        
        # Add default recommendations from pattern signatures
        pattern_info = self.pattern_signatures.get(issue_type, {})
        common_causes = pattern_info.get("common_causes", [])
        
        return {
            "predicted_cause": predicted_cause[0],
            "confidence": confidence,
            "frequency": predicted_cause[1],
            "recommendations": sorted(recommendations, key=lambda x: x["success_rate"], reverse=True),
            "common_causes": common_causes,
            "historical_count": len(history),
            "context_patterns": dict(sorted(context_patterns.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def get_issue_trend_analysis(self, issue_type: str = None) -> Dict[str, Any]:
        """Analyze trends in issue occurrence"""
        if issue_type:
            history = list(self.issue_history.get(issue_type, []))
            issue_types = [issue_type]
        else:
            history = []
            issue_types = list(self.issue_history.keys())
            for issues in self.issue_history.values():
                history.extend(list(issues))
        
        if not history:
            return {"trends": "No historical data available"}
        
        # Time-based analysis
        now = datetime.now()
        recent_issues = [issue for issue in history 
                        if datetime.fromisoformat(issue["timestamp"]) > now - timedelta(hours=24)]
        
        trend_analysis = {
            "total_issues": len(history),
            "recent_issues_24h": len(recent_issues),
            "issue_types": len(set(issue["type"] for issue in history)),
            "average_confidence": sum(issue["confidence"] for issue in history) / len(history),
            "most_frequent_type": None,
            "trend_direction": "stable"
        }
        
        # Find most frequent issue type
        type_counts = defaultdict(int)
        for issue in history:
            type_counts[issue["type"]] += 1
        
        if type_counts:
            trend_analysis["most_frequent_type"] = max(type_counts.items(), key=lambda x: x[1])
        
        # Determine trend direction
        if len(history) >= 2:
            older_half = history[:len(history)//2]
            newer_half = history[len(history)//2:]
            
            older_avg_confidence = sum(issue["confidence"] for issue in older_half) / len(older_half)
            newer_avg_confidence = sum(issue["confidence"] for issue in newer_half) / len(newer_half)
            
            if newer_avg_confidence > older_avg_confidence * 1.1:
                trend_analysis["trend_direction"] = "worsening"
            elif newer_avg_confidence < older_avg_confidence * 0.9:
                trend_analysis["trend_direction"] = "improving"
        
        return trend_analysis
    
    def continuous_learning_scan(self) -> Dict[str, Any]:
        """Perform continuous learning scan of system logs"""
        print("🔍 Starting continuous learning scan...")
        
        # Capture current logs
        logs = self.capture_system_logs()
        
        # Detect new issues
        detected_issues = self.detect_issues_from_logs(logs)
        
        # Record new issues
        for issue in detected_issues:
            self.record_issue(issue)
        
        # Generate learning summary
        summary = {
            "scan_timestamp": datetime.now().isoformat(),
            "logs_analyzed": sum(len(log_list) for log_list in logs.values()),
            "issues_detected": len(detected_issues),
            "new_patterns_learned": 0,
            "total_historical_issues": sum(len(history) for history in self.issue_history.values()),
            "issue_types_tracked": len(self.issue_history),
            "detected_issues": detected_issues
        }
        
        print(f"✅ Scan complete: {len(detected_issues)} issues detected, {summary['total_historical_issues']} total in history")
        
        return summary
    
    def get_predictive_analysis(self, issue_description: str) -> Dict[str, Any]:
        """Provide predictive analysis for a given issue description"""
        issue_text = issue_description.lower()
        
        # Find best matching issue type
        best_match = None
        best_score = 0.0
        
        for issue_type, pattern_info in self.pattern_signatures.items():
            score = 0.0
            
            # Check keyword matches
            keyword_matches = sum(1 for keyword in pattern_info["keywords"] 
                                if keyword.lower() in issue_text)
            if keyword_matches > 0:
                score += (keyword_matches / len(pattern_info["keywords"])) * 0.8
            
            # Check regex patterns
            pattern_matches = sum(1 for pattern in pattern_info["log_patterns"]
                                if re.search(pattern, issue_text, re.IGNORECASE))
            if pattern_matches > 0:
                score += (pattern_matches / len(pattern_info["log_patterns"])) * 0.2
            
            if score > best_score:
                best_score = score
                best_match = issue_type
        
        if not best_match or best_score < 0.3:
            return {
                "prediction": "No matching pattern found",
                "confidence": 0.0,
                "recommendations": ["Perform manual investigation", "Check system logs", "Review recent changes"]
            }
        
        # Get detailed prediction for best match
        prediction = self.predict_root_cause(best_match)
        prediction["pattern_match_confidence"] = best_score
        prediction["issue_type"] = best_match
        
        return prediction
    
    def save_history(self):
        """Save issue history to disk"""
        try:
            # Convert deque objects to lists for JSON serialization
            serializable_history = {}
            for issue_type, history in self.issue_history.items():
                serializable_history[issue_type] = list(history)
            
            data = {
                "issue_history": serializable_history,
                "root_cause_patterns": dict(self.root_cause_patterns),
                "prediction_accuracy": self.prediction_accuracy,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save history: {e}")
    
    def load_history(self):
        """Load issue history from disk"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                
                # Restore issue history with deque objects
                if "issue_history" in data:
                    for issue_type, history in data["issue_history"].items():
                        self.issue_history[issue_type] = deque(history, maxlen=self.max_history)
                
                # Restore other data
                self.root_cause_patterns = defaultdict(int, data.get("root_cause_patterns", {}))
                self.prediction_accuracy = data.get("prediction_accuracy", {})
                
                print(f"📚 Loaded {sum(len(h) for h in self.issue_history.values())} historical issues")
                
        except Exception as e:
            print(f"Warning: Could not load history: {e}")
            # Initialize empty history
            self.issue_history = defaultdict(lambda: deque(maxlen=self.max_history))
    
    def generate_learning_report(self) -> str:
        """Generate a comprehensive learning report"""
        total_issues = sum(len(history) for history in self.issue_history.values())
        
        report = f"""
🧠 CONTINUOUS LEARNING REPORT
================================

📊 Historical Data:
• Total Issues Tracked: {total_issues}
• Issue Types: {len(self.issue_history)}
• Pattern Signatures: {len(self.pattern_signatures)}

🔍 Issue Type Breakdown:
"""
        
        for issue_type, history in self.issue_history.items():
            if history:
                recent_issue = history[-1]
                avg_confidence = sum(issue["confidence"] for issue in history) / len(history)
                report += f"• {issue_type}: {len(history)} occurrences (avg confidence: {avg_confidence:.1%})\n"
        
        report += f"""
🎯 Prediction Accuracy:
"""
        
        for issue_type, accuracy_data in self.prediction_accuracy.items():
            rate = accuracy_data.get("accuracy_rate", 0.0)
            total = accuracy_data.get("total_predictions", 0)
            report += f"• {issue_type}: {rate:.1%} accuracy ({total} predictions)\n"
        
        # Get trend analysis
        trends = self.get_issue_trend_analysis()
        report += f"""
📈 Trend Analysis:
• Recent Issues (24h): {trends.get('recent_issues_24h', 0)}
• Average Confidence: {trends.get('average_confidence', 0):.1%}
• Trend Direction: {trends.get('trend_direction', 'unknown')}
• Most Frequent: {trends.get('most_frequent_type', ['unknown', 0])[0]}

🔮 Learning Status:
• Patterns Learned: {len(self.root_cause_patterns)}
• Continuous Scanning: ✅ Active
• Historical Retention: Last {self.max_history} occurrences per issue type
"""
        
        return report

# Example usage and testing
if __name__ == "__main__":
    # Initialize the history manager
    history_manager = IssueHistoryManager()
    
    # Perform a learning scan
    print("🚀 Testing Issue History Manager...")
    
    # Continuous learning scan
    scan_result = history_manager.continuous_learning_scan()
    print(f"📊 Scan Results: {scan_result}")
    
    # Test predictive analysis
    test_descriptions = [
        "Kubernetes pods are stuck in CrashLoopBackOff state",
        "System is running out of disk space",
        "GlusterFS peer disconnected from cluster",
        "High memory usage causing OOM kills"
    ]
    
    for description in test_descriptions:
        prediction = history_manager.get_predictive_analysis(description)
        print(f"\n🔮 Prediction for '{description}': {prediction}")
    
    # Generate learning report
    report = history_manager.generate_learning_report()
    print(f"\n{report}")
