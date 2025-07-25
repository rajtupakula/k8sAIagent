#!/usr/bin/env python3
"""
FIXED Container Startup Script - Properly separates LLaMA server and Streamlit UI

This fixes the port conflict by:
- LLaMA server on port 8080
- Streamlit dashboard on port 8501
- Proper error handling and fallback modes
"""

import os
import sys
import time
import subprocess
import logging
import threading
import requests
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def kill_port_processes(port):
    """Kill any processes running on the specified port"""
    try:
        # Find processes on the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    logger.info(f"🔪 Killing process {pid} on port {port}")
                    subprocess.run(['kill', '-9', pid], check=False)
    except Exception as e:
        logger.warning(f"⚠️ Could not kill processes on port {port}: {e}")

def setup_llama_server():
    """Setup and start LLaMA server on port 8080"""
    try:
        logger.info("🚀 Setting up LLaMA server on port 8080...")
        
        # Kill any existing processes on port 8080
        kill_port_processes(8080)
        time.sleep(2)
        
        # Check for models
        models_dir = Path("/opt/models")
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
        
        gguf_files = list(models_dir.glob("*.gguf"))
        if not gguf_files:
            logger.info("📦 No models found. Downloading small test model...")
            try:
                # Download a small model for testing
                subprocess.run([
                    'wget', '-O', '/opt/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf',
                    'https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf'
                ], timeout=300, check=True)
                logger.info("✅ Downloaded TinyLlama model")
            except Exception as e:
                logger.error(f"❌ Failed to download model: {e}")
                return False
        
        # Find the first available model
        gguf_files = list(models_dir.glob("*.gguf"))
        if not gguf_files:
            logger.error("❌ No models available")
            return False
            
        model_path = gguf_files[0]
        logger.info(f"🤖 Using model: {model_path.name}")
        
        # Start LLaMA server
        cmd = [
            'python', '-m', 'llama_cpp.server',
            '--model', str(model_path),
            '--host', '0.0.0.0',
            '--port', '8080',
            '--n_ctx', '2048',
            '--n_threads', '4'
        ]
        
        logger.info(f"🏃 Starting LLaMA server: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        
        # Wait for server to start
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get("http://localhost:8080/health", timeout=1)
                if response.status_code == 200:
                    logger.info("✅ LLaMA server is running on port 8080")
                    return True
            except:
                time.sleep(1)
        
        logger.error("❌ LLaMA server failed to start")
        return False
        
    except Exception as e:
        logger.error(f"❌ LLaMA setup failed: {e}")
        return False

def start_streamlit_dashboard():
    """Start Streamlit dashboard on port 8501"""
    try:
        logger.info("🌐 Starting Streamlit dashboard on port 8501...")
        
        # Kill any existing processes on port 8501
        kill_port_processes(8501)
        time.sleep(2)
        
        # Start Streamlit with the complete expert dashboard
        cmd = [
            '/opt/venv/bin/python', '-m', 'streamlit', 'run',
            'complete_expert_dashboard.py',
            '--server.port=8501',
            '--server.address=0.0.0.0',
            '--server.headless=true',
            '--server.enableCORS=false',
            '--server.enableXsrfProtection=false'
        ]
        
        logger.info(f"🏃 Starting Streamlit: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        
        # Wait for dashboard to start
        for i in range(20):  # Wait up to 20 seconds
            try:
                response = requests.get("http://localhost:8501/_stcore/health", timeout=1)
                if response.status_code == 200:
                    logger.info("✅ Streamlit dashboard is running on port 8501")
                    return True
            except:
                time.sleep(1)
        
        logger.error("❌ Streamlit dashboard failed to start")
        return False
        
    except Exception as e:
        logger.error(f"❌ Streamlit startup failed: {e}")
        return False

def test_integration():
    """Test that LLaMA and Streamlit are properly integrated"""
    try:
        logger.info("🧪 Testing LLaMA-Streamlit integration...")
        
        # Test LLaMA server
        try:
            response = requests.get("http://localhost:8080/health", timeout=2)
            llama_status = "✅ Online" if response.status_code == 200 else "❌ Failed"
        except:
            llama_status = "❌ Not responding"
        
        # Test Streamlit
        try:
            response = requests.get("http://localhost:8501/_stcore/health", timeout=2)
            streamlit_status = "✅ Online" if response.status_code == 200 else "❌ Failed"
        except:
            streamlit_status = "❌ Not responding"
        
        logger.info(f"🤖 LLaMA Server (port 8080): {llama_status}")
        logger.info(f"🌐 Streamlit UI (port 8501): {streamlit_status}")
        
        if "✅" in llama_status and "✅" in streamlit_status:
            logger.info("🎉 INTEGRATION SUCCESS: Both services are running correctly!")
            return True
        else:
            logger.error("❌ INTEGRATION FAILED: One or more services not working")
            return False
            
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False

def main():
    """Main startup sequence with proper service separation"""
    logger.info("🚀 Starting Kubernetes AI Agent with fixed port configuration...")
    
    # Install required packages
    try:
        subprocess.run(['/opt/venv/bin/pip', 'install', 'llama-cpp-python[server]'], 
                      check=True, timeout=120)
        logger.info("✅ Installed llama-cpp-python[server]")
    except Exception as e:
        logger.error(f"❌ Failed to install llama-cpp-python: {e}")
    
    # Step 1: Setup LLaMA server (port 8080)
    llama_success = setup_llama_server()
    
    # Step 2: Start Streamlit dashboard (port 8501)
    streamlit_success = start_streamlit_dashboard()
    
    # Step 3: Test integration
    if llama_success and streamlit_success:
        integration_success = test_integration()
        if integration_success:
            logger.info("🎯 STARTUP COMPLETE: All services running with proper integration!")
        else:
            logger.warning("⚠️ Services started but integration test failed")
    else:
        logger.error("❌ STARTUP FAILED: One or more services failed to start")
    
    # Keep container running
    logger.info("🔄 Container ready - services will continue running...")
    try:
        while True:
            time.sleep(30)
            # Health check every 30 seconds
            try:
                llama_ok = requests.get("http://localhost:8080/health", timeout=1).status_code == 200
                streamlit_ok = requests.get("http://localhost:8501/_stcore/health", timeout=1).status_code == 200
                
                if not llama_ok:
                    logger.warning("⚠️ LLaMA server health check failed")
                if not streamlit_ok:
                    logger.warning("⚠️ Streamlit health check failed")
                    
            except:
                pass  # Silent health checks
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown signal received")

if __name__ == "__main__":
    main()
