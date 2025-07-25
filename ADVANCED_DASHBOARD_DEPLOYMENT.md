# Advanced Dashboard UI - Deployment Fix Guide

## Issue Identified
The Advanced Dashboard UI was failing to load due to missing `plotly` dependency in the container deployment.

## Root Cause
- The `Dockerfile` uses `requirements-minimal.txt` for faster builds
- The Advanced Dashboard UI requires `plotly` for interactive charts
- The minimal requirements didn't include `plotly`

## Fixes Applied

### 1. Updated Requirements (✅ FIXED)
**File:** `requirements-minimal.txt`
```diff
+ plotly==5.18.0  # Required for Advanced Dashboard UI
```

### 2. Added Plotly Fallback (✅ FIXED)
**File:** `ui/advanced_dashboard.py`
- Added graceful fallback when plotly is not available
- Charts display as text summaries instead of failing
- User gets notification about missing dependencies

### 3. Updated Deployment Configuration (✅ FIXED)
**Files:** `docker-compose.yml`, `k8s/k8s-ai-agent.yaml`, `app_wrapper.py`
- Fixed port mapping (8080 instead of 8501)
- Added `UI_MODE=advanced` environment variable
- Updated dashboard priority selection logic

### 4. Created Deployment Scripts (✅ NEW)
**Files:** `deploy_advanced_ui.sh`, `test_advanced_dashboard.py`
- Interactive deployment script with multiple options
- Test script to validate dependencies before deployment

## Deployment Options

### Option 1: Docker Compose (Recommended for Testing)
```bash
# Set environment for Advanced UI
export UI_MODE=advanced

# Deploy with docker-compose
docker-compose down
docker-compose up --build

# Access at http://localhost:8080
```

### Option 2: Direct Python (Development)
```bash
# Install dependencies
pip install plotly==5.18.0

# Set environment
export UI_MODE=advanced
export PYTHONPATH="$(pwd)"

# Run directly
python app_wrapper.py

# Access at http://localhost:8080
```

### Option 3: Kubernetes (Production)
```bash
# Build and deploy
docker build -t k8s-ai-agent:advanced .
kubectl apply -f k8s/k8s-ai-agent.yaml

# Port forward
kubectl port-forward service/k8s-ai-agent 8080:8080

# Access at http://localhost:8080
```

### Option 4: Quick Deploy Script
```bash
./deploy_advanced_ui.sh
```

## Advanced Dashboard UI Features

When properly deployed, the Advanced Dashboard includes:

### 🔧 Expert AI-Powered Actions
- **Expert Diagnosis:** Comprehensive system analysis
- **Auto-Remediate:** Automatic issue resolution  
- **Health Check:** Deep system health analysis
- **Smart Optimize:** Performance optimization
- **Security Audit:** Security assessment

### 💬 Intelligent Chat Interface
- Model selection (llama-3.1-8b-instruct, mistral-7b-instruct, codellama-34b)
- Streaming responses
- Auto-remediation toggle
- Smart suggestions with categorized queries

### 📊 Real-time System Monitoring
- Kubernetes cluster status with pod count
- Memory usage with color-coded indicators
- Disk usage with available space
- Load average with performance status

### 📈 Analytics & Performance
- Total queries and success rate metrics
- Average response time tracking
- Confidence score analysis
- Interactive trend charts (when plotly available)

### 🧠 Historical Insights & Learning
- Issue memory and pattern matching
- Success rate tracking
- Trend analysis with 24h activity
- Most frequent issue types

### 🔮 Predictive Recommendations
- Risk assessment with severity levels
- Confidence-based predictions
- Timeframe estimates
- Overall risk level indicators

## Verification Steps

1. **Test Dependencies:**
   ```bash
   python test_advanced_dashboard.py
   ```

2. **Check Service Health:**
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:9090/health
   ```

3. **Verify UI Access:**
   - Open http://localhost:8080
   - Check for Advanced Dashboard title
   - Verify all tabs load without errors
   - Test expert action buttons

## Troubleshooting

### Issue: ModuleNotFoundError: plotly
**Solution:** Rebuild container or install plotly
```bash
pip install plotly==5.18.0
# OR
docker-compose up --build
```

### Issue: Charts not displaying
**Expected:** When plotly unavailable, charts show as text summaries
**Fix:** Install plotly for full visualization

### Issue: Port conflicts
**Solution:** Check port mapping in docker-compose.yml
```yaml
ports:
  - "8080:8080"  # Streamlit UI
  - "9090:9090"  # Health check
```

### Issue: UI_MODE not working
**Solution:** Ensure environment variable is set
```bash
export UI_MODE=advanced
```

## Container Logs
```bash
# Docker Compose
docker-compose logs -f k8s-ai-agent

# Kubernetes
kubectl logs -l app=k8s-ai-agent -f
```

## Success Indicators

✅ Advanced Dashboard UI loads at http://localhost:8080
✅ All 5 expert action buttons visible
✅ System status indicators showing real data
✅ Chat interface accepts inputs
✅ Analytics tab shows metrics
✅ No import errors in logs

The Advanced Dashboard UI is now ready for deployment! 🚀
