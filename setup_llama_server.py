#!/usr/bin/env python3
"""
LLaMA Server Setup and Manager for K8s AI Agent
Sets up and manages LLaMA server for live commands and remediation
"""
import os
import sys
import subprocess
import time
import logging
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.llama_runner import LlamaServerManager

class K8sLlamaManager:
    """K8s AI Agent LLaMA Server Manager"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent
        self.models_dir = self.project_root / "models"
        
        # Create LLaMA server manager
        self.llama_manager = LlamaServerManager(
            model_dir=str(self.models_dir),
            server_host="localhost",
            server_port=8080,
            context_size=4096
        )
        
        # Recommended models for K8s troubleshooting
        self.recommended_models = [
            "mistral-7b-instruct",  # Best for technical tasks
            "codellama-7b-instruct",  # Good for code and commands
            "llama-2-7b-chat"  # General purpose
        ]
    
    def check_requirements(self):
        """Check if llama-cpp-python is installed"""
        print("🔍 Checking LLaMA requirements...")
        
        try:
            import llama_cpp
            print("✅ llama-cpp-python is installed")
            return True
        except ImportError:
            print("❌ llama-cpp-python not found")
            print("📦 Installing llama-cpp-python...")
            
            try:
                # Install with CUDA support if available
                if self._check_cuda():
                    cmd = ["pip", "install", "llama-cpp-python[cuda]", "--upgrade", "--force-reinstall", "--no-cache-dir"]
                else:
                    cmd = ["pip", "install", "llama-cpp-python", "--upgrade"]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ llama-cpp-python installed successfully")
                    return True
                else:
                    print(f"❌ Failed to install llama-cpp-python: {result.stderr}")
                    return False
            except Exception as e:
                print(f"❌ Error installing llama-cpp-python: {e}")
                return False
    
    def _check_cuda(self):
        """Check if CUDA is available"""
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def setup_models(self):
        """Download recommended models"""
        print("\n🤖 Setting up LLaMA models for K8s AI Agent...")
        
        # Check available space
        available_space = self._get_available_space()
        required_space = 12  # GB (3 models × ~4GB each)
        
        if available_space < required_space:
            print(f"⚠️  Warning: Only {available_space:.1f}GB available, need ~{required_space}GB")
            print("Consider downloading only one model")
        
        # List available models
        available_models = self.llama_manager.list_available_models()
        downloaded_models = self.llama_manager.list_downloaded_models()
        
        print(f"\n📚 Available models:")
        for name, config in available_models.items():
            status = "✅ Downloaded" if any(config["filename"] in d for d in downloaded_models) else "⬇️  Available"
            print(f"  • {name}: {config['description']} ({config['size']}) - {status}")
        
        # Download recommended model if none exist
        if not downloaded_models:
            print(f"\n📥 Downloading recommended model: {self.recommended_models[0]}")
            result = self.llama_manager.download_model(self.recommended_models[0])
            
            if result["success"]:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")
                return False
        else:
            print(f"\n✅ Found {len(downloaded_models)} downloaded models")
        
        return True
    
    def _get_available_space(self):
        """Get available disk space in GB"""
        try:
            stat = os.statvfs(self.models_dir.parent)
            available_bytes = stat.f_bavail * stat.f_frsize
            return available_bytes / (1024**3)  # Convert to GB
        except:
            return float('inf')  # If we can't check, assume unlimited
    
    def start_server(self, model_name=None):
        """Start LLaMA server"""
        print("\n🚀 Starting LLaMA Server...")
        
        if not model_name:
            # Use first available model
            downloaded = self.llama_manager.list_downloaded_models()
            if not downloaded:
                print("❌ No models available. Please download a model first.")
                return False
            
            # Prefer recommended models
            for rec_model in self.recommended_models:
                for downloaded_model in downloaded:
                    if rec_model in downloaded_model:
                        model_name = rec_model
                        break
                if model_name:
                    break
            
            if not model_name:
                # Use first available
                model_name = downloaded[0].replace('.gguf', '').replace('.Q4_K_M', '')
        
        print(f"🤖 Starting server with model: {model_name}")
        result = self.llama_manager.start_server(model_name=model_name)
        
        if result["success"]:
            print(f"✅ {result['message']}")
            print(f"🌐 Server URL: {result['url']}")
            print(f"🧠 Model: {result['model']}")
            
            # Test the server
            print("\n🧪 Testing server...")
            if self._test_server():
                print("✅ Server is responding correctly")
                return True
            else:
                print("❌ Server test failed")
                return False
        else:
            print(f"❌ {result['message']}")
            return False
    
    def _test_server(self):
        """Test if server is responding"""
        try:
            test_result = self.llama_manager.query_model(
                "Hello, are you working?",
                max_tokens=50,
                temperature=0.1
            )
            return test_result["success"]
        except Exception as e:
            self.logger.error(f"Server test failed: {e}")
            return False
    
    def stop_server(self):
        """Stop LLaMA server"""
        print("\n🛑 Stopping LLaMA Server...")
        result = self.llama_manager.stop_server()
        print(f"{'✅' if result['success'] else '❌'} {result['message']}")
        return result["success"]
    
    def get_status(self):
        """Get server status"""
        return self.llama_manager.get_server_status()
    
    def interactive_setup(self):
        """Interactive setup process"""
        print("🚀 K8s AI Agent - LLaMA Server Setup")
        print("=" * 50)
        
        # Check requirements
        if not self.check_requirements():
            print("\n❌ Failed to install requirements")
            return False
        
        # Setup models
        if not self.setup_models():
            print("\n❌ Failed to setup models")
            return False
        
        # Ask user if they want to start server
        start_server = input("\n🚀 Start LLaMA server now? (y/n): ").lower().strip()
        if start_server in ['y', 'yes']:
            if self.start_server():
                print("\n🎉 LLaMA Server is ready!")
                print("💡 You can now use the Advanced Dashboard with full AI capabilities")
                print("🌐 Run: streamlit run ui/advanced_dashboard.py")
                
                # Keep server running
                try:
                    print("\n⏳ Server running... Press Ctrl+C to stop")
                    while True:
                        time.sleep(1)
                        status = self.get_status()
                        if not status.get("running"):
                            print("🛑 Server has stopped")
                            break
                except KeyboardInterrupt:
                    print("\n🛑 Stopping server...")
                    self.stop_server()
                    print("👋 Goodbye!")
            else:
                print("\n❌ Failed to start server")
                return False
        else:
            print("\n💡 You can start the server later with:")
            print("   python setup_llama_server.py --start")
        
        return True

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="K8s AI Agent LLaMA Server Manager")
    parser.add_argument("--start", action="store_true", help="Start LLaMA server")
    parser.add_argument("--stop", action="store_true", help="Stop LLaMA server")
    parser.add_argument("--status", action="store_true", help="Show server status")
    parser.add_argument("--setup", action="store_true", help="Run interactive setup")
    parser.add_argument("--model", help="Specific model to use")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    manager = K8sLlamaManager()
    
    if args.setup or (not args.start and not args.stop and not args.status):
        # Default to interactive setup
        manager.interactive_setup()
    elif args.start:
        if manager.check_requirements():
            manager.start_server(args.model)
        else:
            print("❌ Requirements not met. Run --setup first")
    elif args.stop:
        manager.stop_server()
    elif args.status:
        status = manager.get_status()
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
