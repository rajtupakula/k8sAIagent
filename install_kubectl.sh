#!/bin/bash

# Quick kubectl installer for local testing
# This script installs kubectl if it's not available

set -e

echo "🔧 Checking kubectl installation..."

# Check if kubectl is already available
if command -v kubectl &> /dev/null; then
    echo "✅ kubectl is already installed: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    exit 0
fi

echo "❌ kubectl not found. Installing..."

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

case $OS in
    "Darwin")
        echo "📱 Detected macOS"
        if command -v brew &> /dev/null; then
            echo "🍺 Using Homebrew to install kubectl..."
            brew install kubectl
        else
            echo "📥 Downloading kubectl directly..."
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
            chmod +x kubectl
            sudo mv kubectl /usr/local/bin/
        fi
        ;;
    "Linux")
        echo "🐧 Detected Linux"
        echo "📥 Downloading kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        exit 1
        ;;
esac

# Verify installation
if command -v kubectl &> /dev/null; then
    echo "✅ kubectl installed successfully!"
    echo "📋 Version: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Configure kubectl to connect to your cluster"
    echo "   2. Test with: kubectl get nodes"
    echo "   3. Run the interactive chat: streamlit run interactive_chat.py"
else
    echo "❌ kubectl installation failed"
    exit 1
fi
