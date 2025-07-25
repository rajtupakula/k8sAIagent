# Runtime Configuration Management

The Kubernetes AI Assistant now supports **runtime configuration changes** through Kubernetes ConfigMaps and environment variables. The UI remains **always interactive** while backend behavior can be configured dynamically.

## 🎯 Key Principles

1. **UI Always Interactive**: The user interface always prompts for confirmation regardless of backend configuration
2. **Backend Configurable**: Backend processes can be configured for automatic remediation based on confidence levels
3. **Runtime Modifiable**: Configuration can be changed without restarting the application
4. **Kubernetes Native**: Uses ConfigMaps and environment variables for configuration management

## 🛠️ Configuration Architecture

### Frontend Behavior
- **Always Interactive**: UI prompts user for all remediation actions
- **User Confirmation**: All actions require explicit user approval
- **Mode Display**: UI adapts display based on current operational mode
- **Real-time Updates**: Configuration changes reflected in UI immediately

### Backend Behavior
- **Configurable Auto-Remediation**: Can be enabled/disabled at runtime
- **Confidence Thresholds**: Backend respects confidence levels for automatic actions
- **Mode-Specific Logic**: Different operational modes change backend behavior
- **Safety Checks**: Always enforced regardless of automation level

## 📊 Operational Modes

| Mode | UI Behavior | Backend Auto-Remediation | Use Case |
|------|-------------|---------------------------|----------|
| **Debug** | Interactive analysis | ❌ Disabled | Root cause investigation |
| **Remediation** | Interactive prompts | ✅ Configurable | Production auto-healing |
| **Interactive** | Full user control | ❌ Disabled | Development/training |
| **Monitoring** | Dashboard focus | ❌ Disabled | NOC monitoring |
| **Hybrid** | Adaptive interface | ✅ Configurable | Complex environments |

## 🔧 Runtime Configuration

### 1. Environment Variables (Highest Priority)

```bash
# Core mode settings
K8S_AI_MODE=interactive                    # debug, remediation, interactive, monitoring, hybrid
K8S_AI_AUTOMATION_LEVEL=semi_auto         # manual, semi_auto, full_auto
K8S_AI_CONFIDENCE_THRESHOLD=80             # 0-100

# Feature toggles
K8S_AI_HISTORICAL_LEARNING=true           # true/false
K8S_AI_PREDICTIVE_ANALYSIS=true           # true/false
K8S_AI_CONTINUOUS_MONITORING=false        # true/false
K8S_AI_AUTO_REMEDIATION=false             # Backend auto-remediation (UI still prompts)

# Safety settings
K8S_AI_SAFETY_CHECKS=true                 # true/false
K8S_AI_AUDIT_LOGGING=true                 # true/false
```

### 2. Kubernetes ConfigMap

Deploy the runtime configuration:

```bash
kubectl apply -f k8s/runtime-configmap.yaml
```

Modify configuration at runtime:

```bash
# Change to remediation mode with auto-remediation
kubectl patch configmap k8s-ai-runtime-config \
  --type merge -p '{"data":{"mode":"remediation","backend_auto_remediation":"true"}}'

# Restart deployment to pick up environment variable changes
kubectl rollout restart deployment/k8s-ai-assistant
```

### 3. Runtime Configuration Script

Use the provided script for easy configuration management:

```bash
# Show current configuration
./scripts/runtime-config.sh show-config

# Apply predefined mode configurations
./scripts/runtime-config.sh apply-mode remediation
./scripts/runtime-config.sh apply-mode debug
./scripts/runtime-config.sh apply-mode interactive

# Enable/disable specific features
./scripts/runtime-config.sh enable-feature auto-remediation
./scripts/runtime-config.sh disable-feature predictive-analysis

# Set confidence threshold
./scripts/runtime-config.sh set-confidence 90

# Update any configuration key
./scripts/runtime-config.sh update mode hybrid
./scripts/runtime-config.sh update continuous_monitoring true
```

## 🎮 User Experience Flow

### When User Asks for Remediation

1. **User Query**: "Fix the failing pods"
2. **AI Analysis**: System analyzes and identifies root cause
3. **UI Response**: 
   - Shows analysis results
   - Presents remediation options
   - **Always prompts for confirmation**
4. **User Confirmation**: User reviews and approves specific actions
5. **Execution**: 
   - If backend auto-remediation enabled: System executes automatically after confirmation
   - If manual mode: System provides step-by-step instructions

### Example Interaction

```
User: "The nginx pods are failing, please fix them"

AI Assistant: 
🔍 Analysis Complete:
- Root Cause: OOMKilled due to memory limit too low
- Affected: 3 nginx pods in default namespace
- Confidence: 95%

🔧 Remediation Mode: Backend auto-remediation enabled (85% threshold)
Suggested Actions:
1. Increase memory limit from 128Mi to 512Mi
2. Restart affected pods
3. Monitor for stability

⚠️ UI Confirmation Required:
Would you like me to execute these remediation actions?
[✅ Execute All] [🔍 Review Details] [❌ Cancel]
```

