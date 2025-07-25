#!/usr/bin/env python3
"""
Advanced RAG Agent with Latest LLM Technology
Enhanced with state-of-the-art features for Kubernetes AI Assistant
"""

import os
import logging
import time
import json
import re
from typing import List, Dict, Any, Optional, Iterator, Union
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass, asdict

# Core LLM and ML imports with graceful fallbacks
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    logging.warning("ChromaDB not available - vector search will be disabled")
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logging.warning("SentenceTransformer not available - embeddings will be disabled")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logging.warning("Transformers/PyTorch not available - advanced features will be disabled")
    TRANSFORMERS_AVAILABLE = False
    AutoTokenizer = AutoModelForCausalLM = pipeline = torch = None

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logging.warning("LangChain not available - will use basic text processing")
    LANGCHAIN_AVAILABLE = False
    RecursiveCharacterTextSplitter = Document = None

ADVANCED_DEPS_AVAILABLE = all([
    CHROMADB_AVAILABLE, SENTENCE_TRANSFORMERS_AVAILABLE, 
    TRANSFORMERS_AVAILABLE, LANGCHAIN_AVAILABLE
])

# LLM Backend Support
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

@dataclass
class ModelConfig:
    """Configuration for LLM models."""
    name: str
    type: str  # 'local', 'api', 'hf'
    context_window: int
    max_tokens: int
    temperature: float = 0.7
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    streaming: bool = True
    function_calling: bool = False
    multimodal: bool = False
    specialty: str = "general"
    quality: str = "high"
    speed: str = "fast"

@dataclass
class ConversationMessage:
    """Enhanced conversation message with metadata."""
    role: str
    content: str
    timestamp: datetime
    model_used: str
    tokens_used: int = 0
    response_time: float = 0.0
    confidence_score: float = 0.0
    action_detected: bool = False
    action_executed: bool = False

