# K8s AI Agent - CI/CD Pipeline Documentation

This document describes the Jenkins CI/CD pipeline for building, testing, and deploying the K8s AI Agent.

## Overview

The Jenkins pipeline automates:
1. **Code checkout and validation**
2. **Security scanning**
3. **Docker image building**
4. **Container security scanning with Trivy**
5. **Functional testing**
6. **Pushing to Artifactory**
7. **Deployment to various environments**

## Pipeline Structure

### Jenkinsfile

The main pipeline is defined in `Jenkinsfile` and includes:

```groovy
pipeline {
    agent { node { label "${params.AGENT}" } }
    
    stages {
        - Checkout & Verify Tools
        - Security Scan
        - Build AI Agent Image  
        - Trivy Security Scan
        - Test AI Agent
        - Push to Artifactory
    }
}
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `VERSION` | `1.0.0` | AI Agent version for image tagging |
| `IMAGE_NAME` | `k8s-ai-agent` | Docker image name |
| `DOCKER_REGISTRY` | `localhost:5000` | Local registry for building |
| `ARTIFACTORY_DOCKER_REGISTRY` | `dockerhub.cisco.com` | Artifactory Docker registry |
| `ARTIFACTORY_REPO` | `robot-dockerprod` | Artifactory repository |
| `AGENT` | `cw-build` | Jenkins build agent |
| `TRIVY_NOTIFICATION` | `Y` | Send Trivy scan reports via email |
| `SKIP_TESTS` | `N` | Skip testing phase |
| `SKIP_PUSH` | `N` | Skip Artifactory push |

## Build Scripts

### scripts/build.sh

Enhanced build script that:
- Validates prerequisites
- Runs security checks
- Performs code linting
- Executes unit tests
- Builds Docker image
- Tests the container
- Generates build reports

Usage:
```bash
./scripts/build.sh [options]

Options:
  --version VERSION        Set version (default: 1.0.0)
  --build-number NUMBER    Set build number
  --image-name NAME        Set image name
  --registry REGISTRY      Set docker registry
  --skip-tests            Skip testing phase
```

### scripts/deploy_simple.sh

Deployment script for Kubernetes:
```bash
./scripts/deploy_simple.sh [options]

Options:
  -e, --environment ENV    Target environment: local, staging, prod
  -t, --tag TAG           Image tag to deploy
  -n, --namespace NS      Kubernetes namespace
  --dry-run              Perform dry run
```

## Docker Configuration

### Multi-stage Dockerfile

The `Dockerfile` uses multi-stage builds:
1. **Builder stage**: Compiles dependencies and installs Python packages
2. **Runtime stage**: Minimal runtime environment with only necessary components

### docker-compose.yml

For local development and testing:
```bash
# Start local environment
docker-compose up -d

# View logs
docker-compose logs -f k8s-ai-agent

# Stop services
docker-compose down
```

## Artifactory Integration

### Image Naming Convention

Images are tagged using the following convention:
- **Feature branches**: `{VERSION}-{BRANCH}-{BUILD_NUMBER}`
- **Main/Master**: `{VERSION}-{BUILD_NUMBER}`
- **Latest**: Only pushed for main/master branches

### Repositories

| Environment | Repository | Registry |
|-------------|------------|----------|
| Development | `robot-dev` | `dockerhub.cisco.com` |
| Staging | `robot-staging` | `dockerhub.cisco.com` |
| Production | `robot-dockerprod` | `dockerhub.cisco.com` |

## Security Scanning

### Trivy Integration

The pipeline includes comprehensive security scanning:

1. **Code Security Scan**: Checks for hardcoded secrets and security issues
2. **Container Scan**: Uses Trivy to scan the built Docker image
3. **Vulnerability Reports**: Generates HTML and CSV reports
4. **Email Notifications**: Sends scan results to specified recipients

### Security Reports

Generated artifacts:
- `k8s-ai-agent-trivy-report.html` - Detailed HTML report
- `k8s-ai-agent-trivy-summary.csv` - Summary in CSV format
- `k8s-ai-agent-trivy-report.json` - Machine-readable JSON report

## Testing Strategy

### Unit Tests
- Python module imports
- Core functionality validation
- Configuration parsing

### Integration Tests
- Container startup verification
- Health endpoint testing
- API functionality validation

### Smoke Tests
- Service responsiveness
- Basic UI functionality
- Kubernetes deployment verification

## Environment Configuration

### Local Development
```bash
# Build and test locally
./scripts/build.sh --environment local

