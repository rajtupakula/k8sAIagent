#!/usr/bin/env python3
"""
Kubernetes AI Agent Startup Validator
This script validates the application can start correctly before the main application runs.
"""

import os
import sys
import logging
import time

def validate_environment():
    """Validate the environment is properly configured."""
    issues = []
    
    # Check required directories
    required_dirs = ['/data', '/var/log/k8s-ai-agent', '/app', '/opt/models']
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"Created missing directory: {dir_path}")
            except Exception as e:
                issues.append(f"Cannot create required directory {dir_path}: {e}")
        elif not os.access(dir_path, os.W_OK):
            try:
                os.chmod(dir_path, 0o755)
                print(f"Fixed permissions for directory: {dir_path}")
            except Exception as e:
                issues.append(f"Directory not writable and cannot fix: {dir_path}")
    
    # Check virtual environment
    if not os.path.exists('/opt/venv/bin/python'):
        issues.append("Python virtual environment not found at /opt/venv")
    
    # Check model directory
    if not os.path.exists('/opt/models'):
        try:
            os.makedirs('/opt/models', exist_ok=True)
        except Exception as e:
            issues.append(f"Cannot create models directory: {e}")
    
    # Check environment variables
    required_env = [
        'PATH', 'PYTHONPATH', 'CHROMA_TELEMETRY', 
        'STREAMLIT_SERVER_PORT', 'STREAMLIT_SERVER_ADDRESS'
    ]
    for env_var in required_env:
        if env_var not in os.environ:
            issues.append(f"Missing environment variable: {env_var}")
    
    # Validate telemetry is disabled
    if os.environ.get('CHROMA_TELEMETRY', '').lower() != 'false':
        issues.append("ChromaDB telemetry not properly disabled")
    
    return issues

def validate_python_imports():
    """Validate required Python packages can be imported."""
    issues = []
    
    # Core packages - only check truly essential ones
    core_packages = ['os', 'sys', 'logging', 'time', 'json']
    
    for package in core_packages:
        try:
            __import__(package)
        except ImportError:
            issues.append(f"Cannot import required package: {package}")
    
    # Optional packages (warn only, don't fail)
    optional_packages = ['streamlit', 'pandas', 'numpy', 'chromadb', 'sentence_transformers', 'requests']
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✅ Optional package available: {package}")
        except ImportError:
            print(f"⚠️  Optional package not available: {package} (will run with reduced functionality)")
    
    # LLaMA server components (special handling)
    try:
        import llama_cpp
        print("✅ LLaMA server support available: llama_cpp")
    except ImportError:
        print("⚠️  LLaMA server not available: llama_cpp (will run in offline mode)")
    
    # Check for LLaMA setup files
    llama_files = ['setup_llama_server.py', 'scripts/llama_runner.py']
    for file_path in llama_files:
        if os.path.exists(f"/app/{file_path}"):
            print(f"✅ LLaMA component available: {file_path}")
        else:
            print(f"⚠️  LLaMA component missing: {file_path}")
    
    # Check for container startup script
    container_scripts = ['container_startup.py', 'quick_start_llama.py']
    for script in container_scripts:
        if os.path.exists(f"/app/{script}"):
            print(f"✅ Container script available: {script}")
        else:
            print(f"⚠️  Container script missing: {script}")
    
    return issues

def main():
    """Main validation function."""
    print("🔍 Kubernetes AI Agent - Startup Validation")
    print("=" * 50)
    
    # Environment validation
    print("Checking environment...")
    env_issues = validate_environment()
    if env_issues:
        print("❌ Environment issues found:")
        for issue in env_issues:
            print(f"  • {issue}")
        return 1
    else:
        print("✅ Environment validation passed")
    
    # Python imports validation
    print("Checking Python imports...")
    import_issues = validate_python_imports()
    if import_issues:
        print("❌ Import issues found:")
        for issue in import_issues:
            print(f"  • {issue}")
        return 1
    else:
        print("✅ Import validation passed")
    
    # Streamlit config validation
    print("Checking Streamlit configuration...")
    streamlit_config = "/app/.streamlit/config.toml"
    if os.path.exists(streamlit_config):
        with open(streamlit_config, 'r') as f:
            config_content = f.read()
            deprecated_options = [
                'global.logLevel', 'client.caching', 'client.displayEnabled',
                'runner.installTracer', 'runner.fixMatplotlib'
            ]
            found_deprecated = []
            for option in deprecated_options:
                if option in config_content:
                    found_deprecated.append(option)
            
            if found_deprecated:
                print(f"❌ Deprecated Streamlit options found: {found_deprecated}")
                return 1
            else:
                print("✅ Streamlit configuration is clean")
    else:
        print("❌ Streamlit configuration file not found")
        return 1
    
    print("=" * 50)
    print("✅ All validations passed - Application ready to start")
    return 0

if __name__ == "__main__":
    sys.exit(main())
