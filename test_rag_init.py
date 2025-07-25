#!/usr/bin/env python3
"""
Test RAG Agent Initialization - Diagnostic Script
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_rag_initialization():
    """Test RAG agent initialization to identify the exact issue"""
    print("🔍 Testing RAG Agent Initialization...")
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from agent.rag_agent import RAGAgent
        print("✅ RAGAgent import successful")
        
        from agent.expert_remediation_agent import ExpertRemediationAgent
        print("✅ ExpertRemediationAgent import successful")
        
        # Test Expert Agent initialization first
        print("\n🔧 Testing Expert Agent initialization...")
        expert_agent = ExpertRemediationAgent()
        print("✅ Expert Agent initialized successfully")
        
        # Test RAG Agent initialization with detailed error catching
        print("\n🤖 Testing RAG Agent initialization...")
        try:
            rag_agent = RAGAgent(offline_mode=True)
            print("✅ RAG Agent initialized successfully")
            
            # Test a basic method call
            print("\n🔍 Testing basic method calls...")
            if hasattr(rag_agent, 'expert_query'):
                print("✅ expert_query method available")
                
                # Try a simple query
                test_result = rag_agent.expert_query("test query", auto_remediate=False)
                if test_result is not None:
                    print("✅ expert_query returned result")
                    print(f"   Result type: {type(test_result)}")
                    print(f"   Keys: {list(test_result.keys()) if isinstance(test_result, dict) else 'N/A'}")
                else:
                    print("⚠️  expert_query returned None")
            else:
                print("❌ expert_query method not available")
                
        except Exception as rag_error:
            print(f"❌ RAG Agent initialization failed: {rag_error}")
            print(f"   Error type: {type(rag_error).__name__}")
            
            # Try to identify the specific line that's failing
            import traceback
            print("📋 Full traceback:")
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Import or basic initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_initialization()
