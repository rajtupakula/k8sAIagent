import hashlib
from collections import deque


class IssueHistoryManager:
    def __init__(self):
        self.history = {}

    def record_issue(self, issue_type, logs):
        key = self._hash(logs)
        if issue_type not in self.history:
            self.history[issue_type] = deque(maxlen=3)
        self.history[issue_type].append(key)

    def match_confidence(self, issue_type, logs):
        key = self._hash(logs)
        matches = self.history.get(issue_type, [])
        return round((matches.count(key) / 3.0), 2)

    def predict_root_cause(self, issue_type):
        logs = self.history.get(issue_type, [])
        if logs:
            return f"Recurring pattern detected for {issue_type}"
        return "No sufficient history yet"

    def _hash(self, content):
        return hashlib.md5(content.encode()).hexdigest()