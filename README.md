# 🤖 Kubernetes AI Assistant (Offline Edition)

A comprehensive AI-powered Kubernetes cluster management and monitoring solution with **complete offline capabilities** and intelligent remediation features.

## 🔒 Offline Mode Features

- **🌐 No Internet Required**: All processing happens locally within your cluster
- **🔐 Data Privacy**: No external API calls or data transmission
- **⚡ Fast Response**: Local LLM inference with optimized models
- **🛡️ Secure**: Complete air-gapped operation capability
- **📦 Self-Contained**: All dependencies bundled in the container

## 🚀 Key Features

### 🖥️ Interactive Web Dashboard (NodePort Access)
- **Offline Chat Interface**: Chat with a local AI assistant about your cluster
- **Real-time Monitoring**: Live cluster metrics, node status, and resource usage
- **Action Execution**: Direct command execution from natural language prompts
- **Issue Management**: Automatic issue detection with guided remediation
- **External Access**: Available via NodePort for easy external access

### ⚙️ Local LLaMA.cpp Integration
- **CPU-Optimized Inference**: Fast, quantized local language models
- **GGUF Model Support**: Automatic model downloading and management
- **Offline RAG System**: Retrieval-Augmented Generation with local knowledge base
- **Action Processing**: Natural language to Kubernetes commands

### 📊 ML-Based Resource Forecasting
- **Resource Prediction**: ML-based CPU and memory usage forecasting
- **Pod Placement Optimization**: Intelligent scheduling recommendations
- **Capacity Planning**: Proactive cluster scaling insights
- **Offline Analytics**: All processing done locally

### 📦 GlusterFS Health Monitoring
- **Heal Map Visualization**: Visual representation of volume health
- **Split-brain Detection**: Automatic detection and repair guidance
- **Peer Status Monitoring**: Track GlusterFS node connectivity
- **Log-based Analysis**: Intelligent log parsing for issue identification

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (1.19+)
- kubectl configured
- Python 3.11+
- 8GB+ RAM (for running local LLMs)
- 50GB+ storage (for models and data)

### 1. Clone and Setup
```bash
git clone https://github.com/your-org/k8sAIagent.git
cd k8sAIagent

# Install Python dependencies
pip install -r requirements.txt

# Make scripts executable
chmod +x models/download_models.sh
chmod +x scripts/llama_runner.py
```

### 2. Download AI Models
```bash
# See available models
./models/download_models.sh --list

# Get recommendations for your system
./models/download_models.sh --recommend

# Download a model (e.g., Mistral 7B - good balance of size/performance)
./models/download_models.sh --download mistral-7b-instruct

# Install llama.cpp if not already installed
./models/download_models.sh --install-llama-cpp
```

### 3. Run Locally
```bash
# Start the AI assistant (includes dashboard and monitoring)
python3 agent/main.py

# Or run only the dashboard
python3 agent/main.py --dashboard-only

# Check status
python3 agent/main.py --status
```

### 4. Deploy to Kubernetes
```bash
# Apply RBAC and permissions
kubectl apply -f k8s/rbac.yaml

# Deploy the application
kubectl apply -f k8s/pod.yaml
kubectl apply -f k8s/service.yaml

# Check deployment
kubectl get pods -l app=k8s-ai-assistant
kubectl logs -l app=k8s-ai-assistant -f
```

### 5. Access the Dashboard

#### Option A: Direct NodePort Access (External Access)
```bash
# Get node IP addresses
kubectl get nodes -o wide

# Access dashboard directly via NodePort (no port forwarding needed)
# Main Dashboard: http://<node-ip>:30501
# LLM API: http://<node-ip>:30080
# Health Check: http://<node-ip>:30000

# Example: http://192.168.1.100:30501
```

#### Option B: Port Forwarding (Local Access)
```bash
# Set up port forwarding
kubectl port-forward pod/k8s-ai-assistant 8501:8501

# Access locally
# http://localhost:8501
```

### 5. Access Dashboard
- **Local**: http://localhost:8501
- **In-cluster**: http://k8s-ai-assistant.default.svc.cluster.local:8501
- **External**: Configure ingress in `k8s/service.yaml`

## 🎯 Usage Examples

## 🎯 Interactive Usage Examples