## 🔄 Configuration Hot-Reloading

The system supports configuration changes without application restart:

### File-Based Hot-Reloading
- Configuration files are watched for changes
- Updates applied automatically within 10 seconds
- No service interruption

### Environment Variable Updates
- Requires pod restart for environment variable changes
- Use `kubectl rollout restart` for graceful updates
- ConfigMap changes trigger automatic updates

### API-Based Updates
- Configuration can be updated through internal APIs
- Immediate effect without restart
- Thread-safe updates

## 📚 Configuration Examples

### Debug Mode (Analysis Only)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-ai-runtime-config
data:
  mode: "debug"
  automation_level: "manual"
  backend_auto_remediation: "false"
  confidence_threshold: "95"
  historical_learning: "true"
  predictive_analysis: "true"
```

### Remediation Mode (Auto-Healing)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-ai-runtime-config
data:
  mode: "remediation"
  automation_level: "full_auto"
  backend_auto_remediation: "true"
  confidence_threshold: "85"
  continuous_monitoring: "true"
  safety_checks: "true"
```

### Interactive Mode (Full User Control)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-ai-runtime-config
data:
  mode: "interactive"
  automation_level: "semi_auto"
  backend_auto_remediation: "false"
  confidence_threshold: "75"
  historical_learning: "true"
```

## 🛡️ Security and Safety

### Safety Mechanisms
- **UI Always Prompts**: Regardless of backend configuration
- **Confidence Thresholds**: Minimum confidence required for auto-actions
- **Audit Logging**: All configuration changes logged
- **Graceful Fallbacks**: System falls back to manual mode on errors

### RBAC Considerations
Different modes may require different Kubernetes permissions:

```yaml
# For Remediation Mode
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: k8s-ai-remediation
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "update", "patch"]
```

## 📊 Monitoring Configuration Changes

### Logging
All configuration changes are logged with:
- Timestamp
- Old and new values
- Source of change (env var, file, API)
- User/system that made the change

### Metrics
Configuration metrics exposed:
- `k8s_ai_config_mode_current` - Current operational mode
- `k8s_ai_config_changes_total` - Total configuration changes
- `k8s_ai_config_auto_remediation_enabled` - Auto-remediation status
- `k8s_ai_config_confidence_threshold` - Current confidence threshold

## 🚀 Quick Start

1. **Deploy with Runtime Configuration**:
   ```bash
   kubectl apply -f k8s/runtime-configmap.yaml
   ```

2. **Verify Configuration**:
   ```bash
   ./scripts/runtime-config.sh show-config
   ```

3. **Switch to Remediation Mode**:
   ```bash
   ./scripts/runtime-config.sh apply-mode remediation
   ```

4. **Enable Auto-Remediation**:
   ```bash
   ./scripts/runtime-config.sh enable-feature auto-remediation
   ```

5. **Test with User Query**:
   - Open dashboard
   - Ask: "Analyze and fix any pod issues"
   - UI will show analysis and prompt for confirmation
   - Backend will execute automatically after user approval

## 🔧 Troubleshooting

### Configuration Not Applied
1. Check ConfigMap exists: `kubectl get configmap k8s-ai-runtime-config`
2. Verify environment variables: `kubectl describe pod <pod-name>`
3. Check logs: `kubectl logs deployment/k8s-ai-assistant`
4. Restart deployment: `kubectl rollout restart deployment/k8s-ai-assistant`

### UI Not Reflecting Changes
1. Clear browser cache
2. Check WebSocket connection
3. Verify configuration manager is running
4. Check for JavaScript errors in browser console

### Auto-Remediation Not Working
1. Verify `backend_auto_remediation` is `true`
2. Check confidence threshold settings
3. Ensure sufficient RBAC permissions
4. Review safety check configurations

## 📈 Best Practices

1. **Start Conservative**: Begin with manual/interactive modes
2. **Gradual Automation**: Slowly increase confidence thresholds
3. **Monitor Changes**: Always audit configuration modifications
4. **Test Thoroughly**: Validate each mode in non-production first
5. **Backup Configs**: Keep copies of working configurations
6. **Document Changes**: Track why configurations were changed

## 🎯 Use Case Scenarios

### Development Environment
```bash
./scripts/runtime-config.sh apply-mode interactive
./scripts/runtime-config.sh disable-feature auto-remediation
./scripts/runtime-config.sh set-confidence 95
```

### Staging Environment
```bash
./scripts/runtime-config.sh apply-mode hybrid
./scripts/runtime-config.sh enable-feature auto-remediation
./scripts/runtime-config.sh set-confidence 90
```

### Production Environment
```bash
./scripts/runtime-config.sh apply-mode remediation
./scripts/runtime-config.sh enable-feature auto-remediation
./scripts/runtime-config.sh enable-feature continuous-monitoring
./scripts/runtime-config.sh set-confidence 85
```

This runtime configuration system provides the flexibility you requested while maintaining the safety and interactivity of the UI. Users can always control remediation actions through the interface, while the backend can be configured for different levels of automation based on the environment and confidence in the AI's recommendations.
