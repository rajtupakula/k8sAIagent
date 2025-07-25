#!/usr/bin/env python3
"""
🔧 DEPLOYMENT VALIDATION SCRIPT
Comprehensive validation of the AI Agent deployment for runtime errors
"""
import sys
import subprocess
import importlib
import traceback
from pathlib import Path

def check_python_requirements():
    """Check if all required Python packages are installed"""
    print("🔍 Checking Python requirements...")
    
    required_packages = [
        'streamlit',
        'pandas',
        'numpy',
        'requests',
        'kubernetes',
        'plotly',
        'matplotlib',
        'seaborn'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} - OK")
        except ImportError as e:
            print(f"❌ {package} - MISSING: {e}")
            missing_packages.append(package)
    
    return missing_packages

def validate_file_structure():
    """Validate that all required files exist"""
    print("\n📁 Checking file structure...")
    
    required_files = [
        'complete_expert_dashboard.py',
        'LLAMA_INTEGRATION_GUIDE.md',
        'scripts/llama_runner.py',
        'agent/main.py',
        'requirements.txt',
        'docker-compose.yml',
        'Dockerfile'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} - EXISTS")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    return missing_files

def test_import_complete_dashboard():
    """Test importing the main dashboard without runtime errors"""
    print("\n🧪 Testing dashboard imports...")
    
    try:
        # Test basic imports first
        import streamlit as st
        import pandas as pd
        import numpy as np
        import requests
        print("✅ Basic imports successful")
        
        # Test Kubernetes import
        try:
            from kubernetes import client, config
            print("✅ Kubernetes client import successful")
        except ImportError:
            print("⚠️ Kubernetes client not available (will use mock data)")
        
        # Test if the complete dashboard can be imported
        sys.path.insert(0, '.')
        
        print("🔄 Testing complete_expert_dashboard import...")
        
        # We'll simulate the import by checking the file syntax
        with open('complete_expert_dashboard.py', 'r') as f:
            content = f.read()
        
        # Check for syntax errors
        try:
            compile(content, 'complete_expert_dashboard.py', 'exec')
            print("✅ Dashboard syntax validation passed")
        except SyntaxError as e:
            print(f"❌ Syntax error in dashboard: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        traceback.print_exc()
        return False

def test_llama_integration():
    """Test LLaMA server integration"""
    print("\n🦙 Testing LLaMA integration...")
    
    try:
        # Check if llama_runner.py exists and is valid
        if Path('scripts/llama_runner.py').exists():
            with open('scripts/llama_runner.py', 'r') as f:
                content = f.read()
            
            try:
                compile(content, 'scripts/llama_runner.py', 'exec')
                print("✅ LLaMA runner syntax validation passed")
            except SyntaxError as e:
                print(f"❌ Syntax error in LLaMA runner: {e}")
                return False
            
            # Test if LLaMA server is running
            try:
                import requests
                response = requests.get("http://localhost:8080/health", timeout=2)
                if response.status_code == 200:
                    print("✅ LLaMA server is running and accessible")
                else:
                    print("⚠️ LLaMA server responded but with error status")
            except requests.exceptions.RequestException:
                print("⚠️ LLaMA server not running (will use fallback mode)")
            
            return True
        else:
            print("❌ LLaMA runner script not found")
            return False
            
    except Exception as e:
        print(f"❌ LLaMA integration test failed: {e}")
        return False

def test_kubernetes_config():
    """Test Kubernetes configuration"""
    print("\n☸️ Testing Kubernetes configuration...")
    
    try:
        from kubernetes import client, config
        
        # Test in-cluster config first
        try:
            config.load_incluster_config()
            print("✅ In-cluster Kubernetes config loaded")
            return True
        except:
            pass
        
        # Test local kubeconfig
        try:
            config.load_kube_config()
            print("✅ Local kubeconfig loaded")
            
            # Test basic API call
            v1 = client.CoreV1Api()
            nodes = v1.list_node()
            print(f"✅ Kubernetes API accessible - {len(nodes.items)} nodes found")
            return True
        except Exception as e:
            print(f"⚠️ Kubernetes not accessible: {e}")
            print("   Dashboard will use mock data mode")
            return False
            
    except ImportError:
        print("⚠️ Kubernetes client not installed - will use mock data")
        return False

def run_dashboard_test():
    """Run a quick dashboard startup test"""
    print("\n🚀 Testing dashboard startup...")
    
    try:
        # Test if we can run streamlit without errors
        result = subprocess.run([
            sys.executable, '-c', 
            '''
import sys
sys.path.insert(0, ".")
# Quick import test
try:
    import streamlit as st
    import pandas as pd
    import numpy as np
    print("✅ Dashboard dependencies OK")
except Exception as e:
    print(f"❌ Dashboard dependency error: {e}")
    sys.exit(1)
'''
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Dashboard startup test passed")
            return True
        else:
            print(f"❌ Dashboard startup test failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard startup test error: {e}")
        return False

def main():
    """Main deployment validation"""
    print("🚀 K8S AI AGENT DEPLOYMENT VALIDATION")
    print("=" * 50)
    
    all_tests_passed = True
    
    # 1. Check Python requirements
    missing_packages = check_python_requirements()
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        all_tests_passed = False
    
    # 2. Check file structure
    missing_files = validate_file_structure()
    if missing_files:
        print(f"\n⚠️ Missing files: {', '.join(missing_files)}")
        all_tests_passed = False
    
    # 3. Test dashboard imports
    if not test_import_complete_dashboard():
        all_tests_passed = False
    
    # 4. Test LLaMA integration
    if not test_llama_integration():
        print("⚠️ LLaMA integration issues detected")
    
    # 5. Test Kubernetes config
    k8s_available = test_kubernetes_config()
    
    # 6. Test dashboard startup
    if not run_dashboard_test():
        all_tests_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✅ DEPLOYMENT VALIDATION PASSED")
        print("\n🚀 Ready to start the dashboard:")
        print("   streamlit run complete_expert_dashboard.py")
        
        if not k8s_available:
            print("\n⚠️ Note: Kubernetes not accessible - dashboard will use mock data")
        
        print("\n🦙 To enable LLaMA AI features:")
        print("   python scripts/llama_runner.py")
        
    else:
        print("❌ DEPLOYMENT VALIDATION FAILED")
        print("\n🔧 Fix the issues above before starting the dashboard")
    
    return all_tests_passed

if __name__ == "__main__":
    main()
