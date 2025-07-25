/* k8sAIagent Jenkins Declarative Pipeline */

def buildAIAgentImage(serviceName, branch) {
    sh """
        echo "Building AI Agent Docker image for ${serviceName} on branch ${branch}"
        
        # Clean up disk space and ensure fresh build
        echo "=== Cleaning up disk space ==="
        
        # Create nodocker file to quiet podman emulation message
        sudo mkdir -p /etc/containers
        sudo touch /etc/containers/nodocker
        
        # Run emergency cleanup
        if [ -f "./scripts/emergency-space-cleanup.sh" ]; then
            ./scripts/emergency-space-cleanup.sh || true
        else
            # Fallback cleanup if script doesn't exist
            podman system prune -af --volumes || docker system prune -af --volumes || true
            sudo rm -rf /tmp/* || true
        fi
        
        # Clear container build cache to remove any stale layers
        echo "=== Clearing Container Build Cache ==="
        if command -v podman >/dev/null 2>&1; then
            echo "Clearing podman cache and images..."
            podman system prune -af --volumes || true
            podman rmi --all --force || true
            # Force pull fresh base image
            podman pull ubuntu:22.04 --quiet || true
        elif command -v docker >/dev/null 2>&1; then
            echo "Clearing docker cache and images..."
            docker system prune -af --volumes || true
            docker rmi \$(docker images -q) --force || true
            # Force pull fresh base image
            docker pull ubuntu:22.04 || true
        elif command -v buildah >/dev/null 2>&1; then
            echo "Clearing buildah cache..."
            buildah rm --all || true
            buildah rmi --all --force || true
            # Force pull fresh base image
            buildah pull ubuntu:22.04 || true
        fi
        
        # Verify we're using the correct Dockerfile for LLaMA support
        echo "=== Verifying Dockerfile ==="
        if [ -f "Dockerfile.optimized" ]; then
            echo "✓ Found optimized Dockerfile for LLaMA support"
            echo "Using Dockerfile: Dockerfile.optimized"
            head -5 "Dockerfile.optimized"
        elif [ -f "Dockerfile" ]; then
            echo "✓ Using standard Dockerfile" 
            echo "Using Dockerfile: Dockerfile"
            head -5 "Dockerfile"
        else
            echo "✗ ERROR: No Dockerfile found"
            exit 1
        fi
        
        # Force no-cache build to ensure fresh base layers
        export BUILDAH_LAYERS=false
        export DOCKER_BUILDKIT=1
        export BUILDKIT_PROGRESS=plain
        
        # Show disk usage before build
        echo "=== Disk Usage Before Build ==="
        df -h
        echo "=== /home directory space ==="
        df -h /home || df -h \${HOME} || true
        
        # Check if we have enough space in /home
        AVAILABLE_HOME=\$(df /home 2>/dev/null | awk 'NR==2 {print \$4}' || df \${HOME} | awk 'NR==2 {print \$4}')
        MIN_REQUIRED=10485760  # 10GB in KB
        if [ "\${AVAILABLE_HOME}" -lt "\${MIN_REQUIRED}" ]; then
            echo "WARNING: Insufficient space in /home directory"
            echo "Available: \${AVAILABLE_HOME} KB, Required: \${MIN_REQUIRED} KB"
            exit 1
        fi
        
        # Set image tag based on branch and build number
        # Clean branch name to ensure Docker tag compatibility
        CLEAN_BRANCH=\$(echo "${branch}" | sed 's|^*/||' | sed 's/[^a-zA-Z0-9._-]/-/g')
        export IMAGE_TAG="${params.VERSION}-\${CLEAN_BRANCH}-${BUILD_NUMBER}"
        if [ "\${CLEAN_BRANCH}" = "main" ] || [ "\${CLEAN_BRANCH}" = "master" ]; then
            export IMAGE_TAG="${params.VERSION}-${BUILD_NUMBER}"
        fi
        
        echo "Building image with tag: \${IMAGE_TAG}"
        echo "Using optimized build script with space optimization"
        
        # Set environment variables for the build script
        export VERSION="${params.VERSION}"
        export BUILD_NUMBER="${BUILD_NUMBER}"
        export BRANCH="${branch}"
        export IMAGE_NAME="${params.IMAGE_NAME}"
        
        # Build directly with Artifactory image name (no local saving)
        ARTIFACTORY_IMAGE="${params.ARTIFACTORY_DOCKER_REGISTRY}/${params.ARTIFACTORY_REPO}/${params.IMAGE_NAME}:\${IMAGE_TAG}"
        
        # Use optimized build script instead of direct docker build
        if [ -f "./scripts/build-optimized.sh" ]; then
            echo "Using optimized build script..."
            chmod +x ./scripts/build-optimized.sh
            export ARTIFACTORY_IMAGE="\${ARTIFACTORY_IMAGE}"
            ./scripts/build-optimized.sh
        elif [ -f "./scripts/build.sh" ]; then
            echo "Using standard build script..."
            chmod +x ./scripts/build.sh
            export ARTIFACTORY_IMAGE="\${ARTIFACTORY_IMAGE}"
            ./scripts/build.sh
        else
            echo "No build script found, using direct container build..."
            
            # Simple Docker build with automatic Dockerfile selection
            echo "Building image: \${ARTIFACTORY_IMAGE}"
            
            # Try optimized Dockerfile first, fall back to standard
            if [ -f "Dockerfile.optimized" ]; then
                echo "Using optimized Dockerfile for LLaMA support"
                docker build \\
                    --no-cache \\
                    --pull \\
                    --build-arg VERSION=${params.VERSION} \\
                    --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \\
                    --build-arg VCS_REF=\$(git rev-parse --short HEAD) \\
                    --tag "\${ARTIFACTORY_IMAGE}" \\
                    --file "Dockerfile.optimized" .
            else
                echo "Using standard Dockerfile"
                docker build \\
                    --no-cache \\
                    --pull \\
                    --build-arg VERSION=${params.VERSION} \\
                    --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \\
                    --build-arg VCS_REF=\$(git rev-parse --short HEAD) \\
                    --tag "\${ARTIFACTORY_IMAGE}" \\
                    --file "Dockerfile" .
            fi
        fi
        
        # Save image tag for later stages
        echo "\${IMAGE_TAG}" > image_tag.txt
        
        # Detect which container runtime was used for build and verify with the same
        echo "Verifying built image: \${ARTIFACTORY_IMAGE}"
        if command -v buildah >/dev/null 2>&1; then
            echo "Using buildah to verify image..."
            # Use same storage root as build script
            CONTAINER_STORAGE_ROOT="/home/jenkins/.containers"
            buildah images --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" --format "table {{.Repository}}:{{.Tag}}\\t{{.Size}}" "\${ARTIFACTORY_IMAGE}" || true
        elif command -v podman >/dev/null 2>&1; then
            echo "Using podman to verify image..."
            # Use same storage root as build script
            CONTAINER_STORAGE_ROOT="/home/jenkins/.containers"
            podman images --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" "\${ARTIFACTORY_IMAGE}" --format "table {{.Repository}}:{{.Tag}}\\t{{.Size}}" || true
        else
            echo "Using docker to verify image..."
            docker images "\${ARTIFACTORY_IMAGE}" --format "table {{.Repository}}:{{.Tag}}\\t{{.Size}}" || true
        fi
        
        echo "Docker image built successfully with tag: \${IMAGE_TAG}"
        echo "Ready for Artifactory push: \${ARTIFACTORY_IMAGE}"
        
        # Show disk usage after build
        df -h
    """
}

