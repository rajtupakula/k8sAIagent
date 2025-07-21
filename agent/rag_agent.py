import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
from datetime import datetime
import requests
import subprocess
import re
import time

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
        try:
            # Set cache directory to local path to avoid downloads
            os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.join(os.getcwd(), '.cache')
            self.embedding_model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            self.logger.warning(f"Failed to load embedding model: {e}")
            self.logger.info("Will continue without embeddings (reduced functionality)")
            self.embedding_model = None
        
        # Initialize ChromaDB
        try:
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
        
        # Check LLaMA server availability
        self._check_llama_server()
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Load default knowledge base
        self._initialize_knowledge_base()
    
    def _check_llama_server(self):
        """Check if LLaMA server is available."""
        try:
            response = requests.get(f"{self.llama_endpoint}/health", timeout=5)
            if response.status_code == 200:
                self.llama_available = True
                self.logger.info("LLaMA server is available")
            else:
                self.llama_available = False
                self.logger.warning("LLaMA server is not responding correctly")
        except Exception as e:
            self.llama_available = False
            self.logger.warning(f"LLaMA server not available: {e}")
            if not self.offline_mode:
                self.logger.info("Switching to offline mode")
                self.offline_mode = True
    
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
        """Enhanced expert-level query with intelligent issue detection and remediation."""
        result = {
            "query": question,
            "expert_analysis": {},
            "standard_response": "",
            "expert_response": "",
            "recommendations": [],
            "remediation_plan": [],
            "system_health": {},
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
                    # Get comprehensive system analysis
                    system_analysis = self.expert_agent.analyze_system_comprehensive()
                    result["system_health"] = system_analysis
                    
                    # Attempt expert remediation
                    expert_remediation = self.expert_agent.expert_remediate(question, auto_execute=auto_remediate)
                    result["expert_analysis"] = expert_remediation
                    
                    # Generate expert response
                    result["expert_response"] = self._generate_expert_response(
                        question, system_analysis, expert_remediation
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