#!/usr/bin/env python3
"""
Enhanced K8s AI Agent App with Full Functionality
"""
import os
import sys
import subprocess
import time
import threading

# Import health server
try:
    from health_server import start_health_server
except ImportError:
    # Fallback simple health server
    import json
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "time": time.time()}
            self.wfile.write(json.dumps(response).encode())
        def log_message(self, format, *args): pass
    
    def start_health_server():
        server = HTTPServer(('0.0.0.0', 9090), HealthHandler)
        server.serve_forever()

def start_streamlit():
    """Start AI-enabled Streamlit app"""
    try:
        # Use the lightweight AI dashboard as primary, fallback to others
        dashboard_options = ["lightweight_ai_dashboard.py", "ai_dashboard.py", "simple_dashboard.py"]
        dashboard_file = None
        
        for dashboard in dashboard_options:
            if os.path.exists(dashboard):
                dashboard_file = dashboard
                break
        
        if not dashboard_file:
            print("❌ No dashboard file found")
            return None
            
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            dashboard_file,
            "--server.port", "8080",
            "--server.address", "0.0.0.0",
            "--server.headless", "true"
        ]
        
        print("🚀 Starting Streamlit...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if it started
        time.sleep(5)
        if process.poll() is None:
            print("✅ Streamlit started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Streamlit failed: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return None

def main():
    """Main function - Enhanced AI Agent"""
    print("🚀 Starting Enhanced K8s AI Agent")
    print("📊 Features: Interactive AI Chat, Cluster Monitoring, Auto-Remediation")
    
    # Start health server in background
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    print("✅ Health server started on port 9090")
    
    # Start enhanced Streamlit dashboard
    streamlit_process = start_streamlit()
    
    if not streamlit_process:
        print("❌ Could not start AI dashboard, exiting")
        return 1
    
    print("🤖 AI Agent dashboard started successfully!")
    print("🌐 Access the dashboard at: http://<node-ip>:30180")
    print("🔍 Features available:")
    print("   • Interactive AI chat for troubleshooting")
    print("   • Real-time cluster health monitoring") 
    print("   • Automated issue detection and remediation")
    print("   • Expert analysis and recommendations")
    
    # Keep running and monitor
    try:
        while True:
            if streamlit_process.poll() is not None:
                print("❌ AI dashboard died, restarting...")
                streamlit_process = start_streamlit()
                if not streamlit_process:
                    break
            time.sleep(10)
    except KeyboardInterrupt:
        print("👋 Shutting down AI Agent...")
        if streamlit_process:
            streamlit_process.terminate()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
