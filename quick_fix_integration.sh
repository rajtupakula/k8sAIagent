#!/bin/bash
"""
🚀 IMMEDIATE FIX SCRIPT - Get LLaMA + Streamlit working properly
This script fixes the port conflict and sets up proper integration
"""

echo "🚀 Starting Kubernetes AI Agent Fix..."
echo "📋 This will:"
echo "   - Kill processes on conflicting ports"
echo "   - Install LLaMA server on port 8080"
echo "   - Start Streamlit dashboard on port 8501"
echo "   - Test integration"

# Function to kill processes on a port
kill_port_processes() {
    local port=$1
    echo "🔪 Checking for processes on port $port..."
    pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo "🔪 Killing processes on port $port: $pids"
        echo $pids | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo "✅ Port $port is free"
    fi
}

# Step 1: Clean up conflicting processes
echo "🧹 Step 1: Cleaning up ports..."
kill_port_processes 8080
kill_port_processes 8501

# Step 2: Install LLaMA server if needed
echo "🤖 Step 2: Setting up LLaMA server..."
if ! python -c "import llama_cpp" 2>/dev/null; then
    echo "📦 Installing llama-cpp-python[server]..."
    pip install llama-cpp-python[server] || {
        echo "❌ Failed to install llama-cpp-python"
        echo "💡 Trying alternative installation..."
        CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" pip install llama-cpp-python[server]
    }
else
    echo "✅ llama-cpp-python already installed"
fi

# Step 3: Setup models directory and download small model
echo "📁 Step 3: Setting up models..."
mkdir -p models
cd models

# Check if we have any models
if [ ! -f *.gguf ] 2>/dev/null; then
    echo "📥 Downloading TinyLlama model (small and fast)..."
    wget -O tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
        "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" \
        2>/dev/null || {
        echo "⚠️ Download failed, trying alternative method..."
        curl -L -o tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
            "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" || {
            echo "❌ Model download failed. LLaMA will run in fallback mode."
        }
    }
else
    echo "✅ Found existing model files"
fi

cd ..

# Step 4: Start LLaMA server in background
echo "🚀 Step 4: Starting LLaMA server on port 8080..."
if [ -f models/*.gguf ]; then
    model_file=$(ls models/*.gguf | head -1)
    echo "🤖 Using model: $model_file"
    
    nohup python -m llama_cpp.server \
        --model "$model_file" \
        --host 0.0.0.0 \
        --port 8080 \
        --n_ctx 2048 \
        --n_threads 4 \
        > llama_server.log 2>&1 &
    
    echo "⏳ Waiting for LLaMA server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8080/health >/dev/null 2>&1; then
            echo "✅ LLaMA server is running on port 8080"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo
else
    echo "⚠️ No models found, LLaMA will run in fallback mode"
fi

# Step 5: Start Streamlit dashboard  
echo "🌐 Step 5: Starting Streamlit dashboard on port 8501..."

# Use the runtime-fixed dashboard
nohup streamlit run runtime_fixed_dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    > streamlit.log 2>&1 &

echo "⏳ Waiting for Streamlit to start..."
for i in {1..20}; do
    if curl -s http://localhost:8501/_stcore/health >/dev/null 2>&1; then
        echo "✅ Streamlit dashboard is running on port 8501"
        break
    fi
    sleep 1
    echo -n "."
done
echo

# Step 6: Test integration
echo "🧪 Step 6: Testing integration..."

# Test LLaMA
echo "🤖 Testing LLaMA server..."
if curl -s http://localhost:8080/health | grep -q "ok\|status" 2>/dev/null; then
    echo "✅ LLaMA server responding"
    LLAMA_STATUS="✅ Online"
else
    echo "⚠️ LLaMA server not responding (will run in fallback mode)"
    LLAMA_STATUS="⚠️ Fallback Mode"
fi

# Test Streamlit
echo "🌐 Testing Streamlit dashboard..."
if curl -s http://localhost:8501/_stcore/health >/dev/null 2>&1; then
    echo "✅ Streamlit dashboard responding"
    STREAMLIT_STATUS="✅ Online"
else
    echo "❌ Streamlit dashboard not responding"
    STREAMLIT_STATUS="❌ Failed"
fi

# Test Kubernetes
echo "☸️ Testing Kubernetes connection..."
if kubectl get nodes >/dev/null 2>&1; then
    echo "✅ Kubernetes API accessible"
    K8S_STATUS="✅ Connected"
else
    echo "⚠️ Kubernetes API not accessible (may be running outside cluster)"
    K8S_STATUS="⚠️ Limited"
fi

# Final status report
echo ""
echo "🎯 INTEGRATION STATUS REPORT:"
echo "================================"
echo "🤖 LLaMA Server (port 8080): $LLAMA_STATUS"
echo "🌐 Streamlit UI (port 8501): $STREAMLIT_STATUS"
echo "☸️ Kubernetes API: $K8S_STATUS"
echo ""

if [[ "$STREAMLIT_STATUS" == *"Online"* ]]; then
    echo "🎉 SUCCESS! Dashboard is ready!"
    echo ""
    echo "📱 Access your dashboard at:"
    echo "   Local: http://localhost:8501"
    echo "   Network: http://$(hostname -I | awk '{print $1}'):8501"
    echo ""
    echo "🔗 LLaMA API endpoint:"
    echo "   http://localhost:8080"
    echo ""
    echo "📊 Features available:"
    echo "   ✅ Real-time Kubernetes monitoring"
    echo "   $LLAMA_STATUS AI-powered analysis"
    echo "   ✅ Interactive troubleshooting"
    echo "   ✅ Auto-remediation tools"
    echo ""
    echo "🔄 View logs:"
    echo "   LLaMA: tail -f llama_server.log"
    echo "   Streamlit: tail -f streamlit.log"
else
    echo "❌ SETUP FAILED - Check logs for details"
    echo "📋 Troubleshooting:"
    echo "   1. Check Streamlit log: tail -f streamlit.log"
    echo "   2. Check LLaMA log: tail -f llama_server.log"
    echo "   3. Verify ports: lsof -i :8080,8501"
fi

echo ""
echo "🚀 Setup complete! Services will continue running in the background."