# Deploy to local Kubernetes
./scripts/deploy_simple.sh --environment local
```

### Staging Environment
```bash
# Build for staging
./scripts/build.sh --version 1.2.3 --build-number 45

# Deploy to staging
./scripts/deploy_simple.sh --environment staging --tag 1.2.3-45 --namespace ai-staging
```

### Production Environment
```bash
# Deploy to production (requires specific version tag)
./scripts/deploy_simple.sh --environment prod --tag 1.2.3 --namespace ai-production
```

## Jenkins Configuration

### Required Plugins
- Docker Pipeline
- Kubernetes CLI
- Email Extension
- Build Timeout
- AnsiColor

### Credentials Required
| ID | Description | Type |
|----|-------------|------|
| `c65584b2-8051-4474-8e8e-037c44440f4d` | Docker Registry | Username/Password |
| `bdda8672-6f24-428d-bd2d-cf0155816b8d` | Artifactory | Username/Password |
| `robotadm` | Git Access | SSH Key |

### Environment Variables
```groovy
environment {
    VERSION = "${params.VERSION}"
    DOCKER_BUILDKIT = "1"
    BUILDKIT_PROGRESS = "plain"
    // ... other variables
}
```

## Monitoring and Alerts

### Build Notifications

**Success Email:**
- Build summary
- Deployment commands
- Access URLs

**Failure Email:**
- Error details
- Console log links
- Troubleshooting hints

**Trivy Reports:**
- Security scan results
- Vulnerability details
- Remediation suggestions

### Artifacts

The pipeline archives:
- `image_tag.txt` - Built image tag
- `k8s-ai-agent-trivy-report.html` - Security report
- `k8s-ai-agent-trivy-summary.csv` - Vulnerability summary
- `image-manifest.json` - Docker manifest

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs
   docker logs <container-id>
   
   # Verify dependencies
   ./scripts/build.sh --help
   ```

2. **Image Push Failures**
   ```bash
   # Check registry connectivity
   docker login dockerhub.cisco.com
   
   # Verify credentials
   echo $DOCKER_PREPROD_PSW | docker login -u $DOCKER_PREPROD_USR --password-stdin dockerhub.cisco.com
   ```

3. **Deployment Issues**
   ```bash
   # Check Kubernetes connectivity
   kubectl cluster-info
   
   # Verify namespace
   kubectl get ns
   
   # Check deployment status
   kubectl get deployments -n <namespace>
   ```

### Debug Commands

```bash
# Local build debug
./scripts/build.sh --skip-tests

# Container inspection
docker run -it k8s-ai-agent:latest /bin/bash

# Kubernetes debug
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
```

## Best Practices

### Development Workflow
1. Create feature branch
2. Make changes
3. Test locally with `docker-compose`
4. Push to trigger CI/CD
5. Monitor build results
6. Deploy to staging for validation
7. Merge to main for production

### Security
- Never commit secrets to repository
- Use Jenkins credentials for sensitive data
- Regular dependency updates
- Monitor Trivy scan results

### Performance
- Use Docker layer caching
- Optimize Dockerfile for build speed
- Clean up old images and containers
- Monitor resource usage

## Support

For issues with the CI/CD pipeline:
1. Check Jenkins build logs
2. Review this documentation
3. Contact the infrastructure team
4. Create issue in repository

## References

- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Deployment Guide](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Trivy Security Scanner](https://aquasecurity.github.io/trivy/)
