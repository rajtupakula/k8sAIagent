# Multi-stage Dockerfile for Kubernetes AI Assistant
# Optimized for CPU-only inference with llama.cpp

# Stage 1: Build environment for compiling native dependencies
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for building
ENV CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
ENV FORCE_CMAKE=1

# Create build directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install llama-cpp-python with CPU optimizations
RUN CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS -DLLAMA_NATIVE=ON" \
    pip install --no-cache-dir llama-cpp-python[server] --force-reinstall --no-deps --verbose

# Stage 2: Runtime environment
FROM python:3.11-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    htop \
    procps \
    net-tools \
    dumb-init \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r aiuser && useradd -r -g aiuser -u 1000 aiuser

# Set up application directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/models /app/data /app/logs /app/config /tmp && \
    chown -R aiuser:aiuser /app && \
    chmod +x /app/models/download_models.sh && \
    chmod +x /app/scripts/llama_runner.py

# Create health check script
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8000/health || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown aiuser:aiuser /app/healthcheck.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TOKENIZERS_PARALLELISM=false
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4

# Switch to non-root user
USER aiuser

# Create a simple health check endpoint
RUN echo 'from http.server import HTTPServer, BaseHTTPRequestHandler\n\
import json\n\
import threading\n\
import time\n\
\n\
class HealthHandler(BaseHTTPRequestHandler):\n\
    def do_GET(self):\n\
        if self.path == "/health":\n\
            self.send_response(200)\n\
            self.send_header("Content-Type", "application/json")\n\
            self.end_headers()\n\
            response = {"status": "healthy", "timestamp": time.time()}\n\
            self.wfile.write(json.dumps(response).encode())\n\
        elif self.path == "/ready":\n\
            self.send_response(200)\n\
            self.send_header("Content-Type", "application/json")\n\
            self.end_headers()\n\
            response = {"status": "ready", "timestamp": time.time()}\n\
            self.wfile.write(json.dumps(response).encode())\n\
        else:\n\
            self.send_response(404)\n\
            self.end_headers()\n\
\n\
def start_health_server():\n\
    server = HTTPServer(("0.0.0.0", 8000), HealthHandler)\n\
    server.serve_forever()\n\
\n\
if __name__ == "__main__":\n\
    threading.Thread(target=start_health_server, daemon=True).start()\n\
    import time\n\
    while True:\n\
        time.sleep(60)' > /app/health_server.py

# Expose ports
EXPOSE 8501 8080 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Default command with health server
CMD ["sh", "-c", "python3 /app/health_server.py & python3 -u /app/agent/main.py"]

# Labels for metadata
LABEL maintainer="Kubernetes AI Assistant Team"
LABEL version="1.0.0"
LABEL description="AI-powered Kubernetes monitoring, forecasting, and remediation assistant"
LABEL org.opencontainers.image.source="https://github.com/your-org/k8sAIagent"
LABEL org.opencontainers.image.documentation="https://github.com/your-org/k8sAIagent/README.md"
LABEL org.opencontainers.image.title="Kubernetes AI Assistant"
LABEL org.opencontainers.image.description="AI-powered Kubernetes monitoring and remediation"
LABEL org.opencontainers.image.version="1.0.0"

# Build arguments for customization
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

LABEL org.opencontainers.image.created=$BUILD_DATE
LABEL org.opencontainers.image.revision=$VCS_REF
LABEL org.opencontainers.image.version=$VERSION