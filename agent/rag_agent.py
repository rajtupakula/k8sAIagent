import os
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import subprocess
import re
import time
from collections import defaultdict, Counter

# Import with graceful fallbacks for offline operation
try:
    # Set environment variables to prevent ChromaDB telemetry and version issues
    os.environ["CHROMA_TELEMETRY"] = "false"
    os.environ["ANONYMIZED_TELEMETRY"] = "false"
    
    # Import ChromaDB with error handling for container environments
    import chromadb
    from chromadb.config import Settings
    
    # Test ChromaDB initialization to catch runtime errors early
    try:
        # Test basic ChromaDB functionality
        test_client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=False
        ))
        test_client = None  # Clean up test
        CHROMADB_AVAILABLE = True
        logging.info("ChromaDB successfully initialized")
    except Exception as chroma_init_error:
        logging.warning(f"ChromaDB initialization failed: {chroma_init_error}")
        CHROMADB_AVAILABLE = False
        chromadb = None
        
except ImportError as import_error:
    logging.warning(f"ChromaDB not available - vector search will be disabled: {import_error}")
    CHROMADB_AVAILABLE = False
    chromadb = None
except RuntimeError as runtime_error:
    logging.warning(f"ChromaDB RuntimeError - falling back to offline mode: {runtime_error}")
    CHROMADB_AVAILABLE = False
    chromadb = None
except Exception as general_error:
    logging.warning(f"ChromaDB encountered an error - falling back to offline mode: {general_error}")
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
    
    # Test sentence-transformers initialization in container environment
    try:
        # Quick test to ensure sentence-transformers can work
        # This helps catch CUDA/torch issues early
        test_model_name = "all-MiniLM-L6-v2"  # Small, reliable model
        # Don't actually load the model, just test the import works
        SENTENCE_TRANSFORMERS_AVAILABLE = True
        logging.info("SentenceTransformer successfully imported")
    except Exception as st_init_error:
        logging.warning(f"SentenceTransformer initialization test failed: {st_init_error}")
        SENTENCE_TRANSFORMERS_AVAILABLE = False
        SentenceTransformer = None
        
