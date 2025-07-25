#!/usr/bin/env python3
"""
Direct test of the interactive AI dashboard - launch directly
"""
import subprocess
import sys
import os
import time

def launch_interactive_dashboard():
    """Launch the enhanced interactive dashboard directly"""
    print("🚀 Launching Interactive Kubernetes AI Agent Dashboard")
    print("=" * 60)
    
    # Check if streamlit is available
    try:
        import streamlit
        print("✅ Streamlit is available")
    except ImportError:
        print("❌ Streamlit not available - please install: pip install streamlit")
        return
    
    # Find the best dashboard to use
    dashboard_files = [
        "lightweight_ai_dashboard.py",
        "ai_dashboard.py", 
        "ui/dashboard.py",
        "simple_dashboard.py"
    ]
    
    dashboard_to_use = None
    for dashboard in dashboard_files:
        if os.path.exists(dashboard):
            dashboard_to_use = dashboard
            print(f"✅ Found dashboard: {dashboard}")
            break
    
    if not dashboard_to_use:
        print("❌ No dashboard file found")
        return
    
    # Launch Streamlit
    print(f"\n🌐 Starting interactive dashboard: {dashboard_to_use}")
    print("📱 The dashboard will open with:")
    print("   • 💬 Interactive AI chat for troubleshooting")
    print("   • 🔍 Expert-level root cause analysis")
    print("   • 🛠️ Step-by-step remediation guidance")
    print("   • 📊 Real-time cluster monitoring")
    print("   • 🤖 Automated issue detection")
    
    print(f"\n🔗 Access URL: http://localhost:8501")
    print("   (Browser should open automatically)")
    
    try:
        # Launch streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            dashboard_to_use,
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ]
        
        print(f"\n▶️ Running: {' '.join(cmd)}")
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to launch dashboard: {e}")

if __name__ == "__main__":
    launch_interactive_dashboard()
