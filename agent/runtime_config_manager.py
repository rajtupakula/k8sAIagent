#!/usr/bin/env python3
"""
Runtime Configuration Manager for Kubernetes AI Assistant

Supports runtime configuration changes through:
- Kubernetes ConfigMaps and environment variables
- File-based configuration watching
- Runtime API updates

Key principle: UI is always interactive, backend can be configured for auto-remediation
"""

import os
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict


class OperationalMode(Enum):
    """Available operational modes for the AI assistant."""
    DEBUG = "debug"
    REMEDIATION = "remediation"
    INTERACTIVE = "interactive"
    MONITORING = "monitoring"
    HYBRID = "hybrid"


class AutomationLevel(Enum):
    """Automation levels for different operational modes."""
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


@dataclass
class RuntimeConfig:
    """Runtime configuration that can be modified through Kubernetes."""
    # Core operational settings
    mode: OperationalMode = OperationalMode.INTERACTIVE
    automation_level: AutomationLevel = AutomationLevel.SEMI_AUTO
    confidence_threshold: int = 80
    
    # Feature toggles (modifiable at runtime)
    historical_learning: bool = True
    predictive_analysis: bool = True
    continuous_monitoring: bool = False
    backend_auto_remediation: bool = False  # Backend behavior
    
    # UI behavior (always interactive as requested)
    ui_always_interactive: bool = True
    ui_require_confirmation: bool = True
    
    # Safety settings
    safety_checks: bool = True
    audit_logging: bool = True
    max_confidence_required: int = 95
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['mode'] = self.mode.value
        result['automation_level'] = self.automation_level.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuntimeConfig':
        """Create RuntimeConfig from dictionary, handling enum conversion."""
        config_data = data.copy()
        
        # Convert string values back to enums
        if isinstance(config_data.get('mode'), str):
            try:
                config_data['mode'] = OperationalMode(config_data['mode'])
            except ValueError:
                config_data['mode'] = OperationalMode.INTERACTIVE
        
        if isinstance(config_data.get('automation_level'), str):
            try:
                config_data['automation_level'] = AutomationLevel(config_data['automation_level'])
            except ValueError:
                config_data['automation_level'] = AutomationLevel.SEMI_AUTO
        
        return cls(**config_data)