### Chat with AI Assistant
```
User: "Show me pods with high CPU usage"
AI: "I found 3 pods with CPU usage above 80%:
     - nginx-web-1: 85% CPU (recommended: scale horizontally)
     - database-1: 92% CPU (recommended: increase resource limits)
     - worker-2: 88% CPU (recommended: check for memory leaks)"
```

### Execute Actions via Chat
```
User: "Restart failed pods"
AI: "✅ Action Executed: Restarted 2 failed pods
     - pod/app-worker-1 restarted
     - pod/scheduler-3 restarted"

User: "Scale deployment nginx to 5 replicas"  
AI: "✅ Action Executed: Scaled deployment nginx to 5 replicas
     Previous: 3 replicas → Current: 5 replicas"

User: "Clean completed jobs"
AI: "✅ Action Executed: Cleaned 7 completed jobs
     Freed up cluster resources and improved performance"
```

### Resource Forecasting
```
User: "Where should I place my new high-memory pod?"
AI: "Based on forecasting analysis:
     - node-1: Expected 60% memory utilization (RECOMMENDED)
     - node-2: Expected 85% memory utilization (NOT RECOMMENDED)
     - node-3: Expected 45% memory utilization (GOOD OPTION)"
```

### Issue Detection and Auto-Remediation
```
Detected Issues:
- Pod nginx-web-1: CrashLoopBackOff
- Node worker-2: High disk usage (89%)
- Service api-gateway: No healthy endpoints

User: "Fix the CrashLoopBackOff issue"
AI: "✅ Action Executed: Analyzed and fixed CrashLoopBackOff
     - Restarted pod nginx-web-1
     - Updated resource limits
     - Pod is now running successfully"
```

### Resource Forecasting
```bash
# Generate 7-day CPU forecast
python3 scripts/llama_runner.py query "Generate a 7-day CPU usage forecast"

# Get pod placement recommendations
python3 agent/main.py --status | jq '.recommendations'
```

### Manual Operations
```python
from agent.remediate import RemediationEngine

remediate = RemediationEngine()

# Restart failed pods
result = remediate.restart_failed_pods()

# Scale a deployment
result = remediate.scale_deployment("default/web-app", 5)

# Drain a node
result = remediate.drain_node("worker-1", ignore_daemonsets=True)
```

## 🔧 Configuration

### Application Config
Create a `config.json` file or use environment variables:

```json
{
  "kubernetes": {
    "config_file": null,
    "monitoring_interval": 30
  },
  "llama": {
    "model_dir": "./models",
    "server_host": "localhost", 
    "server_port": 8080,
    "default_model": "mistral-7b-instruct",
    "auto_start": true
  },
  "rag": {
    "embedding_model": "all-MiniLM-L6-v2",
    "chroma_path": "./chroma_db"
  },
  "forecasting": {
    "data_path": "./forecast_data",
    "forecast_interval": 3600
  },
  "glusterfs": {
    "enabled": false,
    "check_interval": 300
  },
  "dashboard": {
    "enabled": true,
    "port": 8501
  }
}
```

