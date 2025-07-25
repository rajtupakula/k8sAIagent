#!/usr/bin/env python3
"""
Container Startup Script for Kubernetes AI Agent with LLaMA Serv        # Set environment for         # Set environment for interactive mode with User Guide features
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
        import subprocess
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            dashboard_path,
            "--server.port=8080",
            "--server.address=0.0.0.0",
            "--server.headless=true"
        ])s script automatically sets up and starts the LLaMA server when the container starts.
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
    """Setup LLaMA server if not already configured"""
    try:
        logger.info("🚀 Setting up LLaMA server...")
        
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
        
        # Download a small model for immediate functionality
        logger.info("📦 No models found, downloading compact model...")
        
        # Import and use the setup system
        try:
            from setup_llama_server import K8sLlamaManager
            manager = K8sLlamaManager()
            
            # Download the smallest, fastest model for container use
            success = manager.llama_manager.download_model("mistral-7b-instruct")
            if success:
                logger.info("✅ Model download completed")
                return True
            else:
                logger.warning("⚠️ Model download failed, will run without LLaMA")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ LLaMA setup failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error setting up LLaMA server: {e}")
        return False

def start_llama_background():
    """Start LLaMA server in background if possible"""
    try:
        logger.info("🤖 Starting LLaMA server in background...")
        
        from setup_llama_server import K8sLlamaManager
        manager = K8sLlamaManager()
        
        # Check if we have models
        models = manager.llama_manager.list_downloaded_models()
        if not models:
            logger.warning("⚠️ No models available, skipping LLaMA server start")
            return False
        
        # Start server in background
        result = manager.start_server(background=True)
        if result:
            logger.info("✅ LLaMA server started successfully")
            return True
        else:
            logger.warning("⚠️ LLaMA server failed to start")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ Could not start LLaMA server: {e}")
        return False

def start_main_application():
    """Start the main Streamlit application"""
    try:
        logger.info("🌟 Starting Complete Expert Kubernetes AI Agent...")
        
        # Set environment for interactive mode
        os.environ["K8S_AI_MODE"] = "interactive"
        os.environ["K8S_AI_LLAMA_ENABLED"] = "true"
        
        # Always use the complete expert dashboard (no ChromaDB dependencies)
        logger.info("� Starting Complete Expert Dashboard with all User Guide features...")
        import subprocess
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            dashboard_path,
            "--server.port=8080",
            "--server.address=0.0.0.0",
            "--server.headless=true"
        ])
        
    except Exception as e:
        logger.error(f"❌ Failed to start complete dashboard: {e}")
        logger.info("🚨 Falling back to emergency dashboard...")
        try:
            import subprocess
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
    """Main startup sequence"""
    logger.info("🚀 Kubernetes AI Agent - Container Startup")
    logger.info("=" * 50)
    
    # Phase 0: Safe dependency initialization
    logger.info("Phase 0: Safe Dependency Check")
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
    
    # Phase 1: Setup LLaMA (optional, non-blocking)
    logger.info("Phase 1: LLaMA Server Setup")
    llama_ready = setup_llama_server()
    
    if llama_ready:
        # Phase 2: Start LLaMA server (optional, non-blocking)
        logger.info("Phase 2: Starting LLaMA Server")
        start_llama_background()
        time.sleep(3)  # Give it a moment to start
    
    # Phase 3: Start main application (required)
    logger.info("Phase 3: Starting Main Application")
    start_main_application()

if __name__ == "__main__":
    main()
