# LLaMA Server Setup Guide

This guide explains how to set up and use the LLaMA server for enhanced AI-powered Kubernetes troubleshooting and live command execution.

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
# Run the quick start script
./start_llama.sh
```

### Option 2: Manual Setup
```bash
# Run interactive setup
python3 setup_llama_server.py --setup

# Or manual commands
python3 setup_llama_server.py --start
```

## 📋 What the LLaMA Server Provides

### Enhanced Capabilities
- **Live Command Generation**: AI generates precise kubectl commands
- **Smart Remediation**: Automatic issue resolution with AI reasoning
- **Context-Aware Analysis**: Deep understanding of your specific K8s environment
- **Real-time Troubleshooting**: Interactive problem-solving conversations

### Before vs After LLaMA Server

| Feature | Offline Mode | Online Mode (LLaMA) |
|---------|-------------|-------------------|
| Troubleshooting | Pre-defined responses | AI-generated analysis |
| Commands | Static suggestions | Dynamic, context-aware |
| Remediation | Manual steps | Automated execution |
| Learning | Basic patterns | Continuous improvement |

## 🛠️ Installation Requirements

### System Requirements
- **RAM**: 8GB+ recommended (4GB minimum)
- **Storage**: 5GB+ free space per model
- **CPU**: Multi-core recommended
- **GPU**: Optional (NVIDIA CUDA for faster inference)

### Software Requirements
- Python 3.8+
- pip package manager
- Internet connection (for model download)

## 🤖 Available Models

### Recommended Models for K8s Troubleshooting

1. **mistral-7b-instruct** (Default)
   - Size: ~4GB
   - Best for: Technical analysis and troubleshooting
   - Speed: Fast inference
   - Quality: High accuracy for system tasks

2. **codellama-7b-instruct**
   - Size: ~4GB  
   - Best for: Command generation and code analysis
   - Speed: Fast inference
   - Quality: Excellent for DevOps tasks

3. **llama-2-7b-chat**
   - Size: ~4GB
   - Best for: General conversation and explanations
   - Speed: Fast inference
   - Quality: Good overall performance

## 🔧 Manual Management Commands

### Server Control
```bash
# Start server with default model
python3 setup_llama_server.py --start

# Start with specific model
python3 setup_llama_server.py --start --model mistral-7b-instruct

# Stop server
python3 setup_llama_server.py --stop

# Check status
python3 setup_llama_server.py --status
```

### Model Management
```bash
# Using the llama_runner directly
python3 scripts/llama_runner.py list
python3 scripts/llama_runner.py download mistral-7b-instruct
python3 scripts/llama_runner.py start --model mistral-7b-instruct
```

## 🖥️ Dashboard Integration

### LLaMA Server Controls in Dashboard

The Advanced Dashboard includes built-in LLaMA server management:

1. **Sidebar Controls**
   - Server status indicator
   - Start/Stop buttons
   - Server health testing
   - Setup guide access

2. **System Status Display**
   - Shows "Online Mode" when LLaMA is available
   - "Offline Mode" when server is down
   - Model information and capabilities

3. **Chat Interface**
   - Model selection dropdown
   - Enhanced AI responses when online
   - Streaming support for real-time answers

## 🧪 Testing the Setup

### Verify Server is Running
```bash
# Check server health
curl http://localhost:8080/health

# Test query
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 20}'
```

### Test from Dashboard
1. Open Advanced Dashboard: `streamlit run ui/advanced_dashboard.py`
2. Check sidebar for "✅ RAG Agent: Online Mode"
3. Use "🧪 Test LLaMA" button
4. Try a query in the chat interface

## 🔍 Troubleshooting

### Common Issues

#### Server Won't Start
```bash
# Check if port 8080 is in use
lsof -i :8080

# Check model file exists
ls -la models/

# Check logs for errors
python3 setup_llama_server.py --verbose --start
```

#### Installation Issues
```bash
# Reinstall llama-cpp-python
pip uninstall llama-cpp-python
pip install llama-cpp-python --upgrade

# For CUDA support
pip install llama-cpp-python[cuda] --upgrade --force-reinstall --no-cache-dir
```

#### Performance Issues
- **Slow responses**: Consider GPU acceleration
- **High memory usage**: Use smaller models or reduce context size
- **Timeouts**: Increase timeout settings in configuration

### Model Download Issues
- Check internet connection
- Verify disk space
- Use alternative model sources if needed

## ⚙️ Advanced Configuration

### Custom Server Settings
```python
# In setup_llama_server.py, modify LlamaServerManager parameters:
manager = LlamaServerManager(
    server_host="0.0.0.0",    # Allow external access
    server_port=8080,         # Custom port
    context_size=8192,        # Larger context window
    threads=8                 # More CPU threads
)
```

### Environment Variables
```bash
export LLAMA_SERVER_HOST=localhost
export LLAMA_SERVER_PORT=8080
export LLAMA_CONTEXT_SIZE=4096
export LLAMA_THREADS=4
```

## 🚀 Production Deployment

### Docker Deployment
```dockerfile
# Add to existing Dockerfile
RUN pip install llama-cpp-python
COPY models/ /app/models/
EXPOSE 8080
```

### Kubernetes Deployment
```yaml
# Add LLaMA server as sidecar container
- name: llama-server
  image: your-image:latest
  ports:
  - containerPort: 8080
  resources:
    requests:
      memory: "4Gi"
      cpu: "2"
    limits:
      memory: "8Gi"
      cpu: "4"
```

## 📊 Performance Optimization

### Hardware Recommendations
- **CPU**: 8+ cores for best performance
- **RAM**: 16GB+ for multiple models
- **GPU**: NVIDIA RTX 3060+ for CUDA acceleration
- **Storage**: SSD for faster model loading

### Software Optimization
- Use quantized models (Q4_K_M format)
- Adjust context window based on needs
- Enable GPU acceleration when available
- Use appropriate thread count

## 📚 Usage Examples

### Example Queries with LLaMA Online

1. **Complex Troubleshooting**
   ```
   "My pods are crashlooping in the production namespace. 
   The logs show connection timeout errors. Please analyze 
   and provide a step-by-step remediation plan."
   ```

2. **Performance Analysis**
   ```
   "Show me how to identify and fix high memory usage 
   across my Kubernetes cluster. Include specific 
   commands and monitoring recommendations."
   ```

3. **Security Audit**
   ```
   "Perform a security assessment of my cluster 
   configuration and suggest improvements based on 
   current best practices."
   ```

## 🎯 Benefits of LLaMA Integration

### For DevOps Teams
- Reduced MTTR (Mean Time To Resolution)
- Automated troubleshooting workflows
- Expert-level guidance for junior team members
- 24/7 AI assistance for critical issues

### For Organizations
- Lower operational costs
- Improved system reliability
- Knowledge preservation and sharing
- Standardized troubleshooting processes

---

## 🆘 Need Help?

1. **Check the logs**: `python3 setup_llama_server.py --verbose --status`
2. **Test connectivity**: Use the dashboard test buttons
3. **Verify installation**: Ensure all requirements are met
4. **Review documentation**: Check model and server specifications

The LLaMA server transforms your K8s AI Agent from a helpful assistant into a powerful AI-driven troubleshooting expert capable of real-time analysis and automated remediation.
