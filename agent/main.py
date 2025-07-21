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
"""

import os
import sys
import logging
import asyncio
import threading
import time
import signal
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor import KubernetesMonitor
from rag_agent import RAGAgent
from remediate import RemediationEngine
from scheduler.forecast import ResourceForecaster
from glusterfs.analyze import GlusterFSAnalyzer
from scripts.llama_runner import LlamaServerManager

class KubernetesAIAssistant:
    """Main orchestrator for the Kubernetes AI Assistant."""
    
    def __init__(self, config_file: str = None):
        """
        Initialize the AI Assistant.
        
        Args:
            config_file: Optional configuration file path
        """
        self.logger = self._setup_logging()
        self.config = self._load_config(config_file)
        
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
        """Initialize all AI assistant components."""
        try:
            self.logger.info("Initializing components...")
            
            # Initialize Kubernetes monitor
            self.logger.info("Initializing Kubernetes monitor...")
            self.monitor = KubernetesMonitor(
                config_file=self.config["kubernetes"]["config_file"]
            )
            
            if not self.monitor.is_connected():
                self.logger.warning("Kubernetes cluster not accessible, some features will be limited")
            
            # Initialize LLaMA server if configured
            if self.config["llama"]["auto_start"]:
                self.logger.info("Initializing LLaMA server...")
                self.llama_server = LlamaServerManager(
                    model_dir=self.config["llama"]["model_dir"],
                    server_host=self.config["llama"]["server_host"],
                    server_port=self.config["llama"]["server_port"]
                )
                
                # Try to start with default model
                await self._start_llama_server()
            
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
        if not self.llama_server:
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
            
            cmd = [
                sys.executable, "-m", "streamlit", "run", 
                dashboard_path,
                "--server.port", str(dashboard_port),
                "--server.address", "0.0.0.0"
            ]
            
            # Start dashboard in background
            dashboard_process = subprocess.Popen(cmd)
            
            self.logger.info(f"Dashboard started at http://localhost:{dashboard_port}")
            return dashboard_process
            
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
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create AI assistant
    assistant = KubernetesAIAssistant(config_file=args.config)
    
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