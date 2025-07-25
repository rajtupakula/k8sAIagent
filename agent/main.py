#!/usr/bin/env python3
"""
Kubernetes AI Assistant - Main Entry Point

This is the main application that orchestrates all components:
- Kubernetes monitoring and issue detection
- RAG-based knowledge system with local LLM
- Resource forecasting and optimization
- GlusterFS health monitoring
- Automated remediation capabilities
- Web dashboard interface
- Multi-mode operation (Debug, Remediation, Interactive, Monitoring, Hybrid)
"""

import os
import sys
import logging
import asyncio
import threading
import time

# Disable telemetry before any other imports
try:
    from .telemetry_disable import disable_all_telemetry
    disable_all_telemetry()
except ImportError:
    # Fallback manual telemetry disabling
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["CHROMA_TELEMETRY"] = "False"
    os.environ["DO_NOT_TRACK"] = "1"
import signal
from datetime import datetime
from pathlib import Path

# Add current directory and parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor import KubernetesMonitor
from rag_agent import RAGAgent
from remediate import RemediationEngine
from scheduler.forecast import ResourceForecaster
from glusterfs.analyze import GlusterFSAnalyzer

# Import LlamaServerManager with graceful fallback
try:
    from scripts.llama_runner import LlamaServerManager
    LLAMA_SERVER_AVAILABLE = True
except ImportError:
    logging.debug("LlamaServerManager not available - LLM features will be disabled")
    LLAMA_SERVER_AVAILABLE = False
    LlamaServerManager = None

# Import configuration manager
try:
    from runtime_config_manager import RuntimeConfigManager, OperationalMode, init_with_flags, get_config_manager
    ConfigManager = RuntimeConfigManager
except ImportError:
    try:
        from config_manager import ConfigManager, OperationalMode, init_with_flags
    except ImportError:
        print("Warning: Configuration manager not available, using default settings")
        ConfigManager = None
        OperationalMode = None
        init_with_flags = None