### Environment Variables
```bash
export LOG_LEVEL=INFO
export KUBERNETES_NAMESPACE=default
export LLAMA_MODEL_DIR=/app/models
export RAG_CHROMA_PATH=/app/data/chroma_db
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   Kubernetes    │    │   llama.cpp     │
│   Dashboard     │◄───┤   Monitor       │◄───┤   Server        │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│   RAG Agent     │◄─────────────┘
                        │                 │
                        └─────────────────┘
                                 │
         ┌─────────────────┬─────────────────┬─────────────────┐
         │                 │                 │                 │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Remediation    │ │   Forecaster    │ │   GlusterFS     │ │   Vector DB     │
│   Engine        │ │                 │ │   Analyzer      │ │   (ChromaDB)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Components

1. **Kubernetes Monitor**: Watches cluster state, detects issues
2. **RAG Agent**: Provides intelligent responses using local knowledge + LLM
3. **Remediation Engine**: Executes fixes automatically or on-demand
4. **Resource Forecaster**: Predicts future resource needs using ML
5. **GlusterFS Analyzer**: Monitors distributed storage health
6. **LLaMA Server**: Local LLM inference for natural language processing
7. **Vector Database**: Stores and retrieves knowledge efficiently

## 🔐 Security & Privacy

### Privacy Features
- **No External APIs**: All processing happens locally
- **Offline Capable**: Works without internet connectivity
- **Local LLM Inference**: Your data never leaves your infrastructure
- **Configurable Logging**: Control what information is logged

### Security Best Practices
- **Non-root Containers**: Runs with minimal privileges
- **RBAC Configuration**: Principle of least privilege
- **Read-only Filesystem**: Where possible
- **Resource Limits**: Prevents resource exhaustion
- **Security Contexts**: Enhanced container security

### RBAC Permissions
The assistant requires these permissions:
- **Read**: All cluster resources for monitoring
- **Write**: Pods, deployments, nodes for remediation
- **Create**: Events, logs for issue tracking
- **Delete**: Failed pods, completed jobs for cleanup

## 🛠️ Development

### Project Structure
```
k8sAIagent/
├── agent/                  # Core application
│   ├── main.py            # Entry point
│   ├── monitor.py         # Kubernetes monitoring
│   ├── rag_agent.py       # RAG implementation
│   ├── remediate.py       # Automated remediation
│   └── prompts/           # LLM prompts
├── ui/                    # Streamlit dashboard
│   └── dashboard.py       # Web interface
├── scheduler/             # Resource forecasting
│   └── forecast.py        # ML forecasting
├── glusterfs/             # GlusterFS monitoring
│   └── analyze.py         # Storage health analysis
├── scripts/               # Utility scripts
│   └── llama_runner.py    # LLM server management
├── models/                # AI model storage
│   └── download_models.sh # Model management
├── k8s/                   # Kubernetes manifests
│   ├── rbac.yaml         # RBAC configuration
│   ├── pod.yaml          # Pod specification  
│   └── service.yaml      # Service configuration
└── requirements.txt       # Python dependencies
```

### Building from Source
```bash
# Build Docker image
docker build -t k8s-ai-assistant:latest .

# Run tests (if implemented)
python -m pytest tests/

# Code formatting
black agent/ ui/ scheduler/ glusterfs/
flake8 agent/ ui/ scheduler/ glusterfs/
```

### Adding New Features
1. **New Monitors**: Extend `KubernetesMonitor` class
2. **Custom Remediations**: Add methods to `RemediationEngine`
3. **Additional Forecasts**: Enhance `ResourceForecaster`
4. **UI Components**: Add tabs/pages to Streamlit dashboard
5. **Knowledge Base**: Add documents to RAG system

## 📊 Monitoring & Observability

### Health Checks
- **Liveness**: `/health` endpoint on port 8000
- **Readiness**: `/ready` endpoint on port 8000
- **Startup**: Extended timeout for model loading

### Metrics
- **Cluster Metrics**: CPU, memory, storage utilization
- **Forecast Accuracy**: Model performance tracking
- **Remediation Success**: Action success rates
- **Component Status**: Health of all subsystems

### Logging
- **Structured Logging**: JSON format for parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Component Tagging**: Easy filtering by component
- **Audit Trail**: All remediation actions logged

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Follow coding standards
4. **Add tests**: Ensure functionality works
5. **Update documentation**: Keep README current
6. **Submit a pull request**: Describe your changes

### Development Setup
```bash
# Clone your fork
git clone https://github.com/your-username/k8sAIagent.git
cd k8sAIagent

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Install pre-commit hooks
pre-commit install

# Run in development mode
python3 agent/main.py --verbose
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **llama.cpp**: Efficient LLM inference
- **Streamlit**: Beautiful web applications
- **ChromaDB**: Vector database
- **Kubernetes**: Container orchestration
- **scikit-learn**: Machine learning
- **The open source community**: For making this possible

## 📞 Support

- **Documentation**: Check this README and code comments
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Report security issues privately

## 🗺️ Roadmap

### Version 1.1
- [ ] Multi-cluster support
- [ ] Advanced alerting rules
- [ ] Custom dashboard widgets
- [ ] Plugin architecture

### Version 1.2
- [ ] GitOps integration
- [ ] Policy enforcement
- [ ] Cost optimization
- [ ] Advanced ML models

### Version 2.0
- [ ] Distributed deployment
- [ ] Multi-tenant support
- [ ] Advanced security features
- [ ] Cloud provider integrations

---

**Made with ❤️ for the Kubernetes community**