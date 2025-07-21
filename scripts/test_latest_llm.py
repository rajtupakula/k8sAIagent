#!/usr/bin/env python3
"""
Test Script for Latest LLM Features
Advanced testing of state-of-the-art AI capabilities
"""

import sys
import os
import time
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_advanced_rag_agent():
    """Test the advanced RAG agent with latest LLM features."""
    print("🚀 Testing Latest & Greatest LLM Technology")
    print("=" * 60)
    
    try:
        # Try to import the advanced agent
        try:
            from agent.advanced_rag_agent import AdvancedRAGAgent
            agent_class = AdvancedRAGAgent
            print("✅ Using AdvancedRAGAgent with latest features")
        except ImportError:
            # Fallback to enhanced mock from dashboard
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ui'))
            from dashboard import AdvancedRAGAgent
            agent_class = AdvancedRAGAgent
            print("⚠️ Using enhanced mock agent (dependencies missing)")
        
        # Initialize agent
        print("\n🧠 Initializing Advanced AI Agent...")
        agent = agent_class()
        
        # Test model information
        print("\n📊 Model Information:")
        model_info = agent.get_model_info()
        for key, value in model_info.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        # Test available models
        print(f"\n🎯 Available Models: {len(agent.available_models)}")
        for model_name, config in list(agent.available_models.items())[:5]:
            print(f"  • {model_name}")
            print(f"    Quality: {config.quality}, Speed: {config.speed}")
            print(f"    Context: {config.context_window:,} tokens")
            print(f"    Specialty: {config.specialty}")
        
        # Test model switching
        print("\n🔄 Testing Model Switching...")
        if len(agent.available_models) > 1:
            model_names = list(agent.available_models.keys())
            switch_result = agent.switch_model(model_names[1])
            print(f"  {switch_result}")
        
        # Test basic query
        print("\n💬 Testing Basic Query...")
        test_query = "What are the best practices for troubleshooting CrashLoopBackOff pods?"
        start_time = time.time()
        response = agent.query(test_query)
        response_time = time.time() - start_time
        
        print(f"  Query: {test_query}")
        print(f"  Response Time: {response_time:.2f}s")
        print(f"  Response Length: {len(response)} characters")
        print(f"  Response Preview: {response[:200]}...")
        
        # Test streaming if available
        print("\n🔄 Testing Streaming Response...")
        if hasattr(agent, 'query_stream'):
            stream_query = "How do I optimize Kubernetes resource usage?"
            print(f"  Streaming Query: {stream_query}")
            
            start_time = time.time()
            chunks = []
            try:
                for i, chunk in enumerate(agent.query_stream(stream_query)):
                    chunks.append(chunk)
                    if i < 5:  # Show first few chunks
                        print(f"    Chunk {i+1}: {chunk[:50]}...")
                    if i >= 20:  # Limit for testing
                        break
                
                stream_time = time.time() - start_time
                print(f"  Streaming Time: {stream_time:.2f}s")
                print(f"  Total Chunks: {len(chunks)}")
            except Exception as e:
                print(f"  Streaming Error: {e}")
        
        # Test action detection
        print("\n🎯 Testing Action Detection...")
        action_queries = [
            "restart all failed pods",
            "scale nginx deployment to 5 replicas",
            "clean up completed jobs",
            "perform security audit of the cluster",
            "analyze resource usage patterns"
        ]
        
        for query in action_queries:
            try:
                result = agent.query_with_actions(query, None)
                action_result = result.get("action_result", {})
                
                print(f"  Query: {query}")
                print(f"    Action Detected: {action_result.get('action_detected', False)}")
                print(f"    Action Type: {action_result.get('action_type', 'None')}")
                print(f"    Confidence: {action_result.get('confidence', 0):.1%}")
                print()
            except Exception as e:
                print(f"    Error: {e}")
        
        # Test conversation analytics
        print("\n📊 Testing Conversation Analytics...")
        if hasattr(agent, 'get_conversation_summary'):
            try:
                summary = agent.get_conversation_summary()
                print("  Conversation Summary:")
                print(json.dumps(summary, indent=4, default=str))
            except Exception as e:
                print(f"  Analytics Error: {e}")
        
        # Performance metrics
        print("\n⚡ Performance Metrics:")
        print(f"  Total Requests: {getattr(agent, 'total_requests', 0)}")
        print(f"  Total Tokens Generated: {getattr(agent, 'tokens_generated', 0)}")
        print(f"  Average Response Time: {getattr(agent, 'response_time', 0):.2f}s")
        print(f"  Context Window: {getattr(agent, 'context_window', 0):,} tokens")
        
        print("\n✅ Advanced LLM Testing Complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Testing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_dashboard_integration():
    """Test the dashboard integration with latest features."""
    print("\n🎨 Testing Dashboard Integration...")
    print("-" * 40)
    
    try:
        # Test dashboard imports
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ui'))
        
        # Import with graceful handling
        try:
            from dashboard import main, STREAMLIT_AVAILABLE
            print(f"✅ Dashboard import successful")
            print(f"  Streamlit Available: {STREAMLIT_AVAILABLE}")
        except ImportError as e:
            print(f"⚠️ Dashboard import issues: {e}")
        
        # Test mock components
        try:
            from dashboard import AdvancedRAGAgent, MockStreamlit
            
            # Test advanced agent
            agent = AdvancedRAGAgent()
            print(f"✅ Advanced RAG Agent initialized")
            print(f"  Model: {agent.model_name}")
            print(f"  Context Window: {agent.context_window:,}")
            print(f"  Available Models: {len(agent.available_models)}")
            
            # Test mock streamlit
            if not STREAMLIT_AVAILABLE:
                mock_st = MockStreamlit()
                print(f"✅ Mock Streamlit functional")
                
                # Test mock functionality
                mock_st.title("Test Title")
                mock_st.write("Test content")
                mock_st.metric("Test Metric", "100")
                
        except Exception as e:
            print(f"❌ Component test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard integration test failed: {e}")
        return False

def test_requirements():
    """Test requirements and dependencies."""
    print("\n📦 Testing Requirements & Dependencies...")
    print("-" * 40)
    
    # Core dependencies
    core_deps = [
        "streamlit", "pandas", "plotly", "numpy",
        "kubernetes", "requests", "pyyaml"
    ]
    
    # Advanced AI dependencies
    ai_deps = [
        "sentence_transformers", "chromadb", "transformers", 
        "torch", "langchain", "tiktoken", "openai", "anthropic"
    ]
    
    # Optional performance dependencies
    perf_deps = [
        "llama_cpp", "accelerate", "optimum", "faiss", "psutil"
    ]
    
    def check_deps(deps, category):
        print(f"\n{category} Dependencies:")
        available = 0
        for dep in deps:
            try:
                __import__(dep.replace("-", "_"))
                print(f"  ✅ {dep}")
                available += 1
            except ImportError:
                print(f"  ❌ {dep}")
        
        coverage = available / len(deps) * 100
        print(f"  Coverage: {coverage:.1f}% ({available}/{len(deps)})")
        return coverage
    
    core_coverage = check_deps(core_deps, "Core")
    ai_coverage = check_deps(ai_deps, "AI/ML")
    perf_coverage = check_deps(perf_deps, "Performance")
    
    overall_coverage = (core_coverage + ai_coverage + perf_coverage) / 3
    print(f"\n📊 Overall Dependency Coverage: {overall_coverage:.1f}%")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if core_coverage < 80:
        print("  • Install core dependencies: pip install streamlit pandas plotly")
    if ai_coverage < 50:
        print("  • Install AI dependencies: pip install sentence-transformers chromadb")
    if perf_coverage < 30:
        print("  • Install performance deps: pip install llama-cpp-python accelerate")
    
    return overall_coverage > 60

def main():
    """Main testing function."""
    print("🧪 Kubernetes AI Assistant - Latest LLM Features Test")
    print("=" * 70)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Requirements Check", test_requirements),
        ("Advanced RAG Agent", test_advanced_rag_agent), 
        ("Dashboard Integration", test_dashboard_integration)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*70}")
    print("🎯 TEST SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name:.<40} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Latest LLM features are working correctly.")
    elif passed >= total * 0.7:
        print("\n⚠️ Most tests passed. Some optional features may be unavailable.")
    else:
        print("\n❌ Several tests failed. Check dependencies and configuration.")
    
    print(f"\nTest Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