class KubernetesAIAssistant:
    """Main orchestrator for the Kubernetes AI Assistant with multi-mode operation."""
    
    def __init__(self, config_file: str = None, config_manager=None):
        """
        Initialize the AI Assistant.
        
        Args:
            config_file: Optional configuration file path
            config_manager: Optional configuration manager instance
        """
        # Use provided config manager or create default
        self.config_manager = config_manager
        if not self.config_manager:
            try:
                from agent.runtime_config_manager import get_config_manager
                self.config_manager = get_config_manager()
            except Exception as e:
                print(f"Warning: Could not initialize config manager: {e}")
                self.config_manager = None
        
        self.logger = self._setup_logging()
        self.config = self._load_config(config_file)
        
        # Clean up any existing ChromaDB instances on startup
        self._cleanup_chromadb()
        
        # Initialize components
        self.monitor = None
        self.rag_agent = None
        self.remediation = None
        self.forecaster = None
        self.glusterfs = None
        self.llama_server = None
        
        # Control flags
        self.running = False
        self.monitoring_thread = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Kubernetes AI Assistant initialized")
        if self.config_manager:
            current_config = self.config_manager.get_config()
            self.logger.info(f"Mode: {current_config.mode.value}")
    
    def _cleanup_chromadb(self):
        """Clean up any existing ChromaDB instances to prevent conflicts."""
        try:
            import shutil
            data_dir = "/data"
            if os.path.exists(data_dir):
                # Find and clean up old ChromaDB instances
                for item in os.listdir(data_dir):
                    if item.startswith("chroma_db_") and os.path.isdir(os.path.join(data_dir, item)):
                        try:
                            shutil.rmtree(os.path.join(data_dir, item), ignore_errors=True)
                            print(f"Cleaned up old ChromaDB instance: {item}")
                        except Exception:
                            pass  # Ignore cleanup errors
        except Exception:
            pass  # Ignore all cleanup errors
    
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('k8s_ai_assistant.log')
            ]
        )
        return logging.getLogger(__name__)
    
    def _load_config(self, config_file: str = None) -> dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "kubernetes": {
                "config_file": None,
                "monitoring_interval": 30  # seconds
            },
            "llama": {
                "model_dir": "./models",
                "server_host": "localhost",
                "server_port": 8080,
                "default_model": "mistral-7b-instruct",
                "auto_start": True
            },
            "rag": {
                "embedding_model": "all-MiniLM-L6-v2",
                "chroma_path": "./chroma_db",
                "offline_mode": True
            },
            "forecasting": {
                "data_path": "./forecast_data",
                "forecast_interval": 3600  # 1 hour
            },
            "glusterfs": {
                "enabled": True,
                "check_interval": 300  # 5 minutes
            },
            "dashboard": {
                "enabled": True,
                "port": 8501
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                import json
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge configs (simplified - would use deep merge in production)
                default_config.update(user_config)
                self.logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                self.logger.error(f"Error loading config file: {e}")
        
        return default_config
    
    async def initialize_components(self):
        """Initialize all AI assistant components based on operational mode."""
        try:
            # Show current configuration
            if self.config_manager:
                status = self.config_manager.get_status_summary()
                self.logger.info(f"🎛️ Operational Mode: {status['mode_description']}")
                self.logger.info(f"🤖 Automation Level: {status['automation_description']}")
            
            self.logger.info("Initializing components...")
            
            # Initialize Kubernetes monitor
            self.logger.info("Initializing Kubernetes monitor...")
            self.monitor = KubernetesMonitor(
                config_file=self.config["kubernetes"]["config_file"]
            )
            
            if not self.monitor.is_connected():
                self.logger.warning("Kubernetes cluster not accessible, some features will be limited")
            
            # Initialize LLaMA server if configured and available
            if self.config["llama"]["auto_start"] and LLAMA_SERVER_AVAILABLE:
                self.logger.info("Initializing LLaMA server...")
                self.llama_server = LlamaServerManager(
                    model_dir=self.config["llama"]["model_dir"],
                    server_host=self.config["llama"]["server_host"],
                    server_port=self.config["llama"]["server_port"]
                )
                
                # Try to start with default model
                await self._start_llama_server()
            elif not LLAMA_SERVER_AVAILABLE:
                self.logger.debug("LLaMA server not available - skipping initialization")
                self.llama_server = None
            else:
                self.llama_server = None
            
            # Initialize RAG agent
            self.logger.info("Initializing RAG agent...")
            llama_endpoint = f"http://{self.config['llama']['server_host']}:{self.config['llama']['server_port']}"
            self.rag_agent = RAGAgent(
                model_name=self.config["rag"]["embedding_model"],
                chroma_path=self.config["rag"]["chroma_path"],
                llama_endpoint=llama_endpoint,
                offline_mode=self.config["rag"].get("offline_mode", True)
            )
            
            # Initialize remediation engine
            self.logger.info("Initializing remediation engine...")
            self.remediation = RemediationEngine()
            
            # Apply mode-specific configurations
            if self.config_manager and hasattr(self.rag_agent, 'expert_agent'):
                self.config_manager.apply_mode_specific_settings(
                    expert_agent=self.rag_agent.expert_agent,
                    rag_agent=self.rag_agent
                )
            
            # Configure auto-remediation based on mode
            if self.config_manager:
                auto_remediate = self.config_manager.should_auto_remediate()
                if hasattr(self.remediation, 'set_auto_mode'):
                    self.remediation.set_auto_mode(auto_remediate)
                self.logger.info(f"🔧 Auto-remediation: {'✅ Enabled' if auto_remediate else '❌ Disabled'}")
            
            # Initialize forecaster
            self.logger.info("Initializing resource forecaster...")
            self.forecaster = ResourceForecaster(
                data_path=self.config["forecasting"]["data_path"]
            )
            
            # Initialize GlusterFS analyzer if enabled
            if self.config["glusterfs"]["enabled"]:
                self.logger.info("Initializing GlusterFS analyzer...")
                self.glusterfs = GlusterFSAnalyzer()
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    async def _start_llama_server(self):
        """Start the LLaMA server with retry logic."""
        if not self.llama_server or not LLAMA_SERVER_AVAILABLE:
            return
        
        try:
            # Check if any models are downloaded
            downloaded_models = self.llama_server.list_downloaded_models()
            
            if not downloaded_models:
                self.logger.warning("No models downloaded. LLaMA server will not start.")
                self.logger.info("Run './models/download_models.sh --download mistral-7b-instruct' to download a model")
                return
            
            # Try to start with default model or first available
            model_to_use = self.config["llama"]["default_model"]
            
            # Check if default model is downloaded
            default_model_file = None
            for model_name, config in self.llama_server.model_configs.items():
                if model_name == model_to_use and config["filename"] in downloaded_models:
                    default_model_file = config["filename"]
                    break
            
            if not default_model_file:
                # Use first available model
                model_to_use = downloaded_models[0]
                self.logger.info(f"Default model not found, using {model_to_use}")
            
            result = self.llama_server.start_server(model_name=model_to_use)
            
            if result["success"]:
                self.logger.info(f"LLaMA server started successfully with model {result['model']}")
            else:
                self.logger.warning(f"Failed to start LLaMA server: {result['message']}")
                
        except Exception as e:
            self.logger.error(f"Error starting LLaMA server: {e}")
    
    def start_monitoring(self):
        """Start background monitoring tasks."""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting background monitoring...")
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Start log monitoring if Kubernetes is available
        if self.monitor and self.monitor.is_connected():
            self.monitor.start_log_monitoring()
    
    def _monitoring_loop(self):
        """Main monitoring loop that runs in background."""
        last_scan = 0
        last_forecast = 0
        last_glusterfs_check = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Scan for issues periodically
                if (current_time - last_scan) >= self.config["kubernetes"]["monitoring_interval"]:
                    if self.monitor and self.monitor.is_connected():
                        self.logger.debug("Scanning for Kubernetes issues...")
                        issues = self.monitor.scan_for_issues()
                        
                        if issues:
                            self.logger.info(f"Found {len(issues)} issues")
                            # Auto-remediate critical issues if enabled
                            self._handle_critical_issues(issues)
                        
                        # Update forecaster with current metrics
                        metrics = self.monitor.get_cluster_metrics()
                        if metrics and self.forecaster:
                            self.forecaster.add_metrics_data(metrics)
                    
                    last_scan = current_time
                
                # Generate forecasts periodically
                if (current_time - last_forecast) >= self.config["forecasting"]["forecast_interval"]:
                    if self.forecaster:
                        self.logger.debug("Generating resource forecast...")
                        self.forecaster.generate_forecast(7, "CPU")  # 7-day CPU forecast
                    
                    last_forecast = current_time
                
                # Check GlusterFS health periodically
                if (self.glusterfs and 
                    (current_time - last_glusterfs_check) >= self.config["glusterfs"]["check_interval"]):
                    self.logger.debug("Checking GlusterFS health...")
                    self.glusterfs.refresh_status()
                    last_glusterfs_check = current_time
                
                # Sleep between checks
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _handle_critical_issues(self, issues):
        """Handle critical issues with auto-remediation."""
        critical_issues = [issue for issue in issues if issue.get("severity") == "critical"]
        
        for issue in critical_issues:
            try:
                self.logger.warning(f"Critical issue detected: {issue['title']}")
                
                # Auto-remediate if safe to do so
                if self._is_safe_to_auto_remediate(issue):
                    self.logger.info(f"Attempting auto-remediation for {issue['id']}")
                    result = self.remediation.auto_remediate(issue['id'])
                    
                    if result['success']:
                        self.logger.info(f"Auto-remediation successful: {result['message']}")
                    else:
                        self.logger.warning(f"Auto-remediation failed: {result['message']}")
                else:
                    self.logger.info(f"Issue {issue['id']} requires manual intervention")
                    
            except Exception as e:
                self.logger.error(f"Error handling critical issue {issue.get('id', 'unknown')}: {e}")
    
    def _is_safe_to_auto_remediate(self, issue) -> bool:
        """Determine if an issue is safe for auto-remediation."""
        # Conservative approach - only remediate specific safe issues
        safe_patterns = [
            "pod-.*-failed",  # Failed pods can usually be safely restarted
            "container-.*-not-ready"  # Container restart issues
        ]
        
        issue_id = issue.get('id', '')
        for pattern in safe_patterns:
            import re
            if re.match(pattern, issue_id):
                return True
        
        return False
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.logger.info("Stopping monitoring...")
        self.running = False
        
        if self.monitor:
            self.monitor.stop_log_monitoring()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
    
    def start_dashboard(self):
        """Start the Streamlit dashboard."""
        if not self.config["dashboard"]["enabled"]:
            self.logger.info("Dashboard is disabled in configuration")
            return
        
        try:
            import subprocess
            import sys
            
            dashboard_port = self.config["dashboard"]["port"]
            dashboard_path = os.path.join(os.path.dirname(__file__), "..", "ui", "dashboard.py")
            
            self.logger.info(f"Starting dashboard on port {dashboard_port}...")
            
            # Ensure the dashboard path exists
            if not os.path.exists(dashboard_path):
                self.logger.error(f"Dashboard file not found: {dashboard_path}")
                return None
            
            cmd = [
                sys.executable, "-m", "streamlit", "run", 
                dashboard_path,
                "--server.port", str(dashboard_port),
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--server.enableCORS", "false",
                "--browser.gatherUsageStats", "false"
            ]
            
            # Start dashboard in background with proper error handling
            try:
                dashboard_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=dict(os.environ, STREAMLIT_BROWSER_GATHER_USAGE_STATS="False")
                )
                
                # Give it a moment to start
                time.sleep(2)
                
                # Check if process is still running
                if dashboard_process.poll() is None:
                    self.logger.info(f"Dashboard started successfully at http://0.0.0.0:{dashboard_port}")
                    return dashboard_process
                else:
                    stdout, stderr = dashboard_process.communicate()
                    self.logger.error(f"Dashboard failed to start. Error: {stderr.decode()}")
                    return None
                    
            except Exception as proc_error:
                self.logger.error(f"Failed to start dashboard process: {proc_error}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error starting dashboard: {e}")
            return None
    
    def get_status_report(self) -> dict:
        """Get comprehensive status report of all components."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "cluster_health": {},
            "recommendations": []
        }
        
        try:
            # Kubernetes status
            if self.monitor:
                report["components"]["kubernetes"] = {
                    "connected": self.monitor.is_connected(),
                    "metrics": self.monitor.get_cluster_metrics() if self.monitor.is_connected() else None
                }
                
                if self.monitor.is_connected():
                    health = self.monitor.run_health_check()
                    report["cluster_health"] = health
            
            # LLaMA server status
            if self.llama_server:
                report["components"]["llama_server"] = self.llama_server.get_server_status()
            
            # RAG agent status
            if self.rag_agent:
                report["components"]["rag_agent"] = self.rag_agent.get_knowledge_stats()
            
            # Forecaster status
            if self.forecaster:
                report["components"]["forecaster"] = {
                    "model_performance": self.forecaster.get_model_performance(),
                    "latest_forecast": bool(self.forecaster.get_latest_forecast())
                }
            
            # GlusterFS status
            if self.glusterfs:
                report["components"]["glusterfs"] = self.glusterfs.get_health_status()
            
            # Generate recommendations
            report["recommendations"] = self._generate_recommendations(report)
            
        except Exception as e:
            self.logger.error(f"Error generating status report: {e}")
            report["error"] = str(e)
        
        return report
    
    def get_status(self) -> dict:
        """Alias for get_status_report for compatibility."""
        return self.get_status_report()
    
    def _generate_recommendations(self, status_report: dict) -> list:
        """Generate recommendations based on current status."""
        recommendations = []
        
        try:
            components = status_report.get("components", {})
            
            # Kubernetes recommendations
            k8s_status = components.get("kubernetes", {})
            if not k8s_status.get("connected"):
                recommendations.append({
                    "type": "warning",
                    "component": "kubernetes",
                    "message": "Kubernetes cluster not accessible. Check connectivity and credentials."
                })
            
            # LLaMA server recommendations
            llama_status = components.get("llama_server", {})
            if not llama_status.get("running"):
                recommendations.append({
                    "type": "info",
                    "component": "llama",
                    "message": "LLaMA server is not running. Start it for enhanced AI capabilities."
                })
            elif not llama_status.get("healthy"):
                recommendations.append({
                    "type": "warning",
                    "component": "llama",
                    "message": "LLaMA server is not responding properly. Consider restarting."
                })
            
            # Cluster health recommendations
            cluster_health = status_report.get("cluster_health", {})
            if cluster_health.get("overall_status") == "critical":
                recommendations.append({
                    "type": "critical",
                    "component": "cluster",
                    "message": f"Critical cluster issues detected: {cluster_health.get('critical_count', 0)} critical issues"
                })
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
        
        return recommendations
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def shutdown(self):
        """Graceful shutdown of all components."""
        self.logger.info("Shutting down Kubernetes AI Assistant...")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Stop LLaMA server
        if self.llama_server:
            self.llama_server.stop_server()
        
        self.logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kubernetes AI Assistant")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--dashboard-only", action="store_true", help="Run only the dashboard")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip dashboard startup")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    # Multi-mode configuration arguments
    parser.add_argument("--mode", choices=["debug", "remediation", "interactive", "monitoring", "hybrid"], 
                       default="interactive", help="Operational mode")
    parser.add_argument("--automation-level", choices=["manual", "semi_auto", "full_auto"], 
                       default="semi_auto", help="Automation level")
    parser.add_argument("--confidence-threshold", type=int, default=80, 
                       help="Confidence threshold for automated actions (0-100)")
    parser.add_argument("--historical-learning", type=str, choices=["true", "false"], 
                       default="true", help="Enable historical learning")
    parser.add_argument("--predictive-analysis", type=str, choices=["true", "false"], 
                       default="true", help="Enable predictive analysis")
    parser.add_argument("--continuous-monitoring", type=str, choices=["true", "false"], 
                       default="false", help="Enable continuous monitoring")
    parser.add_argument("--auto-remediation", type=str, choices=["true", "false"], 
                       default="false", help="Enable automatic remediation")
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize configuration manager with runtime flags if available
    if ConfigManager and init_with_flags:
        config_manager = init_with_flags(args)
        current_config = config_manager.get_config()
        print(f"🎛️ Initialized in {current_config.mode.value} mode")
        print(f"📊 Configuration: {config_manager.get_mode_description()}")
    else:
        config_manager = None
        print("⚠️ Running with default configuration (config manager unavailable)")
    
    # Create AI assistant with configuration
    assistant = KubernetesAIAssistant(config_file=args.config, config_manager=config_manager)
    
    try:
        # Initialize components
        await assistant.initialize_components()
        
        if args.status:
            # Show status and exit
            status = assistant.get_status_report()
            import json
            print(json.dumps(status, indent=2))
            return
        
        if args.dashboard_only:
            # Run only dashboard
            dashboard_process = assistant.start_dashboard()
            if dashboard_process:
                try:
                    dashboard_process.wait()
                except KeyboardInterrupt:
                    dashboard_process.terminate()
            return
        
        # Start monitoring
        assistant.start_monitoring()
        
        # Start dashboard unless disabled
        dashboard_process = None
        if not args.no_dashboard:
            dashboard_process = assistant.start_dashboard()
        
        # Main loop
        assistant.logger.info("Kubernetes AI Assistant is running...")
        assistant.logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            assistant.logger.info("Received interrupt signal")
        finally:
            assistant.shutdown()
            if dashboard_process:
                dashboard_process.terminate()
    
    except Exception as e:
        assistant.logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🚀 Starting Kubernetes AI Assistant...")
    asyncio.run(main())