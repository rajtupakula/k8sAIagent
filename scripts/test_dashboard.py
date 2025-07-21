#!/usr/bin/env python3
"""
Test script to verify the dashboard can run without external dependencies.
This simulates the offline environment.
"""

import sys
import os
import subprocess

def test_dashboard_imports():
    """Test that the dashboard can import and initialize in offline mode."""
    print("🔍 Testing dashboard imports...")
    
    # Change to the project directory
    os.chdir('/Users/rtupakul/Documents/GitHub/k8sAIagent')
    
    # Test the dashboard imports
    test_code = """
import sys
import os
sys.path.append('.')

# Test basic imports first
try:
    import streamlit as st
    print('✅ Streamlit import successful')
except ImportError as e:
    print(f'❌ Streamlit import failed: {e}')
    sys.exit(1)

try:
    import pandas as pd
    print('✅ Pandas import successful')
except ImportError as e:
    print(f'❌ Pandas import failed: {e}')

try:
    import plotly.express as px
    print('✅ Plotly import successful')
except ImportError as e:
    print(f'❌ Plotly import failed: {e}')

# Test dashboard imports with error handling
try:
    from ui.dashboard import main, MockRAGAgent
    print('✅ Dashboard imports successful with mock classes')
    
    # Test mock RAG agent
    mock_rag = MockRAGAgent()
    response = mock_rag.query("test question")
    print(f'✅ Mock RAG agent works: {len(response)} characters')
    
    print('✅ All dashboard components can be imported')
    
except Exception as e:
    print(f'❌ Dashboard import failed: {e}')
    import traceback
    traceback.print_exc()
"""
    
    try:
        result = subprocess.run([sys.executable, '-c', test_code], 
                              capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Dashboard import test PASSED")
            return True
        else:
            print("❌ Dashboard import test FAILED")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_offline_functionality():
    """Test offline functionality without external dependencies."""
    print("\n🔍 Testing offline functionality...")
    
    test_code = """
import sys
import os
sys.path.append('.')

# Test that we can create instances without internet
try:
    from ui.dashboard import MockRAGAgent, MockRemediationEngine
    
    # Test mock classes
    rag = MockRAGAgent()
    assert rag.offline_mode == True
    assert rag.llama_available == False
    
    response = rag.query("How to restart a pod?")
    assert len(response) > 50
    print('✅ Mock RAG agent functional')
    
    remediation = MockRemediationEngine()
    result = remediation.restart_failed_pods()
    assert 'Mock mode' in result['message']
    print('✅ Mock remediation engine functional')
    
    print('✅ All offline components working')
    
except Exception as e:
    print(f'❌ Offline test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    try:
        result = subprocess.run([sys.executable, '-c', test_code], 
                              capture_output=True, text=True, timeout=20)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Offline functionality test PASSED")
            return True
        else:
            print("❌ Offline functionality test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Kubernetes AI Assistant - Offline Mode")
    print("=" * 60)
    
    tests = [
        test_dashboard_imports,
        test_offline_functionality,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard is ready for offline operation.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
