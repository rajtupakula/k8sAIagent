# Scripts Directory

This directory contains build and deployment scripts for the Kubernetes AI Assistant.

## Core Build Scripts

### `build.sh`
Main build script (Jenkins compatible). This is a wrapper around `build-optimized.sh`.
```bash
./scripts/build.sh
```

### `build-optimized.sh`
Optimized build script with aggressive space optimization:
- **Redirects ALL storage to /home directory** (prevents "no space left on device")
- Container runtime auto-detection (Docker/Podman/Buildah)
- Automatic image export to `$HOME/k8s-ai-images/`
- Complete temporary file redirection to avoid root filesystem
- Pre-build space checking with warnings

**Environment Variables:**
- `VERSION`: Image version (default: 1.0.0)
- `IMAGE_NAME`: Container image name (default: k8s-ai-agent)
- `REGISTRY`: Container registry URL
- `BUILD_TEMP_DIR`: Temporary build directory (default: $HOME/k8s-ai-build)
- `CONTAINER_STORAGE_ROOT`: Container storage root (default: $HOME/.containers)

### `emergency-space-cleanup.sh`
Emergency cleanup script for container builds when encountering disk space issues.
```bash
./scripts/emergency-space-cleanup.sh
```

## Deployment Scripts

### `deploy.sh` / `deploy_simple.sh` / `easy-deploy.sh`
Various deployment options for different environments.

### `create-deployment-package.sh`
Creates deployment packages for distribution.

## Test Scripts

### `test-*.py`
Python test scripts for various components:
- `test_dashboard.py` - Dashboard functionality tests
- `test_expert_remediation.py` - Expert remediation tests
- `test_historical_learning.py` - Historical learning tests
- `test_latest_llm.py` - LLM functionality tests
- `test_offline.py` - Offline mode tests

## Utility Scripts

### `llama_runner.py`
LLaMA model runner utility.

### `runtime-config.sh`
Runtime configuration script.

### `setup_offline.sh`
Offline environment setup script.

## Usage Examples

**Standard build:**
```bash
./scripts/build.sh
```

**Build with custom registry:**
```bash
REGISTRY=myregistry.com ./scripts/build.sh
```

**Build with space optimization for limited disk:**
```bash
BUILD_TEMP_DIR="$HOME/.build" ./scripts/build.sh
```

**Emergency cleanup if build fails due to space:**
```bash
./scripts/emergency-space-cleanup.sh
```
