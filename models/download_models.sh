#!/bin/bash

# Enhanced Model Download Script for Kubernetes AI Agent
# This script downloads optimized GGUF models for local inference

set -e

# Configuration
MODEL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR="${MODEL_DIR}/temp"
LOG_FILE="${MODEL_DIR}/download.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "${LOG_FILE}"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${LOG_FILE}"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${LOG_FILE}"
}

# Model configurations
declare -A MODELS
MODELS[llama-2-7b-chat]="https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
MODELS[codellama-7b-instruct]="https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf"
MODELS[mistral-7b-instruct]="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf"
MODELS[phi-2]="https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf"
MODELS[openchat-3.5]="https://huggingface.co/TheBloke/openchat-3.5-1210-GGUF/resolve/main/openchat-3.5-1210.Q4_K_M.gguf"

declare -A MODEL_DESCRIPTIONS
MODEL_DESCRIPTIONS[llama-2-7b-chat]="LLaMA 2 7B Chat - General purpose conversational AI"
MODEL_DESCRIPTIONS[codellama-7b-instruct]="Code Llama 7B Instruct - Specialized for code generation and analysis"
MODEL_DESCRIPTIONS[mistral-7b-instruct]="Mistral 7B Instruct - Fast and efficient general purpose model"
MODEL_DESCRIPTIONS[phi-2]="Phi-2 - Microsoft's small but capable model (2.7B parameters)"
MODEL_DESCRIPTIONS[openchat-3.5]="OpenChat 3.5 - High-quality chat model based on Mistral"

declare -A MODEL_SIZES
MODEL_SIZES[llama-2-7b-chat]="3.8GB"
MODEL_SIZES[codellama-7b-instruct]="3.8GB"
MODEL_SIZES[mistral-7b-instruct]="3.8GB"
MODEL_SIZES[phi-2]="1.6GB"
MODEL_SIZES[openchat-3.5]="3.8GB"

# Create directories
mkdir -p "${TEMP_DIR}"
mkdir -p "${MODEL_DIR}"

# Function to check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    # Check for required tools
    local deps=("curl" "wget" "sha256sum")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        error "Please install the missing dependencies and try again."
        exit 1
    fi
    
    success "All dependencies are available"
}

# Function to show available models
show_models() {
    log "Available models:"
    echo
    printf "%-25s %-10s %s\n" "Model Name" "Size" "Description"
    printf "%-25s %-10s %s\n" "----------" "----" "-----------"
    
    for model in "${!MODELS[@]}"; do
        printf "%-25s %-10s %s\n" "$model" "${MODEL_SIZES[$model]}" "${MODEL_DESCRIPTIONS[$model]}"
    done
    echo
}

# Function to download a model
download_model() {
    local model_name="$1"
    local force_download="$2"
    
    if [[ -z "${MODELS[$model_name]}" ]]; then
        error "Unknown model: $model_name"
        show_models
        return 1
    fi
    
    local url="${MODELS[$model_name]}"
    local filename=$(basename "$url")
    local model_path="${MODEL_DIR}/${filename}"
    local temp_path="${TEMP_DIR}/${filename}"
    
    # Check if model already exists
    if [[ -f "$model_path" && "$force_download" != "true" ]]; then
        warning "Model $model_name already exists at $model_path"
        log "Use --force to re-download"
        return 0
    fi
    
    log "Downloading $model_name (${MODEL_SIZES[$model_name]})..."
    log "URL: $url"
    log "Destination: $model_path"
    
    # Download with progress bar
    if command -v wget &> /dev/null; then
        wget --progress=bar:force:noscroll -O "$temp_path" "$url" 2>&1 | tee -a "${LOG_FILE}"
    elif command -v curl &> /dev/null; then
        curl -L --progress-bar -o "$temp_path" "$url" 2>&1 | tee -a "${LOG_FILE}"
    else
        error "Neither wget nor curl is available for downloading"
        return 1
    fi
    
    # Verify download
    if [[ ! -f "$temp_path" ]]; then
        error "Download failed - file not found"
        return 1
    fi
    
    local file_size=$(stat -f%z "$temp_path" 2>/dev/null || stat -c%s "$temp_path" 2>/dev/null)
    if [[ "$file_size" -lt 1000000 ]]; then  # Less than 1MB indicates error
        error "Download failed - file too small (${file_size} bytes)"
        rm -f "$temp_path"
        return 1
    fi
    
    # Move to final location
    mv "$temp_path" "$model_path"
    
    success "Successfully downloaded $model_name"
    log "Model saved to: $model_path"
    log "File size: $(du -h "$model_path" | cut -f1)"
    
    return 0
}