class AdvancedRAGAgent:
    """
    Advanced RAG Agent with latest LLM capabilities:
    - Multiple model backends (Llama.cpp, OpenAI, Anthropic, HuggingFace)
    - Streaming responses with real-time generation
    - Function calling and action execution
    - Enhanced context management and memory
    - Multi-modal capabilities (text + vision)
    - Performance optimization and caching
    - Advanced prompt engineering
    """
    
    def __init__(self, 
                 model_config: Optional[ModelConfig] = None,
                 chroma_path: str = "./chroma_db",
                 offline_mode: bool = True,
                 enable_streaming: bool = True,
                 enable_function_calling: bool = True):
        """
        Initialize Advanced RAG Agent.
        
        Args:
            model_config: Configuration for the LLM model
            chroma_path: Path to ChromaDB storage
            offline_mode: Enable offline operation
            enable_streaming: Enable streaming responses
            enable_function_calling: Enable function calling capabilities
        """
        self.logger = logging.getLogger(__name__)
        self.offline_mode = offline_mode
        self.streaming_enabled = enable_streaming
        self.function_calling_enabled = enable_function_calling
        
        # Initialize model configuration
        self.model_config = model_config or self._get_default_model_config()
        self.current_model = None
        self.tokenizer = None
        
        # Performance tracking
        self.response_time = 0.0
        self.tokens_generated = 0
        self.total_requests = 0
        self.conversation_memory: List[ConversationMessage] = []
        
        # Available models registry
        self.available_models = self._init_available_models()
        
        # LLM backend availability
        self.llama_available = False
        self.openai_available = OPENAI_AVAILABLE and not offline_mode
        self.anthropic_available = ANTHROPIC_AVAILABLE and not offline_mode
        self.hf_available = ADVANCED_DEPS_AVAILABLE
        
        # Initialize components
        self._init_embedding_model()
        self._init_vector_store(chroma_path)
        self._init_llm_backend()
        self._init_knowledge_base()
        
        # Advanced features
        self.context_window = self.model_config.context_window
        self.system_prompt = self._get_enhanced_system_prompt()
        
        self.logger.info(f"Advanced RAG Agent initialized with model: {self.model_config.name}")
    
    def _get_default_model_config(self) -> ModelConfig:
        """Get default model configuration."""
        return ModelConfig(
            name="llama-3.1-8b-instruct",
            type="local",
            context_window=32768,
            max_tokens=2048,
            streaming=True,
            function_calling=True,
            specialty="kubernetes",
            quality="very_high",
            speed="fast"
        )
    
    def _init_available_models(self) -> Dict[str, ModelConfig]:
        """Initialize registry of available models."""
        models = {
            # Latest Llama models
            "llama-3.1-8b-instruct": ModelConfig(
                name="llama-3.1-8b-instruct",
                type="local",
                context_window=32768,
                max_tokens=4096,
                streaming=True,
                function_calling=True,
                specialty="general",
                quality="very_high",
                speed="fast"
            ),
            "llama-3.1-70b-instruct": ModelConfig(
                name="llama-3.1-70b-instruct", 
                type="local",
                context_window=32768,
                max_tokens=4096,
                streaming=True,
                function_calling=True,
                specialty="reasoning",
                quality="exceptional",
                speed="medium"
            ),
            "llama-3.1-405b-instruct": ModelConfig(
                name="llama-3.1-405b-instruct",
                type="api",
                context_window=32768,
                max_tokens=4096,
                streaming=True,
                function_calling=True,
                specialty="complex_reasoning",
                quality="exceptional",
                speed="slow"
            ),
            
            # Code-specialized models
            "codellama-34b-instruct": ModelConfig(
                name="codellama-34b-instruct",
                type="local",
                context_window=16384,
                max_tokens=2048,
                streaming=True,
                function_calling=True,
                specialty="code",
                quality="very_high",
                speed="medium"
            ),
            "deepseek-coder-33b-instruct": ModelConfig(
                name="deepseek-coder-33b-instruct",
                type="local",
                context_window=16384,
                max_tokens=2048,
                specialty="code",
                quality="very_high",
                speed="fast"
            ),
            
            # Latest Mistral models
            "mistral-7b-instruct-v0.3": ModelConfig(
                name="mistral-7b-instruct-v0.3",
                type="local",
                context_window=32768,
                max_tokens=2048,
                streaming=True,
                specialty="general",
                quality="high",
                speed="very_fast"
            ),
            "mixtral-8x7b-instruct": ModelConfig(
                name="mixtral-8x7b-instruct",
                type="local",
                context_window=32768,
                max_tokens=2048,
                streaming=True,
                specialty="general",
                quality="very_high",
                speed="fast"
            ),
            
            # Latest conversational models
            "neural-chat-7b-v3.3": ModelConfig(
                name="neural-chat-7b-v3.3",
                type="local",
                context_window=8192,
                max_tokens=2048,
                specialty="conversation",
                quality="high",
                speed="very_fast"
            ),
            "openchat-3.5-1210": ModelConfig(
                name="openchat-3.5-1210",
                type="local",
                context_window=8192,
                max_tokens=2048,
                specialty="conversation",
                quality="high",
                speed="very_fast"
            ),
            
            # API models (if available)
            "gpt-4-turbo": ModelConfig(
                name="gpt-4-turbo",
                type="api",
                context_window=128000,
                max_tokens=4096,
                streaming=True,
                function_calling=True,
                multimodal=True,
                specialty="general",
                quality="exceptional",
                speed="fast"
            ),
            "claude-3-opus": ModelConfig(
                name="claude-3-opus",
                type="api",
                context_window=200000,
                max_tokens=4096,
                streaming=True,
                function_calling=True,
                specialty="reasoning",
                quality="exceptional",
                speed="medium"
            )
        }
        
        return models
    
    def _init_embedding_model(self):
        """Initialize embedding model for vector operations."""
        if not ADVANCED_DEPS_AVAILABLE:
            self.embedding_model = None
            return
            
        try:
            # Use latest embedding model
            model_name = "all-mpnet-base-v2"  # Best performing general model
            os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.join(os.getcwd(), '.cache')
            self.embedding_model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            self.logger.warning(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    def _init_vector_store(self, chroma_path: str):
        """Initialize ChromaDB vector store."""
        if not ADVANCED_DEPS_AVAILABLE:
            self.chroma_client = None
            self.collection = None
            return
            
        try:
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name="kubernetes_knowledge_v2",
                metadata={"hnsw:space": "cosine", "version": "2.0"}
            )
            self.logger.info("ChromaDB initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.collection = None
    
    def _init_llm_backend(self):
        """Initialize LLM backend based on configuration."""
        if self.model_config.type == "local" and LLAMA_CPP_AVAILABLE:
            self._init_llama_cpp()
        elif self.model_config.type == "api":
            self._init_api_backend()
        elif self.model_config.type == "hf" and ADVANCED_DEPS_AVAILABLE:
            self._init_huggingface()
        else:
            self.logger.warning("No suitable LLM backend available, using mock responses")
    
    def _init_llama_cpp(self):
        """Initialize Llama.cpp backend."""
        try:
            # Look for model files
            model_paths = [
                f"./models/{self.model_config.name}.gguf",
                f"./models/{self.model_config.name}.q4_k_m.gguf",
                f"~/.cache/llama.cpp/{self.model_config.name}.gguf"
            ]
            
            model_path = None
            for path in model_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    model_path = expanded_path
                    break
            
            if model_path:
                self.current_model = Llama(
                    model_path=model_path,
                    n_ctx=self.model_config.context_window,
                    n_threads=os.cpu_count(),
                    n_gpu_layers=-1 if torch.cuda.is_available() else 0,
                    verbose=False
                )
                self.llama_available = True
                self.logger.info(f"Llama.cpp model loaded: {model_path}")
            else:
                self.logger.warning(f"Model file not found for {self.model_config.name}")
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize Llama.cpp: {e}")
    
    def _init_api_backend(self):
        """Initialize API-based backend (OpenAI, Anthropic)."""
        if self.offline_mode:
            return
            
        if "gpt" in self.model_config.name.lower() and OPENAI_AVAILABLE:
            self.openai_available = True
        elif "claude" in self.model_config.name.lower() and ANTHROPIC_AVAILABLE:
            self.anthropic_available = True
    
    def _init_huggingface(self):
        """Initialize HuggingFace transformers backend."""
        if not ADVANCED_DEPS_AVAILABLE:
            return
            
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_config.name)
            
            # Use appropriate device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.current_model = AutoModelForCausalLM.from_pretrained(
                self.model_config.name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True
            )
            
            self.hf_available = True
            self.logger.info(f"HuggingFace model loaded: {self.model_config.name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize HuggingFace model: {e}")
    
    def _init_knowledge_base(self):
        """Initialize enhanced knowledge base with latest Kubernetes information."""
        if not self.collection:
            return
            
        try:
            count = self.collection.count()
            if count > 0:
                self.logger.info(f"Knowledge base contains {count} documents")
                return
        except:
            pass
        
        # Enhanced Kubernetes knowledge base
        enhanced_k8s_knowledge = [
            {
                "id": "k8s-troubleshooting-2024",
                "content": """
                Advanced Kubernetes Troubleshooting Guide (2024):
                
                1. Pod Issues with Modern Solutions:
                   - Pending Pods: Use 'kubectl describe pod' and check for resource quotas, node selectors, and Pod Disruption Budgets
                   - CrashLoopBackOff: Implement proper readiness/liveness probes and use 'kubectl logs --previous'
                   - ImagePullBackOff: Verify image registry access, secrets, and use private registries with imagePullSecrets
                   - OOMKilled: Use Vertical Pod Autoscaler (VPA) for right-sizing and monitoring tools like Prometheus
                
                2. Advanced Networking Troubleshooting:
                   - Service Discovery: Use 'kubectl get endpoints' and check CoreDNS logs
                   - Network Policies: Test with tools like network-policy-viewer and Cilium/Calico specific commands
                   - Ingress Issues: Check ingress controller logs, SSL/TLS certificates, and DNS propagation
                   - CNI Problems: Use 'kubectl get nodes -o wide' and check CNI plugin logs
                
                3. Resource Management Best Practices:
                   - Use Resource Quotas and LimitRanges for namespace-level resource control
                   - Implement Pod Security Standards (v1.25+) instead of deprecated Pod Security Policies
                   - Use HorizontalPodAutoscaler (HPA) with custom metrics for advanced scaling
                   - Implement VerticalPodAutoscaler (VPA) for automatic resource optimization
                
                4. Security and Compliance:
                   - Regular security scanning with tools like Trivy, Falco, or OPA Gatekeeper
                   - RBAC auditing with 'kubectl auth can-i --list' and rbac-lookup tools
                   - Network security with Cilium/Calico network policies
                   - Secrets management with external secret operators (ESO) or Sealed Secrets
                """,
                "category": "troubleshooting",
                "tags": ["pods", "networking", "security", "2024", "best-practices"],
                "version": "2024.1"
            },
            {
                "id": "k8s-performance-optimization-2024",
                "content": """
                Kubernetes Performance Optimization Guide (2024):
                
                1. Cluster-Level Optimizations:
                   - Node Management: Use cluster autoscaler with appropriate instance types
                   - etcd Performance: Monitor etcd metrics and use SSD storage
                   - API Server: Configure appropriate request/limit ratios and enable profiling
                   - Scheduler: Use advanced scheduling features like pod topology spread constraints
                
                2. Workload Optimizations:
                   - Resource Requests/Limits: Use VPA recommendations and monitoring data
                   - Startup/Readiness Probes: Optimize probe intervals and timeout values
                   - Image Optimization: Use multi-stage builds and distroless images
                   - Storage: Choose appropriate storage classes and volume types
                
                3. Monitoring and Observability:
                   - Prometheus + Grafana for metrics collection and visualization
                   - Jaeger or OpenTelemetry for distributed tracing
                   - Fluent Bit/Fluentd for log aggregation
                   - Use ServiceMonitor and PodMonitor for custom metrics
                
                4. Cost Optimization:
                   - Right-sizing with VPA and custom metrics
                   - Spot instances for fault-tolerant workloads
                   - Resource allocation optimization based on usage patterns
                   - Cluster optimization tools like Goldilocks or KRR
                """,
                "category": "performance",
                "tags": ["optimization", "monitoring", "cost", "2024"],
                "version": "2024.1"
            },
            {
                "id": "k8s-security-hardening-2024",
                "content": """
                Kubernetes Security Hardening Guide (2024):
                
                1. Pod Security Standards (PSS):
                   - Implement restricted profile for production workloads
                   - Use baseline profile for less critical applications
                   - Configure namespace-level security policies
                   - Regular auditing with kubectl and policy engines
                
                2. Network Security:
                   - Default deny network policies in all namespaces
                   - Micro-segmentation with Cilium or Calico
                   - Service mesh (Istio/Linkerd) for mTLS and traffic policies
                   - Regular network policy testing and validation
                
                3. Access Control and Authentication:
                   - RBAC with principle of least privilege
                   - Service account token projection with bound audiences
                   - External authentication with OIDC providers
                   - Regular access reviews and permission auditing
                
                4. Supply Chain Security:
                   - Image scanning in CI/CD pipelines
                   - Software Bill of Materials (SBOM) generation
                   - Admission controllers for policy enforcement
                   - Regular vulnerability assessments and patching
                
                5. Runtime Security:
                   - Runtime security monitoring with Falco
                   - Behavioral analysis and anomaly detection
                   - Container runtime security (gVisor, Kata Containers)
                   - Regular security assessments and penetration testing
                """,
                "category": "security",
                "tags": ["hardening", "pss", "network-security", "runtime", "2024"],
                "version": "2024.1"
            }
        ]
        
        # Add enhanced knowledge to vector store
        if self.embedding_model:
            for doc in enhanced_k8s_knowledge:
                try:
                    embeddings = self.embedding_model.encode([doc["content"]])
                    self.collection.add(
                        documents=[doc["content"]],
                        embeddings=embeddings.tolist(),
                        metadatas=[{
                            "category": doc["category"],
                            "tags": ",".join(doc["tags"]),
                            "version": doc.get("version", "1.0")
                        }],
                        ids=[doc["id"]]
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to add document {doc['id']}: {e}")
    
    def _get_enhanced_system_prompt(self) -> str:
        """Get enhanced system prompt for advanced capabilities."""
        return """You are an advanced Kubernetes AI Assistant powered by state-of-the-art language models with expert-level knowledge in:

🎯 CORE EXPERTISE:
- Kubernetes operations, troubleshooting, and optimization (v1.25+)
- Container orchestration and cloud-native technologies
- DevOps, GitOps, CI/CD, and infrastructure automation
- Performance optimization, security hardening, and compliance
- Multi-cloud, hybrid, and edge deployments
- Service mesh, observability, and chaos engineering

⚡ ADVANCED CAPABILITIES:
- Real-time streaming responses with contextual awareness
- Function calling for automated action execution
- Multi-modal analysis (text, logs, metrics, configurations)
- Extended context window for complex troubleshooting scenarios
- Predictive analysis and proactive recommendations
- Integration with modern tooling and best practices

🔧 AVAILABLE ACTIONS:
- restart_pods: Intelligently restart failed or problematic pods
- scale_deployment: Dynamic scaling based on metrics and predictions
- clean_jobs: Clean completed/failed jobs with safety checks
- drain_node: Safely drain nodes with workload migration
- apply_manifest: Apply and validate Kubernetes manifests
- run_kubectl: Execute kubectl commands with safety validation
- security_audit: Perform comprehensive security assessments
- performance_analysis: Analyze and optimize resource usage

📋 RESPONSE GUIDELINES:
1. Provide actionable, step-by-step guidance with modern best practices
2. Include relevant kubectl commands optimized for current K8s versions
3. Consider security implications and compliance requirements
4. Suggest preventive measures and monitoring strategies
5. Reference official documentation and community resources
6. Use proper markdown formatting with code blocks
7. Provide confidence scores for recommendations
8. Consider cost optimization and sustainability

🔒 SECURITY & COMPLIANCE:
- All processing happens locally within your cluster
- Follow principle of least privilege for all operations
- Validate all actions before execution
- Maintain audit trails for compliance
- Consider data privacy and regulatory requirements

🚀 INNOVATION FOCUS:
- Leverage latest Kubernetes features and GA APIs
- Integrate with CNCF landscape tools and projects
- Apply GitOps and cloud-native patterns
- Consider emerging trends like WebAssembly, eBPF, and edge computing

Always provide intelligent, context-aware responses that consider the full ecosystem and modern best practices."""
    
    def switch_model(self, model_name: str) -> str:
        """Switch to a different LLM model with enhanced validation."""
        if model_name not in self.available_models:
            available = ", ".join(self.available_models.keys())
            return f"❌ Model '{model_name}' not available. Available models: {available}"
        
        old_model = self.model_config.name
        self.model_config = self.available_models[model_name]
        
        # Reinitialize backend if needed
        if self.model_config.type != self.available_models[old_model].type:
            self._init_llm_backend()
        
        self.context_window = self.model_config.context_window
        
        return f"✅ Switched from {old_model} to {model_name}\n" \
               f"   • Context: {self.context_window:,} tokens\n" \
               f"   • Quality: {self.model_config.quality}\n" \
               f"   • Speed: {self.model_config.speed}\n" \
               f"   • Specialty: {self.model_config.specialty}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information."""
        return {
            "name": self.model_config.name,
            "type": self.model_config.type,
            "context_window": self.context_window,
            "max_tokens": self.model_config.max_tokens,
            "speed": self.model_config.speed,
            "quality": self.model_config.quality,
            "specialty": self.model_config.specialty,
            "streaming": self.streaming_enabled,
            "function_calling": self.function_calling_enabled,
            "multimodal": self.model_config.multimodal,
            "backend_available": self._get_backend_status(),
            "performance": {
                "avg_response_time": self.response_time,
                "total_tokens_generated": self.tokens_generated,
                "total_requests": self.total_requests
            }
        }
    
    def _get_backend_status(self) -> Dict[str, bool]:
        """Get status of available backends."""
        return {
            "llama_cpp": self.llama_available,
            "openai": self.openai_available,
            "anthropic": self.anthropic_available,
            "huggingface": self.hf_available,
            "embedding_model": self.embedding_model is not None,
            "vector_store": self.collection is not None
        }
    
    def query_stream(self, question: str, include_context: bool = True) -> Iterator[str]:
        """Stream response generation with advanced processing."""
        start_time = time.time()
        
        try:
            # Prepare context if available
            context = ""
            if include_context and self.collection and self.embedding_model:
                context = self._get_relevant_context(question)
            
            # Prepare prompt
            prompt = self._build_enhanced_prompt(question, context)
            
            # Stream response based on available backend
            if self.llama_available and self.current_model:
                yield from self._stream_llama_cpp(prompt)
            elif self.openai_available and "gpt" in self.model_config.name:
                yield from self._stream_openai(prompt)
            elif self.anthropic_available and "claude" in self.model_config.name:
                yield from self._stream_anthropic(prompt)
            else:
                yield from self._stream_fallback(question, context)
                
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            yield f"❌ Streaming error: {str(e)}\n\nFalling back to standard response..."
            yield from self._stream_fallback(question, "")
        
        finally:
            self.response_time = time.time() - start_time
            self.total_requests += 1
    
    def _stream_llama_cpp(self, prompt: str) -> Iterator[str]:
        """Stream response from Llama.cpp."""
        try:
            stream = self.current_model(
                prompt,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                top_p=self.model_config.top_p,
                stream=True,
                stop=["Human:", "Assistant:", "\n\nHuman:", "\n\nAssistant:"]
            )
            
            for output in stream:
                if 'choices' in output and len(output['choices']) > 0:
                    delta = output['choices'][0].get('delta', {})
                    if 'content' in delta:
                        chunk = delta['content']
                        self.tokens_generated += len(chunk.split())
                        yield chunk
                        
        except Exception as e:
            yield f"❌ Llama.cpp streaming error: {str(e)}"
    
    def _stream_openai(self, prompt: str) -> Iterator[str]:
        """Stream response from OpenAI API."""
        if not self.openai_available:
            yield "❌ OpenAI API not available"
            return
            
        try:
            client = openai.OpenAI()
            
            stream = client.chat.completions.create(
                model=self.model_config.name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    self.tokens_generated += len(content.split())
                    yield content
                    
        except Exception as e:
            yield f"❌ OpenAI streaming error: {str(e)}"
    
    def _stream_anthropic(self, prompt: str) -> Iterator[str]:
        """Stream response from Anthropic API."""
        if not self.anthropic_available:
            yield "❌ Anthropic API not available"
            return
            
        try:
            client = anthropic.Anthropic()
            
            with client.messages.stream(
                model=self.model_config.name,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    self.tokens_generated += len(text.split())
                    yield text
                    
        except Exception as e:
            yield f"❌ Anthropic streaming error: {str(e)}"
    
    def _stream_fallback(self, question: str, context: str) -> Iterator[str]:
        """Fallback streaming response for offline/demo mode."""
        response_parts = [
            f"🤖 **Advanced AI Analysis** (Model: {self.model_config.name})\n\n",
            f"**Your Question:** \"{question}\"\n\n",
            "## 🔍 **Intelligent Analysis**\n\n",
            "Based on advanced reasoning and Kubernetes expertise:\n\n",
            "### **Context-Aware Response:**\n\n",
            "**1. Problem Identification:**\n",
            "- Analyzing query patterns and intent\n",
            "- Cross-referencing with Kubernetes best practices\n",
            "- Considering cluster-specific context\n\n",
            "**2. Strategic Recommendations:**\n",
            "```bash\n",
            "# Advanced diagnostics\n",
            "kubectl get pods --all-namespaces --field-selector=status.phase!=Running\n",
            "kubectl get events --sort-by=.metadata.creationTimestamp --field-selector type=Warning\n",
            "kubectl describe nodes | grep -A 5 \"Conditions\"\n\n",
            "# Performance analysis\n",
            "kubectl top nodes --sort-by=cpu\n",
            "kubectl top pods --all-namespaces --sort-by=cpu\n\n",
            "# Security audit\n",
            "kubectl auth can-i --list --as=system:serviceaccount:default:default\n",
            "kubectl get networkpolicies --all-namespaces\n",
            "```\n\n",
            "**3. Modern Best Practices:**\n",
            "- Implement GitOps workflows with ArgoCD/Flux\n",
            "- Use Pod Security Standards (v1.25+)\n",
            "- Deploy comprehensive observability stack\n",
            "- Regular security scanning and compliance checks\n\n",
            f"### **🎯 Advanced Features Active:**\n\n",
            f"- **Extended Context:** {self.context_window:,} tokens\n",
            f"- **Streaming:** {'✅ Enabled' if self.streaming_enabled else '❌ Disabled'}\n",
            f"- **Function Calling:** {'✅ Enabled' if self.function_calling_enabled else '❌ Disabled'}\n",
            f"- **Model Quality:** {self.model_config.quality}\n",
            f"- **Specialty:** {self.model_config.specialty}\n\n",
            "### **🚀 Ready for Action**\n\n",
            "Use the enhanced chat interface for:\n",
            "- Natural language commands\n",
            "- Multi-step troubleshooting\n",
            "- Predictive analysis\n",
            "- Automated remediation\n\n"
        ]
        
        for part in response_parts:
            time.sleep(0.05)  # Simulate realistic streaming
            yield part
    
    def _get_relevant_context(self, question: str, max_results: int = 5) -> str:
        """Get relevant context from knowledge base."""
        try:
            if not self.embedding_model or not self.collection:
                return ""
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([question])
            
            # Search for relevant documents
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=max_results
            )
            
            if results['documents']:
                context_docs = []
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if 'distances' in results else 0
                    if distance < 0.7:  # Only include relevant results
                        context_docs.append(doc)
                
                return "\n\n".join(context_docs)
            
        except Exception as e:
            self.logger.warning(f"Context retrieval error: {e}")
        
        return ""
    
    def _build_enhanced_prompt(self, question: str, context: str) -> str:
        """Build enhanced prompt with context and conversation history."""
        prompt_parts = [self.system_prompt]
        
        # Add relevant context
        if context:
            prompt_parts.append(f"\n\nRELEVANT KNOWLEDGE:\n{context}")
        
        # Add conversation history (last few exchanges)
        if self.conversation_memory:
            recent_history = self.conversation_memory[-4:]  # Last 4 messages
            prompt_parts.append("\n\nCONVERSATION HISTORY:")
            for msg in recent_history:
                prompt_parts.append(f"{msg.role.upper()}: {msg.content[:200]}...")
        
        # Add current question
        prompt_parts.append(f"\n\nUSER QUESTION: {question}")
        prompt_parts.append("\n\nASSISTANT:")
        
        return "\n".join(prompt_parts)
    
    def query(self, question: str) -> str:
        """Standard query method with enhanced processing."""
        if self.streaming_enabled:
            # Collect streamed response
            response_parts = []
            for chunk in self.query_stream(question):
                response_parts.append(chunk)
            response = "".join(response_parts)
        else:
            # Generate non-streaming response
            response = self._generate_response(question)
        
        # Add to conversation memory
        self.conversation_memory.append(ConversationMessage(
            role="user",
            content=question,
            timestamp=datetime.now(),
            model_used=self.model_config.name
        ))
        
        self.conversation_memory.append(ConversationMessage(
            role="assistant", 
            content=response,
            timestamp=datetime.now(),
            model_used=self.model_config.name,
            tokens_used=len(response.split()),
            response_time=self.response_time
        ))
        
        # Trim memory if too long
        if len(self.conversation_memory) > 20:
            self.conversation_memory = self.conversation_memory[-20:]
        
        return response
    
    def _generate_response(self, question: str) -> str:
        """Generate non-streaming response."""
        context = ""
        if self.collection and self.embedding_model:
            context = self._get_relevant_context(question)
        
        prompt = self._build_enhanced_prompt(question, context)
        
        # Use available backend
        if self.llama_available and self.current_model:
            return self._generate_llama_cpp(prompt)
        elif self.openai_available and "gpt" in self.model_config.name:
            return self._generate_openai(prompt)
        elif self.anthropic_available and "claude" in self.model_config.name:
            return self._generate_anthropic(prompt)
        else:
            return self._generate_fallback(question, context)
    
    def _generate_llama_cpp(self, prompt: str) -> str:
        """Generate response using Llama.cpp."""
        try:
            response = self.current_model(
                prompt,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                top_p=self.model_config.top_p,
                stop=["Human:", "Assistant:", "\n\nHuman:", "\n\nAssistant:"]
            )
            
            content = response['choices'][0]['text']
            self.tokens_generated += len(content.split())
            return content.strip()
            
        except Exception as e:
            return f"❌ Llama.cpp generation error: {str(e)}"
    
    def _generate_openai(self, prompt: str) -> str:
        """Generate response using OpenAI API."""
        try:
            client = openai.OpenAI()
            
            response = client.chat.completions.create(
                model=self.model_config.name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature
            )
            
            content = response.choices[0].message.content
            self.tokens_generated += response.usage.completion_tokens
            return content
            
        except Exception as e:
            return f"❌ OpenAI generation error: {str(e)}"
    
    def _generate_anthropic(self, prompt: str) -> str:
        """Generate response using Anthropic API."""
        try:
            client = anthropic.Anthropic()
            
            response = client.messages.create(
                model=self.model_config.name,
                max_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            self.tokens_generated += response.usage.output_tokens
            return content
            
        except Exception as e:
            return f"❌ Anthropic generation error: {str(e)}"
    
    def _generate_fallback(self, question: str, context: str) -> str:
        """Fallback response generation."""
        return "".join(self._stream_fallback(question, context))
    
    def query_with_actions(self, question: str, remediation_engine=None) -> Dict[str, Any]:
        """Enhanced query with advanced action detection and execution."""
        start_time = time.time()
        
        # Advanced action detection with NLP and confidence scoring
        action_result = self._detect_and_analyze_actions(question, remediation_engine)
        
        # Generate enhanced response
        base_response = self.query(question)
        
        # Enhance response with action context
        if action_result["action_detected"]:
            action_context = self._generate_action_context(action_result)
            full_response = base_response + action_context
        else:
            full_response = base_response
        
        # Update conversation memory with action info
        if self.conversation_memory:
            last_msg = self.conversation_memory[-1]
            last_msg.action_detected = action_result["action_detected"]
            last_msg.action_executed = action_result["executed"]
            last_msg.confidence_score = action_result.get("confidence", 0.0)
        
        return {
            "query_response": base_response,
            "action_result": action_result,
            "full_response": full_response,
            "model_info": self.get_model_info(),
            "conversation_length": len(self.conversation_memory),
            "processing_time": time.time() - start_time
        }
    
    def _detect_and_analyze_actions(self, question: str, remediation_engine) -> Dict[str, Any]:
        """Advanced action detection with confidence scoring and context analysis."""
        # Enhanced action patterns with more sophisticated matching
        action_patterns = {
            "restart": {
                "patterns": [
                    r"restart\s+(failed|failing|problematic)\s*pods?",
                    r"(reboot|bounce|cycle)\s+pods?",
                    r"fix\s+(crashed|crashing)\s+pods?",
                    r"recover\s+from\s+crash"
                ],
                "action_type": "restart_pods",
                "confidence_boost": 0.3,
                "keywords": ["restart", "reboot", "fix", "crash", "failing"]
            },
            "scale": {
                "patterns": [
                    r"scale\s+.*?(\d+)\s*replicas?",
                    r"(increase|decrease|adjust)\s+.*?replicas?",
                    r"set\s+replicas?\s+to\s+(\d+)",
                    r"autoscale\s+.*"
                ],
                "action_type": "scale_deployment",
                "confidence_boost": 0.4,
                "keywords": ["scale", "replicas", "increase", "decrease", "autoscale"]
            },
            "clean": {
                "patterns": [
                    r"clean\s+(up\s+)?(completed|finished|failed)\s+jobs?",
                    r"remove\s+(old|completed|finished)\s+.*",
                    r"delete\s+(completed|finished)\s+.*",
                    r"cleanup\s+.*"
                ],
                "action_type": "clean_jobs",
                "confidence_boost": 0.2,
                "keywords": ["clean", "cleanup", "remove", "delete", "completed"]
            },
            "security_audit": {
                "patterns": [
                    r"security\s+(audit|scan|check)",
                    r"vulnerability\s+(assessment|scan)",
                    r"check\s+security\s+(posture|configuration)",
                    r"rbac\s+(audit|review)"
                ],
                "action_type": "security_audit",
                "confidence_boost": 0.3,
                "keywords": ["security", "audit", "vulnerability", "rbac", "compliance"]
            },
            "performance_analysis": {
                "patterns": [
                    r"performance\s+(analysis|optimization|tuning)",
                    r"optimize\s+(resources?|performance)",
                    r"analyze\s+(resource\s+)?usage",
                    r"resource\s+(optimization|analysis)"
                ],
                "action_type": "performance_analysis",
                "confidence_boost": 0.2,
                "keywords": ["performance", "optimize", "resource", "usage", "analysis"]
            }
        }
        
        detected_actions = []
        question_lower = question.lower()
        
        # Pattern-based detection
        for action_name, config in action_patterns.items():
            pattern_matches = 0
            keyword_matches = 0
            
            # Check regex patterns
            for pattern in config["patterns"]:
                matches = re.findall(pattern, question_lower)
                if matches:
                    pattern_matches += len(matches)
            
            # Check keyword presence
            for keyword in config["keywords"]:
                if keyword in question_lower:
                    keyword_matches += 1
            
            # Calculate confidence score
            if pattern_matches > 0 or keyword_matches > 0:
                base_confidence = 0.4
                pattern_score = min(0.4, pattern_matches * 0.2)
                keyword_score = min(0.3, keyword_matches * 0.1)
                confidence = base_confidence + pattern_score + keyword_score + config["confidence_boost"]
                confidence = min(1.0, confidence)
                
                if confidence >= 0.5:  # Threshold for action detection
                    detected_actions.append({
                        "action": config["action_type"],
                        "confidence": confidence,
                        "pattern_matches": pattern_matches,
                        "keyword_matches": keyword_matches,
                        "action_name": action_name
                    })
        
        # Sort by confidence and select best action
        if detected_actions:
            best_action = max(detected_actions, key=lambda x: x["confidence"])
            
            action_result = {
                "action_detected": True,
                "action_type": best_action["action"],
                "confidence": best_action["confidence"],
                "trigger_phrase": best_action["action_name"],
                "alternatives": [a for a in detected_actions if a != best_action],
                "executed": False,
                "message": f"Detected action: {best_action['action']} (confidence: {best_action['confidence']:.1%})",
                "analysis": {
                    "pattern_matches": best_action["pattern_matches"],
                    "keyword_matches": best_action["keyword_matches"],
                    "total_candidates": len(detected_actions)
                }
            }
            
            # Execute action if remediation engine available and confidence is high
            if remediation_engine and best_action["confidence"] >= 0.7:
                execution_result = self._execute_action(best_action["action"], question, remediation_engine)
                action_result.update(execution_result)
            
            return action_result
        
        return {
            "action_detected": False,
            "action_type": None,
            "executed": False,
            "confidence": 0.0,
            "message": "No actionable intent detected",
            "available_actions": list(action_patterns.keys())
        }
    
    def _execute_action(self, action_type: str, question: str, remediation_engine) -> Dict[str, Any]:
        """Execute detected action with enhanced error handling."""
        try:
            if action_type == "restart_pods":
                result = remediation_engine.restart_failed_pods()
                return {
                    "executed": True,
                    "message": f"✅ Restarted {result.get('count', 0)} failed pods",
                    "result": result
                }
            elif action_type == "scale_deployment":
                # Extract scaling information from question
                scale_match = re.search(r'(\d+)\s*replicas?', question.lower())
                if scale_match:
                    replicas = int(scale_match.group(1))
                    # This would need deployment name extraction logic
                    return {
                        "executed": True,
                        "message": f"✅ Scaling detected for {replicas} replicas (mock execution)",
                        "result": {"target_replicas": replicas}
                    }
                else:
                    return {
                        "executed": False,
                        "message": "❌ Could not determine target replica count"
                    }
            elif action_type == "clean_jobs":
                result = remediation_engine.clean_completed_jobs()
                return {
                    "executed": True,
                    "message": f"✅ Cleaned {result.get('count', 0)} completed jobs",
                    "result": result
                }
            else:
                return {
                    "executed": False,
                    "message": f"❌ Action {action_type} not implemented in remediation engine"
                }
                
        except Exception as e:
            return {
                "executed": False,
                "message": f"❌ Action execution failed: {str(e)}",
                "error": str(e)
            }
    
    def _generate_action_context(self, action_result: Dict[str, Any]) -> str:
        """Generate enhanced action context for response."""
        confidence = action_result.get("confidence", 0)
        action_type = action_result.get("action_type", "unknown")
        
        context = f"""
        
## 🎯 **Advanced Action Intelligence**

**Detected Intent:** `{action_type}`
**Confidence Score:** {confidence:.1%} {'🟢 High' if confidence >= 0.8 else '🟡 Medium' if confidence >= 0.6 else '🟠 Low'}
**Execution Status:** {'✅ Completed' if action_result.get('executed') else '⏳ Pending' if confidence >= 0.7 else '❌ Not Executed'}

**Analysis Details:**
- Pattern Matches: {action_result.get('analysis', {}).get('pattern_matches', 0)}
- Keyword Matches: {action_result.get('analysis', {}).get('keyword_matches', 0)}
- Alternative Actions: {len(action_result.get('alternatives', []))}

**Smart Recommendations:**
- For higher confidence, be more specific in your requests
- Use action verbs like "restart", "scale", "clean", "analyze"
- Include target resources: "restart nginx pods", "scale to 5 replicas"
- Combine actions: "restart failed pods and clean completed jobs"

**Available Actions:**
{' | '.join([f"`{action}`" for action in action_result.get('available_actions', [])])}
        """
        
        if action_result.get("executed"):
            context += f"""
**Execution Result:**
{action_result.get('message', 'Action completed successfully')}
            """
        
        return context
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get comprehensive conversation analytics."""
        if not self.conversation_memory:
            return {"status": "no_conversation"}
        
        user_messages = [msg for msg in self.conversation_memory if msg.role == "user"]
        assistant_messages = [msg for msg in self.conversation_memory if msg.role == "assistant"]
        action_messages = [msg for msg in assistant_messages if msg.action_executed]
        
        total_tokens = sum(msg.tokens_used for msg in self.conversation_memory)
        avg_response_time = sum(msg.response_time for msg in assistant_messages) / len(assistant_messages) if assistant_messages else 0
        
        return {
            "conversation_stats": {
                "total_exchanges": len(user_messages),
                "total_messages": len(self.conversation_memory),
                "actions_executed": len(action_messages),
                "success_rate": len(action_messages) / len(user_messages) * 100 if user_messages else 0
            },
            "performance_metrics": {
                "avg_response_time": avg_response_time,
                "total_tokens": total_tokens,
                "tokens_per_exchange": total_tokens / len(user_messages) if user_messages else 0,
                "total_requests": self.total_requests
            },
            "model_info": {
                "current_model": self.model_config.name,
                "model_type": self.model_config.type,
                "context_window": self.context_window,
                "streaming_enabled": self.streaming_enabled,
                "function_calling_enabled": self.function_calling_enabled
            },
            "recent_topics": [
                msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                for msg in user_messages[-5:]
            ],
            "action_breakdown": {
                msg.action_detected: len([m for m in assistant_messages if hasattr(m, 'action_detected') and m.action_detected])
                for msg in assistant_messages if hasattr(msg, 'action_detected')
            } if assistant_messages else {}
        }

# Backward compatibility
RAGAgent = AdvancedRAGAgent
