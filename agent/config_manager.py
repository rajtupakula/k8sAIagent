#!/usr/bin/env python3
"""
Configuration Manager for Kubernetes AI Assistant

Manages different operational modes:
- DEBUG_MODE: Root cause analysis only, no remediation
- REMEDIATION_MODE: Automatic remediation when issues are detected
- INTERACTIVE_MODE: Always interactive UI with user confirmation
- MONITORING_MODE: Continuous monitoring with alerts
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

class OperationalMode(Enum):
    """Operational modes for the AI assistant."""
    DEBUG = "debug"                    # Root cause analysis only
    REMEDIATION = "remediation"        # Auto-remediation enabled
    INTERACTIVE = "interactive"        # Always interactive with user confirmation
    MONITORING = "monitoring"          # Continuous monitoring mode
    HYBRID = "hybrid"                  # Combination of modes

class AutomationLevel(Enum):
    """Automation levels for different operations."""
    MANUAL = "manual"                  # Manual approval required
    SEMI_AUTO = "semi_auto"           # Auto with confirmation
    FULL_AUTO = "full_auto"           # Fully automated

@dataclass
class ModeConfig:
    """Configuration for each operational mode."""
    auto_remediation: bool = False
    require_confirmation: bool = True
    continuous_monitoring: bool = False
    safety_checks_strict: bool = True
    log_level: str = "INFO"
    ui_interactive: bool = True
    historical_learning: bool = True
    predictive_analysis: bool = True
    audit_logging: bool = True

class ConfigManager:
    """Manages configuration and operational modes for the AI assistant."""
    
    def __init__(self, config_file: str = "/app/config/ai_assistant_config.json"):
        self.config_file = config_file
        self.current_mode = OperationalMode.INTERACTIVE
        self.automation_level = AutomationLevel.SEMI_AUTO
        
        # Default configurations for each mode
        self.mode_configs = {
            OperationalMode.DEBUG: ModeConfig(
                auto_remediation=False,
                require_confirmation=True,
                continuous_monitoring=False,
                safety_checks_strict=True,
                log_level="DEBUG",
                ui_interactive=True,
                historical_learning=True,
                predictive_analysis=True,
                audit_logging=True
            ),
            OperationalMode.REMEDIATION: ModeConfig(
                auto_remediation=True,
                require_confirmation=False,
                continuous_monitoring=True,
                safety_checks_strict=True,
                log_level="INFO",
                ui_interactive=True,
                historical_learning=True,
                predictive_analysis=True,
                audit_logging=True
            ),
            OperationalMode.INTERACTIVE: ModeConfig(
                auto_remediation=False,
                require_confirmation=True,
                continuous_monitoring=False,
                safety_checks_strict=True,
                log_level="INFO",
                ui_interactive=True,
                historical_learning=True,
                predictive_analysis=True,
                audit_logging=True
            ),
            OperationalMode.MONITORING: ModeConfig(
                auto_remediation=False,
                require_confirmation=True,
                continuous_monitoring=True,
                safety_checks_strict=True,
                log_level="WARNING",
                ui_interactive=False,
                historical_learning=True,
                predictive_analysis=True,
                audit_logging=True
            ),
            OperationalMode.HYBRID: ModeConfig(
                auto_remediation=True,
                require_confirmation=True,
                continuous_monitoring=True,
                safety_checks_strict=True,
                log_level="INFO",
                ui_interactive=True,
                historical_learning=True,
                predictive_analysis=True,
                audit_logging=True
            )
        }
        
        # Load configuration
        self.load_config()
        
        # Set up logging
        self.setup_logging()
    
    def load_config(self):
        """Load configuration from file or environment variables."""
        # Check environment variables first
        mode_env = os.getenv("AI_ASSISTANT_MODE", "interactive").lower()
        automation_env = os.getenv("AI_ASSISTANT_AUTOMATION", "semi_auto").lower()
        
        try:
            self.current_mode = OperationalMode(mode_env)
        except ValueError:
            print(f"Warning: Invalid mode '{mode_env}', defaulting to interactive")
            self.current_mode = OperationalMode.INTERACTIVE
        
        try:
            self.automation_level = AutomationLevel(automation_env)
        except ValueError:
            print(f"Warning: Invalid automation level '{automation_env}', defaulting to semi_auto")
            self.automation_level = AutomationLevel.SEMI_AUTO
        
        # Load from file if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    
                if "mode" in file_config:
                    self.current_mode = OperationalMode(file_config["mode"])
                if "automation_level" in file_config:
                    self.automation_level = AutomationLevel(file_config["automation_level"])
                    
            except Exception as e:
                print(f"Warning: Could not load config file: {e}")
        
        print(f"✅ Configuration loaded: Mode={self.current_mode.value}, Automation={self.automation_level.value}")
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config_data = {
                "mode": self.current_mode.value,
                "automation_level": self.automation_level.value,
                "last_updated": "2025-07-21T00:00:00Z"
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            print(f"✅ Configuration saved to {self.config_file}")
            
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def setup_logging(self):
        """Set up logging based on current mode."""
        config = self.get_current_config()
        
        log_level = getattr(logging, config.log_level, logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/app/logs/ai_assistant.log', mode='a')
            ]
        )
        
        # Adjust specific loggers based on mode
        if self.current_mode == OperationalMode.DEBUG:
            logging.getLogger('expert_remediation_agent').setLevel(logging.DEBUG)
            logging.getLogger('issue_history_manager').setLevel(logging.DEBUG)
        elif self.current_mode == OperationalMode.MONITORING:
            logging.getLogger('root').setLevel(logging.WARNING)
    
    def get_current_config(self) -> ModeConfig:
        """Get configuration for current mode."""
        return self.mode_configs[self.current_mode]
    
    def set_mode(self, mode: OperationalMode):
        """Set operational mode."""
        self.current_mode = mode
        self.setup_logging()
        self.save_config()
        print(f"🔄 Mode changed to: {mode.value}")
    
    def set_automation_level(self, level: AutomationLevel):
        """Set automation level."""
        self.automation_level = level
        self.save_config()
        print(f"🔄 Automation level changed to: {level.value}")
    
    def should_auto_remediate(self) -> bool:
        """Check if auto-remediation is enabled for current mode."""
        config = self.get_current_config()
        
        if self.current_mode == OperationalMode.DEBUG:
            return False  # Never auto-remediate in debug mode
        
        if self.automation_level == AutomationLevel.MANUAL:
            return False
        
        return config.auto_remediation
    
    def requires_confirmation(self) -> bool:
        """Check if user confirmation is required."""
        config = self.get_current_config()
        
        if self.automation_level == AutomationLevel.FULL_AUTO:
            return False
        
        return config.require_confirmation
    
    def is_continuous_monitoring_enabled(self) -> bool:
        """Check if continuous monitoring is enabled."""
        config = self.get_current_config()
        return config.continuous_monitoring
    
    def is_ui_interactive(self) -> bool:
        """Check if UI should be interactive."""
        config = self.get_current_config()
        return config.ui_interactive
    
    def get_mode_description(self) -> str:
        """Get description of current mode."""
        descriptions = {
            OperationalMode.DEBUG: "🔍 Debug Mode - Root cause analysis only, no remediation actions",
            OperationalMode.REMEDIATION: "🔧 Remediation Mode - Automatic issue remediation when deployed",
            OperationalMode.INTERACTIVE: "💬 Interactive Mode - Always interactive UI with user confirmation",
            OperationalMode.MONITORING: "📊 Monitoring Mode - Continuous monitoring with alerts",
            OperationalMode.HYBRID: "🔄 Hybrid Mode - Combines multiple operational capabilities"
        }
        return descriptions.get(self.current_mode, "Unknown mode")
    
    def get_automation_description(self) -> str:
        """Get description of current automation level."""
        descriptions = {
            AutomationLevel.MANUAL: "👤 Manual - All actions require explicit user approval",
            AutomationLevel.SEMI_AUTO: "🤝 Semi-Automatic - Automated with confirmation prompts",
            AutomationLevel.FULL_AUTO: "🤖 Fully Automatic - No user intervention required"
        }
        return descriptions.get(self.automation_level, "Unknown automation level")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get comprehensive status summary."""
        config = self.get_current_config()
        
        return {
            "operational_mode": self.current_mode.value,
            "automation_level": self.automation_level.value,
            "mode_description": self.get_mode_description(),
            "automation_description": self.get_automation_description(),
            "configuration": {
                "auto_remediation": config.auto_remediation,
                "require_confirmation": config.require_confirmation,
                "continuous_monitoring": config.continuous_monitoring,
                "ui_interactive": config.ui_interactive,
                "historical_learning": config.historical_learning,
                "predictive_analysis": config.predictive_analysis,
                "safety_checks_strict": config.safety_checks_strict,
                "log_level": config.log_level,
                "audit_logging": config.audit_logging
            },
            "runtime_checks": {
                "should_auto_remediate": self.should_auto_remediate(),
                "requires_confirmation": self.requires_confirmation(),
                "continuous_monitoring": self.is_continuous_monitoring_enabled(),
                "ui_interactive": self.is_ui_interactive()
            }
        }
    
    def apply_mode_specific_settings(self, expert_agent=None, rag_agent=None):
        """Apply mode-specific settings to agents."""
        config = self.get_current_config()
        
        if expert_agent:
            # Configure expert agent based on mode
            expert_agent.set_safety_mode(config.safety_checks_strict)
            
            if hasattr(expert_agent, 'history_manager') and expert_agent.history_manager:
                # Configure historical learning
                if not config.historical_learning:
                    expert_agent.history_manager = None
        
        if rag_agent:
            # Configure RAG agent
            if hasattr(rag_agent, 'offline_mode'):
                rag_agent.offline_mode = True  # Always offline for security
        
        print(f"⚙️ Applied {self.current_mode.value} mode settings to agents")

