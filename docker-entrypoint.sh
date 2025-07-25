#!/bin/bash
set -e

# Entrypoint script for k8s-ai-agent with full host system access

# Check if running as root (privileged mode)
if [ "$(id -u)" = "0" ]; then
    echo "Running in privileged mode - Full host system access enabled"
    
    # Set up host command access
    if [ -d "/host/usr/bin" ]; then
        export PATH="/host/usr/bin:/host/usr/sbin:/host/bin:/host/sbin:$PATH"
    fi
    
    # Set up host library paths
    if [ -d "/host/usr/lib" ]; then
        export LD_LIBRARY_PATH="/host/usr/lib:/host/usr/lib64:/host/lib:/host/lib64:$LD_LIBRARY_PATH"
    fi
    
    # Create symlinks for common system commands
    for cmd in gluster glusterd glusterfs df lsblk mount umount ps top htop iostat sar vmstat free lscpu lsof netstat ss iptables; do
        for path in "/host/usr/bin" "/host/usr/sbin" "/host/bin" "/host/sbin"; do
            if [ -f "$path/$cmd" ]; then
                ln -sf "$path/$cmd" "/usr/local/bin/$cmd" 2>/dev/null || true
                break
            fi
        done
    done
    
    # Set up nsenter for host namespace execution
    if [ -f "/host/usr/bin/nsenter" ]; then
        ln -sf "/host/usr/bin/nsenter" "/usr/local/bin/nsenter" 2>/dev/null || true
    fi
    
    # Create helper script for executing commands in host namespace
    cat > /usr/local/bin/host-exec << 'EOF'
#!/bin/bash
# Execute commands in host namespaces
if [ -f "/usr/local/bin/nsenter" ]; then
    exec nsenter -t 1 -m -u -i -n -p "$@"
else
    # Fallback to chroot execution
    exec chroot /host "$@"
fi
EOF
    chmod +x /usr/local/bin/host-exec
    
    # Create helper script for GlusterFS commands
    cat > /usr/local/bin/gluster-exec << 'EOF'
#!/bin/bash
# Execute GlusterFS commands with proper environment
export PATH="/usr/sbin:/usr/bin:/sbin:/bin"
if [ -f "/usr/local/bin/nsenter" ]; then
    exec nsenter -t 1 -m -u -i -n -p gluster "$@"
else
    exec chroot /host gluster "$@"
fi
EOF
    chmod +x /usr/local/bin/gluster-exec
    
    echo "Host system access configured successfully"
    
    # If we have a k8s-agent user and we're asked to run as that user
    if [ "$1" = "k8s-agent" ]; then
        shift
        echo "Switching to k8s-agent user for application execution"
        exec gosu k8s-agent "$@"
    fi
else
    echo "Running in non-privileged mode - limited system access"
fi

# Ensure required directories exist with proper permissions
echo "Setting up application directories..."
mkdir -p /data /var/log/k8s-ai-agent /tmp/.streamlit
chmod 755 /data /var/log/k8s-ai-agent /tmp/.streamlit

# Clean up any existing ChromaDB lock files
find /data -name "*.lock" -type f -delete 2>/dev/null || true

# Set proper environment for ChromaDB
export CHROMA_DB_PATH="/data"
export CHROMA_TELEMETRY=False
export ANONYMIZED_TELEMETRY=False

echo "Application environment configured successfully"

# Execute the main command
exec "$@"