def pushToArtifactory(serviceName, branch) {
    sh """
        echo "Pushing ${serviceName} image to Artifactory"
        
        # Read the image tag
        IMAGE_TAG=\$(cat image_tag.txt)
        
        # Build full image name - this is the same image we already built
        ARTIFACTORY_IMAGE="${params.ARTIFACTORY_DOCKER_REGISTRY}/${params.ARTIFACTORY_REPO}/${params.IMAGE_NAME}:\${IMAGE_TAG}"
        
        # Detect which container runtime to use (same as build)
        if command -v buildah >/dev/null 2>&1; then
            echo "Using buildah for push to Artifactory..."
            
            # Use same storage root as build script
            CONTAINER_STORAGE_ROOT="/home/jenkins/.containers"
            
            # Login to Artifactory with buildah
            echo "Logging into Artifactory with buildah..."
            echo "\${DOCKER_PREPROD_PSW}" | buildah login --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" -u "\${DOCKER_PREPROD_USR}" --password-stdin ${params.ARTIFACTORY_DOCKER_REGISTRY}
            
            # Push image using buildah with same storage options
            echo "Pushing image with buildah: \${ARTIFACTORY_IMAGE}"
            buildah push --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" "\${ARTIFACTORY_IMAGE}"
            
        elif command -v podman >/dev/null 2>&1; then
            echo "Using podman for push to Artifactory..."
            
            # Use same storage root as build script
            CONTAINER_STORAGE_ROOT="/home/jenkins/.containers"
            
            # Login to Artifactory with podman
            echo "Logging into Artifactory with podman..."
            echo "\${DOCKER_PREPROD_PSW}" | podman login --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" -u "\${DOCKER_PREPROD_USR}" --password-stdin ${params.ARTIFACTORY_DOCKER_REGISTRY}
            
            # Push image using podman with same storage options
            echo "Pushing image with podman: \${ARTIFACTORY_IMAGE}"
            podman push --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" "\${ARTIFACTORY_IMAGE}"
            
        else
            echo "Using docker for push to Artifactory..."
            
            # Login to Artifactory with docker
            echo "Logging into Artifactory with docker..."
            echo "\${DOCKER_PREPROD_PSW}" | docker login -u "\${DOCKER_PREPROD_USR}" --password-stdin ${params.ARTIFACTORY_DOCKER_REGISTRY}
            
            # Push image using docker
            echo "Pushing image with docker: \${ARTIFACTORY_IMAGE}"
            docker push "\${ARTIFACTORY_IMAGE}"
        fi
        
        echo "Successfully pushed image to Artifactory: \${ARTIFACTORY_IMAGE}"
    """
}

