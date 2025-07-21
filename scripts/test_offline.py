#!/usr/bin/env python3
"""
Test script for offline functionality of the Kubernetes AI Assistant.
This script verifies that all components work without external internet access.
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_rag_agent_offline():
    """Test RAG agent in offline mode."""
    print("🔍 Testing RAG Agent in offline mode...")
    
    try:
        from agent.rag_agent import RAGAgent
        
        # Initialize with offline mode
        rag = RAGAgent(offline_mode=True, chroma_path="./test_chroma")
        
        # Test basic query
        response = rag.query("What should I do if a pod is in CrashLoopBackOff?")
        assert response is not None, "RAG agent should return a response"
        assert len(response) > 50, "Response should be substantial"
        
        print("✅ RAG Agent offline mode: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ RAG Agent offline mode: FAILED - {e}")
        return False

def test_action_parsing():
    """Test action parsing from natural language prompts."""
    print("🔍 Testing action parsing...")
    
    try:
        from agent.rag_agent import RAGAgent
        
        rag = RAGAgent(offline_mode=True, chroma_path="./test_chroma")
        
        # Test action detection
        test_prompts = [
            "restart failed pods",
            "scale deployment nginx to 5 replicas",
            "clean completed jobs",
            "check status of pods"
        ]
        
        for prompt in test_prompts:
            result = rag.execute_action_from_prompt(prompt)
            assert result["action_detected"], f"Should detect action in: {prompt}"
            print(f"  ✅ Detected action in: '{prompt}' -> {result['action_type']}")
        
        print("✅ Action parsing: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Action parsing: FAILED - {e}")
        return False

def test_kubernetes_monitor():
    """Test Kubernetes monitor (if available)."""
    print("🔍 Testing Kubernetes monitor...")
    
    try:
        from agent.monitor import KubernetesMonitor
        
        monitor = KubernetesMonitor()
        
        # This may fail if not in a k8s environment, which is expected
        try:
            connected = monitor.is_connected()
            if connected:
                print("✅ Kubernetes monitor: PASSED (connected to cluster)")
            else:
                print("⚠️  Kubernetes monitor: Not connected (expected outside cluster)")
        except:
            print("⚠️  Kubernetes monitor: Not available (expected outside cluster)")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Kubernetes monitor: {e}")
        return True  # This is expected outside a k8s environment

def test_dashboard_imports():
    """Test that dashboard imports work correctly."""
    print("🔍 Testing dashboard imports...")
    
    try:
        # Test all critical imports
        import streamlit as st
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        
        from agent.monitor import KubernetesMonitor
        from agent.rag_agent import RAGAgent
        from agent.remediate import RemediationEngine
        from scheduler.forecast import ResourceForecaster
        from glusterfs.analyze import GlusterFSAnalyzer
        
        print("✅ Dashboard imports: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Dashboard imports: FAILED - {e}")
        return False

def test_offline_response_quality():
    """Test the quality of offline responses."""
    print("🔍 Testing offline response quality...")
    
    try:
        from agent.rag_agent import RAGAgent
        
        rag = RAGAgent(offline_mode=True, chroma_path="./test_chroma")
        
        # Test various types of questions
        test_questions = [
            "How do I troubleshoot a pod that won't start?",
            "What causes high CPU usage in Kubernetes?",
            "How to scale a deployment?",
            "What are the best practices for resource limits?"
        ]
        
        for question in test_questions:
            response = rag._offline_response("", question)
            assert response is not None, f"Should have response for: {question}"
            assert len(response) > 100, f"Response should be detailed for: {question}"
            assert "kubectl" in response or "Kubernetes" in response, "Should contain k8s-related content"
            print(f"  ✅ Good response for: '{question[:50]}...'")
        
        print("✅ Offline response quality: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Offline response quality: FAILED - {e}")
        return False

def main():
    """Run all offline functionality tests."""
    print("🚀 Starting Kubernetes AI Assistant Offline Tests")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()
    
    tests = [
        test_dashboard_imports,
        test_rag_agent_offline,
        test_action_parsing,
        test_offline_response_quality,
        test_kubernetes_monitor,
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
        print("🎉 All tests passed! The AI Assistant is ready for offline operation.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
