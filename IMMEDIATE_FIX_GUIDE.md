# IMMEDIATE FIX GUIDE - Real-Time Data & LLaMA Integration

## Current Issues Identified:

1. **Port 8080 Conflict**: Streamlit app running instead of LLaMA server
2. **Missing Real Kubernetes Integration**: Dashboard not connected to live cluster
3. **No Actual LLaMA Server**: Need proper llama.cpp server setup

## IMMEDIATE SOLUTION - 5 Minutes to Working System

### 🚀 QUICKEST FIX (For Container Environment):
```bash
# Run the automated fix script
./quick_fix_integration.sh
```

### Manual Steps (If needed):

### Step 1: Stop Conflicting Services
```bash
# Find and kill any process on port 8080
lsof -ti:8080 2>/dev/null | xargs kill -9 2>/dev/null || true

# Find and kill any Streamlit processes
pkill -f streamlit 2>/dev/null || true
```

### Step 2: Start Real LLaMA Server (Choose ONE method)

#### Method A: Using llama-cpp-python (Recommended)
```bash
# Install llama-cpp-python with server
pip install llama-cpp-python[server]

# Download a model (7B model for fast testing)
mkdir -p models
cd models
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

# Start LLaMA server on port 8080
python -m llama_cpp.server \
  --model models/llama-2-7b-chat.Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --n_ctx 4096 \
  --verbose
```

#### Method B: Using our llama_runner.py
```bash
cd /Users/rtupakul/Documents/GitHub/cisco/k8sAIAgent

# Download model using our script
python scripts/llama_runner.py download llama-2-7b-chat

# Start server
python scripts/llama_runner.py start llama-2-7b-chat
```

### Step 3: Verify LLaMA Server is Working
```bash
# Test health endpoint
curl http://localhost:8080/health

# Test completion endpoint
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 10}'
```

### Step 4: Start the Fixed Dashboard
```bash
# Use the runtime-fixed dashboard (no errors, proper integration)
streamlit run runtime_fixed_dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

# Alternative: Use the complete expert dashboard 
streamlit run complete_expert_dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

### Step 5: Verify Real-Time Kubernetes Data
The dashboard should now show:
- ✅ Real Kubernetes API connection
- ✅ Live pod/node data from your cluster
- ✅ LLaMA server integration for AI responses
- ✅ Interactive chat with actual AI analysis

## Quick Validation Commands

```bash
# 1. Check LLaMA server
curl -s http://localhost:8080/health | jq

# 2. Check Kubernetes connection
kubectl get nodes
kubectl get pods -A

# 3. Check dashboard
curl -s http://localhost:8501/_stcore/health
```

## Expected Results:

1. **Port 8080**: LLaMA API server responding with JSON
2. **Port 8501**: Streamlit dashboard with real Kubernetes data
3. **AI Chat**: Actual LLaMA responses, not pattern matching
4. **Cluster Data**: Live pods, nodes, events from your cluster

## If Still Having Issues:

### Alternative LLaMA Setup (Ollama)
```bash
# Install Ollama (easier alternative)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2:7b

# Start Ollama server (runs on port 11434 by default)
ollama serve

# Update dashboard to use port 11434 instead of 8080
```

### Kubernetes Connection Issues
```bash
# Verify kubectl works
kubectl cluster-info

# Check kubeconfig
cat ~/.kube/config

# Test with simple query
kubectl get namespaces
```

## SUCCESS INDICATORS:

✅ LLaMA server responds with JSON on port 8080
✅ Dashboard shows "🟢 LLaMA Server Online" 
✅ Dashboard shows "✅ AI Agent Online - Kubernetes cluster connected"
✅ Chat responses come from actual AI, not patterns
✅ Cluster resources show real data from your cluster
✅ Auto-remediation features work with real commands

This should get you a fully functional system in under 5 minutes!
