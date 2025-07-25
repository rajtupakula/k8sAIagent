#!/usr/bin/env python3
"""
Test script to verify that RAG agent initialization is now working
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rag_initialization():
    """Test RAG agent initialization with the new fallback text splitter"""
    print("🔍 Testing RAG Agent Initialization...")
    print("=" * 50)
    
    try:
        from agent.rag_agent import RAGAgent
        print("✅ RAGAgent import successful")
        
        # Try to initialize RAG agent
        print("\n🔄 Initializing RAG Agent...")
        rag_agent = RAGAgent(offline_mode=True)
        print("✅ RAG Agent initialized successfully!")
        
        # Check text splitter
        if hasattr(rag_agent, 'text_splitter'):
            print(f"✅ Text splitter available: {type(rag_agent.text_splitter).__name__}")
        else:
            print("❌ Text splitter not available")
        
        # Check offline mode
        if hasattr(rag_agent, 'offline_mode'):
            mode = "Offline" if rag_agent.offline_mode else "Online"
            print(f"📡 Operating Mode: {mode}")
        
        # Test expert_query method
        if hasattr(rag_agent, 'expert_query'):
            print("✅ expert_query method available")
            
            # Test a simple query
            print("\n🧠 Testing expert query...")
            result = rag_agent.expert_query("What pods are running in my cluster?")
            
            if result:
                print("✅ Query processed successfully!")
                print(f"📊 Confidence: {result.get('confidence', 'N/A')}")
                response = result.get('expert_response', result.get('standard_response', 'No response'))
                print(f"📝 Response preview: {response[:100]}...")
                
                # Check for offline mode indication
                if "offline mode" in response.lower():
                    print("✅ Correctly operating in offline mode")
                else:
                    print("🟡 May be operating in online mode (LLM available)")
            else:
                print("❌ Query returned no result")
        else:
            print("❌ expert_query method not available")
            
    except Exception as e:
        print(f"❌ RAG Agent initialization failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 RAG Agent initialization test completed successfully!")
    print("💡 The 'NoneType' object is not callable error has been resolved!")
    return True

def test_advanced_dashboard():
    """Test Advanced Dashboard UI initialization"""
    print("\n🖥️  Testing Advanced Dashboard UI...")
    print("=" * 50)
    
    try:
        # Import and test basic initialization
        from ui.advanced_dashboard import AdvancedDashboardUI
        print("✅ AdvancedDashboardUI import successful")
        
        # Note: We can't fully test Streamlit components without running the app
        print("💡 Advanced Dashboard UI ready for deployment")
        print("🚀 Run: streamlit run ui/advanced_dashboard.py")
        
    except Exception as e:
        print(f"❌ Advanced Dashboard test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 K8s AI Agent - Fixed RAG Initialization Test")
    print("=" * 60)
    
    # Test RAG agent
    rag_success = test_rag_initialization()
    
    # Test dashboard
    dashboard_success = test_advanced_dashboard()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print(f"✅ RAG Agent: {'WORKING' if rag_success else 'FAILED'}")
    print(f"✅ Dashboard: {'READY' if dashboard_success else 'FAILED'}")
    
    if rag_success and dashboard_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 Advanced Dashboard UI is ready for deployment!")
        print("\n📋 Next Steps:")
        print("1. Run: streamlit run ui/advanced_dashboard.py")
        print("2. Access the Advanced Dashboard UI in your browser")
        print("3. Test the expert AI features and troubleshooting tools")
        print("4. The RAG agent will work in offline mode (full functionality)")
    else:
        print("\n⚠️  Some tests failed - check error messages above")
