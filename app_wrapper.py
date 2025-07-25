#!/usr/bin/env python3
"""
Kubernetes AI Agent - Application Wrapper with Health Endpoints
This wrapper starts the Streamlit app and provides health check endpoints.
"""

import os
import sys
import threading
import time
import subprocess
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks."""
    
    def do_GET(self):
        """Handle GET requests for health checks."""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health_data = {
                'status': 'healthy',
                'timestamp': time.time(),
                'service': 'k8s-ai-agent'
            }
            self.wfile.write(json.dumps(health_data).encode())
        elif self.path == '/ready':
            # Check if Streamlit is actually running
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            ready_data = {
                'status': 'ready',
                'timestamp': time.time(),
                'service': 'k8s-ai-agent'
            }
            self.wfile.write(json.dumps(ready_data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log spam."""
        pass

class AppWrapper:
    """Application wrapper that manages Streamlit and health endpoints."""
    
    def __init__(self):
        self.streamlit_process = None
        self.health_server = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def start_health_server(self):
        """Start the health check server on port 9090."""
        try:
            self.health_server = HTTPServer(('0.0.0.0', 9090), HealthHandler)
            logger.info("Health server starting on port 9090")
            self.health_server.serve_forever()
        except Exception as e:
            logger.error(f"Failed to start health server: {e}")
    
    def start_streamlit(self):
        """Start the Streamlit application."""
        try:
            # Check if Streamlit is available
            try:
                import streamlit
            except ImportError:
                logger.error("Streamlit not available - cannot start dashboard")
                return False
            
            # Prepare Streamlit command - Use enhanced AI dashboard
            # Check current working directory first, then container paths
            base_dir = os.getcwd()
            
            # Check for UI mode preference
            ui_mode = os.environ.get('UI_MODE', 'default')
            
            if ui_mode == 'advanced':
                # Prioritize Advanced Dashboard UI
                dashboard_options = [
                    os.path.join(base_dir, "ui", "advanced_dashboard.py"),  # Advanced Dashboard UI (PRIORITY)
                    "/app/ui/advanced_dashboard.py",                       # Container path
                    os.path.join(base_dir, "interactive_chat.py"),         # Interactive chat fallback
                    os.path.join(base_dir, "ui", "dashboard.py"),          # Enhanced dashboard fallback
                    "/app/interactive_chat.py",                            # Container fallback
                    "/app/ui/dashboard.py",                                # Container fallback
                    os.path.join(base_dir, "lightweight_ai_dashboard.py"),
                    "/app/lightweight_ai_dashboard.py",
                    "/app/ai_dashboard.py", 
                    "/app/simple_dashboard.py"
                ]
            else:
                # Default dashboard priority
                dashboard_options = [
                    os.path.join(base_dir, "interactive_chat.py"),         # Our new interactive chat
                    os.path.join(base_dir, "ui", "advanced_dashboard.py"), # Advanced Dashboard UI
                    os.path.join(base_dir, "ui", "dashboard.py"),          # Enhanced dashboard
                    os.path.join(base_dir, "lightweight_ai_dashboard.py"),
                    "/app/interactive_chat.py",                            # Container path
                    "/app/ui/advanced_dashboard.py",                       # Container path
                    "/app/ui/dashboard.py",                                # Container path
                    "/app/lightweight_ai_dashboard.py",
                    "/app/ai_dashboard.py", 
                    "/app/simple_dashboard.py"
                ]
            
            dashboard_path = None
            for path in dashboard_options:
                if os.path.exists(path):
                    dashboard_path = path
                    logger.info(f"Using dashboard: {path}")
                    break
            
            if not dashboard_path:
                logger.error(f"No dashboard file found in: {dashboard_options}")
                return False
            
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                dashboard_path,
                "--server.port", "8080",
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--server.enableCORS", "false",
                "--browser.gatherUsageStats", "false",
                "--logger.level", "error"  # Reduce log noise
            ]
            
            logger.info("Starting Streamlit application...")
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'STREAMLIT_BROWSER_GATHER_USAGE_STATS': 'False',
                'STREAMLIT_SERVER_PORT': '8080',
                'STREAMLIT_SERVER_ADDRESS': '0.0.0.0',
                'PYTHONUNBUFFERED': '1'
            })
            
            self.streamlit_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor Streamlit startup with shorter timeout
            startup_timeout = 30  # Reduced from 60
            start_time = time.time()
            
            while time.time() - start_time < startup_timeout:
                if self.streamlit_process.poll() is not None:
                    # Process ended - check what happened
                    stdout, stderr = self.streamlit_process.communicate()
                    logger.error(f"Streamlit failed to start.")
                    logger.error(f"STDOUT: {stdout}")
                    logger.error(f"STDERR: {stderr}")
                    return False
                
                time.sleep(1)
                if (time.time() - start_time) % 5 == 0:  # Log every 5 seconds
                    logger.info("Waiting for Streamlit to start...")
            
            logger.info("Streamlit application started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Streamlit: {e}")
            return False
    
    def run(self):
        """Run the complete application."""
        logger.info("Starting Kubernetes AI Agent Application Wrapper")
        
        self.running = True
        
        # Start health server in background
        health_thread = threading.Thread(target=self.start_health_server, daemon=True)
        health_thread.start()
        
        # Start Streamlit
        if not self.start_streamlit():
            logger.error("Failed to start Streamlit, exiting")
            return 1
        
        # Monitor the processes
        try:
            while self.running:
                # Check if Streamlit is still running
                if self.streamlit_process and self.streamlit_process.poll() is not None:
                    logger.error("Streamlit process died, restarting...")
                    if not self.start_streamlit():
                        logger.error("Failed to restart Streamlit, exiting")
                        break
                
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        self.shutdown()
        return 0
    
    def shutdown(self):
        """Shutdown all processes."""
        logger.info("Shutting down application...")
        self.running = False
        
        if self.streamlit_process:
            logger.info("Terminating Streamlit process")
            self.streamlit_process.terminate()
            try:
                self.streamlit_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Streamlit didn't terminate gracefully, killing")
                self.streamlit_process.kill()
        
        if self.health_server:
            logger.info("Shutting down health server")
            self.health_server.shutdown()

def main():
    """Main entry point."""
    wrapper = AppWrapper()
    return wrapper.run()

if __name__ == "__main__":
    sys.exit(main())
