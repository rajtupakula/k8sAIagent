#!/usr/bin/env python3
"""
LLaMA.cpp Server Runner and Management Script

This script provides functionality to:
1. Download and manage GGUF models
2. Start/stop llama.cpp server
3. Provide API interface for the AI agent
4. Monitor server health and performance
"""

import os
import sys
import subprocess
import requests
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading
import signal

class LlamaServerManager:
    """Manage llama.cpp server instance and model operations."""
    
    def __init__(self, 
                 model_dir: str = "./models",
                 server_host: str = "localhost",
                 server_port: int = 8080,
                 context_size: int = 4096,
                 threads: int = None):
        """
        Initialize LLaMA server manager.
        
        Args:
            model_dir: Directory to store GGUF models
            server_host: Host to bind server to
            server_port: Port for server
            context_size: Context window size
            threads: Number of threads (auto-detect if None)
        """
        self.logger = logging.getLogger(__name__)
        self.model_dir = Path(model_dir)
        self.server_host = server_host
        self.server_port = server_port
        self.context_size = context_size
        self.threads = threads or os.cpu_count()
        
        self.server_process = None
        self.current_model = None
        self.server_url = f"http://{server_host}:{server_port}"
        
        # Ensure model directory exists
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Default model configurations
        self.model_configs = {
            "llama-2-7b-chat": {
                "url": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf",
                "filename": "llama-2-7b-chat.Q4_K_M.gguf",
                "size": "3.8GB",
                "description": "LLaMA 2 7B Chat model, 4-bit quantized"
            },
            "codellama-7b-instruct": {
                "url": "https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf", 
                "filename": "codellama-7b-instruct.Q4_K_M.gguf",
                "size": "3.8GB",
                "description": "Code Llama 7B Instruct model, 4-bit quantized"
            },
            "mistral-7b-instruct": {
                "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf",
                "filename": "mistral-7b-instruct-v0.1.Q4_K_M.gguf", 
                "size": "3.8GB",
                "description": "Mistral 7B Instruct model, 4-bit quantized"
            }
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def list_available_models(self) -> Dict[str, Any]:
        """List all available model configurations."""
        return self.model_configs
    
    def list_downloaded_models(self) -> List[str]:
        """List all downloaded GGUF models."""
        try:
            gguf_files = list(self.model_dir.glob("*.gguf"))
            return [f.name for f in gguf_files]
        except Exception as e:
            self.logger.error(f"Error listing downloaded models: {e}")
            return []
    
    def download_model(self, model_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Download a GGUF model.
        
        Args:
            model_name: Name of model to download
            force: Force re-download if model exists
            
        Returns:
            Dict with success status and message
        """
        if model_name not in self.model_configs:
            return {
                "success": False,
                "message": f"Unknown model: {model_name}. Available: {list(self.model_configs.keys())}"
            }
        
        config = self.model_configs[model_name]
        model_path = self.model_dir / config["filename"]
        
        # Check if already downloaded
        if model_path.exists() and not force:
            return {
                "success": True,
                "message": f"Model {model_name} already downloaded",
                "path": str(model_path)
            }
        
        try:
            self.logger.info(f"Downloading {model_name} ({config['size']})...")
            
            # Download with progress
            response = requests.get(config["url"], stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded % (100 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size * 100) if total_size > 0 else 0
                            self.logger.info(f"Downloaded {downloaded / (1024*1024):.1f}MB ({progress:.1f}%)")
            
            self.logger.info(f"Successfully downloaded {model_name}")
            return {
                "success": True,
                "message": f"Successfully downloaded {model_name}",
                "path": str(model_path)
            }
            
        except Exception as e:
            self.logger.error(f"Error downloading {model_name}: {e}")
            # Clean up partial download
            if model_path.exists():
                model_path.unlink()
            return {
                "success": False,
                "message": f"Failed to download {model_name}: {str(e)}"
            }
    
    def start_server(self, model_name: str = None, model_path: str = None) -> Dict[str, Any]:
        """
        Start llama.cpp server with specified model.
        
        Args:
            model_name: Name of predefined model to use
            model_path: Direct path to GGUF model file
            
        Returns:
            Dict with success status and message
        """
        if self.server_process and self.server_process.poll() is None:
            return {
                "success": False,
                "message": "Server is already running"
            }
        
        # Determine model path
        if model_path:
            model_file = Path(model_path)
        elif model_name:
            if model_name not in self.model_configs:
                return {
                    "success": False,
                    "message": f"Unknown model: {model_name}"
                }
            model_file = self.model_dir / self.model_configs[model_name]["filename"]
        else:
            # Use first available downloaded model
            downloaded = self.list_downloaded_models()
            if not downloaded:
                return {
                    "success": False, 
                    "message": "No models downloaded. Please download a model first."
                }
            model_file = self.model_dir / downloaded[0]
        
        if not model_file.exists():
            return {
                "success": False,
                "message": f"Model file not found: {model_file}"
            }
        
        try:
            # Check if llama.cpp server is available
            server_cmd = self._find_llama_server()
            if not server_cmd:
                return {
                    "success": False,
                    "message": "llama.cpp server not found. Please install llama-cpp-python or build from source."
                }
            
            # Build server command
            cmd = [
                server_cmd,
                "--model", str(model_file),
                "--host", self.server_host,
                "--port", str(self.server_port),
                "--ctx-size", str(self.context_size),
                "--threads", str(self.threads),
                "--verbose"
            ]
            
            self.logger.info(f"Starting llama.cpp server: {' '.join(cmd)}")
            
            # Start server process
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait for server to start
            if self._wait_for_server_start(timeout=60):
                self.current_model = model_file.name
                self.logger.info(f"Server started successfully with model {self.current_model}")
                return {
                    "success": True,
                    "message": f"Server started with model {self.current_model}",
                    "url": self.server_url,
                    "model": self.current_model
                }
            else:
                self.stop_server()
                return {
                    "success": False,
                    "message": "Server failed to start within timeout period"
                }
                
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            return {
                "success": False,
                "message": f"Failed to start server: {str(e)}"
            }
    
    def stop_server(self) -> Dict[str, Any]:
        """Stop the llama.cpp server."""
        try:
            if not self.server_process:
                return {
                    "success": True,
                    "message": "Server is not running"
                }
            
            self.logger.info("Stopping llama.cpp server...")
            
            # Try graceful shutdown first
            self.server_process.terminate()
            
            # Wait up to 10 seconds for graceful shutdown
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown fails
                self.server_process.kill()
                self.server_process.wait()
            
            self.server_process = None
            self.current_model = None
            
            self.logger.info("Server stopped successfully")
            return {
                "success": True,
                "message": "Server stopped successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
            return {
                "success": False,
                "message": f"Error stopping server: {str(e)}"
            }
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get current server status."""
        try:
            if not self.server_process:
                return {
                    "running": False,
                    "message": "Server is not started"
                }
            
            # Check if process is still alive
            if self.server_process.poll() is not None:
                return {
                    "running": False,
                    "message": "Server process has terminated",
                    "exit_code": self.server_process.returncode
                }
            
            # Try to ping the server
            try:
                response = requests.get(f"{self.server_url}/health", timeout=5)
                if response.status_code == 200:
                    return {
                        "running": True,
                        "healthy": True,
                        "model": self.current_model,
                        "url": self.server_url,
                        "pid": self.server_process.pid
                    }
                else:
                    return {
                        "running": True,
                        "healthy": False,
                        "message": f"Server responded with status {response.status_code}"
                    }
            except requests.exceptions.RequestException:
                return {
                    "running": True,
                    "healthy": False,
                    "message": "Server is not responding to health check"
                }
                
        except Exception as e:
            self.logger.error(f"Error checking server status: {e}")
            return {
                "running": False,
                "error": str(e)
            }
    
    def query_model(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Query the running model with a prompt.
        
        Args:
            prompt: Text prompt for the model
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dict with response or error
        """
        try:
            status = self.get_server_status()
            if not status.get("running") or not status.get("healthy"):
                return {
                    "success": False,
                    "message": "Server is not running or healthy"
                }
            
            # Prepare request
            payload = {
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 500),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "stop": kwargs.get("stop", []),
                "stream": False
            }
            
            response = requests.post(
                f"{self.server_url}/completion",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("content", ""),
                    "tokens": result.get("tokens_predicted", 0),
                    "model": self.current_model
                }
            else:
                return {
                    "success": False,
                    "message": f"Server error: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            self.logger.error(f"Error querying model: {e}")
            return {
                "success": False,
                "message": f"Query failed: {str(e)}"
            }
    
    def _find_llama_server(self) -> Optional[str]:
        """Find llama.cpp server executable."""
        # Try common locations and names
        candidates = [
            "llama-server",  # From llama-cpp-python
            "server",       # From llama.cpp build
            "./llama.cpp/server",
            "/usr/local/bin/llama-server",
            "/opt/llama.cpp/server"
        ]
        
        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "--help"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return candidate
            except:
                continue
        
        # Try to use python -m llama_cpp.server
        try:
            result = subprocess.run(
                [sys.executable, "-m", "llama_cpp.server", "--help"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return f"{sys.executable} -m llama_cpp.server"
        except:
            pass
        
        return None
    
    def _wait_for_server_start(self, timeout: int = 60) -> bool:
        """Wait for server to start and become healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.server_process.poll() is not None:
                # Process has terminated
                return False
            
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
        
        return False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_server()
        sys.exit(0)


def main():
    """Main CLI interface for llama.cpp server management."""
    parser = argparse.ArgumentParser(description="LLaMA.cpp Server Manager")
    parser.add_argument("--model-dir", default="./models", help="Directory for models")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--threads", type=int, help="Number of threads")
    parser.add_argument("--context-size", type=int, default=4096, help="Context window size")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List models command
    list_parser = subparsers.add_parser("list", help="List available and downloaded models")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("model", help="Model name to download")
    download_parser.add_argument("--force", action="store_true", help="Force re-download")
    
    # Start server command
    start_parser = subparsers.add_parser("start", help="Start llama.cpp server")
    start_parser.add_argument("--model", help="Model name to use")
    start_parser.add_argument("--model-path", help="Direct path to model file")
    
    # Stop server command
    stop_parser = subparsers.add_parser("stop", help="Stop llama.cpp server")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get server status")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the model")
    query_parser.add_argument("prompt", help="Prompt to send to model")
    query_parser.add_argument("--temperature", type=float, default=0.7, help="Temperature")
    query_parser.add_argument("--max-tokens", type=int, default=500, help="Max tokens")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create manager
    manager = LlamaServerManager(
        model_dir=args.model_dir,
        server_host=args.host,
        server_port=args.port,
        threads=args.threads,
        context_size=args.context_size
    )
    
    # Execute command
    if args.command == "list":
        print("Available models:")
        for name, config in manager.list_available_models().items():
            print(f"  {name}: {config['description']} ({config['size']})")
        
        print("\nDownloaded models:")
        downloaded = manager.list_downloaded_models()
        if downloaded:
            for model in downloaded:
                print(f"  {model}")
        else:
            print("  None")
    
    elif args.command == "download":
        result = manager.download_model(args.model, force=args.force)
        print(result["message"])
        if not result["success"]:
            sys.exit(1)
    
    elif args.command == "start":
        result = manager.start_server(model_name=args.model, model_path=args.model_path)
        print(result["message"])
        if result["success"]:
            print(f"Server URL: {result['url']}")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
                    status = manager.get_server_status()
                    if not status.get("running"):
                        print("Server has stopped")
                        break
            except KeyboardInterrupt:
                print("\nShutting down...")
                manager.stop_server()
        else:
            sys.exit(1)
    
    elif args.command == "stop":
        result = manager.stop_server()
        print(result["message"])
    
    elif args.command == "status":
        status = manager.get_server_status()
        print(json.dumps(status, indent=2))
    
    elif args.command == "query":
        result = manager.query_model(
            args.prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        if result["success"]:
            print(f"Response: {result['response']}")
            print(f"Tokens: {result['tokens']}")
        else:
            print(f"Error: {result['message']}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()