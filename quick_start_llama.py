#!/usr/bin/env python3
"""
Quick Start LLaMA Server - Expert Solution
Get the LLaMA server running immediately for interactive K8s troubleshooting
"""
import os
import sys
import subprocess
import requests
import time
import json
from pathlib import Path

class QuickLlamaSetup:
    def __init__(self):
        self.models_dir = Path("./models")
        self.models_dir.mkdir(exist_ok=True)
        
        # Small, fast model for immediate testing
        self.quick_model = {
            "name": "phi-2",
            "url": "https://huggingface.co/microsoft/phi-2-gguf/resolve/main/phi-2.Q4_K_M.gguf",
            "size": "1.8GB",
            "file": "phi-2.Q4_K_M.gguf"
        }
        
        # Production model for full capabilities  
        self.production_model = {
            "name": "mistral-7b-instruct",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
            "size": "4.1GB", 
            "file": "mistral-7b-instruct-v0.1.Q4_K_M.gguf"
        }
        
    def check_server_status(self):
        """Check if LLaMA server is running"""
        try:
            response = requests.get("http://localhost:8080/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def download_model(self, model_info, force=False):
        """Download a model if not exists"""
        model_path = self.models_dir / model_info["file"]
        
        if model_path.exists() and not force:
            print(f"✅ Model {model_info['name']} already exists")
            return str(model_path)
        
        print(f"📥 Downloading {model_info['name']} ({model_info['size']})...")
        print(f"🔗 URL: {model_info['url']}")
        
        try:
            import urllib.request
            urllib.request.urlretrieve(model_info['url'], model_path)
            print(f"✅ Downloaded {model_info['name']}")
            return str(model_path)
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    def start_server(self, model_path, background=True):
        """Start LLaMA server with model"""
        if self.check_server_status():
            print("✅ LLaMA server already running!")
            return True
        
        print(f"🚀 Starting LLaMA server with model: {model_path}")
        
        # llama.cpp server command
        cmd = [
            sys.executable, "-m", "llama_cpp.server",
            "--model", model_path,
            "--host", "localhost", 
            "--port", "8080",
            "--n_ctx", "4096",
            "--verbose"
        ]
        
        try:
            if background:
                # Start in background
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Wait for server to start
                print("⏳ Waiting for server to start...")
                for i in range(30):
                    time.sleep(2)
                    if self.check_server_status():
                        print("✅ LLaMA server started successfully!")
                        return True
                    print(f"   Checking... ({i+1}/30)")
                
                print("❌ Server failed to start within timeout")
                return False
            else:
                # Start in foreground for debugging
                subprocess.run(cmd)
                return True
                
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def test_server(self):
        """Test server with a simple query"""
        if not self.check_server_status():
            print("❌ Server not running")
            return False
        
        print("🧪 Testing server...")
        
        try:
            test_data = {
                "prompt": "Hello! Respond with 'LLaMA server is working for K8s troubleshooting!'",
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(
                "http://localhost:8080/v1/completions",
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("choices", [{}])[0].get("text", "")
                print(f"✅ Server response: {text.strip()}")
                return True
            else:
                print(f"❌ Server error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def quick_setup(self):
        """Quick setup for immediate use"""
        print("🚀 Quick LLaMA Setup for K8s AI Agent")
        print("=" * 50)
        
        # Check if server already running
        if self.check_server_status():
            print("✅ LLaMA server already running!")
            if self.test_server():
                print("🎉 Ready to use! Go to your dashboard.")
                return True
        
        # Download quick model first for immediate testing
        print("\n📦 Setting up quick model for immediate use...")
        model_path = self.download_model(self.quick_model)
        
        if not model_path:
            print("❌ Failed to download model")
            return False
        
        # Start server
        if self.start_server(model_path):
            if self.test_server():
                print("\n🎉 SUCCESS! LLaMA server is ready!")
                print("💡 Go to your dashboard - it should now show 'LLaMA Server Online'")
                print("💬 You can now chat with the AI for K8s troubleshooting!")
                return True
        
        return False
    
    def production_setup(self):
        """Setup production model"""
        print("🏭 Setting up production model...")
        model_path = self.download_model(self.production_model)
        
        if model_path:
            print("✅ Production model ready")
            print("🔄 Restart server with: python quick_start_llama.py --restart-production")
        
    def stop_server(self):
        """Stop LLaMA server"""
        print("🛑 Stopping LLaMA server...")
        try:
            # Find and kill llama processes
            result = subprocess.run(["pkill", "-f", "llama_cpp.server"], capture_output=True)
            time.sleep(2)
            
            if not self.check_server_status():
                print("✅ LLaMA server stopped")
                return True
            else:
                print("⚠️ Server may still be running")
                return False
        except Exception as e:
            print(f"❌ Error stopping server: {e}")
            return False

def main():
    setup = QuickLlamaSetup()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            setup.quick_setup()
        elif sys.argv[1] == "--production":
            setup.production_setup()
        elif sys.argv[1] == "--stop":
            setup.stop_server()
        elif sys.argv[1] == "--status":
            if setup.check_server_status():
                print("✅ LLaMA server is running")
                setup.test_server()
            else:
                print("❌ LLaMA server is offline")
        elif sys.argv[1] == "--restart-production":
            setup.stop_server()
            time.sleep(3)
            prod_model = setup.models_dir / setup.production_model["file"]
            if prod_model.exists():
                setup.start_server(str(prod_model))
            else:
                print("❌ Production model not found")
        else:
            print("Usage: python quick_start_llama.py [--quick|--production|--stop|--status]")
    else:
        # Default: quick setup
        setup.quick_setup()

if __name__ == "__main__":
    main()
