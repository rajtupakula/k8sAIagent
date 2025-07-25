#!/usr/bin/env python3
"""
🔍 User Guide Feature Validation Script
Checks if all build and deployment files support the User Guide features
"""
import os
import sys
import json
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists"""
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {file_path}")
    return exists

def check_dockerfile_dependencies():
    """Check if Dockerfile has required dependencies for User Guide features"""
    print("\n📦 Checking Dockerfile Dependencies...")
    
    dockerfile_path = "Dockerfile.optimized"
    if not os.path.exists(dockerfile_path):
        print("❌ Dockerfile.optimized not found")
        return False
    
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    required_deps = {
        "streamlit": "Web framework for dashboard",
        "plotly": "Charts for forecasting tab", 
        "pandas": "Data manipulation for analytics",
        "numpy": "Numerical operations",
        "kubernetes": "K8s client for monitoring"
    }
    
    all_present = True
    for dep, description in required_deps.items():
        if dep in content:
            print(f"✅ {dep}: {description}")
        else:
            print(f"❌ {dep}: {description} - MISSING")
            all_present = False
    
    return all_present

def check_dashboard_features():
    """Check if dashboard files implement User Guide features"""
    print("\n🎯 Checking Dashboard Features...")
    
    dashboards = [
        ("complete_expert_dashboard.py", "Complete User Guide implementation"),
        ("ui/dashboard.py", "Enhanced dashboard with 5-tab interface"),
        ("emergency_dashboard.py", "Emergency fallback dashboard")
    ]
    
    available_dashboards = 0
    for dashboard_file, description in dashboards:
        if os.path.exists(dashboard_file):
            print(f"✅ {dashboard_file}: {description}")
            available_dashboards += 1
            
            # Check for key User Guide features
            with open(dashboard_file, 'r') as f:
                content = f.read()
            
            features = {
                "st.tabs": "5-tab interface",
                "Expert Diagnosis": "Expert action buttons",
                "Forecasting": "Resource forecasting",
                "GlusterFS": "Storage health monitoring",
                "plotly": "Interactive charts"
            }
            
            for feature, description in features.items():
                if feature in content:
                    print(f"  ✅ {description}")
                else:
                    print(f"  ⚠️ {description} - Not found in {dashboard_file}")
        else:
            print(f"❌ {dashboard_file}: {description} - FILE MISSING")
    
    return available_dashboards > 0

def check_startup_configuration():
    """Check if startup files are configured correctly"""
    print("\n🚀 Checking Startup Configuration...")
    
    startup_files = [
        ("container_startup.py", "Main container startup"),
        ("app_wrapper.py", "Application wrapper")
    ]
    
    all_configured = True
    for file_path, description in startup_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}: {description}")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for proper dashboard configuration
            if "complete_expert_dashboard.py" in content or "ui/dashboard.py" in content:
                print(f"  ✅ Configured to use User Guide dashboard")
            else:
                print(f"  ⚠️ May not be configured for User Guide dashboard")
        else:
            print(f"❌ {file_path}: {description} - FILE MISSING")
            all_configured = False
    
    return all_configured

def check_kubernetes_deployment():
    """Check Kubernetes deployment configuration"""
    print("\n☸️ Checking Kubernetes Deployment...")
    
    k8s_files = [
        ("k8s/k8s-ai-agent.yaml", "Main deployment manifest"),
        ("k8s/02-rbac.yaml", "RBAC configuration")
    ]
    
    all_present = True
    for file_path, description in k8s_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}: {description}")
            
            if file_path.endswith("k8s-ai-agent.yaml"):
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for User Guide environment variables
                env_vars = [
                    "ui_mode",
                    "enable_forecasting", 
                    "enable_glusterfs",
                    "continuous_monitoring"
                ]
                
                for env_var in env_vars:
                    if env_var in content:
                        print(f"  ✅ {env_var} environment configured")
                    else:
                        print(f"  ⚠️ {env_var} not found in deployment")
        else:
            print(f"❌ {file_path}: {description} - FILE MISSING")
            all_present = False
    
    return all_present

def check_user_guide_compliance():
    """Check User Guide feature compliance"""
    print_section("User Guide Compliance")
    
    # Updated advanced features to check for
    advanced_features = [
        "Advanced Model Configuration",
        "Predictive Analytics", 
        "AI Health Analysis",
        "Smart Auto-Diagnosis",
        "Turbo Analysis",
        "Performance Tuning",
        "Security Audit",
        "Cost Optimization",
        "Auto-Scale Recommendations",
        "Precision Mode",
        "Live Streaming",
        "Continuous Scan",
        "Predictive Alerts",
        "Neural Network",
        "LSTM",
        "Prophet ML",
        "Ensemble Hybrid"
    ]
    
    # Check complete dashboard for advanced features
    dashboard_file = "complete_expert_dashboard.py"
    advanced_count = 0
    
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r') as f:
            content = f.read()
            for feature in advanced_features:
                if feature in content:
                    advanced_count += 1
    
    # Calculate compliance scores
    tab_interface = "st.tabs" in open("complete_expert_dashboard.py").read() if os.path.exists("complete_expert_dashboard.py") else False
    expert_actions = "Expert Diagnosis" in open("complete_expert_dashboard.py").read() if os.path.exists("complete_expert_dashboard.py") else False
    model_selection = "selectbox" in open("complete_expert_dashboard.py").read() and "Model" in open("complete_expert_dashboard.py").read() if os.path.exists("complete_expert_dashboard.py") else False
    advanced_features_score = advanced_count >= 8  # At least 8 advanced features
    
    print(f"📋 User Guide Feature Compliance Check:")
    print(f"✅ 5-Tab Interface: {'Implemented' if tab_interface else 'Missing'}")
    print(f"✅ Expert Actions: {'Implemented' if expert_actions else 'Missing'}")
    print(f"✅ Model Selection: {'Implemented' if model_selection else 'Missing'}")
    print(f"{'✅' if advanced_features_score else '❌'} Advanced Features: {'Implemented' if advanced_features_score else 'Missing or incomplete'} ({advanced_count}/{len(advanced_features)} detected)")
    
    # Calculate overall compliance
    compliance_score = sum([tab_interface, expert_actions, model_selection, advanced_features_score]) / 4 * 100
    
    print(f"\n📊 Overall User Guide Compliance: {compliance_score:.0f}%")
    
    return compliance_score >= 95  # 95% or higher for PASS

def main():
    """Main validation function"""
    print("🔍 User Guide Feature Validation")
    print("=" * 50)
    
    # Run all checks
    checks = [
        ("Essential Files", lambda: all([
            check_file_exists("complete_expert_dashboard.py", "Complete dashboard"),
            check_file_exists("ui/dashboard.py", "Enhanced dashboard"),
            check_file_exists("Dockerfile.optimized", "Optimized Dockerfile")
        ])),
        ("Dockerfile Dependencies", check_dockerfile_dependencies),
        ("Dashboard Features", check_dashboard_features),
        ("Startup Configuration", check_startup_configuration),
        ("Kubernetes Deployment", check_kubernetes_deployment),
        ("User Guide Compliance", check_user_guide_compliance)
    ]
    
    results = {}
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            result = check_func()
            results[check_name] = result
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"\n{check_name}: {status}")
        except Exception as e:
            results[check_name] = False
            print(f"\n{check_name}: ❌ ERROR - {e}")
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\nOverall: {passed}/{total} checks passed ({(passed/total)*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED! User Guide features are ready to deploy!")
        return True
    else:
        print(f"\n⚠️ {total-passed} issues found. Review the failures above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
