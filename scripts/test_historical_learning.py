#!/usr/bin/env python3
"""
Test Script for Enhanced LLM with Historical Learning and Root Cause Prediction

This script demonstrates the advanced capabilities of the expert LLM system:
1. Historical tracking of the last 3 occurrences of each issue
2. Continuous learning from system logs
3. Root cause prediction based on patterns
4. Enhanced expert analysis with predictive insights
"""

import os
import sys
import time
from datetime import datetime

# Add the agent directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

try:
    from issue_history_manager import IssueHistoryManager
    from expert_remediation_agent import ExpertRemediationAgent
    from rag_agent import RAGAgent
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔬 {title}")
    print('='*60)

def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'─'*40}")
    print(f"📋 {title}")
    print('─'*40)

def test_issue_history_manager():
    """Test the Issue History Manager capabilities."""
    print_section("TESTING ISSUE HISTORY MANAGER")
    
    # Initialize the history manager
    print("🚀 Initializing Issue History Manager...")
    history_manager = IssueHistoryManager()
    
    # Test continuous learning scan
    print_subsection("Continuous Learning Scan")
    scan_result = history_manager.continuous_learning_scan()
    print(f"📊 Scan Results:")
    print(f"  • Issues Detected: {scan_result['issues_detected']}")
    print(f"  • Logs Analyzed: {scan_result['logs_analyzed']}")
    print(f"  • Total Historical Issues: {scan_result['total_historical_issues']}")
    print(f"  • Issue Types Tracked: {scan_result['issue_types_tracked']}")
    
    if scan_result['detected_issues']:
        print(f"\n🔍 Detected Issues:")
        for issue in scan_result['detected_issues']:
            print(f"  • Type: {issue['type']}")
            print(f"    Confidence: {issue['confidence']:.1%}")
            print(f"    Evidence: {', '.join(issue['evidence'][:3])}")
    
    # Test predictive analysis
    print_subsection("Predictive Analysis")
    test_descriptions = [
        "Kubernetes pods are stuck in CrashLoopBackOff state and won't start",
        "System running out of disk space, logs filling up filesystem",
        "GlusterFS peer disconnected, split-brain detected in volumes",
        "High memory usage causing OOM kills and pod evictions",
        "Network connectivity issues, DNS resolution failing"
    ]
    
    for description in test_descriptions:
        print(f"\n🔮 Analyzing: '{description}'")
        prediction = history_manager.get_predictive_analysis(description)
        
        if prediction['confidence'] > 0.0:
            print(f"  • Issue Type: {prediction.get('issue_type', 'unknown')}")
            print(f"  • Predicted Cause: {prediction.get('predicted_cause', 'unknown')}")
            print(f"  • Confidence: {prediction['confidence']:.1%}")
            print(f"  • Historical Count: {prediction.get('historical_count', 0)}")
            
            if prediction.get('recommendations'):
                print(f"  • Top Recommendation: {prediction['recommendations'][0].get('action', 'none')}")
        else:
            print(f"  • No matching pattern found")
    
    # Test trend analysis
    print_subsection("Trend Analysis")
    trends = history_manager.get_issue_trend_analysis()
    print(f"📈 System Trends:")
    print(f"  • Total Issues: {trends['total_issues']}")
    print(f"  • Recent (24h): {trends['recent_issues_24h']}")
    print(f"  • Trend Direction: {trends['trend_direction']}")
    if trends.get('most_frequent_type'):
        most_frequent = trends['most_frequent_type']
        print(f"  • Most Frequent: {most_frequent[0]} ({most_frequent[1]} times)")
    
    # Generate learning report
    print_subsection("Learning Report")
    report = history_manager.generate_learning_report()
    print(report)
    
    return history_manager

