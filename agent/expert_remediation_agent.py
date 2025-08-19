import json
import re
from agent.issue_history_manager import IssueHistoryManager


class ExpertRemediationAgent:
    def __init__(self):
        self.history = IssueHistoryManager()
        self.patterns = self.load_patterns()

    def load_patterns(self):
        return {
            "kubernetes_pod_crashloop": {
                "regex": r"CrashLoopBackOff|Error response from daemon",
                "remediation": [
                    "Check pod logs: kubectl logs <pod-name> --previous",
                    "Delete pod: kubectl delete pod <pod-name>",
                    "Check events: kubectl describe pod <pod-name>",
                    "Verify image: docker pull <image-name>"
                ]
            },
            "ubuntu_disk_full": {
                "regex": r"No space left on device|df:.*No such file or directory",
                "remediation": [
                    "Clear journal logs: sudo journalctl --vacuum-time=2d",
                    "Clean apt: sudo apt-get clean",
                    "Check disk usage: df -h",
                    "Remove orphaned docker volumes: docker volume prune"
                ]
            },
            "gluster_split_brain": {
                "regex": r"Split-brain|Pending heal|Unsynced entries",
                "remediation": [
                    "Check heal status: gluster volume heal <vol> info",
                    "Resolve split-brain: gluster volume heal <vol> split-brain info",
                    "Trigger heal: gluster volume heal <vol>",
                    "Check peer status: gluster peer status"
                ]
            }
        }

    def expert_query(self, logs):
        for issue_type, pattern in self.patterns.items():
            if re.search(pattern["regex"], logs, re.IGNORECASE):
                confidence = self.history.match_confidence(issue_type, logs)
                self.history.record_issue(issue_type, logs)
                return {
                    "matched_issue": issue_type,
                    "confidence": confidence,
                    "remediation_plan": pattern["remediation"],
                    "root_cause_prediction": self.history.predict_root_cause(issue_type),
                }
        return {
            "matched_issue": None,
            "confidence": 0.0,
            "remediation_plan": [],
            "root_cause_prediction": None
        }
