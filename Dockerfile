# Offline-ready Dockerfile for Kubernetes AI Assistant
# All dependencies downloaded during build - no internet required at runtime

# Stage 1: Build environment with all dependencies
FROM python:3.11-slim-bullseye as builder

# Set environment variables for consistent builds
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    git \
    curl \
    wget \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    libpthread-stubs0-dev \
    && rm -rf /var/lib/apt/lists/*

# Create build environment
WORKDIR /build
COPY requirements-minimal.txt ./requirements.txt

# Install Python dependencies in virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install essential build tools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install dependencies in order of complexity to maximize cache hits
# First install basic dependencies
RUN pip install --no-cache-dir streamlit==1.32.0 pandas==2.0.3 plotly==5.18.0 numpy==1.25.2 requests==2.31.0 pyyaml==6.0.1 psutil==5.9.8 kubernetes==28.1.0 scikit-learn==1.3.2 langchain==0.1.10

# Install sentence-transformers and chromadb
RUN pip install --no-cache-dir sentence-transformers>=2.5.0 chromadb>=0.4.22

# Install llama-cpp-python with server support and specific build flags to avoid pthread issues
ENV CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS -DCMAKE_EXE_LINKER_FLAGS=-lpthread"
ENV FORCE_CMAKE=1
RUN pip install --no-cache-dir llama-cpp-python[server]>=0.2.55 --verbose

# Create models directory but skip downloads to avoid build failures
RUN mkdir -p /opt/models && \
    echo "Models directory created - downloads skipped for fast build" > /opt/models/README.txt

# Stage 2: Runtime environment
FROM python:3.11-slim-bullseye as runtime

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libgomp1 \
    curl \
    dumb-init \
    gosu \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment and models from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/models /opt/models

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 k8s-agent

# Set up application directory
WORKDIR /app
RUN mkdir -p /data /var/log/k8s-ai-agent /etc/config && \
    chown -R k8s-agent:k8s-agent /app /data /var/log/k8s-ai-agent /opt/models

# Install GlusterFS client tools and system utilities for host access
RUN apt-get update && apt-get install -y --no-install-recommends \
    glusterfs-client \
    glusterfs-common \
    procps \
    util-linux \
    sysstat \
    net-tools \
    iproute2 \
    lsof \
    strace \
    htop \
    iotop \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install kubectl for interactive functionality
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/kubectl \
    && kubectl version --client

# Copy application code - Enhanced AI Agent
COPY --chown=k8s-agent:k8s-agent agent/ ./agent/
COPY --chown=k8s-agent:k8s-agent ui/ ./ui/
COPY --chown=k8s-agent:k8s-agent scheduler/ ./scheduler/
COPY --chown=k8s-agent:k8s-agent glusterfs/ ./glusterfs/
COPY --chown=k8s-agent:k8s-agent scripts/ ./scripts/
COPY --chown=k8s-agent:k8s-agent .streamlit/ ./.streamlit/
# Copy LLaMA server components
COPY --chown=k8s-agent:k8s-agent setup_llama_server.py ./
COPY --chown=k8s-agent:k8s-agent start_llama.sh ./
COPY --chown=k8s-agent:k8s-agent quick_start_llama.py ./
COPY --chown=k8s-agent:k8s-agent test_llama_integration.py ./
COPY --chown=k8s-agent:k8s-agent simple_dashboard.py ./
COPY --chown=k8s-agent:k8s-agent ai_dashboard.py ./
COPY --chown=k8s-agent:k8s-agent app_wrapper.py ./
COPY --chown=k8s-agent:k8s-agent interactive_chat.py ./
COPY --chown=k8s-agent:k8s-agent lightweight_ai_dashboard.py ./
COPY --chown=k8s-agent:k8s-agent health_server.py ./
COPY --chown=k8s-agent:k8s-agent simple_app.py ./
COPY --chown=k8s-agent:k8s-agent container_startup.py ./

# Copy NEW FIXED FILES for proper LLaMA integration
COPY --chown=k8s-agent:k8s-agent fixed_container_startup.py ./
COPY --chown=k8s-agent:k8s-agent runtime_fixed_dashboard.py ./
COPY --chown=k8s-agent:k8s-agent complete_expert_dashboard.py ./
COPY --chown=k8s-agent:k8s-agent quick_fix_integration.sh ./
COPY --chown=k8s-agent:k8s-agent IMMEDIATE_FIX_GUIDE.md ./

# Make shell scripts executable
RUN chmod +x ./start_llama.sh ./quick_fix_integration.sh
# NO MORE BASH ENTRYPOINT - causes GLIBC issues

# Clean up any Python cache files and Streamlit cache that might have been copied
RUN find /app -name "*.pyc" -delete && \
    find /app -name "*.pyo" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + || true && \
    rm -rf /app/.streamlit/.cache* || true && \
    rm -rf /app/.streamlit/cache* || true

# Set environment variables for offline operation and FIXED port configuration
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SENTENCE_TRANSFORMERS_HOME="/opt/models" \
    HF_HOME="/opt/models" \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    ANONYMIZED_TELEMETRY=False \
    CHROMA_SERVER_NOFILE=1048576 \
    CHROMA_TELEMETRY=False \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=False \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    LLAMA_SERVER_PORT=8080 \
    LLAMA_SERVER_HOST=0.0.0.0 \
    K8S_AI_MODE=interactive \
    K8S_AI_AUTOMATION_LEVEL=semi_auto \
    K8S_AI_CONFIDENCE_THRESHOLD=80

# Switch to non-root user for default operation
USER k8s-agent

# Health check - Updated for proper port configuration (8501 for UI, 8080 for LLaMA)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || curl -f http://localhost:8080/health || exit 1

# Expose ports - 8080 for LLaMA API, 8501 for Streamlit UI, 9090 for metrics
EXPOSE 8080 8501 9090

# NO ENTRYPOINT - Direct Python execution to avoid ALL shell issues
# This completely eliminates GLIBC version conflicts

# Default command - runs the FIXED startup script for proper LLaMA+Streamlit integration
CMD ["python", "fixed_container_startup.py"]