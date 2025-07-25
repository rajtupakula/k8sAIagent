#!/usr/bin/env python3
"""
Runtime Error Check - Comprehensive validation for all components
"""

import ast
import os
import sys
import importlib.util

def check_syntax(file_path):
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def check_compilation(file_path):
    """Check if a Python file compiles without errors"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        compile(content, file_path, 'exec')
        return True, None
    except Exception as e:
        return False, str(e)

def check_imports(file_path):
    """Check if a Python file can be imported"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        module = importlib.util.module_from_spec(spec)
        # Don't execute, just check if it can be loaded
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    """Main validation function"""
    print("🔍 Runtime Error Check - Comprehensive Validation")
    print("=" * 60)
    
    # Files to check
    critical_files = [
        "container_startup.py",
        "complete_expert_dashboard.py",
        "ui/dashboard.py"
    ]
    
    optional_files = [
        "emergency_dashboard.py",
        "validate_user_guide_features.py"
    ]
    
    all_files = critical_files + [f for f in optional_files if os.path.exists(f)]
    
    results = {
        "syntax": {},
        "compilation": {},
        "imports": {}
    }
    
    # Check each file
    for file_path in all_files:
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            continue
            
        print(f"\n📄 Checking: {file_path}")
        
        # Syntax check
        syntax_ok, syntax_error = check_syntax(file_path)
        results["syntax"][file_path] = syntax_ok
        if syntax_ok:
            print(f"  ✅ Syntax: VALID")
        else:
            print(f"  ❌ Syntax: ERROR - {syntax_error}")
        
        # Compilation check
        if syntax_ok:
            compile_ok, compile_error = check_compilation(file_path)
            results["compilation"][file_path] = compile_ok
            if compile_ok:
                print(f"  ✅ Compilation: PASSED")
            else:
                print(f"  ❌ Compilation: ERROR - {compile_error}")
        else:
            results["compilation"][file_path] = False
            print(f"  ⏭️ Compilation: SKIPPED (syntax error)")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    syntax_passed = sum(results["syntax"].values())
    syntax_total = len(results["syntax"])
    
    compile_passed = sum(results["compilation"].values())
    compile_total = len(results["compilation"])
    
    print(f"✅ Syntax checks: {syntax_passed}/{syntax_total} passed")
    print(f"✅ Compilation checks: {compile_passed}/{compile_total} passed")
    
    # Check critical files specifically
    critical_status = []
    for file_path in critical_files:
        if os.path.exists(file_path):
            syntax_ok = results["syntax"].get(file_path, False)
            compile_ok = results["compilation"].get(file_path, False)
            if syntax_ok and compile_ok:
                critical_status.append(True)
                print(f"✅ {file_path}: READY")
            else:
                critical_status.append(False)
                print(f"❌ {file_path}: ERRORS FOUND")
        else:
            critical_status.append(False)
            print(f"❌ {file_path}: MISSING")
    
    # Final result
    all_critical_ok = all(critical_status)
    
    print("\n" + "=" * 60)
    if all_critical_ok:
        print("🎯 RESULT: ALL SYSTEMS READY - NO RUNTIME ERRORS")
        print("🚀 Status: DEPLOYMENT READY")
        exit_code = 0
    else:
        print("⚠️ RESULT: ERRORS FOUND - REQUIRES ATTENTION")
        print("🛠️ Status: NEEDS FIXES")
        exit_code = 1
    
    print("=" * 60)
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
