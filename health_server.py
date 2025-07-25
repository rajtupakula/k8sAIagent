#!/usr/bin/env python3
"""
Health endpoints for Kubernetes probes
"""
import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_health_response()
        elif self.path == '/ready':
            self.send_ready_response()
        elif self.path == '/metrics':
            self.send_metrics_response()
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_health_response(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - getattr(self.server, 'start_time', time.time()),
            "version": "1.0.0"
        }
        self.wfile.write(json.dumps(response).encode())
    
    def send_ready_response(self):
        """Readiness check endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Check if required components are available
        ready = True
        checks = {}
        
        # Check if AI dashboard is available
        try:
            import streamlit
            checks['streamlit'] = 'ok'
        except ImportError:
            checks['streamlit'] = 'unavailable'
            ready = False
        
        # Check if agent directory exists
        checks['agent_directory'] = 'ok' if os.path.exists('agent') else 'missing'
        
        response = {
            "status": "ready" if ready else "not_ready",
            "timestamp": time.time(),
            "checks": checks
        }
        self.wfile.write(json.dumps(response).encode())
    
    def send_metrics_response(self):
        """Metrics endpoint for monitoring"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        # Basic metrics in Prometheus format
        uptime = time.time() - getattr(self.server, 'start_time', time.time())
        metrics = f"""# HELP app_uptime_seconds Application uptime in seconds
# TYPE app_uptime_seconds counter
app_uptime_seconds {uptime}

# HELP app_health_status Application health status (1=healthy, 0=unhealthy)  
# TYPE app_health_status gauge
app_health_status 1

# HELP app_ready_status Application readiness status (1=ready, 0=not_ready)
# TYPE app_ready_status gauge
app_ready_status 1
"""
        self.wfile.write(metrics.encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def start_health_server(port=9090):
    """Start health server on specified port"""
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        server.start_time = time.time()
        print(f"✅ Health server started on port {port}")
        print(f"   Health endpoint: http://0.0.0.0:{port}/health")
        print(f"   Ready endpoint: http://0.0.0.0:{port}/ready")
        print(f"   Metrics endpoint: http://0.0.0.0:{port}/metrics")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Health server failed: {e}")

if __name__ == "__main__":
    # Can be run standalone for testing
    start_health_server()
