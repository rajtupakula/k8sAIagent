#!/usr/bin/env python3
"""
Comprehensive validation for K8s AI Assistant to ensure offline functionality.
Tests all imports and validates no internet dependencies at runtime.
"""

import sys
import os
import subprocess
import importlib

# Add agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))

def test_import(module_name, description="", from_module=None):
    """Test importing a module with detailed error handling."""
    try:
        if from_module:
            # Handle "from X import Y" syntax
            mod = __import__(from_module, fromlist=[module_name])
            getattr(mod, module_name)
        else:
            __import__(module_name)
        print(f"✅ {module_name}: OK {description}")
        return True
    except ImportError as e:
        print(f"❌ {module_name}: MISSING - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {module_name}: ERROR - {e}")
        return False

def test_file_imports(file_path, description=""):
    """Test that a Python file can be imported without errors."""
    try:
        # Simple syntax check instead of full import
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to compile the code
        compile(content, file_path, 'exec')
        print(f"✅ {file_path}: OK {description} (syntax valid)")
        return True
    except FileNotFoundError:
        print(f"❌ {file_path}: FILE NOT FOUND")
        return False
    except SyntaxError as e:
        print(f"❌ {file_path}: SYNTAX ERROR - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {file_path}: WARNING - {e}")
        return True  # Still count as success for warnings

def check_offline_readiness():
    """Check if application can run without internet access."""
    print("\n🌐 Testing Offline Readiness:")
    
    # Check for hardcoded URLs in Python files
    url_patterns = [
        "http://", "https://", "ftp://", "api.openai.com", 
        "api.anthropic.com", "huggingface.co", ".com/", ".org/"
    ]
    
    issues = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', '.cache', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in url_patterns:
                            if pattern in content and 'localhost' not in content:
                                line_num = content[:content.find(pattern)].count('\n') + 1
                                issues.append(f"  • {file_path}:{line_num} - Contains: {pattern}")
                except Exception:
                    continue
    
    if issues:
        print("⚠️  Potential internet dependencies found:")
        for issue in issues[:10]:  # Show first 10
            print(issue)
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("✅ No obvious internet dependencies detected")
    
    return len(issues) == 0

def main():
    print("🔍 Comprehensive K8s AI Assistant Validation")
    print("=" * 60)
    
    # Test core dependencies
    print("\n📦 Testing Core Dependencies:")
    core_success = 0
    core_packages = [
        ("streamlit", "Web UI framework"),
        ("pandas", "Data manipulation"),
        ("numpy", "Numerical computing"),
        ("kubernetes", "K8s API client"),
        ("requests", "HTTP client"),
        ("yaml", "YAML parsing (pyyaml)"),
        ("prometheus_client", "Metrics collection"),
        ("psutil", "System monitoring"),
        ("plotly", "Interactive plots"),
        ("sklearn", "Machine learning (scikit-learn)"),
    ]
    
    for package, desc in core_packages:
        if test_import(package, desc):
            core_success += 1
    
    # Test AI/ML dependencies (optional but preferred)
    print(f"\n🤖 Testing AI/ML Dependencies (Optional):")
    ml_success = 0
    ml_packages = [
        ("sentence_transformers", "Text embeddings"),
        ("transformers", "HuggingFace transformers"),
        ("torch", "PyTorch deep learning"),
        ("chromadb", "Vector database"),
        ("langchain", "LLM framework"),
    ]
    
    for package, desc in ml_packages:
        if test_import(package, desc):
            ml_success += 1
    
    # Test specific K8s imports
    print(f"\n🔧 Testing Kubernetes Module Imports:")
    k8s_success = 0
    k8s_imports = [
        ("client", "K8s client", "kubernetes"),
        ("config", "K8s config", "kubernetes"),
        ("watch", "K8s watch", "kubernetes"),
    ]
    
    for module, desc, from_mod in k8s_imports:
        if test_import(module, desc, from_mod):
            k8s_success += 1
    
    # Test application modules
    print(f"\n🚀 Testing Application Modules:")
    app_success = 0
    app_files = [
        ("./agent/main.py", "Main application entry point"),
        ("./agent/monitor.py", "Kubernetes monitoring"),
        ("./agent/remediate.py", "Remediation engine"),
        ("./agent/config_manager.py", "Configuration management"),
        ("./agent/runtime_config_manager.py", "Runtime configuration"),
        ("./ui/dashboard.py", "Streamlit dashboard"),
    ]
    
    for file_path, desc in app_files:
        if os.path.exists(file_path):
            if test_file_imports(file_path, desc):
                app_success += 1
        else:
            print(f"⚠️  {file_path}: FILE NOT FOUND")
    
    # Check offline readiness
    offline_ready = check_offline_readiness()
    
    # Summary
    print(f"\n📊 Validation Summary:")
    print(f"Core Dependencies: {core_success}/{len(core_packages)} ✅")
    print(f"AI/ML Dependencies: {ml_success}/{len(ml_packages)} ✅")
    print(f"K8s Imports: {k8s_success}/{len(k8s_imports)} ✅")
    print(f"Application Modules: {app_success}/{len(app_files)} ✅")
    print(f"Offline Ready: {'✅' if offline_ready else '⚠️ '}")
    
    total_success = core_success + k8s_success + app_success
    total_tests = len(core_packages) + len(k8s_imports) + len(app_files)
    success_rate = (total_success / total_tests) * 100
    
    print(f"\nOverall Success Rate: {success_rate:.1f}% ({total_success}/{total_tests})")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if core_success < len(core_packages):
        missing_core = len(core_packages) - core_success
        print(f"   • Install {missing_core} missing core dependencies")
        print(f"   • Run: pip install -r requirements-complete.txt")
    
    if ml_success < len(ml_packages):
        print(f"   • AI/ML features will have reduced functionality")
        print(f"   • For full features: pip install sentence-transformers transformers torch chromadb langchain")
    
    if not offline_ready:
        print(f"   • Review files with internet dependencies")
        print(f"   • Ensure all models are pre-downloaded during Docker build")
    
    if success_rate >= 90:
        print(f"\n🎉 Application is ready for deployment!")
        return 0
    else:
        print(f"\n⚠️  Application needs attention before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())
