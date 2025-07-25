#!/usr/bin/env python3
"""
Simple Python-based entrypoint to avoid shell GLIBC issues
"""
import os
import sys
import subprocess
import signal
import time

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entrypoint logic"""
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Starting Kubernetes AI Agent")
    
    # Ensure we're running as k8s-agent user
    try:
        import pwd
        current_user = pwd.getpwuid(os.getuid()).pw_name
        print(f"Running as user: {current_user}")
    except:
        print("Running with current user")
    
    # Create required directories
    required_dirs = ['/data', '/var/log/k8s-ai-agent']
    for dir_path in required_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"Ensured directory exists: {dir_path}")
        except Exception as e:
            print(f"Warning: Could not create {dir_path}: {e}")
    
    # Run startup validation
    print("🔍 Running startup validation...")
    try:
        result = subprocess.run([sys.executable, "validate_startup.py"], 
                               capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ Startup validation failed: {result.stderr}")
            return 1
        else:
            print("✅ Startup validation passed")
    except Exception as e:
        print(f"❌ Startup validation error: {e}")
        return 1
    
    # Start the main application
    print("🎯 Starting main application...")
    try:
        # Start app wrapper which handles both Streamlit and health endpoints
        process = subprocess.Popen([sys.executable, "app_wrapper.py"])
        
        # Wait for the process
        while True:
            try:
                exit_code = process.wait()
                print(f"Application exited with code: {exit_code}")
                return exit_code
            except KeyboardInterrupt:
                print("Received interrupt, shutting down...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                return 0
                
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
