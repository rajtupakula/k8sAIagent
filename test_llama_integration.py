#!/usr/bin/env python3
"""
Test LLaMA Server Integration
Verifies that the LLaMA server can be used for live K8s troubleshooting
"""
import sys
import os
import time
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_llama_server():
    """Test LLaMA server functionality"""
    print("🔬 Testing LLaMA Server Integration")
    print("=" * 40)
    
    # Test 1: Server health check
    print("1. 🏥 Checking server health...")
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is healthy")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server not responding: {e}")
        print("   💡 Start server with: python3 setup_llama_server.py --start")
        return False
    
    # Test 2: Basic query
    print("2. 🧪 Testing basic query...")
    try:
        test_payload = {
            "prompt": "Hello, are you working correctly?",
            "max_tokens": 30,
            "temperature": 0.1
        }
        
        response = requests.post(
            "http://localhost:8080/v1/completions",
            json=test_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("choices", [{}])[0].get("text", "")
            print(f"   ✅ Response: {response_text.strip()}")
        else:
            print(f"   ❌ Query failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return False
    
    # Test 3: Kubernetes-specific query
    print("3. 🚢 Testing Kubernetes query...")
    try:
        k8s_payload = {
            "prompt": "What kubectl command shows all pods in all namespaces?",
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        response = requests.post(
            "http://localhost:8080/v1/completions",
            json=k8s_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("choices", [{}])[0].get("text", "")
            print(f"   ✅ K8s Response: {response_text.strip()}")
        else:
            print(f"   ❌ K8s query failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ K8s query failed: {e}")
        return False
    
    # Test 4: RAG Agent integration
    print("4. 🤖 Testing RAG Agent integration...")
    try:
        from agent.rag_agent import RAGAgent
        
        # Create RAG agent without forcing offline mode
        rag_agent = RAGAgent(offline_mode=False)
        
        if hasattr(rag_agent, 'llama_available') and rag_agent.llama_available:
            print("   ✅ RAG Agent can connect to LLaMA server")
            
            # Test expert query
            result = rag_agent.expert_query("Test LLaMA integration", auto_remediate=False)
            if result and result.get('confidence', 0) > 0:
                print(f"   ✅ Expert query successful (confidence: {result.get('confidence', 0):.1%})")
            else:
                print("   ⚠️  Expert query returned low confidence")
        else:
            print("   ❌ RAG Agent cannot connect to LLaMA server")
            print(f"   📊 Offline mode: {getattr(rag_agent, 'offline_mode', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"   ❌ RAG Agent test failed: {e}")
        return False
    
    print("\n🎉 All tests passed! LLaMA server is ready for live commands and remediation.")
    return True

def test_dashboard_integration():
    """Test dashboard integration"""
    print("\n🖥️  Testing Dashboard Integration")
    print("=" * 40)
    
    try:
        from ui.advanced_dashboard import AdvancedDashboardUI
        
        # Create dashboard instance
        dashboard = AdvancedDashboardUI()
        
        # Check agent status
        if dashboard.rag_agent and hasattr(dashboard.rag_agent, 'llama_available'):
            if dashboard.rag_agent.llama_available:
                print("✅ Dashboard RAG agent connected to LLaMA server")
            else:
                print("⚠️  Dashboard RAG agent in offline mode")
        else:
            print("❌ Dashboard RAG agent not properly initialized")
            return False
        
        # Test server status check
        server_status = dashboard._check_llama_server_status()
        if server_status.get("running"):
            print("✅ Dashboard can detect running LLaMA server")
        else:
            print("❌ Dashboard cannot detect LLaMA server")
            return False
        
        print("✅ Dashboard integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 K8s AI Agent - LLaMA Server Integration Test")
    print("=" * 50)
    
    # Test server
    server_ok = test_llama_server()
    
    if server_ok:
        # Test dashboard integration
        dashboard_ok = test_dashboard_integration()
        
        if dashboard_ok:
            print("\n🎉 SUCCESS: LLaMA server integration is working perfectly!")
            print("\n📋 Next Steps:")
            print("1. Start Advanced Dashboard: streamlit run ui/advanced_dashboard.py")
            print("2. Look for 'AI Agent Active (Online Mode)' status")
            print("3. Try asking complex Kubernetes questions in the chat")
            print("4. Use the expert action buttons for live remediation")
            print("\n💡 The system is now capable of:")
            print("   • Live command generation and execution")
            print("   • Context-aware troubleshooting")
            print("   • Automated remediation workflows")
            print("   • Real-time AI-powered analysis")
        else:
            print("\n⚠️  Server works but dashboard integration has issues")
    else:
        print("\n❌ LLaMA server is not available")
        print("\n🔧 To fix this:")
        print("1. Run: python3 setup_llama_server.py --setup")
        print("2. Or: ./start_llama.sh")
        print("3. Wait for model download and server startup")
        print("4. Run this test again")

if __name__ == "__main__":
    main()