except ImportError as import_error:
    logging.warning(f"SentenceTransformer not available - embeddings will be disabled: {import_error}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None
except Exception as general_error:
    logging.warning(f"SentenceTransformer encountered an error - falling back to basic mode: {general_error}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logging.warning("LangChain not available - will use basic text splitting")
    LANGCHAIN_AVAILABLE = False
    RecursiveCharacterTextSplitter = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    logging.warning("Requests not available - external API calls will be disabled")
    REQUESTS_AVAILABLE = False
    requests = None

# Import expert remediation agent
try:
    from .expert_remediation_agent import ExpertRemediationAgent
except ImportError:
    try:
        from expert_remediation_agent import ExpertRemediationAgent
    except ImportError:
        ExpertRemediationAgent = None

class RAGAgent:
    """Retrieval-Augmented Generation agent for Kubernetes knowledge with offline capabilities."""
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 chroma_path: str = "./chroma_db",
                 llama_endpoint: str = "http://localhost:8080",
                 offline_mode: bool = True):
        """
        Initialize RAG agent.
        
        Args:
            model_name: Sentence transformer model for embeddings
            chroma_path: Path to ChromaDB storage
            llama_endpoint: Endpoint for llama.cpp server
            offline_mode: Enable offline mode for complete local operation
        """
        self.logger = logging.getLogger(__name__)
        self.llama_endpoint = llama_endpoint
        self.offline_mode = offline_mode
        self.llama_available = False
        
        # Initialize expert remediation agent
        if ExpertRemediationAgent:
            try:
                self.expert_agent = ExpertRemediationAgent()
                self.logger.info("Expert remediation agent initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize expert agent: {e}")
                self.expert_agent = None
        else:
            self.expert_agent = None
            self.logger.warning("Expert remediation agent not available")
        
        # Enhanced system prompt for expert-level troubleshooting
        self.expert_system_prompt = """You are an expert-level system engineer and developer with deep expertise in:

**UBUNTU/LINUX SYSTEMS:**
- System administration, performance tuning, and troubleshooting
- Service management (systemd), process monitoring, and resource optimization
- Network configuration, storage management, and security hardening
- Log analysis, debugging kernel issues, and system recovery

**KUBERNETES ORCHESTRATION:**
- Cluster administration, node management, and workload orchestration
- Pod lifecycle, container runtime troubleshooting, and networking
- Storage orchestration, RBAC, security policies, and admission controllers
- Performance optimization, capacity planning, and disaster recovery

**GLUSTERFS DISTRIBUTED STORAGE:**
- Volume management, brick configuration, and peer connectivity
- Heal operations, split-brain resolution, and data consistency
- Performance tuning, quota management, and backup strategies
- Integration with container orchestration and application storage

**EXPERT CAPABILITIES:**
✅ Intelligent issue detection using pattern recognition
✅ Automated diagnosis with safety-first approach
✅ Root cause analysis with comprehensive system context
✅ Step-by-step remediation with rollback procedures
✅ Proactive monitoring and preventive maintenance
✅ Security-aware operations with audit trails

**OPERATIONAL CONSTRAINTS:**
- Work within existing system configuration (no external binaries)
- Prioritize system stability and data integrity
- Use built-in tools and commands only
- Implement comprehensive safety checks
- Provide clear explanations and documentation

**RESPONSE FORMAT:**
Always provide:
1. **Issue Analysis**: Root cause identification with confidence level
2. **Impact Assessment**: System impact and urgency level
3. **Remediation Plan**: Step-by-step resolution with safety checks
4. **Verification Steps**: How to confirm the fix worked
5. **Prevention**: How to prevent recurrence
6. **Commands**: Exact commands to execute (if applicable)

Be thorough, precise, and always consider the broader system context. Prioritize solutions that maintain system stability while effectively resolving issues."""
        
        # Initialize embedding model with offline capability
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Set cache directory to local path to avoid downloads
                os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.join(os.getcwd(), '.cache')
                self.embedding_model = SentenceTransformer(model_name)
                self.logger.info(f"Loaded embedding model: {model_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load embedding model: {e}")
                self.logger.info("Will continue without embeddings (reduced functionality)")
                self.embedding_model = None
        else:
            self.embedding_model = None
            self.logger.warning("SentenceTransformers not available - embeddings disabled")
        
        # Initialize ChromaDB
        if CHROMADB_AVAILABLE and chromadb is not None:
            try:
                # Comprehensive telemetry disabling
                os.environ["ANONYMIZED_TELEMETRY"] = "False"
                os.environ["CHROMA_SERVER_NOFILE"] = "1048576"
                os.environ["CHROMA_TELEMETRY"] = "False"
                
                # Import telemetry disabling utility
                try:
                    from .telemetry_disable import disable_chromadb_telemetry
                    disable_chromadb_telemetry()
                except ImportError:
                    pass
                
                # Create unique database path to prevent conflicts
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                chroma_path = f"/data/chroma_db_{unique_id}"
                
                # Ensure directory exists and is writable
                os.makedirs(chroma_path, exist_ok=True)
                os.chmod(chroma_path, 0o755)
                
                # Clean up any existing conflicting databases
                try:
                    import shutil
                    existing_dbs = [d for d in os.listdir("/data") if d.startswith("chroma_db_") and d != f"chroma_db_{unique_id}"]
                    for db_dir in existing_dbs[-5:]:  # Keep only last 5 instances
                        old_path = f"/data/{db_dir}"
                        if os.path.exists(old_path):
                            shutil.rmtree(old_path, ignore_errors=True)
                except Exception:
                    pass  # Ignore cleanup errors
                
                # Disable telemetry at module level
                try:
                    import chromadb.telemetry.product.posthog as posthog_telemetry
                    if hasattr(posthog_telemetry, 'posthog'):
                        posthog_telemetry.posthog = None
                except ImportError:
                    pass
                
                # Create client with telemetry disabled in settings
                try:
                    from chromadb.config import Settings
                    settings = Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                    self.chroma_client = chromadb.PersistentClient(
                        path=chroma_path,
                        settings=settings
                    )
                except Exception:
                    # Fallback to basic client
                    self.chroma_client = chromadb.PersistentClient(path=chroma_path)
                
                self.collection = self.chroma_client.get_or_create_collection(
                    name="kubernetes_knowledge",
                    metadata={"hnsw:space": "cosine"}
                )
                self.logger.info("ChromaDB initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize ChromaDB: {e}")
                self.logger.info("Will continue without vector database (reduced functionality)")
                self.chroma_client = None
                self.collection = None
        else:
            self.chroma_client = None
            self.collection = None
            self.logger.warning("ChromaDB not available - vector search disabled")
        
        # Check LLaMA server availability
        self._check_llama_server()
        
        # Text splitter for chunking documents with fallback
        if RecursiveCharacterTextSplitter is not None:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", " ", ""]
            )
            self.logger.info("LangChain text splitter initialized")
        else:
            # Fallback text splitter implementation
            self.text_splitter = self._create_fallback_text_splitter()
            self.logger.warning("Using fallback text splitter (LangChain not available)")
        
        # Initialize issue history manager for enhanced RAG features
        try:
            from .issue_history_manager import IssueHistoryManager
            self.issue_history = IssueHistoryManager()
            self.logger.info("Issue history manager initialized")
        except ImportError:
            try:
                from issue_history_manager import IssueHistoryManager
                self.issue_history = IssueHistoryManager()
                self.logger.info("Issue history manager initialized")
            except ImportError:
                self.issue_history = None
                self.logger.warning("Issue history manager not available - historical analysis disabled")
        except Exception as e:
            self.logger.warning(f"Failed to initialize issue history manager: {e}")
            self.issue_history = None
        
        # Load default knowledge base
        self._initialize_knowledge_base()
    
    def _check_llama_server(self):
        """Check if LLaMA server is available."""
        if not REQUESTS_AVAILABLE:
            self.llama_available = False
            return
            
        try:
            response = requests.get(f"{self.llama_endpoint}/health", timeout=2)
            if response.status_code == 200:
                self.llama_available = True
                self.logger.info("LLaMA server is available")
            else:
                self.llama_available = False
        except Exception as e:
            self.llama_available = False
            # Only log as debug to reduce noise - this is expected in many environments
            self.logger.debug(f"LLaMA server not available: {e}")
            if not self.offline_mode:
                self.offline_mode = True
    
    def _create_fallback_text_splitter(self):
        """Create a fallback text splitter when LangChain is not available."""
        class FallbackTextSplitter:
            def __init__(self, chunk_size=1000, chunk_overlap=200, separators=None):
                self.chunk_size = chunk_size
                self.chunk_overlap = chunk_overlap
                self.separators = separators or ["\n\n", "\n", " ", ""]
            
            def split_text(self, text):
                """Split text into chunks using basic string operations."""
                if not text:
                    return []
                
                # Try separators in order of preference
                for separator in self.separators:
                    if separator in text:
                        # Split by separator and create chunks
                        parts = text.split(separator)
                        chunks = []
                        current_chunk = ""
                        
                        for part in parts:
                            # If adding this part would exceed chunk size, finalize current chunk
                            if len(current_chunk) + len(part) + len(separator) > self.chunk_size:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                    # Start new chunk with overlap if possible
                                    if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                                        current_chunk = current_chunk[-self.chunk_overlap:] + separator + part
                                    else:
                                        current_chunk = part
                                else:
                                    current_chunk = part
                            else:
                                # Add to current chunk
                                if current_chunk:
                                    current_chunk += separator + part
                                else:
                                    current_chunk = part
                        
                        # Add final chunk
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        
                        return [chunk for chunk in chunks if chunk.strip()]
                
                # If no separators found, just split by chunk size
                chunks = []
                for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                    chunk = text[i:i + self.chunk_size]
                    if chunk.strip():
                        chunks.append(chunk.strip())
                
                return chunks
        
        return FallbackTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def _initialize_knowledge_base(self):
        """Initialize with basic Kubernetes knowledge."""
        if not self.collection:
            return
        
        # Check if knowledge base is already populated
        try:
            count = self.collection.count()
            if count > 0:
                self.logger.info(f"Knowledge base already contains {count} documents")
                return
        except:
            pass
        
        # Basic Kubernetes troubleshooting knowledge
        k8s_knowledge = [
            {
                "id": "pod-troubleshooting",
                "content": """
                Pod Troubleshooting Guide:
                
                1. Pod stuck in Pending state:
                   - Check resource requests vs available resources
                   - Verify node selectors and affinity rules
                   - Check if persistent volumes are available
                   - Review taints and tolerations
                
                2. Pod in CrashLoopBackOff:
                   - Check container logs: kubectl logs <pod-name>
                   - Verify environment variables and configuration
                   - Check resource limits and requests
                   - Review container health checks
                
                3. Pod stuck in Terminating:
                   - Check for finalizers blocking deletion
                   - Force delete if necessary: kubectl delete pod <name> --force --grace-period=0
                   - Check for stuck volume mounts
                """,
                "category": "troubleshooting",
                "tags": ["pods", "pending", "crashloop", "terminating"]
            },
            {
                "id": "node-troubleshooting",
                "content": """
                Node Troubleshooting Guide:
                
                1. Node NotReady:
                   - Check kubelet logs: journalctl -u kubelet
                   - Verify network connectivity
                   - Check disk space and memory pressure
                   - Review container runtime status
                
                2. Node resource pressure:
                   - DiskPressure: Clean up unused images and logs
                   - MemoryPressure: Evict pods or add memory
                   - PIDPressure: Increase PID limits or reduce pod density
                
                3. Node scheduling issues:
                   - Check taints: kubectl describe node <name>
                   - Review resource availability
                   - Verify node labels and selectors
                """,
                "category": "troubleshooting",
                "tags": ["nodes", "notready", "pressure", "scheduling"]
            },
            {
                "id": "storage-troubleshooting",
                "content": """
                Storage Troubleshooting Guide:
                
                1. PersistentVolume issues:
                   - Check PV status: kubectl get pv
                   - Verify storage class configuration
                   - Review access modes compatibility
                   - Check underlying storage provider
                
                2. PersistentVolumeClaim stuck:
                   - Verify storage class exists and is default
                   - Check resource requests vs available PVs
                   - Review access mode requirements
                   - Check volume binding mode
                
                3. Mount issues:
                   - Check pod events for mount errors
                   - Verify file system permissions
                   - Review SELinux/AppArmor policies
                   - Check storage provider connectivity
                """,
                "category": "troubleshooting",
                "tags": ["storage", "pv", "pvc", "mount"]
            },
            {
                "id": "network-troubleshooting",
                "content": """
                Network Troubleshooting Guide:
                
                1. Service connectivity issues:
                   - Check service endpoints: kubectl get endpoints
                   - Verify service selector matches pod labels
                   - Test DNS resolution: nslookup service-name
                   - Check network policies
                
                2. Ingress problems:
                   - Verify ingress controller is running
                   - Check ingress resource configuration
                   - Review TLS certificate issues
                   - Test backend service connectivity
                
                3. Pod-to-pod communication:
                   - Check CNI plugin status
                   - Verify network policies
                   - Test with netshoot or debug containers
                   - Review firewall rules
                """,
                "category": "troubleshooting",
                "tags": ["networking", "service", "ingress", "connectivity"]
            }
        ]
        
        # Add knowledge to vector database
        for doc in k8s_knowledge:
            self.add_document(doc["content"], doc["id"], doc)
    
    def add_document(self, content: str, doc_id: str, metadata: Dict[str, Any] = None):
        """Add a document to the knowledge base."""
        if not self.collection or not self.embedding_model:
            return False
        
        try:
            # Split document into chunks
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                
                # Generate embedding
                embedding = self.embedding_model.encode(chunk).tolist()
                
                # Prepare metadata
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata.update({
                    "chunk_id": chunk_id,
                    "chunk_index": i,
                    "source_doc": doc_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add to collection
                self.collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[chunk_metadata]
                )
            
            self.logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add document {doc_id}: {e}")
            return False
    
    def query(self, question: str, max_results: int = 5) -> str:
        """Query the RAG agent with a question."""
        
        # If no embedding model or collection available, use offline response
        if not self.collection or not self.embedding_model:
            self.logger.info("Using offline response mode - no embeddings/database available")
            return self._offline_response("", question)
        
        try:
            # Generate embedding for question
            question_embedding = self.embedding_model.encode(question).tolist()
            
            # Search for relevant documents
            results = self.collection.query(
                query_embeddings=[question_embedding],
                n_results=max_results,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["documents"][0]:
                return self._offline_response("", question)
            
            # Prepare context from retrieved documents
            context = self._prepare_context(results, question)
            
            # Generate response using llama.cpp or offline mode
            response = self._generate_response(context, question)
            
            return response
            
        except Exception as e:
            self.logger.warning(f"Error processing query: {e}")
            return self._offline_response("", question)
    
    def investigate_issue(self, issue_id: str) -> str:
        """Investigate a specific issue and provide recommendations."""
        # This would typically fetch issue details from the monitor
        # For now, provide general investigation guidance
        
        investigation_prompt = f"""
        Investigate issue ID: {issue_id}
        
        Please provide:
        1. Possible root causes
        2. Diagnostic steps to take
        3. Recommended remediation actions
        4. Prevention strategies
        """
        
        return self.query(investigation_prompt)
    
    def _prepare_context(self, results: Dict, question: str) -> str:
        """Prepare context from search results."""
        context_parts = []
        
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            
            # Only include relevant results (distance threshold)
            if distance < 0.8:  # Cosine similarity threshold
                context_parts.append(f"[Document {i+1}]:\n{doc}\n")
        
        context = "\n".join(context_parts)
        
        return f"""
        Based on the following Kubernetes knowledge:
        
        {context}
        
        Question: {question}
        
        Please provide a helpful response based on the provided context.
        """
    
    def _generate_response(self, context: str, question: str) -> str:
        """Generate response using llama.cpp server or offline mode."""
        
        # If LLaMA is available and we're not in offline mode, try using it
        if self.llama_available and not self.offline_mode:
            try:
                # Prepare prompt
                prompt = f"""
                You are a Kubernetes expert assistant. Answer the following question based on the provided context.
                Be concise, practical, and provide actionable advice.
                If the question requests an action, provide specific kubectl commands or steps.
                
                Context:
                {context}
                
                Question: {question}
                
                Answer:
                """
                
                # Call llama.cpp server
                response = requests.post(
                    f"{self.llama_endpoint}/completion",
                    json={
                        "prompt": prompt,
                        "max_tokens": 500,
                        "temperature": 0.7,
                        "stop": ["Question:", "Context:"]
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("content", "").strip()
                    # Add action suggestions if this is an action-oriented question
                    return self._enhance_with_actions(answer, question)
                else:
                    self.logger.warning(f"LLM server returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Failed to connect to LLM server: {e}")
                # Switch to offline mode temporarily
                self.llama_available = False
            except Exception as e:
                self.logger.error(f"Error generating response: {e}")
        
        # Fallback to offline response generation
        return self._offline_response(context, question)
    
    def _offline_response(self, context: str, question: str) -> str:
        """Generate intelligent offline response based on patterns and context."""
        question_lower = question.lower()
        context_lower = context.lower()
        
        # Detect action keywords and intents
        action_keywords = {
            'restart': ['restart', 'reboot', 'reload'],
            'scale': ['scale', 'increase', 'decrease', 'replicas'],
            'delete': ['delete', 'remove', 'clean'],
            'check': ['check', 'status', 'health', 'describe'],
            'troubleshoot': ['troubleshoot', 'debug', 'investigate', 'problem', 'issue'],
            'logs': ['logs', 'log', 'events'],
            'create': ['create', 'deploy', 'add'],
            'update': ['update', 'modify', 'change', 'edit']
        }
        
        detected_action = None
        for action, keywords in action_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                detected_action = action
                break
        
        # Extract resource types from question
        k8s_resources = ['pod', 'node', 'service', 'deployment', 'configmap', 'secret', 
                        'pv', 'pvc', 'namespace', 'ingress', 'job', 'cronjob']
        mentioned_resources = [res for res in k8s_resources if res in question_lower]
        
        # Generate contextual response
        response_parts = []
        
        # Add context summary
        if context.strip():
            context_lines = [line.strip() for line in context.split('\n') if line.strip()]
            relevant_context = [line for line in context_lines if not line.startswith('[Document')]
            if relevant_context:
                response_parts.append("📖 **Based on available knowledge:**")
                response_parts.append(' '.join(relevant_context[:3])[:300] + "...")
                response_parts.append("")
        
        # Add action-specific guidance
        if detected_action and mentioned_resources:
            response_parts.append(f"🔧 **For {detected_action} operations on {', '.join(mentioned_resources)}:**")
            response_parts.extend(self._get_action_commands(detected_action, mentioned_resources))
            response_parts.append("")
        
        # Add general troubleshooting if it's a problem/issue question
        if any(word in question_lower for word in ['problem', 'issue', 'error', 'fail', 'broken']):
            response_parts.append("🔍 **General troubleshooting steps:**")
            response_parts.extend([
                "1. Check resource status: `kubectl get pods,nodes,services`",
                "2. Review recent events: `kubectl get events --sort-by=.metadata.creationTimestamp`",
                "3. Examine logs: `kubectl logs <resource-name>`",
                "4. Describe problematic resources: `kubectl describe <resource-type> <name>`"
            ])
            response_parts.append("")
        
        # Add note about offline mode
        response_parts.extend([
            "⚠️ **Note:** Operating in offline mode - LLM service unavailable.",
            "For complex issues, consider checking official Kubernetes documentation."
        ])
        
        return '\n'.join(response_parts) if response_parts else self._fallback_response(context, question)
    
    def _get_action_commands(self, action: str, resources: List[str]) -> List[str]:
        """Get specific kubectl commands for actions and resources."""
        commands = []
        
        for resource in resources:
            if action == 'restart' and resource == 'pod':
                commands.extend([
                    f"• Restart pods: `kubectl delete pod <pod-name>`",
                    f"• Restart deployment: `kubectl rollout restart deployment <deployment-name>`"
                ])
            elif action == 'scale' and resource in ['deployment', 'pod']:
                commands.append(f"• Scale deployment: `kubectl scale deployment <name> --replicas=<number>`")
            elif action == 'check':
                commands.extend([
                    f"• Check {resource} status: `kubectl get {resource}`",
                    f"• Describe {resource}: `kubectl describe {resource} <name>`"
                ])
            elif action == 'logs' and resource == 'pod':
                commands.extend([
                    f"• View logs: `kubectl logs <pod-name>`",
                    f"• Follow logs: `kubectl logs -f <pod-name>`"
                ])
            elif action == 'delete':
                commands.append(f"• Delete {resource}: `kubectl delete {resource} <name>`")
            elif action == 'create':
                commands.append(f"• Create {resource}: `kubectl create {resource} <name> [options]`")
        
        return commands if commands else [f"• Use: `kubectl {action} {resources[0]} <name>`"]
    
    def _enhance_with_actions(self, llm_response: str, question: str) -> str:
        """Enhance LLM response with actionable commands if appropriate."""
        question_lower = question.lower()
        
        # If the question seems to ask for action, append relevant commands
        if any(word in question_lower for word in ['how to', 'how do i', 'can i', 'should i']):
            action_suffix = "\n\n🔧 **Quick Actions Available:**\n"
            action_suffix += "Use the Manual Remediation tab in the dashboard for guided actions."
            return llm_response + action_suffix
        
        return llm_response
    
    def _fallback_response(self, context: str, question: str) -> str:
        """Provide fallback response when LLM is not available."""
        # Extract key information from context
        context_lines = context.split('\n')
        relevant_lines = [line for line in context_lines if line.strip() and not line.startswith('[Document')]
        
        if relevant_lines:
            return f"""
            Based on the available knowledge base, here's what I found relevant to your question:
            
            {' '.join(relevant_lines[:10])}...
            
            For more detailed guidance, please:
            1. Check the official Kubernetes documentation
            2. Review cluster logs and events
            3. Use kubectl describe commands for detailed resource information
            
            Note: LLM service is currently unavailable, so this is a basic knowledge base response.
            """
        else:
            return """
            I don't have specific information about this issue in my knowledge base.
            
            General troubleshooting steps:
            1. Check pod/node status: kubectl get pods,nodes
            2. Review events: kubectl get events --sort-by=.metadata.creationTimestamp
            3. Check logs: kubectl logs <resource-name>
            4. Describe resources: kubectl describe <resource-type> <name>
            
            Note: LLM service is currently unavailable.
            """
    
    def add_cluster_context(self, cluster_info: Dict[str, Any]):
        """Add current cluster context to knowledge base."""
        if not cluster_info:
            return
        
        # Convert cluster info to searchable text
        context_text = f"""
        Current Cluster Information:
        
        Timestamp: {datetime.now().isoformat()}
        Node Count: {cluster_info.get('node_count', 'Unknown')}
        Pod Count: {cluster_info.get('pod_count', 'Unknown')}
        CPU Usage: {cluster_info.get('cpu_usage', 'Unknown')}%
        Memory Usage: {cluster_info.get('memory_usage', 'Unknown')}%
        
        Recent Issues:
        {json.dumps(cluster_info.get('recent_issues', []), indent=2)}
        """
        
        # Add as a temporary document (could be cleaned up periodically)
        doc_id = f"cluster_context_{int(datetime.now().timestamp())}"
        self.add_document(
            context_text, 
            doc_id, 
            {"category": "cluster_context", "temporary": True}
        )
    
    def execute_action_from_prompt(self, prompt: str, remediation_engine=None) -> Dict[str, Any]:
        """
        Parse user prompt and execute appropriate actions.
        
        Args:
            prompt: User input prompt
            remediation_engine: RemediationEngine instance for executing actions
            
        Returns:
            Dict with execution results
        """
        prompt_lower = prompt.lower()
        result = {
            "action_detected": False,
            "action_type": None,
            "executed": False,
            "result": None,
            "message": ""
        }
        
        # Define action patterns
        action_patterns = {
            'restart_pods': [
                r'restart.*failed.*pods?',
                r'restart.*pod.*(\w+)',
                r'fix.*crashloop.*pod'
            ],
            'scale_deployment': [
                r'scale.*deployment.*(\w+).*to.*(\d+)',
                r'increase.*replicas?.*(\w+)',
                r'scale.*up.*(\w+)'
            ],
            'check_status': [
                r'check.*status.*(\w+)',
                r'show.*me.*(\w+).*status',
                r'what.*status.*(\w+)'
            ],
            'clean_resources': [
                r'clean.*completed.*jobs?',
                r'remove.*failed.*pods?',
                r'delete.*orphaned.*resources?'
            ],
            'node_operations': [
                r'drain.*node.*(\w+)',
                r'cordon.*node.*(\w+)',
                r'uncordon.*node.*(\w+)'
            ]
        }
        
        # Check for action patterns
        for action_type, patterns in action_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, prompt_lower)
                if match:
                    result["action_detected"] = True
                    result["action_type"] = action_type
                    
                    if remediation_engine:
                        try:
                            if action_type == 'restart_pods':
                                if 'failed' in prompt_lower:
                                    exec_result = remediation_engine.restart_failed_pods()
                                    result["executed"] = True
                                    result["result"] = exec_result
                                    result["message"] = f"Restarted {exec_result.get('count', 0)} failed pods"
                                
                            elif action_type == 'scale_deployment':
                                # Extract deployment name and replica count from match
                                if len(match.groups()) >= 2:
                                    deployment_name = match.group(1)
                                    replica_count = int(match.group(2))
                                    exec_result = remediation_engine.scale_deployment(deployment_name, replica_count)
                                    result["executed"] = exec_result.get('success', False)
                                    result["result"] = exec_result
                                    result["message"] = exec_result.get('message', 'Scaling operation completed')
                                
                            elif action_type == 'clean_resources':
                                if 'jobs' in prompt_lower:
                                    exec_result = remediation_engine.clean_completed_jobs()
                                elif 'pods' in prompt_lower:
                                    exec_result = remediation_engine.restart_failed_pods()
                                else:
                                    exec_result = remediation_engine.clean_orphaned_storage()
                                result["executed"] = True
                                result["result"] = exec_result
                                result["message"] = f"Cleaned {exec_result.get('count', 0)} resources"
                            
                            elif action_type == 'check_status':
                                result["message"] = "Status check requested - please use the dashboard tabs for detailed status information"
                                
                        except Exception as e:
                            result["message"] = f"Error executing action: {str(e)}"
                            self.logger.error(f"Action execution error: {e}")
                    else:
                        result["message"] = "Action detected but remediation engine not available"
                    
                    break
        
        if not result["action_detected"]:
            result["message"] = "No specific action detected in prompt. Try asking to 'restart failed pods', 'scale deployment X to N replicas', or 'clean completed jobs'."
        
        return result
    
    def query_with_actions(self, question: str, remediation_engine=None, max_results: int = 5) -> Dict[str, Any]:
        """
        Enhanced query method that can execute actions based on the prompt.
        
        Args:
            question: User question/prompt
            remediation_engine: RemediationEngine for executing actions
            max_results: Maximum search results
            
        Returns:
            Dict containing both query response and action results
        """
        # First, check if this is an action request
        action_result = self.execute_action_from_prompt(question, remediation_engine)
        
        # Get the regular query response
        query_response = self.query(question, max_results)
        
        # Combine the responses
        combined_response = {
            "query_response": query_response,
            "action_result": action_result,
            "full_response": query_response
        }
        
        # If an action was executed, prepend the action result to the response
        if action_result["executed"]:
            action_msg = f"✅ **Action Executed**: {action_result['message']}\n\n"
            combined_response["full_response"] = action_msg + query_response
        elif action_result["action_detected"]:
            action_msg = f"🔍 **Action Detected**: {action_result['message']}\n\n"
            combined_response["full_response"] = action_msg + query_response
        
        return combined_response
    
    def clear_temporary_documents(self, hours_old: int = 24):
        """Clear temporary context documents older than specified hours."""
        if not self.collection:
            return
        
        try:
            # This would require querying by metadata and filtering by timestamp
            # ChromaDB doesn't have built-in TTL, so this would need custom implementation
            self.logger.info("Temporary document cleanup would be implemented here")
        except Exception as e:
            self.logger.error(f"Error clearing temporary documents: {e}")
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        if not self.collection:
            return {"status": "unavailable"}
        
        try:
            count = self.collection.count()
            
            # Get sample of metadata to analyze categories
            sample = self.collection.get(limit=min(100, count), include=["metadatas"])
            categories = {}
            
            for metadata in sample.get("metadatas", []):
                category = metadata.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1
            
            return {
                "status": "ready",
                "total_documents": count,
                "categories": categories,
                "embedding_model": self.embedding_model.get_sentence_embedding_dimension() if self.embedding_model else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting knowledge stats: {e}")
            return {"status": "error", "message": str(e)}
    
    def expert_query(self, question: str, auto_remediate: bool = False) -> Dict[str, Any]:
        """Enhanced expert-level query with intelligent issue detection, historical learning, and remediation."""
        result = {
            "query": question,
            "expert_analysis": {},
            "standard_response": "",
            "expert_response": "",
            "recommendations": [],
            "remediation_plan": [],
            "system_health": {},
            "historical_insights": {},
            "predictive_analysis": {},
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Get standard RAG response
            result["standard_response"] = self.query(question)
            
            # If expert agent is available, perform expert analysis
            if self.expert_agent:
                # Analyze if this is a troubleshooting query
                is_troubleshooting = self._is_troubleshooting_query(question)
                
                if is_troubleshooting:
                    # Get historical analysis first for better context
                    if hasattr(self.expert_agent, 'history_manager') and self.expert_agent.history_manager:
                        try:
                            historical_analysis = self.expert_agent.get_historical_issue_analysis(question)
                            result["historical_insights"] = historical_analysis
                        except Exception as e:
                            self.logger.warning(f"Historical analysis failed: {e}")
                    
                    # Get comprehensive system analysis (includes continuous learning)
                    system_analysis = self.expert_agent.analyze_system_comprehensive()
                    result["system_health"] = system_analysis
                    
                    # Extract predictive analysis from system analysis
                    if "predictive_analysis" in system_analysis:
                        result["predictive_analysis"] = system_analysis["predictive_analysis"]
                    
                    # Attempt expert remediation
                    expert_remediation = self.expert_agent.expert_remediate(question, auto_execute=auto_remediate)
                    result["expert_analysis"] = expert_remediation
                    
                    # Generate expert response with historical context
                    result["expert_response"] = self._generate_expert_response_with_history(
                        question, system_analysis, expert_remediation, result["historical_insights"]
                    )
                    
                    result["confidence"] = expert_remediation["issue_analysis"].get("confidence", 0.0)
                    result["recommendations"] = expert_remediation.get("remediation_plan", [])
                else:
                    # For non-troubleshooting queries, provide enhanced knowledge response
                    result["expert_response"] = self._enhance_knowledge_response(question, result["standard_response"])
                    result["confidence"] = 0.8  # High confidence for knowledge queries
            else:
                # Fallback to enhanced standard response
                result["expert_response"] = self._enhance_standard_response(question, result["standard_response"])
                result["confidence"] = 0.6
            
        except Exception as e:
            self.logger.error(f"Error in expert query: {e}")
            result["expert_response"] = f"Expert analysis failed: {e}\n\nFalling back to standard response:\n{result['standard_response']}"
        
        return result
    
    def _is_troubleshooting_query(self, question: str) -> bool:
        """Determine if a query is asking for troubleshooting help."""
        troubleshooting_keywords = [
            "error", "fail", "issue", "problem", "broken", "not work", "crash", "stuck",
            "timeout", "slow", "high cpu", "memory", "disk", "network", "connection",
            "pod pending", "crashloop", "image pull", "mount", "volume", "service down",
            "node not ready", "gluster", "split brain", "brick", "heal", "quota"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in troubleshooting_keywords)
    
    def _generate_expert_response(self, question: str, system_analysis: Dict, expert_remediation: Dict) -> str:
        """Generate comprehensive expert response."""
        response_parts = []
        
        # Header
        response_parts.append("🔧 **EXPERT SYSTEM ANALYSIS**")
        response_parts.append("=" * 50)
        
        # System health overview
        overall_health = system_analysis.get("overall_health", "unknown")
        health_emoji = {
            "healthy": "🟢", "warning": "🟡", "degraded": "🟠", 
            "critical": "🔴", "unknown": "⚪"
        }.get(overall_health, "⚪")
        
        response_parts.append(f"\n**🏥 System Health Status:** {health_emoji} {overall_health.upper()}")
        
        # Issue analysis
        issue_analysis = expert_remediation.get("issue_analysis", {})
        if issue_analysis.get("pattern_matched"):
            confidence = issue_analysis.get("confidence", 0.0)
            area = issue_analysis.get("area", "unknown")
            issue_type = issue_analysis.get("issue_type", "unknown")
            severity = issue_analysis.get("severity", "unknown")
            
            response_parts.append(f"\n**🎯 Issue Pattern Detected:**")
            response_parts.append(f"• **Area:** {area.replace('_', ' ').title()}")
            response_parts.append(f"• **Type:** {issue_type.replace('_', ' ').title()}")
            response_parts.append(f"• **Severity:** {severity.upper()}")
            response_parts.append(f"• **Confidence:** {confidence:.1%}")
        
        # Critical issues
        critical_issues = system_analysis.get("critical_issues", [])
        if critical_issues:
            response_parts.append(f"\n**🚨 CRITICAL ISSUES ({len(critical_issues)}):**")
            for issue in critical_issues[:5]:
                response_parts.append(f"• {issue}")
        
        # Warnings
        warnings = system_analysis.get("warnings", [])
        if warnings:
            response_parts.append(f"\n**⚠️ WARNINGS ({len(warnings)}):**")
            for warning in warnings[:3]:
                response_parts.append(f"• {warning}")
        
        # Remediation plan
        remediation_plan = expert_remediation.get("remediation_plan", [])
        if remediation_plan:
            response_parts.append(f"\n**📋 EXPERT REMEDIATION PLAN:**")
            for i, step in enumerate(remediation_plan, 1):
                phase = step.get("phase", "").title()
                description = step.get("description", "")
                safety_level = step.get("safety_level", "unknown")
                safety_emoji = {"safe": "✅", "medium": "⚠️", "high": "🔴"}.get(safety_level, "❓")
                
                response_parts.append(f"\n**Step {i} - {phase}** {safety_emoji}")
                response_parts.append(f"• {description}")
                
                if step.get("command"):
                    response_parts.append(f"• Command: `{step['command']}`")
        
        # Executed actions (if any)
        executed_actions = expert_remediation.get("executed_actions", [])
        if executed_actions:
            response_parts.append(f"\n**⚡ EXECUTED ACTIONS:**")
            for action in executed_actions:
                status = "✅ SUCCESS" if action.get("success") else "❌ FAILED"
                response_parts.append(f"• {status}: {action.get('description', 'Unknown action')}")
                if action.get("error"):
                    response_parts.append(f"  Error: {action['error']}")
        
        # Safety checks
        safety_checks = expert_remediation.get("safety_checks", {})
        if safety_checks:
            safe_to_proceed = safety_checks.get("safe_to_proceed", True)
            safety_status = "✅ PASSED" if safe_to_proceed else "❌ FAILED"
            response_parts.append(f"\n**🛡️ Safety Checks:** {safety_status}")
            
            if not safe_to_proceed:
                response_parts.append(f"• Reason: {safety_checks.get('reason', 'Unknown')}")
            
            warnings = safety_checks.get("warnings", [])
            if warnings:
                response_parts.append("• Warnings:")
                for warning in warnings:
                    response_parts.append(f"  - {warning}")
        
        # Top recommendations
        recommendations = system_analysis.get("recommendations", [])
        if recommendations:
            response_parts.append(f"\n**💡 EXPERT RECOMMENDATIONS:**")
            for rec in recommendations[:5]:
                response_parts.append(f"• {rec}")
        
        # Component health summary
        detailed_analysis = system_analysis.get("detailed_analysis", {})
        if detailed_analysis:
            response_parts.append(f"\n**📊 COMPONENT STATUS:**")
            for component, data in detailed_analysis.items():
                status = data.get("status", "unknown")
                emoji = {
                    "healthy": "✅", "warning": "⚠️", "degraded": "🟠", 
                    "critical": "🔴", "unavailable": "⚫", "error": "❌"
                }.get(status, "❓")
                component_name = component.replace("_", " ").title()
                response_parts.append(f"• {emoji} **{component_name}:** {status.upper()}")
        
        # Action buttons
        response_parts.append(f"\n**🎮 QUICK ACTIONS:**")
        response_parts.append("• Use the Manual Remediation tab for guided remediation")
        response_parts.append("• Click 'Health Check' in the sidebar for real-time analysis")
        response_parts.append("• Enable auto-remediation for automatic issue resolution")
        
        # Footer
        response_parts.append(f"\n---")
        response_parts.append(f"**Expert Analysis completed at {datetime.now().strftime('%H:%M:%S')}**")
        response_parts.append(f"**System:** Operating in offline mode with comprehensive local analysis")
        
        return "\n".join(response_parts)
    
    def _generate_expert_response_with_history(self, question: str, system_analysis: Dict, expert_remediation: Dict, historical_insights: Dict) -> str:
        """Generate expert response with historical context and predictive analysis."""
        response_parts = []
        
        # Header with confidence
        confidence = expert_remediation["issue_analysis"].get("confidence", 0.0)
        confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
        
        response_parts.append("🔧 **EXPERT SYSTEM ANALYSIS WITH HISTORICAL INTELLIGENCE**")
        response_parts.append("=" * 70)
        
        # Overall health status
        health_status = system_analysis.get("overall_health", "unknown")
        health_emoji = {
            "healthy": "🟢", "warning": "🟡", "degraded": "🟠", 
            "critical": "🔴", "unknown": "❓"
        }.get(health_status, "❓")
        
        response_parts.append(f"\n🏥 **System Health Status:** {health_emoji} {health_status.upper()}")
        
        # Historical Analysis Section
        if historical_insights and "prediction" in historical_insights:
            prediction = historical_insights["prediction"]
            if prediction.get("confidence", 0) > 0.3:
                response_parts.append(f"\n🧠 **HISTORICAL INTELLIGENCE:**")
                response_parts.append(f"• Pattern Match: {prediction.get('issue_type', 'unknown').replace('_', ' ').title()}")
                response_parts.append(f"• Prediction Confidence: {confidence_emoji} {prediction.get('confidence', 0):.1%}")
                response_parts.append(f"• Historical Occurrences: {prediction.get('historical_count', 0)}")
                
                if prediction.get("predicted_cause") != "unknown":
                    response_parts.append(f"• Predicted Root Cause: **{prediction['predicted_cause'].replace('_', ' ').title()}**")
                
                # Historical recommendations
                hist_recommendations = prediction.get("recommendations", [])
                if hist_recommendations:
                    response_parts.append(f"• Top Historical Solutions:")
                    for rec in hist_recommendations[:3]:
                        success_rate = rec.get("success_rate", 0)
                        success_emoji = "✅" if success_rate > 0.8 else "⚠️" if success_rate > 0.5 else "❌"
                        response_parts.append(f"  {success_emoji} {rec.get('action', 'Unknown')} (success: {success_rate:.1%})")
        
        # Learning scan results
        if "learning_scan" in system_analysis:
            scan = system_analysis["learning_scan"]
            response_parts.append(f"\n📊 **CONTINUOUS LEARNING UPDATE:**")
            response_parts.append(f"• New Issues Detected: {scan['issues_detected']}")
            response_parts.append(f"• Total Historical Issues: {scan['total_historical']}")
            response_parts.append(f"• Learning Database: ✅ Active and updated")
        
        # Issue pattern analysis
        issue_analysis = expert_remediation.get("issue_analysis", {})
        if issue_analysis.get("pattern_matched"):
            area = issue_analysis.get("area", "unknown")
            severity = issue_analysis.get("severity", "unknown")
            
            response_parts.append(f"\n🎯 **Issue Pattern Detected:**")
            response_parts.append(f"• Area: **{area.replace('_', ' ').title()}**")
            response_parts.append(f"• Type: **{issue_analysis.get('issue_type', 'Unknown').replace('_', ' ').title()}**")
            response_parts.append(f"• Severity: **{severity.upper()}**")
            response_parts.append(f"• Confidence: {confidence_emoji} **{confidence:.1%}**")
        
        # Critical issues
        critical_issues = system_analysis.get("critical_issues", [])
        if critical_issues:
            response_parts.append(f"\n🚨 **CRITICAL ISSUES ({len(critical_issues)}):**")
            for issue in critical_issues[:5]:
                response_parts.append(f"• {issue}")
        
        # Warnings
        warnings = system_analysis.get("warnings", [])
        if warnings:
            response_parts.append(f"\n⚠️ **WARNINGS ({len(warnings)}):**")
            for warning in warnings[:3]:
                response_parts.append(f"• {warning}")
        
        # Predictive analysis from system analysis
        if "predictive_analysis" in system_analysis and system_analysis["predictive_analysis"]:
            response_parts.append(f"\n🔮 **PREDICTIVE ANALYSIS:**")
            for area, predictions in system_analysis["predictive_analysis"].items():
                response_parts.append(f"• **{area.title()} Predictions:**")
                for pred_data in predictions[:2]:  # Top 2 predictions
                    pred = pred_data["prediction"]
                    confidence_pred = pred.get("confidence", 0)
                    if confidence_pred > 0.5:
                        response_parts.append(f"  - {pred.get('predicted_cause', 'unknown').replace('_', ' ').title()} ({confidence_pred:.1%})")
        
        # Remediation plan
        remediation_plan = expert_remediation.get("remediation_plan", [])
        if remediation_plan:
            response_parts.append(f"\n📋 **EXPERT REMEDIATION PLAN:**")
            for i, step in enumerate(remediation_plan, 1):
                phase = step.get("phase", "").title()
                description = step.get("description", "")
                safety_level = step.get("safety_level", "unknown")
                safety_emoji = {"safe": "✅", "medium": "⚠️", "high": "🔴"}.get(safety_level, "❓")
                
                response_parts.append(f"\n**Step {i} - {phase}** {safety_emoji}")
                response_parts.append(f"• {description}")
                
                if step.get("command"):
                    response_parts.append(f"• Command: `{step['command']}`")
        
        # Historical trends
        if historical_insights and "trends" in historical_insights:
            trends = historical_insights["trends"]
            if trends.get("recent_issues_24h", 0) > 0:
                response_parts.append(f"\n📈 **TREND ANALYSIS:**")
                response_parts.append(f"• Recent Issues (24h): {trends['recent_issues_24h']}")
                response_parts.append(f"• Trend Direction: {trends.get('trend_direction', 'stable').title()}")
                if trends.get('most_frequent_type'):
                    most_frequent = trends['most_frequent_type']
                    response_parts.append(f"• Most Frequent Issue: {most_frequent[0].replace('_', ' ').title()}")
        
        # Component health summary
        detailed_analysis = system_analysis.get("detailed_analysis", {})
        if detailed_analysis:
            response_parts.append(f"\n📊 **COMPONENT STATUS:**")
            for component, data in detailed_analysis.items():
                status = data.get("status", "unknown")
                emoji = {
                    "healthy": "✅", "warning": "⚠️", "degraded": "🟠", 
                    "critical": "🔴", "unavailable": "⚫", "error": "❌"
                }.get(status, "❓")
                component_name = component.replace("_", " ").title()
                response_parts.append(f"• {emoji} **{component_name}:** {status.upper()}")
        
        # Action recommendations with historical context
        recommendations = system_analysis.get("recommendations", [])
        if recommendations:
            response_parts.append(f"\n💡 **EXPERT RECOMMENDATIONS (Historically Informed):**")
            for rec in recommendations[:5]:
                response_parts.append(f"• {rec}")
        
        # Footer with enhanced information
        response_parts.append(f"\n---")
        response_parts.append(f"**Expert Analysis with Historical Intelligence completed at {datetime.now().strftime('%H:%M:%S')}**")
        response_parts.append(f"**System:** Advanced AI + Continuous Learning + Historical Pattern Recognition")
        
        if historical_insights and "learning_report" in historical_insights:
            response_parts.append(f"**Learning Status:** Actively learning from {historical_insights.get('total_issues', 0)} historical patterns")
        
        return "\n".join(response_parts)
    
    def _enhance_knowledge_response(self, question: str, standard_response: str) -> str:
        """Enhance knowledge-based responses with expert insights."""
        enhanced_parts = []
        
        enhanced_parts.append("📚 **EXPERT KNOWLEDGE RESPONSE**")
        enhanced_parts.append("=" * 40)
        
        # Add expert context
        enhanced_parts.append("\n**🎓 Expert Analysis:**")
        
        question_lower = question.lower()
        
        # Kubernetes-specific enhancements
        if any(k8s_term in question_lower for k8s_term in ["kubernetes", "k8s", "pod", "deployment", "service", "node"]):
            enhanced_parts.append("• Drawing from Kubernetes best practices and real-world troubleshooting experience")
            enhanced_parts.append("• Considering cluster topology, resource constraints, and operational patterns")
            
        # Ubuntu/Linux enhancements
        elif any(os_term in question_lower for os_term in ["ubuntu", "linux", "systemd", "service", "process"]):
            enhanced_parts.append("• Applying enterprise Linux administration expertise")
            enhanced_parts.append("• Considering system dependencies, security implications, and performance impact")
            
        # GlusterFS enhancements
        elif any(gluster_term in question_lower for gluster_term in ["gluster", "volume", "brick", "distributed"]):
            enhanced_parts.append("• Leveraging distributed storage system expertise")
            enhanced_parts.append("• Considering data consistency, network topology, and fault tolerance")
        
        # Add the standard response
        enhanced_parts.append(f"\n**📖 Detailed Response:**")
        enhanced_parts.append(standard_response)
        
        # Add expert tips
        enhanced_parts.append(f"\n**💡 Expert Tips:**")
        enhanced_parts.append("• Always test changes in a non-production environment first")
        enhanced_parts.append("• Monitor system metrics before and after implementing changes")
        enhanced_parts.append("• Keep detailed logs of all administrative actions")
        enhanced_parts.append("• Have a rollback plan ready for critical operations")
        
        # Add related considerations
        enhanced_parts.append(f"\n**🔗 Related Considerations:**")
        enhanced_parts.append("• Check system resource availability before making changes")
        enhanced_parts.append("• Verify backup procedures are in place")
        enhanced_parts.append("• Consider the impact on dependent services")
        enhanced_parts.append("• Review security implications of proposed changes")
        
        return "\n".join(enhanced_parts)
    
    def _enhance_standard_response(self, question: str, standard_response: str) -> str:
        """Enhance standard response when expert agent is not available."""
        enhanced_parts = []
        
        enhanced_parts.append("🤖 **AI ASSISTANT RESPONSE**")
        enhanced_parts.append("=" * 30)
        
        enhanced_parts.append(f"\n{standard_response}")
        
        enhanced_parts.append(f"\n**⚠️ Note:** Expert analysis temporarily unavailable. For complex troubleshooting:")
        enhanced_parts.append("• Use the Manual Remediation tab for guided actions")
        enhanced_parts.append("• Check system logs manually: `journalctl -xe`")
        enhanced_parts.append("• Monitor resource usage: `top`, `df -h`, `free -h`")
        enhanced_parts.append("• Verify service status: `systemctl status <service>`")
        
        return "\n".join(enhanced_parts)
    
    def get_system_health_report(self) -> str:
        """Get comprehensive system health report."""
        if not self.expert_agent:
            return "🔧 Expert analysis not available. Please use manual monitoring tools."
        
        try:
            return self.expert_agent.get_system_health_summary()
        except Exception as e:
            return f"❌ Failed to generate health report: {e}"
    
    def auto_remediate_system_issues(self) -> Dict[str, Any]:
        """Automatically detect and remediate system issues."""
        if not self.expert_agent:
            return {
                "success": False,
                "message": "Expert remediation agent not available",
                "issues_found": 0,
                "issues_resolved": 0
            }
        
        try:
            # Perform comprehensive system analysis
            analysis = self.expert_agent.analyze_system_comprehensive()
            
            issues_found = len(analysis.get("critical_issues", []))
            issues_resolved = 0
            remediation_results = []
            
            # Attempt to remediate critical issues
            for issue in analysis.get("critical_issues", []):
                remediation = self.expert_agent.expert_remediate(issue, auto_execute=True)
                remediation_results.append(remediation)
                
                if remediation.get("success"):
                    issues_resolved += 1
            
            return {
                "success": issues_resolved > 0,
                "message": f"Found {issues_found} critical issues, resolved {issues_resolved}",
                "issues_found": issues_found,
                "issues_resolved": issues_resolved,
                "overall_health": analysis.get("overall_health", "unknown"),
                "remediation_details": remediation_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Auto-remediation failed: {e}",
                "issues_found": 0,
                "issues_resolved": 0
            }
    
    def detect_intelligent_actions(self, query: str) -> Dict[str, Any]:
        """
        Enhanced RAG Agent Feature: Intelligent Action Detection
        Detects actionable intents from conversational input and suggests specific operations.
        """
        query_lower = query.lower()
        detected_actions = []
        
        # Define action patterns with confidence scoring
        action_patterns = {
            "diagnostic": {
                "keywords": ["diagnose", "analyze", "check", "status", "health", "examine", "inspect"],
                "commands": ["kubectl get pods", "systemctl status", "df -h", "free -h"],
                "confidence_multiplier": 1.2
            },
            "remediation": {
                "keywords": ["fix", "repair", "resolve", "solve", "remediate", "heal", "recover"],
                "commands": ["kubectl delete pod", "systemctl restart", "gluster heal"],
                "confidence_multiplier": 1.5
            },
            "monitoring": {
                "keywords": ["monitor", "watch", "track", "observe", "follow", "logs"],
                "commands": ["kubectl logs", "journalctl -f", "top", "htop"],
                "confidence_multiplier": 1.0
            },
            "optimization": {
                "keywords": ["optimize", "improve", "tune", "performance", "speed up"],
                "commands": ["kubectl scale", "sysctl", "nice"],
                "confidence_multiplier": 1.3
            },
            "security": {
                "keywords": ["secure", "audit", "vulnerability", "scan", "permission"],
                "commands": ["kubectl auth", "chmod", "chown", "fail2ban"],
                "confidence_multiplier": 1.4
            }
        }
        
        # Kubernetes-specific actions
        k8s_actions = {
            "get_pods": {
                "triggers": ["show pods", "list pods", "get pods", "pod status"],
                "command": "kubectl get pods -o wide",
                "description": "List all pods with detailed information",
                "safety_level": "safe"
            },
            "get_nodes": {
                "triggers": ["show nodes", "list nodes", "node status", "cluster nodes"],
                "command": "kubectl get nodes -o wide",
                "description": "Display cluster node information",
                "safety_level": "safe"
            },
            "describe_pod": {
                "triggers": ["describe pod", "pod details", "pod events"],
                "command": "kubectl describe pod",
                "description": "Get detailed pod information and events",
                "safety_level": "safe"
            },
            "pod_logs": {
                "triggers": ["pod logs", "show logs", "container logs"],
                "command": "kubectl logs",
                "description": "Retrieve pod container logs",
                "safety_level": "safe"
            },
            "restart_deployment": {
                "triggers": ["restart deployment", "rollout restart", "redeploy"],
                "command": "kubectl rollout restart deployment",
                "description": "Restart deployment (rolling update)",
                "safety_level": "medium"
            }
        }
        
        # GlusterFS-specific actions
        gluster_actions = {
            "volume_status": {
                "triggers": ["gluster volume", "volume status", "gluster status"],
                "command": "gluster volume status",
                "description": "Check GlusterFS volume status",
                "safety_level": "safe"
            },
            "volume_info": {
                "triggers": ["volume info", "gluster info", "volume details"],
                "command": "gluster volume info",
                "description": "Display GlusterFS volume information",
                "safety_level": "safe"
            },
            "heal_info": {
                "triggers": ["heal status", "split brain", "heal info"],
                "command": "gluster volume heal",
                "description": "Check and initiate healing process",
                "safety_level": "medium"
            }
        }
        
        # System administration actions
        system_actions = {
            "service_status": {
                "triggers": ["service status", "systemd status", "check service"],
                "command": "systemctl status",
                "description": "Check system service status",
                "safety_level": "safe"
            },
            "disk_usage": {
                "triggers": ["disk space", "storage usage", "disk full"],
                "command": "df -h",
                "description": "Display disk space usage",
                "safety_level": "safe"
            },
            "memory_usage": {
                "triggers": ["memory usage", "ram usage", "free memory"],
                "command": "free -h",
                "description": "Display memory usage statistics",
                "safety_level": "safe"
            },
            "process_list": {
                "triggers": ["running processes", "process list", "top processes"],
                "command": "ps aux",
                "description": "List running processes",
                "safety_level": "safe"
            }
        }
        
        # Combine all action sets
        all_actions = {**k8s_actions, **gluster_actions, **system_actions}
        
        # Detect specific actions
        for action_name, action_data in all_actions.items():
            for trigger in action_data["triggers"]:
                if trigger in query_lower:
                    confidence = 0.8 + (0.2 * len([word for word in trigger.split() if word in query_lower]))
                    detected_actions.append({
                        "action": action_name,
                        "command": action_data["command"],
                        "description": action_data["description"],
                        "safety_level": action_data["safety_level"],
                        "confidence": min(confidence, 1.0),
                        "category": "kubernetes" if "kubectl" in action_data["command"] 
                                   else "glusterfs" if "gluster" in action_data["command"] 
                                   else "system"
                    })
        
        # Detect general action categories
        for category, pattern_data in action_patterns.items():
            keyword_matches = sum(1 for keyword in pattern_data["keywords"] if keyword in query_lower)
            if keyword_matches > 0:
                confidence = (keyword_matches / len(pattern_data["keywords"])) * pattern_data["confidence_multiplier"]
                detected_actions.append({
                    "action": f"general_{category}",
                    "category": category,
                    "confidence": min(confidence, 1.0),
                    "suggested_commands": pattern_data["commands"][:3],
                    "description": f"General {category} operations detected"
                })
        
        # Sort by confidence and remove duplicates
        detected_actions = sorted(detected_actions, key=lambda x: x["confidence"], reverse=True)
        seen_actions = set()
        unique_actions = []
        
        for action in detected_actions:
            action_key = action.get("action", "") + action.get("command", "")
            if action_key not in seen_actions:
                seen_actions.add(action_key)
                unique_actions.append(action)
        
        return {
            "query": query,
            "actions_detected": len(unique_actions),
            "actions": unique_actions[:5],  # Top 5 most relevant actions
            "has_actionable_intent": len(unique_actions) > 0,
            "primary_category": unique_actions[0]["category"] if unique_actions else "informational",
            "confidence_score": unique_actions[0]["confidence"] if unique_actions else 0.0
        }
    
    def generate_context_aware_response(self, query: str, system_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhanced RAG Agent Feature: Context-Aware Response Generation
        Generates intelligent responses based on system state, user intent, and available context.
        """
        if system_context is None:
            system_context = self._gather_system_context()
        
        # Detect intelligent actions
        action_detection = self.detect_intelligent_actions(query)
        
        # Analyze query intent
        query_analysis = self._analyze_query_intent(query)
        
        # Get system health if expert agent is available
        system_health = {}
        if self.expert_agent:
            try:
                health_analysis = self.expert_agent.analyze_system_comprehensive()
                system_health = {
                    "overall_status": health_analysis.get("overall_health", "unknown"),
                    "critical_issues": health_analysis.get("critical_issues", []),
                    "warnings": health_analysis.get("warnings", []),
                    "component_health": health_analysis.get("detailed_analysis", {})
                }
            except Exception as e:
                system_health = {"error": f"Health analysis failed: {e}"}
        
        # Generate context-aware response
        response_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "response_type": self._determine_response_type(query, action_detection, system_health),
            "system_context": system_context,
            "action_detection": action_detection,
            "query_analysis": query_analysis,
            "system_health": system_health
        }
        
        # Generate appropriate response based on context
        if action_detection["has_actionable_intent"]:
            response_data["response"] = self._generate_actionable_response(query, action_detection, system_health)
        elif query_analysis["type"] == "troubleshooting":
            response_data["response"] = self._generate_troubleshooting_response(query, system_health)
        elif query_analysis["type"] == "informational":
            response_data["response"] = self._generate_informational_response(query, system_context)
        else:
            response_data["response"] = self._generate_general_response(query, system_context)
        
        # Add proactive suggestions
        response_data["proactive_suggestions"] = self._generate_proactive_suggestions(
            query, system_health, action_detection
        )
        
        return response_data
    
    def _gather_system_context(self) -> Dict[str, Any]:
        """Gather current system context for enhanced responses."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "kubernetes": {"available": False, "version": None},
            "glusterfs": {"available": False, "volumes": []},
            "system": {"load": None, "memory": None, "disk": None}
        }
        
        try:
            # Check Kubernetes availability
            result = subprocess.run(["kubectl", "version", "--client"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                context["kubernetes"]["available"] = True
                version_match = re.search(r'v(\d+\.\d+\.\d+)', result.stdout)
                if version_match:
                    context["kubernetes"]["version"] = version_match.group(1)
        except Exception:
            pass
        
        try:
            # Check GlusterFS availability
            result = subprocess.run(["gluster", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                context["glusterfs"]["available"] = True
        except Exception:
            pass
        
        try:
            # Get basic system info
            load_result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=2)
            if load_result.returncode == 0:
                context["system"]["load"] = load_result.stdout.strip()
        except Exception:
            pass
        
        return context
    
    def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze the intent and type of user query."""
        query_lower = query.lower()
        
        # Define intent patterns
        troubleshooting_patterns = [
            "error", "fail", "problem", "issue", "not working", "broken", "crash",
            "timeout", "slow", "high cpu", "memory leak", "disk full", "split brain"
        ]
        
        informational_patterns = [
            "what is", "how to", "explain", "show me", "list", "describe", "tell me"
        ]
        
        action_patterns = [
            "restart", "delete", "create", "update", "scale", "deploy", "run", "execute"
        ]
        
        monitoring_patterns = [
            "status", "health", "check", "monitor", "logs", "metrics", "dashboard"
        ]
        
        # Classify query type
        if any(pattern in query_lower for pattern in troubleshooting_patterns):
            query_type = "troubleshooting"
            confidence = 0.8
        elif any(pattern in query_lower for pattern in action_patterns):
            query_type = "action"
            confidence = 0.9
        elif any(pattern in query_lower for pattern in monitoring_patterns):
            query_type = "monitoring"
            confidence = 0.7
        elif any(pattern in query_lower for pattern in informational_patterns):
            query_type = "informational"
            confidence = 0.6
        else:
            query_type = "general"
            confidence = 0.4
        
        # Detect domain focus
        domain = "general"
        if any(k8s_term in query_lower for k8s_term in ["kubernetes", "k8s", "pod", "deployment", "service", "kubectl"]):
            domain = "kubernetes"
        elif any(gluster_term in query_lower for gluster_term in ["gluster", "volume", "brick", "heal"]):
            domain = "glusterfs"
        elif any(sys_term in query_lower for sys_term in ["system", "ubuntu", "service", "process", "memory", "cpu"]):
            domain = "system"
        
        return {
            "type": query_type,
            "domain": domain,
            "confidence": confidence,
            "complexity": len(query.split()),
            "contains_technical_terms": len([word for word in query_lower.split() 
                                           if word in ["kubernetes", "pod", "gluster", "volume", "systemd"]]) > 0
        }
    
    def _determine_response_type(self, query: str, action_detection: Dict, system_health: Dict) -> str:
        """Determine the most appropriate response type."""
        if action_detection["has_actionable_intent"] and action_detection["confidence_score"] > 0.7:
            return "actionable"
        elif system_health.get("critical_issues") and len(system_health["critical_issues"]) > 0:
            return "critical_alert"
        elif "troubleshoot" in query.lower() or "error" in query.lower():
            return "troubleshooting"
        elif any(info_word in query.lower() for info_word in ["what", "how", "explain", "show"]):
            return "informational"
        else:
            return "general"
    
    def _generate_actionable_response(self, query: str, action_detection: Dict, system_health: Dict) -> str:
        """Generate response for actionable queries with detected actions."""
        response_parts = []
        
        response_parts.append("🎯 **ACTIONABLE INTENT DETECTED**")
        response_parts.append("=" * 40)
        
        # Show detected actions
        actions = action_detection["actions"]
        if actions:
            primary_action = actions[0]
            response_parts.append(f"\n**🔍 Primary Action Detected:** {primary_action['description']}")
            response_parts.append(f"**🎚️ Confidence:** {primary_action['confidence']:.1%}")
            response_parts.append(f"**🔒 Safety Level:** {primary_action['safety_level'].upper()}")
            
            if primary_action.get("command"):
                response_parts.append(f"\n**💻 Suggested Command:**")
                response_parts.append(f"```bash\n{primary_action['command']}\n```")
            
            # Add safety warnings for medium/high risk actions
            if primary_action["safety_level"] in ["medium", "high"]:
                response_parts.append(f"\n⚠️ **Safety Notice:** This action has {primary_action['safety_level']} risk level.")
                response_parts.append("Consider testing in a non-production environment first.")
            
            # Show alternative actions
            if len(actions) > 1:
                response_parts.append(f"\n**🔄 Alternative Actions:**")
                for i, action in enumerate(actions[1:3], 2):
                    response_parts.append(f"{i}. {action['description']} (confidence: {action['confidence']:.1%})")
        
        # Add system context if relevant
        if system_health.get("critical_issues"):
            response_parts.append(f"\n🚨 **Critical Issues Detected:** {len(system_health['critical_issues'])}")
            response_parts.append("Consider addressing these before proceeding with the requested action.")
        
        response_parts.append(f"\n**💡 Recommendation:** Use the Manual Remediation tab for guided execution.")
        
        return "\n".join(response_parts)
    
    def _generate_troubleshooting_response(self, query: str, system_health: Dict) -> str:
        """Generate response for troubleshooting queries."""
        response_parts = []
        
        response_parts.append("🔧 **TROUBLESHOOTING ASSISTANCE**")
        response_parts.append("=" * 35)
        
        # System health overview
        if system_health:
            status = system_health.get("overall_status", "unknown")
            emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}.get(status, "❓")
            response_parts.append(f"\n**{emoji} System Status:** {status.upper()}")
            
            # Critical issues
            critical_issues = system_health.get("critical_issues", [])
            if critical_issues:
                response_parts.append(f"\n**🚨 Critical Issues ({len(critical_issues)}):**")
                for issue in critical_issues[:3]:
                    response_parts.append(f"• {issue}")
            
            # Warnings
            warnings = system_health.get("warnings", [])
            if warnings:
                response_parts.append(f"\n**⚠️ Warnings ({len(warnings)}):**")
                for warning in warnings[:2]:
                    response_parts.append(f"• {warning}")
        
        # Troubleshooting steps
        response_parts.append(f"\n**🔍 Recommended Troubleshooting Steps:**")
        response_parts.append("1. **Check System Resources:** `df -h`, `free -h`, `top`")
        response_parts.append("2. **Review Recent Logs:** `journalctl -xe --since '1 hour ago'`")
        response_parts.append("3. **Verify Service Status:** `systemctl status <service>`")
        
        if "pod" in query.lower() or "kubernetes" in query.lower():
            response_parts.append("4. **Check Pod Status:** `kubectl get pods -o wide`")
            response_parts.append("5. **Review Pod Logs:** `kubectl logs <pod-name>`")
        
        if "gluster" in query.lower():
            response_parts.append("4. **Check Volume Status:** `gluster volume status`")
            response_parts.append("5. **Check Heal Status:** `gluster volume heal <volume> info`")
        
        response_parts.append(f"\n**⚡ Quick Actions:** Use Expert Diagnosis or Health Check buttons for automated analysis.")
        
        return "\n".join(response_parts)
    
    def _generate_informational_response(self, query: str, system_context: Dict) -> str:
        """Generate response for informational queries."""
        response_parts = []
        
        response_parts.append("📚 **INFORMATION RESPONSE**")
        response_parts.append("=" * 25)
        
        # Context-aware information
        if system_context:
            k8s_available = system_context.get("kubernetes", {}).get("available", False)
            gluster_available = system_context.get("glusterfs", {}).get("available", False)
            
            response_parts.append(f"\n**🏗️ System Environment:**")
            response_parts.append(f"• Kubernetes: {'✅ Available' if k8s_available else '❌ Not Available'}")
            response_parts.append(f"• GlusterFS: {'✅ Available' if gluster_available else '❌ Not Available'}")
            
            if k8s_available:
                version = system_context["kubernetes"].get("version")
                if version:
                    response_parts.append(f"• Kubernetes Version: {version}")
        
        # Add relevant information based on query content
        query_lower = query.lower()
        if "kubernetes" in query_lower or "k8s" in query_lower:
            response_parts.append(f"\n**🔍 Kubernetes Information:**")
            response_parts.append("• Use `kubectl get pods` to list all pods")
            response_parts.append("• Use `kubectl get nodes` to check cluster nodes")
            response_parts.append("• Use `kubectl describe <resource>` for detailed info")
        
        if "gluster" in query_lower:
            response_parts.append(f"\n**📁 GlusterFS Information:**")
            response_parts.append("• Use `gluster volume info` for volume details")
            response_parts.append("• Use `gluster volume status` for operational status")
            response_parts.append("• Use `gluster peer status` for cluster peer info")
        
        response_parts.append(f"\n**💡 Tip:** Use the Chat Assistant for specific questions or the Dashboard tabs for detailed analysis.")
        
        return "\n".join(response_parts)
    
    def _generate_general_response(self, query: str, system_context: Dict) -> str:
        """Generate general response for queries that don't fit other categories."""
        response_parts = []
        
        response_parts.append("🤖 **AI ASSISTANT RESPONSE**")
        response_parts.append("=" * 25)
        
        response_parts.append(f"\nI'm here to help with Kubernetes, GlusterFS, and Ubuntu system administration.")
        response_parts.append(f"Your query: \"{query}\"")
        
        response_parts.append(f"\n**🎯 Available Capabilities:**")
        response_parts.append("• System health analysis and diagnostics")
        response_parts.append("• Kubernetes cluster management and troubleshooting")
        response_parts.append("• GlusterFS distributed storage operations")
        response_parts.append("• Ubuntu system administration assistance")
        response_parts.append("• Automated remediation with safety checks")
        
        response_parts.append(f"\n**🚀 Try These Actions:**")
        response_parts.append("• Ask: 'Check pod status' or 'Show cluster health'")
        response_parts.append("• Use: Expert Diagnosis, Health Check, or Auto-Remediate buttons")
        response_parts.append("• Browse: Dashboard tabs for comprehensive system analysis")
        
        return "\n".join(response_parts)
    
    def _generate_proactive_suggestions(self, query: str, system_health: Dict, action_detection: Dict) -> List[Dict[str, Any]]:
        """Generate proactive suggestions based on current context."""
        suggestions = []
        
        # Health-based suggestions
        if system_health.get("critical_issues"):
            suggestions.append({
                "type": "alert",
                "priority": "high",
                "title": "Critical Issues Detected",
                "description": f"{len(system_health['critical_issues'])} critical issues need attention",
                "action": "Run Expert Diagnosis for detailed analysis"
            })
        
        if system_health.get("warnings") and len(system_health["warnings"]) > 2:
            suggestions.append({
                "type": "warning",
                "priority": "medium",
                "title": "Multiple Warnings Present",
                "description": f"{len(system_health['warnings'])} warnings detected",
                "action": "Consider running Health Check"
            })
        
        # Action-based suggestions
        if action_detection["has_actionable_intent"]:
            primary_action = action_detection["actions"][0] if action_detection["actions"] else {}
            if primary_action.get("safety_level") == "medium":
                suggestions.append({
                    "type": "safety",
                    "priority": "medium",
                    "title": "Safety Check Recommended",
                    "description": "The detected action has medium risk level",
                    "action": "Review the action carefully before execution"
                })
        
        # General suggestions
        query_lower = query.lower()
        if "slow" in query_lower or "performance" in query_lower:
            suggestions.append({
                "type": "optimization",
                "priority": "low",
                "title": "Performance Optimization",
                "description": "Consider running system performance analysis",
                "action": "Use Smart Optimize for automated performance tuning"
            })
        
        if "security" in query_lower or "audit" in query_lower:
            suggestions.append({
                "type": "security",
                "priority": "medium",
                "title": "Security Review",
                "description": "Security-related query detected",
                "action": "Run Security Audit for comprehensive security analysis"
            })
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def integrate_historical_context(self, query: str, current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced RAG Agent Feature: Historical Context Integration
        Integrates historical patterns and previous solutions for enhanced troubleshooting.
        """
        # Get historical insights
        if self.issue_history:
            try:
                historical_insights = self.issue_history.get_predictive_insights(
                    query, context=current_analysis
                )
            except Exception as e:
                logging.warning(f"Failed to get historical insights: {e}")
                historical_insights = {}
        else:
            historical_insights = {}
        
        # Analyze historical patterns
        historical_analysis = self._analyze_historical_patterns(query, historical_insights)
        
        # Generate historical recommendations
        historical_recommendations = self._generate_historical_recommendations(
            query, current_analysis, historical_insights
        )
        
        # Calculate confidence scores based on historical data
        confidence_scores = self._calculate_historical_confidence(
            query, historical_insights, current_analysis
        )
        
        return {
            "query": query,
            "historical_insights": historical_insights,
            "historical_patterns": historical_analysis,
            "historical_recommendations": historical_recommendations,
            "confidence_scores": confidence_scores,
            "learning_status": {
                "total_historical_issues": len(historical_insights.get("similar_issues", [])),
                "pattern_matches": historical_analysis.get("pattern_matches", 0),
                "confidence_level": confidence_scores.get("overall_confidence", 0.0)
            }
        }
    
    def perform_predictive_analysis(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced RAG Agent Feature: Predictive Analysis
        Performs predictive analysis based on past issue patterns and system trends.
        """
        predictions = {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "predictive",
            "predictions": [],
            "risk_assessment": {},
            "proactive_recommendations": []
        }
        
        try:
            # Get system trend data
            trend_data = self._analyze_system_trends()
            
            # Predict potential issues based on current patterns
            issue_predictions = self._predict_potential_issues(current_state, trend_data)
            
            # Resource-based predictions
            resource_predictions = self._predict_resource_issues(current_state)
            
            # Component health predictions
            component_predictions = self._predict_component_issues(current_state)
            
            # Combine all predictions
            all_predictions = []
            all_predictions.extend(issue_predictions)
            all_predictions.extend(resource_predictions)
            all_predictions.extend(component_predictions)
            
            # Sort by confidence and filter significant predictions
            significant_predictions = [
                pred for pred in all_predictions 
                if pred.get("confidence", 0) > 0.3
            ]
            significant_predictions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            
            predictions["predictions"] = significant_predictions[:10]
            
            # Generate risk assessment
            predictions["risk_assessment"] = self._assess_predictive_risks(significant_predictions)
            
            # Generate proactive recommendations
            predictions["proactive_recommendations"] = self._generate_proactive_recommendations_from_predictions(
                significant_predictions, current_state
            )
            
            # Add trend analysis
            predictions["trend_analysis"] = trend_data
            
        except Exception as e:
            logging.error(f"Predictive analysis failed: {e}")
            predictions["error"] = str(e)
        
        return predictions
    
    def _analyze_historical_patterns(self, query: str, historical_insights: Dict) -> Dict[str, Any]:
        """Analyze historical patterns for the given query."""
        patterns = {
            "pattern_matches": 0,
            "common_causes": [],
            "successful_solutions": [],
            "recurring_themes": [],
            "seasonal_patterns": {}
        }
        
        if not historical_insights:
            return patterns
        
        # Extract pattern information from historical insights
        similar_issues = historical_insights.get("similar_issues", [])
        patterns["pattern_matches"] = len(similar_issues)
        
        # Analyze common causes
        causes = defaultdict(int)
        solutions = defaultdict(int)
        themes = defaultdict(int)
        
        for issue in similar_issues:
            # Count causes
            if issue.get("root_cause"):
                causes[issue["root_cause"]] += 1
            
            # Count successful solutions
            if issue.get("resolution") and issue.get("success"):
                solutions[issue["resolution"]] += 1
            
            # Extract themes from issue types
            if issue.get("issue_type"):
                themes[issue["issue_type"]] += 1
        
        # Convert to sorted lists
        patterns["common_causes"] = [
            {"cause": cause, "frequency": count} 
            for cause, count in sorted(causes.items(), key=lambda x: x[1], reverse=True)
        ][:5]
        
        patterns["successful_solutions"] = [
            {"solution": solution, "success_count": count}
            for solution, count in sorted(solutions.items(), key=lambda x: x[1], reverse=True)
        ][:5]
        
        patterns["recurring_themes"] = [
            {"theme": theme, "occurrences": count}
            for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True)
        ][:3]
        
        # Analyze temporal patterns if timestamp data is available
        if similar_issues and all(issue.get("timestamp") for issue in similar_issues):
            patterns["seasonal_patterns"] = self._analyze_temporal_patterns(similar_issues)
        
        return patterns
    
    def _generate_historical_recommendations(self, query: str, current_analysis: Dict, historical_insights: Dict) -> List[Dict[str, Any]]:
        """Generate recommendations based on historical data."""
        recommendations = []
        
        if not historical_insights:
            return recommendations
        
        # Get predictions from historical insights
        prediction_data = historical_insights.get("prediction", {})
        if prediction_data:
            confidence = prediction_data.get("confidence", 0)
            if confidence > 0.5:
                recommendations.append({
                    "type": "historical_prediction",
                    "title": "Historical Pattern Match",
                    "description": f"Similar issue detected with {confidence:.1%} confidence",
                    "predicted_cause": prediction_data.get("predicted_cause", "unknown"),
                    "confidence": confidence,
                    "historical_occurrences": prediction_data.get("historical_count", 0)
                })
        
        # Add recommendations from successful historical solutions
        historical_recommendations = prediction_data.get("recommendations", [])
        for rec in historical_recommendations[:3]:
            recommendations.append({
                "type": "historical_solution",
                "title": "Proven Historical Solution",
                "description": rec.get("action", "Unknown action"),
                "success_rate": rec.get("success_rate", 0),
                "confidence": rec.get("success_rate", 0),
                "safety_level": "medium"  # Historical solutions need verification
            })
        
        # Add preventive recommendations if patterns suggest recurring issues
        similar_issues = historical_insights.get("similar_issues", [])
        if len(similar_issues) > 2:  # Recurring pattern
            recommendations.append({
                "type": "preventive",
                "title": "Recurring Issue Prevention",
                "description": f"This issue has occurred {len(similar_issues)} times previously",
                "recommendation": "Consider implementing monitoring or preventive measures",
                "confidence": 0.7
            })
        
        return recommendations
    
    def _calculate_historical_confidence(self, query: str, historical_insights: Dict, current_analysis: Dict) -> Dict[str, float]:
        """Calculate confidence scores based on historical data."""
        confidence_scores = {
            "overall_confidence": 0.0,
            "pattern_match_confidence": 0.0,
            "solution_confidence": 0.0,
            "prediction_confidence": 0.0
        }
        
        if not historical_insights:
            return confidence_scores
        
        # Pattern match confidence
        similar_issues = historical_insights.get("similar_issues", [])
        if similar_issues:
            confidence_scores["pattern_match_confidence"] = min(len(similar_issues) * 0.2, 1.0)
        
        # Solution confidence based on historical success rates
        prediction_data = historical_insights.get("prediction", {})
        if prediction_data:
            confidence_scores["prediction_confidence"] = prediction_data.get("confidence", 0.0)
            
            recommendations = prediction_data.get("recommendations", [])
            if recommendations:
                avg_success_rate = sum(rec.get("success_rate", 0) for rec in recommendations) / len(recommendations)
                confidence_scores["solution_confidence"] = avg_success_rate
        
        # Calculate overall confidence
        individual_scores = [
            confidence_scores["pattern_match_confidence"],
            confidence_scores["solution_confidence"],
            confidence_scores["prediction_confidence"]
        ]
        
        # Weight the scores (prediction is most important)
        weights = [0.3, 0.4, 0.3]
        confidence_scores["overall_confidence"] = sum(
            score * weight for score, weight in zip(individual_scores, weights)
        )
        
        return confidence_scores
    
    def _analyze_system_trends(self) -> Dict[str, Any]:
        """Analyze system trends for predictive analysis."""
        trends = {
            "timestamp": datetime.now().isoformat(),
            "resource_trends": {},
            "error_trends": {},
            "performance_trends": {},
            "availability_trends": {}
        }
        
        try:
            # Get historical data if available
            if self.issue_history:
                # Get recent issues for trend analysis
                recent_issues = self.issue_history.get_recent_issues(days=7)
                
                # Analyze error trends
                error_counts = defaultdict(int)
                daily_counts = defaultdict(int)
                
                for issue in recent_issues:
                    error_type = issue.get("issue_type", "unknown")
                    error_counts[error_type] += 1
                    
                    # Group by day
                    if issue.get("timestamp"):
                        try:
                            issue_date = datetime.fromisoformat(issue["timestamp"]).date()
                            daily_counts[str(issue_date)] += 1
                        except:
                            pass
                
                trends["error_trends"] = {
                    "by_type": dict(error_counts),
                    "daily_counts": dict(daily_counts),
                    "total_recent_issues": len(recent_issues)
                }
            
            # Analyze current resource trends
            trends["resource_trends"] = self._analyze_current_resource_trends()
            
        except Exception as e:
            logging.error(f"Failed to analyze system trends: {e}")
            trends["error"] = str(e)
        
        return trends
    
    def _analyze_current_resource_trends(self) -> Dict[str, Any]:
        """Analyze current resource utilization trends."""
        resource_trends = {}
        
        try:
            # Get current memory usage
            mem_result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
            if mem_result.returncode == 0:
                lines = mem_result.stdout.strip().split('\n')
                if len(lines) > 1:
                    mem_line = lines[1].split()
                    if len(mem_line) >= 3:
                        total_mem = int(mem_line[1])
                        used_mem = int(mem_line[2])
                        mem_usage_percent = (used_mem / total_mem) * 100
                        resource_trends["memory_usage_percent"] = round(mem_usage_percent, 2)
            
            # Get current disk usage
            df_result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            if df_result.returncode == 0:
                lines = df_result.stdout.strip().split('\n')
                if len(lines) > 1:
                    disk_line = lines[1].split()
                    if len(disk_line) >= 5:
                        usage_str = disk_line[4].rstrip('%')
                        try:
                            resource_trends["disk_usage_percent"] = int(usage_str)
                        except ValueError:
                            pass
            
            # Get load average
            uptime_result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
            if uptime_result.returncode == 0:
                # Extract load average
                uptime_output = uptime_result.stdout
                load_match = re.search(r'load average: ([\d.]+)', uptime_output)
                if load_match:
                    resource_trends["load_average"] = float(load_match.group(1))
            
        except Exception as e:
            logging.warning(f"Failed to get resource trends: {e}")
        
        return resource_trends
    
    def _predict_potential_issues(self, current_state: Dict, trend_data: Dict) -> List[Dict[str, Any]]:
        """Predict potential issues based on current state and trends."""
        predictions = []
        
        # Resource-based predictions
        resource_trends = trend_data.get("resource_trends", {})
        
        # Memory usage predictions
        memory_usage = resource_trends.get("memory_usage_percent", 0)
        if memory_usage > 80:
            predictions.append({
                "type": "resource_exhaustion",
                "category": "memory",
                "description": "High memory usage detected - potential memory exhaustion",
                "current_value": memory_usage,
                "threshold": 80,
                "confidence": min((memory_usage - 70) / 30, 1.0),
                "timeframe": "within 1-2 hours",
                "severity": "high" if memory_usage > 90 else "medium"
            })
        
        # Disk usage predictions
        disk_usage = resource_trends.get("disk_usage_percent", 0)
        if disk_usage > 85:
            predictions.append({
                "type": "resource_exhaustion",
                "category": "disk",
                "description": "High disk usage detected - potential disk space exhaustion",
                "current_value": disk_usage,
                "threshold": 85,
                "confidence": min((disk_usage - 75) / 25, 1.0),
                "timeframe": "within hours to days",
                "severity": "critical" if disk_usage > 95 else "high"
            })
        
        # Load average predictions
        load_avg = resource_trends.get("load_average", 0)
        if load_avg > 2.0:
            predictions.append({
                "type": "performance_degradation",
                "category": "cpu_load",
                "description": "High system load detected - potential performance issues",
                "current_value": load_avg,
                "threshold": 2.0,
                "confidence": min((load_avg - 1.0) / 3.0, 1.0),
                "timeframe": "immediate",
                "severity": "medium"
            })
        
        # Error trend predictions
        error_trends = trend_data.get("error_trends", {})
        total_recent_issues = error_trends.get("total_recent_issues", 0)
        
        if total_recent_issues > 5:
            predictions.append({
                "type": "stability_degradation",
                "category": "error_frequency",
                "description": f"Increased error frequency detected ({total_recent_issues} in 7 days)",
                "current_value": total_recent_issues,
                "threshold": 5,
                "confidence": min(total_recent_issues / 20, 1.0),
                "timeframe": "ongoing trend",
                "severity": "medium"
            })
        
        return predictions
    
    def _predict_resource_issues(self, current_state: Dict) -> List[Dict[str, Any]]:
        """Predict resource-related issues."""
        predictions = []
        
        # Check for Kubernetes resource predictions if available
        if self.expert_agent:
            try:
                analysis = self.expert_agent.analyze_system_comprehensive()
                detailed_analysis = analysis.get("detailed_analysis", {})
                
                # Check Kubernetes resource status
                k8s_status = detailed_analysis.get("kubernetes", {})
                if k8s_status.get("status") in ["warning", "degraded"]:
                    predictions.append({
                        "type": "kubernetes_resource_issue",
                        "category": "orchestration",
                        "description": "Kubernetes cluster showing resource stress indicators",
                        "confidence": 0.6,
                        "timeframe": "within hours",
                        "severity": "medium",
                        "component": "kubernetes"
                    })
                
                # Check storage predictions
                storage_status = detailed_analysis.get("storage", {})
                if storage_status.get("status") in ["warning", "degraded"]:
                    predictions.append({
                        "type": "storage_degradation",
                        "category": "storage",
                        "description": "Storage system showing degradation signs",
                        "confidence": 0.7,
                        "timeframe": "within hours to days",
                        "severity": "high",
                        "component": "storage"
                    })
                
            except Exception as e:
                logging.warning(f"Failed to get expert analysis for predictions: {e}")
        
        return predictions
    
    def _predict_component_issues(self, current_state: Dict) -> List[Dict[str, Any]]:
        """Predict component-specific issues."""
        predictions = []
        
        # Check for component-specific patterns
        components_to_check = ["kubernetes", "glusterfs", "system_services"]
        
        for component in components_to_check:
            # Basic health check prediction
            try:
                if component == "kubernetes":
                    # Check if kubectl is responsive
                    result = subprocess.run(["kubectl", "cluster-info"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode != 0:
                        predictions.append({
                            "type": "component_unavailability",
                            "category": "kubernetes",
                            "description": "Kubernetes cluster connectivity issues detected",
                            "confidence": 0.8,
                            "timeframe": "immediate",
                            "severity": "high",
                            "component": "kubernetes"
                        })
                
                elif component == "glusterfs":
                    # Check if gluster is responsive
                    result = subprocess.run(["gluster", "peer", "status"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode != 0:
                        predictions.append({
                            "type": "component_unavailability",
                            "category": "glusterfs",
                            "description": "GlusterFS cluster communication issues detected",
                            "confidence": 0.7,
                            "timeframe": "immediate",
                            "severity": "medium",
                            "component": "glusterfs"
                        })
                
            except subprocess.TimeoutExpired:
                predictions.append({
                    "type": "component_timeout",
                    "category": component,
                    "description": f"{component.title()} component responding slowly",
                    "confidence": 0.6,
                    "timeframe": "immediate",
                    "severity": "medium",
                    "component": component
                })
            except Exception:
                pass  # Component might not be installed
        
        return predictions
    
    def _assess_predictive_risks(self, predictions: List[Dict]) -> Dict[str, Any]:
        """Assess overall risk based on predictions."""
        if not predictions:
            return {"overall_risk": "low", "risk_factors": []}
        
        # Calculate risk scores
        high_severity_count = len([p for p in predictions if p.get("severity") == "high"])
        critical_severity_count = len([p for p in predictions if p.get("severity") == "critical"])
        medium_severity_count = len([p for p in predictions if p.get("severity") == "medium"])
        
        # Calculate overall risk
        risk_score = (critical_severity_count * 3) + (high_severity_count * 2) + (medium_severity_count * 1)
        
        if risk_score >= 6:
            overall_risk = "critical"
        elif risk_score >= 4:
            overall_risk = "high"
        elif risk_score >= 2:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        # Identify risk factors
        risk_factors = []
        categories = defaultdict(int)
        
        for prediction in predictions:
            category = prediction.get("category", "unknown")
            categories[category] += 1
        
        for category, count in categories.items():
            risk_factors.append({
                "category": category,
                "prediction_count": count,
                "risk_contribution": count * 0.2
            })
        
        return {
            "overall_risk": overall_risk,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "total_predictions": len(predictions),
            "severity_breakdown": {
                "critical": critical_severity_count,
                "high": high_severity_count,
                "medium": medium_severity_count
            }
        }
    
    def _generate_proactive_recommendations_from_predictions(self, predictions: List[Dict], current_state: Dict) -> List[Dict[str, Any]]:
        """Generate proactive recommendations based on predictions."""
        recommendations = []
        
        # Group predictions by category
        by_category = defaultdict(list)
        for pred in predictions:
            by_category[pred.get("category", "unknown")].append(pred)
        
        # Generate category-specific recommendations
        for category, category_predictions in by_category.items():
            high_confidence_preds = [p for p in category_predictions if p.get("confidence", 0) > 0.6]
            
            if not high_confidence_preds:
                continue
                
            if category == "memory":
                recommendations.append({
                    "type": "proactive_action",
                    "category": "memory",
                    "title": "Memory Usage Optimization",
                    "description": "Proactively manage memory usage to prevent exhaustion",
                    "actions": [
                        "Identify memory-intensive processes",
                        "Clear system caches if safe",
                        "Consider scaling down non-critical services"
                    ],
                    "urgency": "medium",
                    "confidence": max(p.get("confidence", 0) for p in high_confidence_preds)
                })
            
            elif category == "disk":
                recommendations.append({
                    "type": "proactive_action",
                    "category": "disk",
                    "title": "Disk Space Management",
                    "description": "Prevent disk space exhaustion through proactive cleanup",
                    "actions": [
                        "Clean up log files and temporary files",
                        "Archive or compress old data",
                        "Check for large files that can be removed"
                    ],
                    "urgency": "high",
                    "confidence": max(p.get("confidence", 0) for p in high_confidence_preds)
                })
            
            elif category == "kubernetes":
                recommendations.append({
                    "type": "proactive_action",
                    "category": "kubernetes",
                    "title": "Kubernetes Cluster Maintenance",
                    "description": "Address cluster issues before they become critical",
                    "actions": [
                        "Check pod resource limits and requests",
                        "Verify node availability and health",
                        "Review cluster networking configuration"
                    ],
                    "urgency": "medium",
                    "confidence": max(p.get("confidence", 0) for p in high_confidence_preds)
                })
        
        # Add general recommendations for high-risk situations
        high_risk_predictions = [p for p in predictions if p.get("severity") in ["high", "critical"]]
        if high_risk_predictions:
            recommendations.append({
                "type": "general_precaution",
                "category": "system",
                "title": "System Stability Precautions",
                "description": "Take general precautions due to predicted high-risk conditions",
                "actions": [
                    "Ensure recent backups are available",
                    "Verify monitoring systems are active",
                    "Prepare rollback procedures",
                    "Schedule maintenance window if needed"
                ],
                "urgency": "high",
                "confidence": 0.8
            })
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _analyze_temporal_patterns(self, issues: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal patterns in historical issues."""
        patterns = {
            "hourly_distribution": defaultdict(int),
            "daily_distribution": defaultdict(int),
            "weekly_distribution": defaultdict(int),
            "monthly_distribution": defaultdict(int),
            "time_based_insights": []
        }
        
        for issue in issues:
            timestamp_str = issue.get("timestamp")
            if not timestamp_str:
                continue
                
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Hour of day (0-23)
                patterns["hourly_distribution"][timestamp.hour] += 1
                
                # Day of week (0-6, Monday is 0)
                patterns["daily_distribution"][timestamp.weekday()] += 1
                
                # Week of year
                week_num = timestamp.isocalendar()[1]
                patterns["weekly_distribution"][week_num] += 1
                
                # Month
                patterns["monthly_distribution"][timestamp.month] += 1
                
            except Exception as e:
                logging.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
                continue
        
        # Generate insights from patterns
        if patterns["hourly_distribution"]:
            peak_hour = max(patterns["hourly_distribution"].items(), key=lambda x: x[1])
            patterns["time_based_insights"].append({
                "type": "peak_hour",
                "description": f"Most issues occur at hour {peak_hour[0]}:00 ({peak_hour[1]} occurrences)"
            })
        
        if patterns["daily_distribution"]:
            peak_day = max(patterns["daily_distribution"].items(), key=lambda x: x[1])
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            patterns["time_based_insights"].append({
                "type": "peak_day",
                "description": f"Most issues occur on {day_names[peak_day[0]]} ({peak_day[1]} occurrences)"
            })
        
        return patterns