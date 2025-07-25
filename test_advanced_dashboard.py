#!/usr/bin/env python3
"""
Test Advanced Dashboard UI - Quick validation script
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test if all required imports work"""
    try:
        # Test basic imports
        import streamlit as st
        print("✅ Streamlit available")
        
        import pandas as pd
        print("✅ Pandas available")
        
        try:
            import plotly.express as px
            import plotly.graph_objects as go
            print("✅ Plotly available")
        except ImportError:
            print("⚠️  Plotly not available - will use fallback mode")
        
        # Test dashboard import
        from ui.advanced_dashboard import AdvancedDashboardUI
        print("✅ Advanced Dashboard UI class imports successfully")
        
        # Test basic initialization
        dashboard = AdvancedDashboardUI()
        print("✅ Advanced Dashboard UI initializes successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_system_commands():
    """Test system command availability"""
    import subprocess
    
    commands = [
        ('kubectl', 'kubectl version --client'),
        ('free', 'free -m'),
        ('df', 'df -h'),
        ('uptime', 'uptime')
    ]
    
    for cmd_name, cmd in commands:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {cmd_name} command available")
            else:
                print(f"⚠️  {cmd_name} command failed: {result.stderr}")
        except FileNotFoundError:
            print(f"❌ {cmd_name} command not found")
        except Exception as e:
            print(f"⚠️  {cmd_name} command error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Advanced Dashboard UI...")
    print()
    
    print("📦 Testing imports...")
    if test_imports():
        print("✅ All critical imports successful")
    else:
        print("❌ Import test failed")
        sys.exit(1)
    
    print()
    print("🔧 Testing system commands...")
    test_system_commands()
    
    print()
    print("🎯 Advanced Dashboard UI test complete!")
    print("🚀 Ready to deploy Advanced Dashboard UI")