def createDeploymentPackage(serviceName, branch) {
    sh """
        echo "Creating deployment package for ${serviceName}"
        
        # Read the image tag
        IMAGE_TAG=\$(cat image_tag.txt)
        
        # Set environment variables for package creation
        export IMAGE_TAG="\${IMAGE_TAG}"
        export VERSION="${params.VERSION}"
        export BUILD_NUMBER="${BUILD_NUMBER}"
        export IMAGE_REGISTRY="${params.ARTIFACTORY_DOCKER_REGISTRY}"
        export IMAGE_REPO="${params.ARTIFACTORY_REPO}"
        export IMAGE_NAME="${params.IMAGE_NAME}"
        export GIT_BRANCH="${branch}"
        
        # Create deployment package directory
        PACKAGE_DIR="k8s-ai-agent-deployment-\${IMAGE_TAG}"
        mkdir -p "\${PACKAGE_DIR}"
        
        # Copy k8s manifests to package directory
        cp -r k8s/* "\${PACKAGE_DIR}/"
        
        # Update image tag in the main manifest
        sed -i "s|image: dockerhub.cisco.com/robot-dockerprod/k8s-ai-agent:latest|image: ${params.ARTIFACTORY_DOCKER_REGISTRY}/${params.ARTIFACTORY_REPO}/${params.IMAGE_NAME}:\${IMAGE_TAG}|g" "\${PACKAGE_DIR}/k8s-ai-agent.yaml"
        
        # Create deployment info file
        cat > "\${PACKAGE_DIR}/deployment-info.txt" << EOF
K8s AI Agent Deployment Package
==============================
Version: ${params.VERSION}
Build: ${BUILD_NUMBER}
Branch: ${branch}
Image: ${params.ARTIFACTORY_DOCKER_REGISTRY}/${params.ARTIFACTORY_REPO}/${params.IMAGE_NAME}:\${IMAGE_TAG}
Created: \$(date)

Deployment Instructions:
1. kubectl apply -f 02-rbac.yaml
2. kubectl apply -f k8s-ai-agent.yaml
3. kubectl get pods -l app=k8s-ai-agent

Or use the deployment script:
./deploy-simple.sh
EOF
        
        # Create zip package
        zip -r "\${PACKAGE_DIR}.zip" "\${PACKAGE_DIR}/"
        
        # Create checksum
        sha256sum "\${PACKAGE_DIR}.zip" > "\${PACKAGE_DIR}.zip.sha256"
        
        # Show package contents
        echo "Deployment package created successfully:"
        ls -la "\${PACKAGE_DIR}.zip"*
        echo ""
        echo "Package contents:"
        unzip -l "\${PACKAGE_DIR}.zip"
    """
}

def getGitBranchName() {
    def branchName = scm.branches[0].name
    // Remove any wildcard prefix (*/master -> master)
    if (branchName.startsWith('*/')) {
        branchName = branchName.substring(2)
    }
    // Clean branch name for Docker tag compatibility
    return branchName.replaceAll('[^a-zA-Z0-9._-]', '-')
}

