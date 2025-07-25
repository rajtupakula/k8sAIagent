#!/usr/bin/env python3
"""
Container Startup Script for Kubernetes AI Agent with LLaMA Server Support

This script automatically sets up and starts the LLaMA server when the container starts.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_llama_server():
    """Setup LLaMA server if not already configured - NON-BLOCKING for production"""
    try:
        logger.info("🚀 Setting up LLaMA server (non-blocking)...")
        
        # Check if models directory exists and has content
        models_dir = Path("/opt/models")
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
            logger.info("📁 Created models directory")
        
        # Check for existing models
        gguf_files = list(models_dir.glob("*.gguf"))
        if gguf_files:
            logger.info(f"✅ Found {len(gguf_files)} existing model(s)")
            return True
        
        # CRITICAL FIX: Don't download during container startup
        # This prevents startup timeout and allows graceful degradation
        logger.info("📦 No models found - will run without LLaMA (User Guide features still available)")
        logger.info("💡 To enable LLaMA: Mount pre-downloaded models to /opt/models")
        
        # Return True to indicate system can continue without models
        return False
            
    except Exception as e:
        logger.warning(f"⚠️ LLaMA setup check failed: {e}")
        return False

def start_llama_background():
    """Start LLaMA server in background if possible - SAFE FOR PRODUCTION"""
    try:
        logger.info("🤖 Checking LLaMA server availability...")
        
        # Skip if setup_llama_server import fails
        try:
            from setup_llama_server import K8sLlamaManager
        except ImportError:
            logger.info("📦 LLaMA server module not available - continuing without LLaMA")
            return False
        
        manager = K8sLlamaManager()
        
        # Check if we have models
        try:
            models = manager.llama_manager.list_downloaded_models()
            if not models:
                logger.info("⚠️ No models available - User Guide features work without LLaMA")
                return False
        except Exception:
            logger.info("⚠️ Cannot access models - continuing with dashboard-only mode")
            return False
        
        # Start server in background (non-blocking)
        try:
            result = manager.start_server(background=True)
            if result:
                logger.info("✅ LLaMA server started successfully")
                return True
            else:
                logger.info("⚠️ LLaMA server failed to start - dashboard will work without AI")
                return False
        except Exception as e:
            logger.info(f"⚠️ LLaMA server startup failed: {e} - continuing with dashboard")
            return False
            
    except Exception as e:
        logger.info(f"⚠️ LLaMA background start failed: {e} - User Guide features still available")
        return False

def start_health_check_server():
    """Start health check server immediately for Kubernetes probes"""
    try:
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "status": "healthy",
                        "timestamp": time.time(),
                        "service": "k8s-ai-agent",
                        "version": "1.0.0"
                    }
                    self.wfile.write(json.dumps(response).encode())
                elif self.path == '/ready':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {
                        "status": "ready",
                        "timestamp": time.time(),
                        "dashboard": "available"
                    }
                    self.wfile.write(json.dumps(response).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress health check logs to reduce noise
                pass
        
        def run_health_server():
            try:
                server = HTTPServer(('0.0.0.0', 9090), HealthHandler)
                logger.info("✅ Health check server started on port 9090")
                server.serve_forever()
            except Exception as e:
                logger.error(f"❌ Health server failed: {e}")
        
        # Start health server in background thread
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
        # Give it a moment to start
        time.sleep(1)
        logger.info("🩺 Health endpoints available: /health, /ready")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start health server: {e}")
        return False

def start_main_application():
    """Start the main Streamlit application"""
    try:
        logger.info("🌟 Starting Complete Expert Kubernetes AI Agent...")
        
        # Set environment for interactive mode with User Guide features
        os.environ["K8S_AI_MODE"] = "interactive"
        os.environ["K8S_AI_LLAMA_ENABLED"] = "true"
        os.environ["K8S_AI_UI_MODE"] = "advanced"  # Enable User Guide features
        
        # Priority order for User Guide compliance:
        # 1. complete_expert_dashboard.py (has ALL User Guide features)
        # 2. ui/dashboard.py (has most User Guide features)
        # 3. Emergency fallback
        
        dashboard_options = [
            "complete_expert_dashboard.py",    # Complete User Guide implementation
            "ui/dashboard.py",                 # Enhanced dashboard with 5-tab interface
            "emergency_dashboard.py"           # Reliable fallback
        ]
        
        dashboard_path = None
        for option in dashboard_options:
            if os.path.exists(option):
                dashboard_path = option
                logger.info(f"✅ Found dashboard: {option}")
                break
        
        if not dashboard_path:
            logger.error("❌ No dashboard files found!")
            sys.exit(1)
        
        logger.info(f"🚀 Starting {dashboard_path} with full User Guide features...")
        
        # Start the selected dashboard
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            dashboard_path,
            "--server.port=8080",
            "--server.address=0.0.0.0",
            "--server.headless=true"
        ])
        
    except Exception as e:
        logger.error(f"❌ Failed to start selected dashboard: {e}")
        logger.info("🚨 Falling back to emergency dashboard...")
        try:
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", 
                "emergency_dashboard.py",
                "--server.port=8080",
                "--server.address=0.0.0.0",
                "--server.headless=true"
            ])
        except Exception as fallback_error:
            logger.error(f"❌ Emergency dashboard also failed: {fallback_error}")
            sys.exit(1)

def main():
    """Main startup sequence - PRODUCTION OPTIMIZED"""
    logger.info("🚀 Kubernetes AI Agent - Container Startup")
    logger.info("=" * 50)
    
    # Phase 0: Start health check server IMMEDIATELY for Kubernetes probes
    logger.info("Phase 0: Starting Health Check Server")
    health_started = start_health_check_server()
    if not health_started:
        logger.error("❌ Critical: Health check server failed - Kubernetes probes will fail")
        # Continue anyway as dashboard might still work
    
    # Phase 1: Safe dependency initialization
    logger.info("Phase 1: Safe Dependency Check")
    try:
        from safe_init import safe_imports
        dep_results = safe_imports()
        
        # Set environment variables based on available dependencies
        chromadb_available = dep_results.get('chromadb', {}).get('available', False)
        st_available = dep_results.get('sentence_transformers', {}).get('available', False)
        
        if chromadb_available:
            os.environ["K8S_AI_CHROMADB_ENABLED"] = "true"
        else:
            os.environ["K8S_AI_CHROMADB_ENABLED"] = "false"
            
        if st_available:
            os.environ["K8S_AI_EMBEDDINGS_ENABLED"] = "true"
        else:
            os.environ["K8S_AI_EMBEDDINGS_ENABLED"] = "false"
            
        logger.info(f"ChromaDB: {'enabled' if chromadb_available else 'disabled'}")
        logger.info(f"Embeddings: {'enabled' if st_available else 'disabled'}")
        
    except Exception as e:
        logger.warning(f"Dependency check failed: {e}")
        logger.info("Continuing with basic mode...")
        os.environ["K8S_AI_CHROMADB_ENABLED"] = "false"
        os.environ["K8S_AI_EMBEDDINGS_ENABLED"] = "false"
    
    # Phase 2: LLaMA setup (optional, non-blocking, no downloads)
    logger.info("Phase 2: LLaMA Server Check")
    llama_ready = setup_llama_server()
    
    # Phase 3: LLaMA background start (optional, non-blocking)
    if llama_ready:
        logger.info("Phase 3: Starting LLaMA Server")
        start_llama_background()
        # Don't wait - let it start in background
    else:
        logger.info("Phase 3: Skipping LLaMA (not available)")
    
    # Phase 4: Start main application (required, MUST succeed)
    logger.info("Phase 4: Starting Main Dashboard Application")
    start_main_application()

if __name__ == "__main__":
    main()