# Global configuration instance
config_manager = ConfigManager()

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager

def init_with_flags():
    """Initialize configuration from command line flags and environment."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kubernetes AI Assistant')
    parser.add_argument('--mode', choices=['debug', 'remediation', 'interactive', 'monitoring', 'hybrid'],
                       default='interactive', help='Operational mode')
    parser.add_argument('--automation', choices=['manual', 'semi_auto', 'full_auto'],
                       default='semi_auto', help='Automation level')
    parser.add_argument('--config-file', default='/app/config/ai_assistant_config.json',
                       help='Configuration file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (same as --mode debug)')
    parser.add_argument('--auto-remediate', action='store_true', help='Enable auto-remediation')
    parser.add_argument('--continuous-monitor', action='store_true', help='Enable continuous monitoring')
    
    args = parser.parse_args()
    
    # Override with command line arguments
    if args.debug:
        args.mode = 'debug'
    
    if args.auto_remediate:
        args.automation = 'full_auto'
        if args.mode == 'interactive':
            args.mode = 'remediation'
    
    # Set configuration
    global config_manager
    config_manager.config_file = args.config_file
    config_manager.set_mode(OperationalMode(args.mode))
    config_manager.set_automation_level(AutomationLevel(args.automation))
    
    return config_manager

if __name__ == "__main__":
    # Test configuration manager
    config = init_with_flags()
    
    print("\n" + "="*60)
    print("🎛️ KUBERNETES AI ASSISTANT - CONFIGURATION TEST")
    print("="*60)
    
    status = config.get_status_summary()
    
    print(f"\n📋 Current Configuration:")
    print(f"• Mode: {status['mode_description']}")
    print(f"• Automation: {status['automation_description']}")
    
    print(f"\n⚙️ Runtime Settings:")
    for key, value in status['runtime_checks'].items():
        emoji = "✅" if value else "❌"
        print(f"• {key.replace('_', ' ').title()}: {emoji} {value}")
    
    print(f"\n🔧 Configuration Details:")
    for key, value in status['configuration'].items():
        emoji = "✅" if value else "❌"
        if isinstance(value, bool):
            print(f"• {key.replace('_', ' ').title()}: {emoji} {value}")
        else:
            print(f"• {key.replace('_', ' ').title()}: {value}")
    
    print(f"\n🎯 Mode Capabilities:")
    if config.current_mode == OperationalMode.DEBUG:
        print("• Root cause analysis and investigation")
        print("• Historical pattern analysis")
        print("• Detailed logging and diagnostics")
        print("• No remediation actions (read-only)")
    elif config.current_mode == OperationalMode.REMEDIATION:
        print("• Automatic issue detection and resolution")
        print("• Continuous monitoring and alerting")
        print("• Historical learning and prediction")
        print("• Safety-validated remediation actions")
    elif config.current_mode == OperationalMode.INTERACTIVE:
        print("• User-guided troubleshooting")
        print("• Interactive UI with confirmations")
        print("• Expert recommendations with approval")
        print("• Manual control over all actions")
    
    print(f"\n✅ Configuration test completed!")