pipeline {
    agent {
        node {
            label "${params.AGENT}"
        }
    }

    parameters {
        string(name: 'VERSION', defaultValue: '1.0.0', description: 'AI Agent version')
        string(name: 'IMAGE_NAME', defaultValue: 'k8s-ai-agent', description: 'Docker image name')
        string(name: 'ARTIFACTORY_DOCKER_REGISTRY', defaultValue: 'dockerhub.cisco.com', description: 'Artifactory Docker registry')
        string(name: 'ARTIFACTORY_REPO', defaultValue: 'robot-dockerprod', description: 'Artifactory repository name')
        string(name: 'GIT_BRANCH', defaultValue: 'master', description: 'Git branch to build')
        string(name: 'AGENT', defaultValue: '172.29.77.153', description: 'Jenkins Node')
        string(name: 'ARTIFACTS', defaultValue: 'image_tag.txt,k8s-ai-agent-deployment-*.zip,k8s-ai-agent-deployment-*.zip.sha256', description: 'List of artifacts')
    }

    environment {
        VERSION = "${params.VERSION}"
        IMAGE_NAME = "${params.IMAGE_NAME}"
        BRANCH = getGitBranchName()
        
        // Docker and Artifactory credentials
        DOCKER_PREPROD = credentials('c65584b2-8051-4474-8e8e-037c44440f4d')
        
        // Build optimization
        DOCKER_BUILDKIT = "1"
        BUILDKIT_PROGRESS = "plain"
    }

    options {
        ansiColor('xterm')
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(false)
        buildDiscarder(
            logRotator(
                daysToKeepStr: '30',
                numToKeepStr: '50',
                artifactDaysToKeepStr: '20',
                artifactNumToKeepStr: '20'
            )
        )
        timeout(time: 45, unit: 'MINUTES')
    }

    stages {
        stage('Build AI Agent Image') {
            steps {
                echo "Building AI Agent Docker image"
                echo "Building version: ${params.VERSION} on branch: ${BRANCH}"
                
                // Check initial disk space
                sh "df -h"
                
                cleanWs()
                
                // Checkout from the specified repository and branch with SSH credentials
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/${params.GIT_BRANCH}"]],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [],
                    submoduleCfg: [],
                    userRemoteConfigs: [[
                        credentialsId: 'robotadm',
                        url: "git@github3.cisco.com:rtupakul/k8sAIAgent.git"
                    ]]
                ])
                
                buildAIAgentImage('k8s-ai-agent', "${BRANCH}")
                echo "Docker image built successfully"
            }
        }

        stage('Push to Artifactory') {
            steps {
                echo "Pushing AI Agent image to Artifactory"
                pushToArtifactory('k8s-ai-agent', "${BRANCH}")
                echo "Successfully pushed to Artifactory"
            }
        }

        stage('Create Deployment Package') {
            steps {
                echo "Creating Kubernetes deployment package"
                createDeploymentPackage('k8s-ai-agent', "${BRANCH}")
                echo "Deployment package created successfully"
            }
        }
    }

    post {
        always {
            echo "Build pipeline completed"
            
            // Archive deployment package and artifacts
            archiveArtifacts artifacts: "${params.ARTIFACTS}", allowEmptyArchive: true
            
            // Final cleanup to free space for next build
            sh """
                echo "Final cleanup..."
                # Use the same container runtime and storage for cleanup
                CONTAINER_STORAGE_ROOT="/home/jenkins/.containers"
                if command -v buildah >/dev/null 2>&1; then
                    echo "Cleaning up buildah..."
                    buildah rm --all || true
                    buildah rmi --all --force || true
                elif command -v podman >/dev/null 2>&1; then
                    podman system prune --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" -f --volumes || true
                else
                    docker system prune -f --volumes || true
                fi
                sudo rm -rf /tmp/* || true
                df -h
            """
        }
        
        success {
            echo "Build completed successfully"
        }
        
        failure {
            echo "Build failed - check logs for details"
            
            // Emergency cleanup on failure
            sh """
                echo "Emergency cleanup due to build failure..."
                # Use the same container runtime and storage for emergency cleanup
                CONTAINER_STORAGE_ROOT="/home/jenkins/.containers"
                if command -v buildah >/dev/null 2>&1; then
                    echo "Emergency buildah cleanup..."
                    buildah rm --all || true
                    buildah rmi --all --force || true
                elif command -v podman >/dev/null 2>&1; then
                    podman system prune --storage-driver overlay --root "\${CONTAINER_STORAGE_ROOT}/storage" --runroot "\${CONTAINER_STORAGE_ROOT}/run" -af --volumes || true
                else
                    docker system prune -af --volumes || true
                fi
                sudo rm -rf /tmp/* || true
                df -h
            """
        }
    }
}