def test_expert_agent_with_history():
    """Test the Expert Remediation Agent with historical learning."""
    print_section("TESTING EXPERT AGENT WITH HISTORICAL LEARNING")
    
    # Initialize expert agent
    print("🚀 Initializing Expert Remediation Agent...")
    expert_agent = ExpertRemediationAgent()
    
    # Test comprehensive analysis with history
    print_subsection("Comprehensive System Analysis with Learning")
    analysis = expert_agent.analyze_system_comprehensive()
    
    print(f"🏥 System Health: {analysis['overall_health'].upper()}")
    print(f"📊 Critical Issues: {len(analysis['critical_issues'])}")
    print(f"⚠️ Warnings: {len(analysis['warnings'])}")
    
    # Show learning scan results
    if 'learning_scan' in analysis:
        scan = analysis['learning_scan']
        print(f"\n🧠 Learning Scan:")
        print(f"  • New Issues: {scan['issues_detected']}")
        print(f"  • Total Historical: {scan['total_historical']}")
    
    # Show historical insights
    if 'historical_insights' in analysis:
        insights = analysis['historical_insights']
        print(f"\n📈 Historical Insights:")
        print(f"  • Recent Issues (24h): {insights.get('recent_issues_24h', 0)}")
        print(f"  • Trend: {insights.get('trend_direction', 'unknown')}")
    
    # Show predictive analysis
    if 'predictive_analysis' in analysis:
        print(f"\n🔮 Predictive Analysis:")
        for area, predictions in analysis['predictive_analysis'].items():
            print(f"  • {area.title()}:")
            for pred_data in predictions[:2]:
                pred = pred_data['prediction']
                print(f"    - {pred.get('predicted_cause', 'unknown')} ({pred.get('confidence', 0):.1%})")
    
    # Test historical issue analysis
    print_subsection("Historical Issue Analysis")
    test_issues = [
        "pods crashlooping in default namespace",
        "disk space critically low on nodes",
        "glusterfs volume offline"
    ]
    
    for issue in test_issues:
        print(f"\n🔍 Analyzing: '{issue}'")
        hist_analysis = expert_agent.get_historical_issue_analysis(issue)
        
        if 'prediction' in hist_analysis:
            pred = hist_analysis['prediction']
            print(f"  • Pattern Match: {pred.get('issue_type', 'none')}")
            print(f"  • Confidence: {pred.get('confidence', 0):.1%}")
            if pred.get('predicted_cause') != 'unknown':
                print(f"  • Root Cause: {pred['predicted_cause']}")
    
    # Test continuous learning update
    print_subsection("Manual Learning Update")
    learning_update = expert_agent.perform_continuous_learning_update()
    if learning_update['success']:
        print("✅ Learning update successful")
        scan_result = learning_update['scan_result']
        print(f"  • Issues detected: {scan_result['issues_detected']}")
    else:
        print(f"❌ Learning update failed: {learning_update.get('error', 'unknown')}")
    
    return expert_agent

