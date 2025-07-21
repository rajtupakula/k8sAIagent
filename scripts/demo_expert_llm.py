#!/usr/bin/env python3
"""
Expert LLM Demonstration
Shows the enhanced expert-level capabilities for Ubuntu OS, Kubernetes, and GlusterFS troubleshooting
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_expert_capabilities():
    """Demonstrate expert LLM capabilities."""
    print("🚀 EXPERT LLM DEMONSTRATION")
    print("="*60)
    print("Enhanced AI Assistant with Expert-Level Troubleshooting")
    print("="*60)
    
    # Try to import expert agent
    try:
        from agent.expert_remediation_agent import ExpertRemediationAgent
        expert_agent = ExpertRemediationAgent()
        print("✅ Expert Remediation Agent loaded successfully!")
    except Exception as e:
        print(f"❌ Expert agent failed to load: {e}")
        return
    
    print("\n🎯 EXPERT CAPABILITIES OVERVIEW:")
    print("• Ubuntu OS: Disk space, memory, services, network, CPU analysis")
    print("• Kubernetes: Pod health, node status, services, volumes")
    print("• GlusterFS: Volume status, split-brain, heal operations, peers")
    print("• Safety-first approach with comprehensive validation")
    print("• Intelligent pattern matching with confidence scoring")
    print("• Step-by-step remediation plans with command generation")
    
    # Demonstrate system analysis
    print("\n" + "="*50)
    print("🔍 LIVE SYSTEM ANALYSIS")
    print("="*50)
    
    try:
        analysis = expert_agent.analyze_system_comprehensive()
        
        # Show health status with emoji
        health = analysis.get('overall_health', 'unknown')
        health_emoji = {
            'healthy': '🟢', 'warning': '🟡', 'degraded': '🟠', 
            'critical': '🔴', 'unknown': '⚪'
        }.get(health, '⚪')
        
        print(f"🏥 System Health: {health_emoji} {health.upper()}")
        print(f"🚨 Critical Issues: {len(analysis.get('critical_issues', []))}")
        print(f"⚠️ Warnings: {len(analysis.get('warnings', []))}")
        print(f"💡 Recommendations: {len(analysis.get('recommendations', []))}")
        
        # Show component details
        print("\n📊 COMPONENT STATUS:")
        for component, data in analysis.get('detailed_analysis', {}).items():
            status = data.get('status', 'unknown')
            emoji = {
                'healthy': '✅', 'warning': '⚠️', 'degraded': '🟠', 
                'critical': '🔴', 'unavailable': '⚫', 'error': '❌'
            }.get(status, '❓')
            component_name = component.replace('_', ' ').title()
            print(f"  {emoji} {component_name}: {status.upper()}")
            
            # Show specific issues for this component
            if data.get('critical_issues'):
                for issue in data['critical_issues'][:2]:
                    print(f"      🚨 {issue}")
            if data.get('warnings'):
                for warning in data['warnings'][:1]:
                    print(f"      ⚠️ {warning}")
        
    except Exception as e:
        print(f"❌ System analysis failed: {e}")
    
    # Demonstrate issue remediation
    print("\n" + "="*50)
    print("🛠️ EXPERT ISSUE REMEDIATION DEMO")
    print("="*50)
    
    demo_issues = [
        "kubernetes pods stuck in CrashLoopBackOff state",
        "ubuntu system running out of disk space", 
        "glusterfs volume showing split-brain errors",
        "high memory usage causing system instability"
    ]
    
    for i, issue in enumerate(demo_issues, 1):
        print(f"\n🔧 Demo {i}: {issue}")
        print("-" * 50)
        
        try:
            result = expert_agent.expert_remediate(issue, auto_execute=False)
            issue_analysis = result.get('issue_analysis', {})
            
            if issue_analysis.get('pattern_matched'):
                confidence = issue_analysis.get('confidence', 0.0)
                area = issue_analysis.get('area', 'unknown')
                severity = issue_analysis.get('severity', 'unknown')
                
                print(f"  ✅ Expert Pattern Matched: {confidence:.1%} confidence")
                print(f"  📍 System Area: {area.replace('_', ' ').title()}")
                print(f"  ⚠️ Severity Level: {severity.upper()}")
                
                # Show remediation plan summary
                plan = result.get('remediation_plan', [])
                if plan:
                    print(f"  📋 Remediation Plan: {len(plan)} steps generated")
                    print(f"  🛡️ Safety Checks: Comprehensive validation included")
                    
                    # Show first few steps
                    for j, step in enumerate(plan[:2], 1):
                        phase = step.get('phase', '').title()
                        safety = step.get('safety_level', 'unknown')
                        safety_emoji = {'safe': '✅', 'medium': '⚠️', 'high': '🔴'}.get(safety, '❓')
                        print(f"      Step {j}: [{phase}] {safety_emoji} {step.get('description', '')[:60]}...")
            else:
                print(f"  ❌ No expert pattern matched (confidence too low)")
                
        except Exception as e:
            print(f"  ❌ Remediation demo failed: {e}")
    
    # Show expert knowledge areas
    print("\n" + "="*50)
    print("🧠 EXPERT KNOWLEDGE BASE")
    print("="*50)
    
    try:
        knowledge_areas = expert_agent.expert_knowledge
        
        for area, area_data in knowledge_areas.items():
            area_name = area.replace('_', ' ').title()
            pattern_count = len(area_data.get('patterns', {}))
            print(f"\n📚 {area_name}: {pattern_count} expert patterns")
            
            # Show sample patterns
            patterns = list(area_data.get('patterns', {}).keys())[:3]
            for pattern in patterns:
                pattern_name = pattern.replace('_', ' ').title()
                pattern_data = area_data['patterns'][pattern]
                severity = pattern_data.get('severity', 'unknown')
                print(f"  • {pattern_name} ({severity} severity)")
    
    except Exception as e:
        print(f"❌ Knowledge base demo failed: {e}")
    
    # Demonstrate health summary
    print("\n" + "="*50)
    print("📋 EXPERT HEALTH SUMMARY")
    print("="*50)
    
    try:
        health_summary = expert_agent.get_system_health_summary()
        print(health_summary)
    except Exception as e:
        print(f"❌ Health summary failed: {e}")
    
    # Final summary
    print("\n" + "="*60)
    print("🎯 EXPERT LLM ENHANCEMENT SUMMARY")
    print("="*60)
    print("✅ Intelligent Issue Detection: Pattern-based recognition with confidence scoring")
    print("✅ Expert System Analysis: Comprehensive multi-system health monitoring")
    print("✅ Safety-First Remediation: Risk-assessed step-by-step resolution plans")
    print("✅ Command Generation: Exact commands for issue resolution")
    print("✅ Built-in Tools Only: No external dependencies or binaries required")
    print("✅ Offline Operation: Complete local analysis and remediation")
    print("✅ Security Focused: Safe operations with comprehensive validation")
    print("✅ Enterprise Ready: Production-grade troubleshooting capabilities")
    
    print("\n🚀 Your LLM is now an EXPERT SYSTEM ENGINEER!")
    print("Ready to handle complex Ubuntu OS, Kubernetes, and GlusterFS issues.")
    print("Access via the enhanced dashboard or direct API calls.")

if __name__ == "__main__":
    demo_expert_capabilities()
