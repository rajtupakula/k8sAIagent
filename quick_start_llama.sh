#!/bin/bash

# IMMEDIATE FIX SCRIPT - Get LLaMA Server Running in 2 Minutes
# This script will set up a working LLaMA server for the dashboard

echo "🚀 Kubernetes AI Agent - LLaMA Server Setup"
echo "============================================="

# Step 1: Kill any conflicting processes
echo "🔧 Cleaning up conflicting processes..."
sudo lsof -ti:8080 | xargs kill -9 2>/dev/null || true
pkill -f streamlit 2>/dev/null || true

# Step 2: Check if llama-cpp-python is installed
echo "📦 Checking dependencies..."
if ! python3 -c "import llama_cpp" 2>/dev/null; then
    echo "Installing llama-cpp-python with server support..."
    pip3 install llama-cpp-python[server] --upgrade
fi

# Step 3: Create models directory
echo "📁 Setting up models directory..."
mkdir -p models
cd models

# Step 4: Download a small model if not exists
MODEL_FILE="llama-2-7b-chat.Q4_K_M.gguf"
if [ ! -f "$MODEL_FILE" ]; then
    echo "⬇️ Downloading LLaMA 2 7B model (this may take a few minutes)..."
    wget -O "$MODEL_FILE" "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
    
    if [ $? -ne 0 ]; then
        echo "❌ Download failed. Trying alternative smaller model..."
        wget -O "phi-2.Q4_K_M.gguf" "https://huggingface.co/microsoft/phi-2-gguf/resolve/main/phi-2.q4_k_m.gguf"
        MODEL_FILE="phi-2.Q4_K_M.gguf"
    fi
else
    echo "✅ Model file already exists: $MODEL_FILE"
fi

cd ..

# Step 5: Start LLaMA server
echo "🚀 Starting LLaMA server..."
echo "Server will be available at http://localhost:8080"

# Start server in background
nohup python3 -m llama_cpp.server \
    --model "models/$MODEL_FILE" \
    --host 0.0.0.0 \
    --port 8080 \
    --n_ctx 4096 \
    --verbose > llama_server.log 2>&1 &

# Get the PID
LLAMA_PID=$!
echo "LLaMA server started with PID: $LLAMA_PID"

# Wait for server to start
echo "⏳ Waiting for server to initialize..."
sleep 10

# Test server
for i in {1..30}; do
    if curl -s http://localhost:8080/health >/dev/null 2>&1; then
        echo "✅ LLaMA server is running successfully!"
        break
    elif curl -s http://localhost:8080/v1/models >/dev/null 2>&1; then
        echo "✅ LLaMA server is running successfully!"
        break
    else
        echo "⏳ Waiting for server... ($i/30)"
        sleep 2
    fi
done

# Verify server is responding
echo ""
echo "🧪 Testing server endpoints..."
echo "Health check:"
curl -s http://localhost:8080/health || echo "Health endpoint not available"

echo ""
echo "Models endpoint:"
curl -s http://localhost:8080/v1/models || echo "Models endpoint not available"

echo ""
echo "🎉 Setup complete! Now you can:"
echo "1. Start the dashboard: streamlit run production_dashboard.py --server.port 8501"
echo "2. Open your browser to: http://localhost:8501"
echo ""
echo "To monitor LLaMA server logs: tail -f llama_server.log"
echo "To stop LLaMA server: kill $LLAMA_PID"
echo ""
echo "✅ LLaMA server PID: $LLAMA_PID"
echo "✅ Dashboard will show: '🟢 LLaMA Online' when connected"