class RuntimeConfigManager:
    """
    Manages runtime configuration for the Kubernetes AI Assistant.
    
    Features:
    - Runtime updates via environment variables and ConfigMaps
    - Configuration watching and hot-reloading
    - UI always remains interactive while backend can be configured
    - Thread-safe configuration updates
    """
    
    def __init__(self, config_file: str = None, watch_interval: int = 10):
        """
        Initialize the runtime configuration manager.
        
        Args:
            config_file: Path to configuration file
            watch_interval: Seconds between configuration checks
        """
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or os.getenv("K8S_AI_CONFIG_FILE", "/app/config/runtime_config.json")
        self.watch_interval = watch_interval
        
        # Thread safety
        self._lock = threading.RLock()
        self._config = RuntimeConfig()
        self._watchers = []
        self._watch_thread = None
        self._stop_watching = threading.Event()
        
        # Change notification
        self._change_callbacks: list[Callable] = []
        self._last_update = datetime.now()
        
        # Kubernetes ConfigMap paths
        self.k8s_config_paths = [
            "/etc/config/k8s-ai-config",  # Standard ConfigMap mount
            "/etc/k8s-ai/config.json",    # Alternative mount
            "/configmap/config.json"      # Another common pattern
        ]
        
        # Initialize configuration
        self._load_initial_config()
        self._start_config_watcher()
        
        self.logger.info(f"RuntimeConfigManager initialized - Mode: {self._config.mode.value}")
    
    def _load_initial_config(self):
        """Load initial configuration from all available sources."""
        with self._lock:
            # 1. Load defaults
            self._config = RuntimeConfig()
            
            # 2. Apply environment variables (highest priority for K8s)
            self._apply_env_variables()
            
            # 3. Load from file if exists
            if os.path.exists(self.config_file):
                self._load_from_file(self.config_file)
            
            # 4. Check for Kubernetes ConfigMaps
            self._load_from_k8s_configmaps()
            
            # 5. Ensure UI is always interactive
            self._config.ui_always_interactive = True
            self._config.ui_require_confirmation = True
            
            self._last_update = datetime.now()
            self.logger.info("Initial configuration loaded")
    
    def _apply_env_variables(self):
        """Apply configuration from environment variables."""
        # Mode setting
        mode_str = os.getenv("K8S_AI_MODE", self._config.mode.value).lower()
        try:
            self._config.mode = OperationalMode(mode_str)
        except ValueError:
            self.logger.warning(f"Invalid mode '{mode_str}', keeping current: {self._config.mode.value}")
        
        # Automation level
        automation_str = os.getenv("K8S_AI_AUTOMATION_LEVEL", self._config.automation_level.value)
        try:
            self._config.automation_level = AutomationLevel(automation_str)
        except ValueError:
            self.logger.warning(f"Invalid automation level '{automation_str}'")
        
        # Numeric settings
        try:
            self._config.confidence_threshold = int(os.getenv("K8S_AI_CONFIDENCE_THRESHOLD", self._config.confidence_threshold))
        except ValueError:
            self.logger.warning("Invalid confidence threshold in environment")
        
        # Boolean settings
        self._config.historical_learning = os.getenv("K8S_AI_HISTORICAL_LEARNING", "true").lower() == "true"
        self._config.predictive_analysis = os.getenv("K8S_AI_PREDICTIVE_ANALYSIS", "true").lower() == "true"
        self._config.continuous_monitoring = os.getenv("K8S_AI_CONTINUOUS_MONITORING", "false").lower() == "true"
        self._config.backend_auto_remediation = os.getenv("K8S_AI_AUTO_REMEDIATION", "false").lower() == "true"
        
        # Safety settings
        self._config.safety_checks = os.getenv("K8S_AI_SAFETY_CHECKS", "true").lower() == "true"
        self._config.audit_logging = os.getenv("K8S_AI_AUDIT_LOGGING", "true").lower() == "true"
    
    def _load_from_file(self, file_path: str):
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self._apply_config_dict(data)
                self.logger.info(f"Configuration loaded from {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to load config from {file_path}: {e}")
    
    def _load_from_k8s_configmaps(self):
        """Load configuration from Kubernetes ConfigMap mounts."""
        for config_path in self.k8s_config_paths:
            if os.path.exists(config_path):
                try:
                    # Handle both direct JSON files and key-value mounts
                    if os.path.isfile(config_path):
                        self._load_from_file(config_path)
                    elif os.path.isdir(config_path):
                        # Check for common config file names in directory
                        for filename in ["config.json", "runtime-config.json", "ai-config.json"]:
                            file_path = os.path.join(config_path, filename)
                            if os.path.exists(file_path):
                                self._load_from_file(file_path)
                                break
                except Exception as e:
                    self.logger.error(f"Failed to load K8s config from {config_path}: {e}")
    
    def _apply_config_dict(self, config_dict: Dict[str, Any]):
        """Apply configuration from dictionary."""
        try:
            # Handle mode
            if "mode" in config_dict:
                self._config.mode = OperationalMode(config_dict["mode"])
            
            # Handle automation level
            if "automation_level" in config_dict:
                self._config.automation_level = AutomationLevel(config_dict["automation_level"])
            
            # Apply other settings
            for key, value in config_dict.items():
                if hasattr(self._config, key) and key not in ["mode", "automation_level"]:
                    setattr(self._config, key, value)
            
            # Always ensure UI is interactive
            self._config.ui_always_interactive = True
            self._config.ui_require_confirmation = True
            
        except Exception as e:
            self.logger.error(f"Failed to apply config dict: {e}")
    
    def _start_config_watcher(self):
        """Start the configuration watcher thread."""
        if self._watch_thread is None:
            self._watch_thread = threading.Thread(
                target=self._config_watch_loop,
                daemon=True,
                name="ConfigWatcher"
            )
            self._watch_thread.start()
            self.logger.info("Configuration watcher started")
    
    def _config_watch_loop(self):
        """Main configuration watching loop."""
        last_check_times = {}
        
        # Initialize check times
        for path in [self.config_file] + self.k8s_config_paths:
            last_check_times[path] = 0
        
        last_env_check = 0
        
        while not self._stop_watching.is_set():
            try:
                current_time = time.time()
                config_changed = False
                
                # Check environment variables every watch_interval
                if current_time - last_env_check > self.watch_interval:
                    old_config = self._config.to_dict()
                    self._apply_env_variables()
                    if old_config != self._config.to_dict():
                        config_changed = True
                        self.logger.info("Configuration updated from environment variables")
                    last_env_check = current_time
                
                # Check file modifications
                for file_path in [self.config_file] + self.k8s_config_paths:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        try:
                            mtime = os.path.getmtime(file_path)
                            if mtime > last_check_times[file_path]:
                                old_config = self._config.to_dict()
                                self._load_from_file(file_path)
                                if old_config != self._config.to_dict():
                                    config_changed = True
                                    self.logger.info(f"Configuration updated from {file_path}")
                                last_check_times[file_path] = mtime
                        except Exception as e:
                            self.logger.debug(f"Error checking {file_path}: {e}")
                
                # Notify of changes
                if config_changed:
                    self._last_update = datetime.now()
                    self._notify_change_callbacks()
                
                time.sleep(self.watch_interval)
                
            except Exception as e:
                self.logger.error(f"Config watcher error: {e}")
                time.sleep(self.watch_interval * 2)
    
    def _notify_change_callbacks(self):
        """Notify all registered change callbacks."""
        for callback in self._change_callbacks:
            try:
                callback(self._config)
            except Exception as e:
                self.logger.error(f"Config change callback error: {e}")
    
    def register_change_callback(self, callback: Callable[[RuntimeConfig], None]):
        """
        Register a callback to be called when configuration changes.
        
        Args:
            callback: Function that accepts RuntimeConfig parameter
        """
        self._change_callbacks.append(callback)
    
    def update_config(self, **kwargs) -> bool:
        """
        Update configuration at runtime.
        
        Args:
            **kwargs: Configuration keys and values to update
            
        Returns:
            bool: True if update was successful
        """
        with self._lock:
            try:
                old_config = self._config.to_dict()
                
                # Apply updates
                for key, value in kwargs.items():
                    if key == "mode" and isinstance(value, str):
                        self._config.mode = OperationalMode(value)
                    elif key == "automation_level" and isinstance(value, str):
                        self._config.automation_level = AutomationLevel(value)
                    elif hasattr(self._config, key):
                        setattr(self._config, key, value)
                    else:
                        self.logger.warning(f"Unknown config key: {key}")
                        return False
                
                # Always ensure UI is interactive
                self._config.ui_always_interactive = True
                self._config.ui_require_confirmation = True
                
                # Save to file
                self._save_config()
                
                # Notify if changed
                if old_config != self._config.to_dict():
                    self._last_update = datetime.now()
                    self._notify_change_callbacks()
                    self.logger.info(f"Configuration updated: {kwargs}")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to update config: {e}")
                return False
    
    def _save_config(self):
        """Save current configuration to file."""
        try:
            config_data = {
                "runtime_config": self._config.to_dict(),
                "metadata": {
                    "last_update": self._last_update.isoformat(),
                    "ui_mode": "always_interactive"
                }
            }
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def get_config(self) -> RuntimeConfig:
        """Get current configuration (thread-safe)."""
        with self._lock:
            # Return a copy to prevent external modification
            return RuntimeConfig.from_dict(self._config.to_dict())
    
    def should_auto_remediate(self, confidence: int = None) -> bool:
        """
        Check if backend should auto-remediate (UI will still prompt user).
        
        Args:
            confidence: Confidence level of the proposed action
            
        Returns:
            bool: Whether backend auto-remediation is allowed
        """
        config = self.get_config()
        
        if not config.backend_auto_remediation:
            return False
        
        if confidence is not None:
            return confidence >= config.confidence_threshold
        
        return True
    
    def should_prompt_user(self) -> bool:
        """
        Check if UI should prompt user. Always returns True as requested.
        
        Returns:
            bool: Always True for interactive UI
        """
        return True
    
    def get_remediation_strategy(self) -> str:
        """
        Get the remediation strategy for UI display.
        
        Returns:
            str: Strategy description
        """
        config = self.get_config()
        
        if config.backend_auto_remediation:
            return "ui_prompt_backend_auto"  # UI prompts, backend can execute automatically
        else:
            return "ui_prompt_manual_only"   # UI prompts, manual execution only
    
    def get_mode_description(self) -> str:
        """Get human-readable description of current mode."""
        config = self.get_config()
        descriptions = {
            OperationalMode.DEBUG: "Root cause analysis and debugging (UI interactive, no auto-remediation)",
            OperationalMode.REMEDIATION: f"Issue remediation mode (UI interactive, backend {'auto' if config.backend_auto_remediation else 'manual'})",
            OperationalMode.INTERACTIVE: "Full interactive mode (UI prompts for all actions)",
            OperationalMode.MONITORING: "Monitoring and alerting mode (UI interactive dashboard)",
            OperationalMode.HYBRID: f"Adaptive hybrid mode (UI interactive, backend {'auto' if config.backend_auto_remediation else 'manual'})"
        }
        return descriptions.get(config.mode, "Unknown mode")
    
    def _get_automation_description(self) -> str:
        """Get human-readable description of current automation level."""
        config = self.get_config()
        descriptions = {
            AutomationLevel.MANUAL: "Manual execution only (user confirms all actions)",
            AutomationLevel.SEMI_AUTO: "Semi-automatic (user confirms critical actions)",
            AutomationLevel.FULL_AUTO: "Fully automatic (minimal user intervention)"
        }
        return descriptions.get(config.automation_level, "Unknown automation level")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary."""
        config = self.get_config()
        return {
            "mode": config.mode.value,
            "mode_description": self.get_mode_description(),
            "automation_level": config.automation_level.value,
            "automation_description": self._get_automation_description(),
            "ui_behavior": "always_interactive",
            "backend_auto_remediation": config.backend_auto_remediation,
            "confidence_threshold": config.confidence_threshold,
            "features": {
                "historical_learning": config.historical_learning,
                "predictive_analysis": config.predictive_analysis,
                "continuous_monitoring": config.continuous_monitoring,
                "safety_checks": config.safety_checks,
                "audit_logging": config.audit_logging
            },
            "last_update": self._last_update.isoformat(),
            "remediation_strategy": self.get_remediation_strategy()
        }
    
    def export_config(self) -> Dict[str, Any]:
        """Export configuration for backup or transfer."""
        config = self.get_config()
        return {
            "config": config.to_dict(),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "ui_mode": "always_interactive",
                "last_update": self._last_update.isoformat()
            }
        }
    
    def import_config(self, config_data: Dict[str, Any]) -> bool:
        """
        Import configuration from exported data.
        
        Args:
            config_data: Configuration data dictionary
            
        Returns:
            bool: True if import was successful
        """
        try:
            if "config" in config_data:
                return self.update_config(**config_data["config"])
            else:
                return self.update_config(**config_data)
        except Exception as e:
            self.logger.error(f"Failed to import config: {e}")
            return False
    
    def apply_mode_specific_settings(self, expert_agent=None, rag_agent=None):
        """
        Apply mode-specific settings to agent components.
        
        Args:
            expert_agent: Expert remediation agent instance
            rag_agent: RAG agent instance
        """
        config = self.get_config()
        self.logger.info(f"Applying mode-specific settings for {config.mode.value} mode")
        
        try:
            # Configure components based on operational mode
            if config.mode == OperationalMode.DEBUG:
                # Debug mode: enable detailed logging, disable auto-remediation
                if expert_agent and hasattr(expert_agent, 'set_debug_mode'):
                    expert_agent.set_debug_mode(True)
                if rag_agent and hasattr(rag_agent, 'set_debug_mode'):
                    rag_agent.set_debug_mode(True)
                    
            elif config.mode == OperationalMode.REMEDIATION:
                # Remediation mode: focus on problem solving
                if expert_agent and hasattr(expert_agent, 'set_remediation_focus'):
                    expert_agent.set_remediation_focus(True)
                    
            elif config.mode == OperationalMode.MONITORING:
                # Monitoring mode: enable continuous monitoring features
                if rag_agent and hasattr(rag_agent, 'enable_monitoring'):
                    rag_agent.enable_monitoring(True)
                    
            # Apply automation level settings
            if config.automation_level == AutomationLevel.FULL_AUTO:
                if expert_agent and hasattr(expert_agent, 'set_auto_execution'):
                    expert_agent.set_auto_execution(config.backend_auto_remediation)
                    
        except Exception as e:
            self.logger.warning(f"Some mode-specific settings could not be applied: {e}")
    
    def shutdown(self):
        """Shutdown the configuration manager."""
        self._stop_watching.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
        self.logger.info("RuntimeConfigManager shutdown complete")


# Global configuration manager instance
_global_config_manager: Optional[RuntimeConfigManager] = None
_global_lock = threading.Lock()


def get_config_manager() -> RuntimeConfigManager:
    """Get the global configuration manager instance."""
    global _global_config_manager
    
    if _global_config_manager is None:
        with _global_lock:
            if _global_config_manager is None:
                _global_config_manager = RuntimeConfigManager()
    
    return _global_config_manager


def init_with_flags(args=None) -> RuntimeConfigManager:
    """
    Initialize configuration manager with command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        RuntimeConfigManager: Configured instance
    """
    global _global_config_manager
    
    with _global_lock:
        if _global_config_manager is None:
            _global_config_manager = RuntimeConfigManager()
        
        if args:
            # Apply command line arguments
            config_updates = {}
            
            if hasattr(args, 'mode') and args.mode:
                config_updates['mode'] = args.mode
            if hasattr(args, 'automation_level') and args.automation_level:
                config_updates['automation_level'] = args.automation_level
            if hasattr(args, 'confidence_threshold') and args.confidence_threshold:
                config_updates['confidence_threshold'] = args.confidence_threshold
            if hasattr(args, 'historical_learning') and args.historical_learning:
                config_updates['historical_learning'] = args.historical_learning == 'true'
            if hasattr(args, 'predictive_analysis') and args.predictive_analysis:
                config_updates['predictive_analysis'] = args.predictive_analysis == 'true'
            if hasattr(args, 'continuous_monitoring') and args.continuous_monitoring:
                config_updates['continuous_monitoring'] = args.continuous_monitoring == 'true'
            if hasattr(args, 'auto_remediation') and args.auto_remediation:
                config_updates['backend_auto_remediation'] = args.auto_remediation == 'true'
            
            if config_updates:
                _global_config_manager.update_config(**config_updates)
    
    return _global_config_manager


# Convenience functions for compatibility
def get_current_mode() -> OperationalMode:
    """Get current operational mode."""
    return get_config_manager().get_config().mode


def can_auto_remediate(confidence: int = None) -> bool:
    """Check if auto-remediation is allowed."""
    return get_config_manager().should_auto_remediate(confidence)


def should_prompt_user() -> bool:
    """Check if user should be prompted (always True)."""
    return get_config_manager().should_prompt_user()
