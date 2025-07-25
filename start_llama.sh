#!/bin/bash
# Quick start script for LLaMA server setup

echo "🚀 K8s AI Agent - LLaMA Server Quick Start"
echo "=========================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "setup_llama_server.py" ]; then
    echo "❌ Please run this script from the k8sAIAgent directory"
    exit 1
fi

echo "🔍 Checking system requirements..."

# Check available disk space (rough estimate)
available_space=$(df . | tail -1 | awk '{print $4}')
available_gb=$((available_space / 1024 / 1024))

if [ $available_gb -lt 5 ]; then
    echo "⚠️  Warning: Only ${available_gb}GB available. Recommend 5GB+ for model download"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ System checks passed"

# Run the Python setup script
echo "🤖 Starting LLaMA server setup..."
python3 setup_llama_server.py --setup

# Check if setup was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. LLaMA server should now be running"
    echo "2. Start the Advanced Dashboard: streamlit run ui/advanced_dashboard.py"
    echo "3. The dashboard will show 'AI Agent Active (Online Mode)'"
    echo ""
    echo "🔧 Manual controls:"
    echo "  Start server: python3 setup_llama_server.py --start"
    echo "  Stop server:  python3 setup_llama_server.py --stop"
    echo "  Check status: python3 setup_llama_server.py --status"
else
    echo "❌ Setup failed. Check the error messages above."
    exit 1
fi
