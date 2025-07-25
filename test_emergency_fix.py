#!/usr/bin/env python3
"""
Quick test to verify the emergency dashboard works
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_emergency_dashboard():
    """Test if emergency dashboard can start"""
    try:
        print("🧪 Testing emergency dashboard import...")
        import emergency_dashboard
        print("✅ Emergency dashboard imports successfully!")
        return True
    except Exception as e:
        print(f"❌ Emergency dashboard failed: {e}")
        return False

def test_chromadb_import():
    """Test ChromaDB import with proper error handling"""
    try:
        print("🧪 Testing ChromaDB import...")
        os.environ["CHROMA_TELEMETRY"] = "false"
        os.environ["ANONYMIZED_TELEMETRY"] = "false"
        import chromadb
        print("✅ ChromaDB imports successfully!")
        return True
    except RuntimeError as e:
        print(f"⚠️ ChromaDB RuntimeError (expected in container): {e}")
        return False
    except ImportError as e:
        print(f"⚠️ ChromaDB not available: {e}")
        return False
    except Exception as e:
        print(f"❌ ChromaDB unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick Dashboard Test")
    print("=" * 40)
    
    # Test emergency dashboard
    emergency_ok = test_emergency_dashboard()
    
    # Test ChromaDB
    chromadb_ok = test_chromadb_import()
    
    print("\n📊 Test Results:")
    print(f"Emergency Dashboard: {'✅ PASS' if emergency_ok else '❌ FAIL'}")
    print(f"ChromaDB Available: {'✅ YES' if chromadb_ok else '⚠️ NO (will use emergency mode)'}")
    
    if emergency_ok:
        print("\n🎯 RECOMMENDATION: Use emergency dashboard for reliable startup")
        print("🔧 Command: streamlit run emergency_dashboard.py --server.port=8080")
    else:
        print("\n❌ CRITICAL: Emergency dashboard also failed!")
        sys.exit(1)