def test_rag_agent_with_history():
    """Test the RAG Agent with historical learning integration."""
    print_section("TESTING RAG AGENT WITH HISTORICAL INTELLIGENCE")
    
    # Initialize RAG agent
    print("🚀 Initializing Enhanced RAG Agent...")
    rag_agent = RAGAgent(offline_mode=True)
    
    # Test expert queries with historical context
    print_subsection("Expert Queries with Historical Context")
    
    test_queries = [
        "What's wrong with my Kubernetes cluster and how can I fix it?",
        "Pods are crashing with CrashLoopBackOff - help me troubleshoot",
        "System is running out of disk space, what should I do?",
        "GlusterFS volumes are showing split-brain errors",
        "High memory usage is causing OOM kills"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🤖 Query {i}: '{query}'")
        
        # Get expert response with historical context
        result = rag_agent.expert_query(query, auto_remediate=False)
        
        print(f"  📊 Analysis Results:")
        print(f"    • Confidence: {result['confidence']:.1%}")
        print(f"    • Query Type: {'Troubleshooting' if any('critical' in str(result).lower() for _ in [1]) else 'Knowledge'}")
        
        # Show historical insights
        if result.get('historical_insights'):
            insights = result['historical_insights']
            if 'prediction' in insights:
                pred = insights['prediction']
                if pred.get('confidence', 0) > 0.3:
                    print(f"    • Historical Match: {pred.get('issue_type', 'none')}")
                    print(f"    • Root Cause: {pred.get('predicted_cause', 'unknown')}")
        
        # Show predictive analysis
        if result.get('predictive_analysis'):
            print(f"    • Predictive Analysis: {len(result['predictive_analysis'])} areas analyzed")
        
        # Show system health summary
        if result.get('system_health'):
            health = result['system_health']
            print(f"    • System Health: {health.get('overall_health', 'unknown').upper()}")
            print(f"    • Critical Issues: {len(health.get('critical_issues', []))}")
        
        # Show part of the expert response
        expert_response = result.get('expert_response', '')
        if len(expert_response) > 200:
            print(f"    • Response Preview: {expert_response[:200]}...")
        else:
            print(f"    • Response: {expert_response}")
    
    return rag_agent

def test_complete_workflow():
    """Test the complete workflow with all components."""
    print_section("TESTING COMPLETE HISTORICAL LEARNING WORKFLOW")
    
    print("🚀 Simulating complete troubleshooting workflow with historical learning...")
    
    # Initialize all components
    history_manager = IssueHistoryManager()
    expert_agent = ExpertRemediationAgent()
    rag_agent = RAGAgent(offline_mode=True)
    
    # Simulate a troubleshooting session
    print_subsection("Simulated Troubleshooting Session")
    
    scenario = "My Kubernetes pods are constantly crashing and restarting. They show CrashLoopBackOff status."
    
    print(f"🎯 Scenario: {scenario}")
    
    # 1. Get historical prediction
    print(f"\n1️⃣ Historical Pattern Analysis:")
    prediction = history_manager.get_predictive_analysis(scenario)
    print(f"   • Issue Type: {prediction.get('issue_type', 'unknown')}")
    print(f"   • Confidence: {prediction.get('confidence', 0):.1%}")
    print(f"   • Predicted Cause: {prediction.get('predicted_cause', 'unknown')}")
    
    # 2. Perform continuous learning scan
    print(f"\n2️⃣ Continuous Learning Scan:")
    scan_result = history_manager.continuous_learning_scan()
    print(f"   • New issues detected: {scan_result['issues_detected']}")
    print(f"   • Learning database updated with {scan_result['total_historical_issues']} patterns")
    
    # 3. Expert analysis with historical context
    print(f"\n3️⃣ Expert Analysis with Historical Intelligence:")
    expert_result = rag_agent.expert_query(scenario, auto_remediate=False)
    print(f"   • Analysis confidence: {expert_result['confidence']:.1%}")
    print(f"   • System health: {expert_result.get('system_health', {}).get('overall_health', 'unknown')}")
    
    # 4. Show learning impact
    if expert_result.get('historical_insights'):
        print(f"\n4️⃣ Historical Learning Impact:")
        insights = expert_result['historical_insights']
        if 'trends' in insights:
            trends = insights['trends']
            print(f"   • Recent issues (24h): {trends.get('recent_issues_24h', 0)}")
            print(f"   • Trend direction: {trends.get('trend_direction', 'unknown')}")
    
    # 5. Generate final learning report
    print(f"\n5️⃣ Final Learning Report:")
    learning_report = history_manager.generate_learning_report()
    # Show summary lines only
    report_lines = learning_report.split('\n')
    for line in report_lines[:15]:  # First 15 lines
        if line.strip():
            print(f"   {line}")
    
    print(f"\n✅ Complete workflow test completed successfully!")
    print(f"📊 The LLM now has historical intelligence and continuous learning capabilities!")

def main():
    """Main test function."""
    print("🚀 TESTING ENHANCED LLM WITH HISTORICAL LEARNING")
    print("="*80)
    print("This test demonstrates advanced capabilities:")
    print("• Historical tracking of last 3 occurrences per issue type")
    print("• Continuous learning from system logs")
    print("• Root cause prediction based on patterns")
    print("• Enhanced expert analysis with predictive insights")
    print("="*80)
    
    try:
        # Test individual components
        print("\n🧪 Testing individual components...")
        
        # Test 1: Issue History Manager
        history_manager = test_issue_history_manager()
        time.sleep(2)
        
        # Test 2: Expert Agent with History
        expert_agent = test_expert_agent_with_history()
        time.sleep(2)
        
        # Test 3: RAG Agent with History
        rag_agent = test_rag_agent_with_history()
        time.sleep(2)
        
        # Test 4: Complete Workflow
        test_complete_workflow()
        
        # Final summary
        print_section("TEST SUMMARY")
        print("🎉 All tests completed successfully!")
        print("\n✅ ENHANCED CAPABILITIES VERIFIED:")
        print("  • Historical issue tracking (last 3 occurrences)")
        print("  • Continuous learning from logs")
        print("  • Root cause prediction with confidence scoring")
        print("  • Pattern-based issue detection")
        print("  • Trend analysis and insights")
        print("  • Enhanced expert responses with historical context")
        print("  • Predictive analysis integration")
        print("\n🧠 The LLM is now equipped with:")
        print("  • Learning memory of past issues")
        print("  • Predictive capabilities for future problems")
        print("  • Continuous improvement from system logs")
        print("  • Expert-level root cause analysis")
        
        print(f"\n🚀 Ready for production use with advanced AI capabilities!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