# Function to verify model integrity
verify_model() {
    local model_path="$1"
    
    if [[ ! -f "$model_path" ]]; then
        error "Model file not found: $model_path"
        return 1
    fi
    
    log "Verifying model: $model_path"
    
    # Basic checks
    local file_size=$(stat -f%z "$model_path" 2>/dev/null || stat -c%s "$model_path" 2>/dev/null)
    local file_type=$(file "$model_path" 2>/dev/null || echo "unknown")
    
    log "File size: $(du -h "$model_path" | cut -f1)"
    log "File type: $file_type"
    
    # Check if it's a valid GGUF file
    if [[ "$file_type" == *"GGUF"* ]] || head -c 4 "$model_path" | grep -q "GGUF"; then
        success "Model appears to be a valid GGUF file"
        return 0
    else
        warning "Model may not be a valid GGUF file"
        return 1
    fi
}

# Function to clean up downloads
cleanup() {
    log "Cleaning up temporary files..."
    rm -rf "${TEMP_DIR}"
    success "Cleanup completed"
}

# Function to list downloaded models
list_downloaded() {
    log "Downloaded models:"
    echo
    
    local found_models=false
    for file in "${MODEL_DIR}"/*.gguf; do
        if [[ -f "$file" ]]; then
            found_models=true
            local filename=$(basename "$file")
            local size=$(du -h "$file" | cut -f1)
            local modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$file" 2>/dev/null || stat -c "%y" "$file" | cut -d' ' -f1-2)
            
            printf "%-40s %-10s %s\n" "$filename" "$size" "$modified"
        fi
    done
    
    if [[ "$found_models" == false ]]; then
        log "No GGUF models found in $MODEL_DIR"
    fi
    echo
}

# Function to recommend models based on system specs
recommend_models() {
    log "Analyzing system specifications..."
    
    # Get available RAM
    local ram_gb
    if [[ "$OSTYPE" == "darwin"* ]]; then
        ram_gb=$(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024))
    else
        ram_gb=$(($(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024))
    fi
    
    # Get CPU cores
    local cpu_cores
    if [[ "$OSTYPE" == "darwin"* ]]; then
        cpu_cores=$(sysctl -n hw.ncpu)
    else
        cpu_cores=$(nproc)
    fi
    
    log "System specs: ${ram_gb}GB RAM, ${cpu_cores} CPU cores"
    echo
    
    log "Recommended models for your system:"
    echo
    
    if [[ $ram_gb -ge 16 ]]; then
        echo "✅ llama-2-7b-chat - Excellent general purpose model"
        echo "✅ codellama-7b-instruct - Great for code-related tasks"
        echo "✅ mistral-7b-instruct - Fast and efficient"
        echo "✅ openchat-3.5 - High quality chat model"
    elif [[ $ram_gb -ge 8 ]]; then
        echo "✅ phi-2 - Smaller but capable model"
        echo "⚠️  mistral-7b-instruct - May work with limited memory"
    else
        echo "⚠️  Consider upgrading RAM for better model performance"
        echo "✅ phi-2 - Smallest model, may still work"
    fi
    echo
}

# Function to install llama.cpp
install_llama_cpp() {
    log "Installing llama-cpp-python..."
    
    if command -v pip3 &> /dev/null; then
        pip3 install llama-cpp-python[server] --upgrade
    elif command -v pip &> /dev/null; then
        pip install llama-cpp-python[server] --upgrade
    else
        error "pip not found. Please install Python and pip first."
        return 1
    fi
    
    success "llama-cpp-python installed successfully"
}

# Function to test model loading
test_model() {
    local model_path="$1"
    
    if [[ ! -f "$model_path" ]]; then
        error "Model file not found: $model_path"
        return 1
    fi
    
    log "Testing model loading: $model_path"
    
    # Simple test using python
    python3 -c "
import sys
try:
    from llama_cpp import Llama
    print('Loading model...')
    llm = Llama(model_path='$model_path', n_ctx=512, verbose=False)
    print('Model loaded successfully!')
    
    # Simple test prompt
    output = llm('Q: What is Kubernetes? A:', max_tokens=50, stop=['Q:', '\n'], echo=False)
    print('Test output:', output['choices'][0]['text'].strip())
    print('Model test passed!')
    
except ImportError:
    print('llama-cpp-python not installed. Run: $0 --install-llama-cpp')
    sys.exit(1)
except Exception as e:
    print(f'Model test failed: {e}')
    sys.exit(1)
" 2>&1 | tee -a "${LOG_FILE}"
    
    if [[ $? -eq 0 ]]; then
        success "Model test passed"
        return 0
    else
        error "Model test failed"
        return 1
    fi
}

# Main function
main() {
    echo "=== Kubernetes AI Agent - Model Download Script ==="
    echo
    
    # Parse command line arguments
    local command=""
    local model_name=""
    local force_download=false
    local model_path=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --list|-l)
                command="list"
                shift
                ;;
            --download|-d)
                command="download"
                model_name="$2"
                shift 2
                ;;
            --force|-f)
                force_download=true
                shift
                ;;
            --verify|-v)
                command="verify"
                model_path="$2"
                shift 2
                ;;
            --recommend|-r)
                command="recommend"
                shift
                ;;
            --install-llama-cpp)
                command="install"
                shift
                ;;
            --test|-t)
                command="test"
                model_path="$2"
                shift 2
                ;;
            --cleanup|-c)
                command="cleanup"
                shift
                ;;
            --help|-h)
                command="help"
                shift
                ;;
            *)
                if [[ -z "$command" ]]; then
                    command="download"
                    model_name="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Check dependencies
    check_dependencies
    
    # Execute command
    case "$command" in
        "list")
            show_models
            list_downloaded
            ;;
        "download")
            if [[ -z "$model_name" ]]; then
                error "Please specify a model name"
                show_models
                exit 1
            fi
            download_model "$model_name" "$force_download"
            ;;
        "verify")
            if [[ -z "$model_path" ]]; then
                error "Please specify a model path"
                exit 1
            fi
            verify_model "$model_path"
            ;;
        "recommend")
            recommend_models
            ;;
        "install")
            install_llama_cpp
            ;;
        "test")
            if [[ -z "$model_path" ]]; then
                error "Please specify a model path"
                exit 1
            fi
            test_model "$model_path"
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            echo "Usage: $0 [OPTIONS] [MODEL_NAME]"
            echo
            echo "Options:"
            echo "  -l, --list              List available and downloaded models"
            echo "  -d, --download MODEL    Download a specific model"
            echo "  -f, --force             Force re-download even if model exists"
            echo "  -v, --verify PATH       Verify a downloaded model"
            echo "  -r, --recommend         Recommend models for this system"
            echo "  --install-llama-cpp     Install llama-cpp-python"
            echo "  -t, --test PATH         Test model loading"
            echo "  -c, --cleanup           Clean up temporary files"
            echo "  -h, --help              Show this help message"
            echo
            echo "Examples:"
            echo "  $0 --list                          # List all models"
            echo "  $0 --download llama-2-7b-chat     # Download LLaMA 2 7B Chat"
            echo "  $0 --recommend                     # Get model recommendations"
            echo "  $0 --install-llama-cpp             # Install llama-cpp-python"
            echo
            show_models
            ;;
    esac
}

# Trap for cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"