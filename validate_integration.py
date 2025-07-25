#!/usr/bin/env python3
"""
🧪 INTEGRATION VALIDATION SCRIPT
Tests that all new fixes are properly integrated into the container
"""

import os
import sys
import time
import requests
import subprocess
import json
from datetime import datetime

def print_status(message, status="INFO"):
    """Print colored status messages"""
    colors = {
        "INFO": "\033[94m",     # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",    # Red
        "RESET": "\033[0m"      # Reset
    }
    
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️", 
        "ERROR": "❌"
    }
    
    print(f"{colors.get(status, '')}{prefix.get(status, '')} {message}{colors['RESET']}")

def check_file_exists(filepath):
    """Check if a file exists and is readable"""
    if os.path.exists(filepath):
        print_status(f"File exists: {filepath}", "SUCCESS")
        return True
    else:
        print_status(f"File missing: {filepath}", "ERROR")
        return False

def test_port_availability(port, service_name):
    """Test if a port is available or in use"""
    try:
        result = subprocess.run(['lsof', '-i', f':{port}'], 
                              capture_output=True, text=True)
        if result.stdout:
            print_status(f"Port {port} ({service_name}) - Process found: {result.stdout.split()[1] if result.stdout.split() else 'Unknown'}", "INFO")
            return True
        else:
            print_status(f"Port {port} ({service_name}) - Available", "SUCCESS")
            return False
    except Exception as e:
        print_status(f"Port {port} check failed: {e}", "WARNING")
        return False

def test_service_health(url, service_name, timeout=5):
    """Test if a service is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print_status(f"{service_name} - Healthy (HTTP {response.status_code})", "SUCCESS")
            return True
        else:
            print_status(f"{service_name} - Unhealthy (HTTP {response.status_code})", "WARNING")
            return False
    except requests.exceptions.Timeout:
        print_status(f"{service_name} - Timeout", "WARNING")
        return False
    except requests.exceptions.ConnectionError:
        print_status(f"{service_name} - Connection refused", "ERROR")
        return False
    except Exception as e:
        print_status(f"{service_name} - Error: {e}", "ERROR")
        return False

def test_kubernetes_access():
    """Test Kubernetes API access"""
    try:
        result = subprocess.run(['kubectl', 'get', 'nodes'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            node_count = len(result.stdout.strip().split('\n')) - 1  # Subtract header
            print_status(f"Kubernetes API - Connected ({node_count} nodes)", "SUCCESS")
            return True
        else:
            print_status(f"Kubernetes API - Failed: {result.stderr}", "ERROR")
            return False
    except subprocess.TimeoutExpired:
        print_status("Kubernetes API - Timeout", "WARNING")
        return False
    except Exception as e:
        print_status(f"Kubernetes API - Error: {e}", "ERROR")
        return False

def main():
    """Main validation function"""
    print_status("🚀 Starting Kubernetes AI Agent Integration Validation", "INFO")
    print_status(f"Timestamp: {datetime.now().isoformat()}", "INFO")
    print()
    
    # 1. Check that all new files are present
    print_status("📁 Step 1: Checking file integration", "INFO")
    files_to_check = [
        'fixed_container_startup.py',
        'runtime_fixed_dashboard.py', 
        'complete_expert_dashboard.py',
        'quick_fix_integration.sh',
        'IMMEDIATE_FIX_GUIDE.md',
        'Dockerfile'
    ]
    
    all_files_present = True
    for file in files_to_check:
        if not check_file_exists(file):
            all_files_present = False
    
    if all_files_present:
        print_status("All required files are present", "SUCCESS")
    else:
        print_status("Some files are missing - container build may fail", "ERROR")
    
    print()
    
    # 2. Check port configuration
    print_status("🔌 Step 2: Checking port configuration", "INFO")
    
    # Check if ports are configured correctly
    port_8080_used = test_port_availability(8080, "LLaMA Server")
    port_8501_used = test_port_availability(8501, "Streamlit UI")
    
    print()
    
    # 3. Test service health (if running)
    print_status("🏥 Step 3: Testing service health", "INFO")
    
    llama_healthy = test_service_health("http://localhost:8080/health", "LLaMA Server")
    streamlit_healthy = test_service_health("http://localhost:8501/_stcore/health", "Streamlit UI")
    
    print()
    
    # 4. Test Kubernetes integration
    print_status("☸️ Step 4: Testing Kubernetes integration", "INFO")
    kubernetes_working = test_kubernetes_access()
    
    print()
    
    # 5. Test LLaMA integration (if available)
    print_status("🤖 Step 5: Testing LLaMA integration", "INFO")
    
    if llama_healthy:
        try:
            test_payload = {
                "prompt": "Hello",
                "max_tokens": 5,
                "temperature": 0.1
            }
            response = requests.post("http://localhost:8080/completion", 
                                   json=test_payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                print_status("LLaMA completion test - Success", "SUCCESS")
                print_status(f"Response: {result.get('content', 'No content')[:50]}...", "INFO")
            else:
                print_status(f"LLaMA completion test - Failed (HTTP {response.status_code})", "WARNING")
        except Exception as e:
            print_status(f"LLaMA completion test - Error: {e}", "WARNING")
    else:
        print_status("LLaMA server not available - skipping integration test", "WARNING")
    
    print()
    
    # 6. Generate summary report
    print_status("📊 VALIDATION SUMMARY", "INFO")
    print_status("=" * 50, "INFO")
    
    issues = []
    successes = []
    
    if all_files_present:
        successes.append("✅ All required files present")
    else:
        issues.append("❌ Missing required files")
    
    if not port_8080_used and not port_8501_used:
        successes.append("✅ Ports available for services")
    elif port_8080_used and port_8501_used:
        successes.append("✅ Services running on correct ports")
    else:
        issues.append("⚠️ Port configuration may need adjustment")
    
    if llama_healthy:
        successes.append("✅ LLaMA server responding")
    else:
        issues.append("⚠️ LLaMA server not responding")
    
    if streamlit_healthy:
        successes.append("✅ Streamlit UI responding")
    else:
        issues.append("⚠️ Streamlit UI not responding")
    
    if kubernetes_working:
        successes.append("✅ Kubernetes API accessible")
    else:
        issues.append("⚠️ Kubernetes API not accessible")
    
    # Print results
    for success in successes:
        print_status(success, "SUCCESS")
    
    for issue in issues:
        print_status(issue, "WARNING")
    
    print()
    
    # Final assessment
    if len(issues) == 0:
        print_status("🎉 VALIDATION PASSED - System ready for deployment!", "SUCCESS")
        exit_code = 0
    elif len(issues) <= 2:
        print_status("⚠️ VALIDATION PARTIAL - Some issues detected but system should work", "WARNING") 
        exit_code = 1
    else:
        print_status("❌ VALIDATION FAILED - Multiple issues need to be resolved", "ERROR")
        exit_code = 2
    
    print()
    print_status("📋 Next steps:", "INFO")
    if not all_files_present:
        print_status("• Ensure all files are copied to container during build", "INFO")
    if not llama_healthy and not streamlit_healthy:
        print_status("• Run: ./quick_fix_integration.sh", "INFO")
    if not kubernetes_working:
        print_status("• Verify running inside Kubernetes cluster or valid kubeconfig", "INFO")
    
    print_status("• Build container: docker build -t k8s-ai-agent .", "INFO")
    print_status("• Deploy: kubectl apply -f k8s/k8s-ai-agent.yaml", "INFO")
    print_status("• Access UI: http://localhost:30185 (NodePort)", "INFO")
    print_status("• Access LLaMA API: http://localhost:30180 (NodePort)", "INFO")
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
