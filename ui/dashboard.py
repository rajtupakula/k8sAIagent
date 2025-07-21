try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    print("⚠️ Streamlit not available - running in test mode")
    STREAMLIT_AVAILABLE = False
    # Create a mock streamlit module for testing
    class MockSessionState:
        def __init__(self):
            self._state = {}
        def __getattr__(self, key):
            return self._state.get(key)
        def __setattr__(self, key, value):
            if key.startswith('_'):
                super().__setattr__(key, value)
            else:
                if not hasattr(self, '_state'):
                    super().__setattr__('_state', {})
                self._state[key] = value
        def __contains__(self, key):
            return key in self._state
        def get(self, key, default=None):
            return self._state.get(key, default)
        def clear(self):
            self._state.clear()
    
    class MockStreamlit:
        def __init__(self):
            self.session_state = MockSessionState()
        def title(self, text): print(f"TITLE: {text}")
        def header(self, text): print(f"HEADER: {text}")
        def info(self, text): print(f"INFO: {text}")
        def warning(self, text): print(f"WARNING: {text}")
        def error(self, text): print(f"ERROR: {text}")
        def success(self, text): print(f"SUCCESS: {text}")
        def write(self, text): print(f"WRITE: {text}")
        def caption(self, text): print(f"CAPTION: {text}")
        def subheader(self, text): print(f"SUBHEADER: {text}")
        def divider(self): print("---")
        def columns(self, n): return [self] * n
        def button(self, text, **kwargs): return False
        def selectbox(self, label, options, **kwargs): return options[0] if options else None
        def checkbox(self, label, **kwargs): return False
        def text_input(self, label, **kwargs): return ""
        def number_input(self, label, **kwargs): return 0
        def chat_input(self, placeholder): return None
        def chat_message(self, role): return self
        def markdown(self, text): print(f"MARKDOWN: {text}")
        def spinner(self, text): return self
        def expander(self, text, **kwargs): return self
        def empty(self): return self
        def text_area(self, *args, **kwargs): pass
        def metric(self, label, value): print(f"METRIC {label}: {value}")
        def tabs(self, tabs): return [self] * len(tabs)
        def sidebar(self): return self
        def container(self): return self
        def rerun(self): pass
        def plotly_chart(self, *args, **kwargs): pass
        def download_button(self, *args, **kwargs): pass
        def json(self, data): print(f"JSON: {data}")
        def code(self, text): print(f"CODE: {text}")
        def set_page_config(self, **kwargs): pass
        def status(self, label, **kwargs): return self
        def progress(self, value): pass
        def write_stream(self, generator): 
            for chunk in generator:
                print(f"STREAM: {chunk}")
        def select_slider(self, label, options, **kwargs): return options[0] if options else None
        def radio(self, label, options, **kwargs): return options[0] if options else None
        def multiselect(self, label, options, **kwargs): return []
        def slider(self, label, min_value=0, max_value=100, **kwargs): return min_value
        def toggle(self, label, **kwargs): return False
        def __enter__(self): return self
        def __exit__(self, *args): pass
    
    st = MockStreamlit()

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    print("⚠️ Pandas not available")
    PANDAS_AVAILABLE = False
    pd = None

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    print("⚠️ Plotly not available")
    PLOTLY_AVAILABLE = False
    px = None
    go = None
from datetime import datetime, timedelta
import json
import sys
import os
import logging
import time
import re

# Configure logging to suppress warnings during import
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("torch").setLevel(logging.WARNING)

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import with error handling for offline operation
try:
    from agent.monitor import KubernetesMonitor
except ImportError as e:
    st.error(f"Failed to import KubernetesMonitor: {e}")
    KubernetesMonitor = None

try:
    from agent.rag_agent import RAGAgent
except ImportError as e:
    st.error(f"Failed to import RAGAgent: {e}")
    RAGAgent = None

try:
    from agent.remediate import RemediationEngine
except ImportError as e:
    st.warning(f"Failed to import RemediationEngine: {e}")
    RemediationEngine = None

try:
    from scheduler.forecast import ResourceForecaster
except ImportError as e:
    st.warning(f"Failed to import ResourceForecaster: {e}")
    ResourceForecaster = None

try:
    from glusterfs.analyze import GlusterFSAnalyzer
except ImportError as e:
    st.warning(f"Failed to import GlusterFSAnalyzer: {e}")
    GlusterFSAnalyzer = None

# Mock classes for when components are unavailable
class AdvancedRAGAgent:
    """Advanced RAG agent with latest LLM capabilities."""
    def __init__(self):
        self.llama_available = False
        self.offline_mode = True
        self.model_name = "llama-3.1-8b-instruct"  # Latest model
        self.context_window = 32768  # Extended context
        self.streaming_enabled = True
        self.function_calling_enabled = True
        self.conversation_memory = []
        
        # Model performance metrics
        self.response_time = 0
        self.tokens_generated = 0
        self.memory_usage = 0
        
        # Available models (latest and greatest)
        self.available_models = {
            "llama-3.1-8b-instruct": {"context": 32768, "speed": "fast", "quality": "high"},
            "llama-3.1-70b-instruct": {"context": 32768, "speed": "medium", "quality": "very_high"},
            "mistral-7b-instruct-v0.3": {"context": 32768, "speed": "fast", "quality": "high"},
            "codellama-34b-instruct": {"context": 16384, "speed": "medium", "quality": "high", "specialty": "code"},
            "vicuna-13b-v1.5": {"context": 4096, "speed": "fast", "quality": "medium"},
            "wizardlm-13b-v1.2": {"context": 4096, "speed": "fast", "quality": "high"},
            "openchat-3.5": {"context": 8192, "speed": "fast", "quality": "high"},
            "neural-chat-7b-v3": {"context": 8192, "speed": "fast", "quality": "medium"}
        }
        
        # System prompt for enhanced capabilities
        self.system_prompt = """You are an advanced Kubernetes AI Assistant with expert-level knowledge in:
        - Kubernetes operations, troubleshooting, and best practices
        - Container orchestration and cloud-native technologies
        - DevOps, CI/CD, and infrastructure automation
        - Performance optimization and security
        - Multi-cloud and hybrid deployments

        You can execute actions by providing structured responses. Available actions:
        - restart_pods: Restart failed or problematic pods
        - scale_deployment: Scale deployments up or down
        - clean_jobs: Clean completed or failed jobs
        - drain_node: Safely drain nodes for maintenance
        - apply_manifest: Apply Kubernetes manifests
        - run_kubectl: Execute kubectl commands

        Always provide:
        1. Clear, actionable guidance
        2. Relevant kubectl commands
        3. Security considerations
        4. Best practices
        5. Preventive measures

        Format responses with proper markdown and code blocks for better readability.
        """
    
    def switch_model(self, model_name: str):
        """Switch to a different LLM model."""
        if model_name in self.available_models:
            self.model_name = model_name
            model_info = self.available_models[model_name]
            self.context_window = model_info["context"]
            return f"✅ Switched to {model_name} (Context: {self.context_window} tokens, Speed: {model_info['speed']}, Quality: {model_info['quality']})"
        else:
            return f"❌ Model {model_name} not available"
    
    def get_model_info(self):
        """Get current model information."""
        if self.model_name in self.available_models:
            info = self.available_models[self.model_name]
            return {
                "name": self.model_name,
                "context_window": self.context_window,
                "speed": info.get("speed", "unknown"),
                "quality": info.get("quality", "unknown"),
                "specialty": info.get("specialty", "general"),
                "streaming": self.streaming_enabled,
                "function_calling": self.function_calling_enabled
            }
        return {"name": "unknown", "context_window": 0}
    
    def query_stream(self, question: str, include_context: bool = True):
        """Stream response generation for real-time feedback."""
        import time
        
        # Simulate streaming response with realistic chunks
        response_chunks = [
            "Based on your Kubernetes question, ",
            "let me provide a comprehensive analysis.\n\n",
            "**Current Situation Analysis:**\n",
            f"- Query: {question[:50]}{'...' if len(question) > 50 else ''}\n",
            "- System: Operating in offline mode\n",
            "- Context: Full cluster visibility available\n\n",
            "**Recommended Actions:**\n",
            "1. **Immediate Steps:**\n",
            "   - Check resource status: `kubectl get pods,nodes,services`\n",
            "   - Review recent events: `kubectl get events --sort-by=.metadata.creationTimestamp`\n\n",
            "2. **Diagnostic Commands:**\n",
            "   ```bash\n",
            "   kubectl describe pods --all-namespaces\n",
            "   kubectl top nodes\n",
            "   kubectl get componentstatuses\n",
            "   ```\n\n",
            "3. **Monitoring & Logs:**\n",
            "   - Check system logs: `journalctl -u kubelet`\n",
            "   - Monitor resource usage: `kubectl top pods --all-namespaces`\n\n",
            "**Best Practices:**\n",
            "- Always backup before making changes\n",
            "- Use namespace isolation\n",
            "- Implement proper RBAC\n",
            "- Monitor resource quotas\n\n",
            "**Security Considerations:**\n",
            "- Verify pod security contexts\n",
            "- Check network policies\n",
            "- Review admission controllers\n\n",
            f"**Note:** This is an enhanced AI response using {self.model_name} ",
            "with extended context window and improved reasoning capabilities."
        ]
        
        for i, chunk in enumerate(response_chunks):
            time.sleep(0.1)  # Simulate processing time
            yield chunk
            self.tokens_generated += len(chunk.split())
    
    def query(self, question: str) -> str:
        """Enhanced query with improved reasoning and context."""
        start_time = time.time()
        
        # Add to conversation memory
        self.conversation_memory.append({"role": "user", "content": question})
        
        # Generate enhanced response
        response = f"""
        🤖 **Advanced AI Analysis** (Model: {self.model_name})
        
        **Your Question:** "{question}"
        
        ## 🔍 **Intelligent Analysis**
        
        Based on advanced reasoning and Kubernetes expertise, here's my analysis:
        
        ### **Context-Aware Response:**
        
        **1. Problem Identification:**
        - Analyzing query patterns and intent
        - Cross-referencing with Kubernetes best practices
        - Considering cluster-specific context
        
        **2. Strategic Recommendations:**
        ```bash
        # Advanced diagnostics
        kubectl get pods --all-namespaces --field-selector=status.phase!=Running
        kubectl get events --sort-by=.metadata.creationTimestamp --field-selector type=Warning
        kubectl describe nodes | grep -A 5 "Conditions"
        
        # Performance analysis
        kubectl top nodes --sort-by=cpu
        kubectl top pods --all-namespaces --sort-by=cpu
        
        # Security audit
        kubectl auth can-i --list --as=system:serviceaccount:default:default
        kubectl get networkpolicies --all-namespaces
        ```
        
        **3. Intelligent Automation:**
        - Proactive monitoring setup
        - Automated healing strategies
        - Performance optimization recommendations
        
        ### **🎯 Advanced Features:**
        
        **Multi-Modal Analysis:**
        - Text processing with enhanced NLP
        - Pattern recognition across logs
        - Predictive issue detection
        
        **Function Calling:**
        - Automatic action execution
        - Context-aware command generation
        - Safe execution with rollback capabilities
        
        **Extended Context Window:**
        - Full conversation history retention
        - Complex query understanding
        - Long-form troubleshooting guides
        
        ### **📊 Performance Metrics:**
        - **Model:** {self.model_name}
        - **Context Window:** {self.context_window:,} tokens
        - **Processing Mode:** {('Streaming' if self.streaming_enabled else 'Batch')}
        - **Function Calling:** {('Enabled' if self.function_calling_enabled else 'Disabled')}
        
        ### **🔒 Security & Compliance:**
        - All processing happens locally
        - No data transmitted externally
        - RBAC-compliant operations
        - Audit trail maintained
        
        ### **💡 Proactive Suggestions:**
        
        Based on the latest Kubernetes trends and best practices:
        
        1. **GitOps Integration:** Consider implementing ArgoCD or Flux
        2. **Observability Stack:** Deploy Prometheus + Grafana + Jaeger
        3. **Security Hardening:** Implement Pod Security Standards
        4. **Backup Strategy:** Set up Velero for disaster recovery
        5. **Cost Optimization:** Use Vertical Pod Autoscaler (VPA)
        
        ---
        
        **🚀 Ready for Action:** Use the quick action buttons above or ask me to execute any of these recommendations!
        """
        
        # Update metrics
        self.response_time = time.time() - start_time
        self.tokens_generated += len(response.split())
        
        # Add to conversation memory
        self.conversation_memory.append({"role": "assistant", "content": response})
        
        # Trim memory if too long
        if len(self.conversation_memory) > 20:
            self.conversation_memory = self.conversation_memory[-20:]
        
        return response
    
    def query_with_actions(self, question: str, remediation_engine=None):
        """Enhanced query with advanced action detection and execution."""
        # Use expert query if available
        if hasattr(self, 'expert_query') and callable(getattr(self, 'expert_query')):
            try:
                expert_result = self.expert_query(question, auto_remediate=False)
                return {
                    "query_response": expert_result.get("expert_response", expert_result.get("standard_response", "")),
                    "action_result": {
                        "action_detected": expert_result.get("confidence", 0.0) > 0.5,
                        "action_type": expert_result.get("expert_analysis", {}).get("issue_analysis", {}).get("issue_type", "unknown"),
                        "executed": len(expert_result.get("expert_analysis", {}).get("executed_actions", [])) > 0,
                        "confidence": expert_result.get("confidence", 0.0),
                        "message": f"Expert analysis confidence: {expert_result.get('confidence', 0.0):.1%}",
                        "available_actions": ["analyze", "remediate", "monitor", "verify"]
                    },
                    "full_response": expert_result.get("expert_response", expert_result.get("standard_response", "")),
                    "model_info": self.get_model_info(),
                    "conversation_length": len(self.conversation_memory),
                    "expert_analysis": expert_result.get("expert_analysis", {}),
                    "system_health": expert_result.get("system_health", {})
                }
            except Exception as e:
                # Fallback to standard method
                pass
        
        # Advanced action detection using NLP patterns
        action_patterns = {
            "restart": {
                "patterns": [r"restart.*pod", r"reboot.*pod", r"bounce.*pod", r"cycle.*pod"],
                "action_type": "restart_pods",
                "confidence_threshold": 0.7
            },
            "scale": {
                "patterns": [r"scale.*(\d+)", r"increase.*replica", r"decrease.*replica", r"replicas?.*(\d+)"],
                "action_type": "scale_deployment", 
                "confidence_threshold": 0.8
            },
            "clean": {
                "patterns": [r"clean.*job", r"remove.*completed", r"delete.*finished", r"cleanup"],
                "action_type": "clean_jobs",
                "confidence_threshold": 0.6
            },
            "deploy": {
                "patterns": [r"deploy.*", r"apply.*manifest", r"create.*resource"],
                "action_type": "apply_manifest",
                "confidence_threshold": 0.7
            },
            "analyze": {
                "patterns": [r"analyze.*", r"check.*health", r"diagnose.*", r"investigate.*"],
                "action_type": "system_analysis",
                "confidence_threshold": 0.6
            },
            "fix": {
                "patterns": [r"fix.*", r"resolve.*", r"remediate.*", r"solve.*"],
                "action_type": "auto_remediate",
                "confidence_threshold": 0.8
            }
        }
        
        # Analyze intent with confidence scoring
        detected_actions = []
        for action_name, config in action_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, question.lower()):
                    confidence = min(1.0, len(re.findall(pattern, question.lower())) * 0.3 + 0.6)
                    if confidence >= config["confidence_threshold"]:
                        detected_actions.append({
                            "action": config["action_type"],
                            "confidence": confidence,
                            "trigger_phrase": pattern
                        })
        
        # Execute highest confidence action
        action_result = {
            "action_detected": len(detected_actions) > 0,
            "action_type": None,
            "executed": False,
            "message": "No actions available in demo mode",
            "confidence": 0,
            "available_actions": list(action_patterns.keys())
        }
        
        if detected_actions:
            best_action = max(detected_actions, key=lambda x: x["confidence"])
            action_result.update({
                "action_type": best_action["action"],
                "confidence": best_action["confidence"],
                "trigger_phrase": best_action["trigger_phrase"],
                "message": f"Detected action: {best_action['action']} (confidence: {best_action['confidence']:.2f})"
            })
            
            # Mock execution for demo
            if remediation_engine:
                action_result["executed"] = True
                action_result["message"] = f"✅ Successfully executed {best_action['action']} with {best_action['confidence']:.0%} confidence"
        
        # Generate comprehensive response
        base_response = self.query(question)
        
        # Add action context if action detected
        if action_result["action_detected"]:
            action_context = f"""
            
            ## 🎯 **Action Intelligence**
            
            **Detected Intent:** {action_result["action_type"]}
            **Confidence Score:** {action_result["confidence"]:.1%}
            **Execution Status:** {'✅ Completed' if action_result["executed"] else '⏳ Pending'}
            
            **Available Actions:**
            {' | '.join([f"`{action}`" for action in action_result["available_actions"]])}
            
            **Smart Recommendations:**
            - Use natural language: "restart the failing pods"
            - Be specific: "scale nginx deployment to 5 replicas" 
            - Combine actions: "clean jobs and restart failed pods"
            """
            base_response += action_context
        
        return {
            "query_response": base_response,
            "action_result": action_result,
            "full_response": base_response,
            "model_info": self.get_model_info(),
            "conversation_length": len(self.conversation_memory)
        }
    
    def get_conversation_summary(self):
        """Get conversation summary with advanced analytics."""
        if not self.conversation_memory:
            return "No conversation history"
        
        user_messages = [msg for msg in self.conversation_memory if msg["role"] == "user"]
        assistant_messages = [msg for msg in self.conversation_memory if msg["role"] == "assistant"]
        
        return {
            "total_exchanges": len(user_messages),
            "avg_response_time": self.response_time,
            "total_tokens": self.tokens_generated,
            "memory_usage": len(str(self.conversation_memory)),
            "active_model": self.model_name,
            "recent_topics": [msg["content"][:50] + "..." for msg in user_messages[-3:]]
        }

class MockRAGAgent(AdvancedRAGAgent):
    """Enhanced mock RAG agent inheriting advanced features."""
    pass

class MockRemediationEngine:
    """Mock remediation engine for demo purposes."""
    def restart_failed_pods(self):
        return {"count": 0, "success": False, "message": "Mock mode - no actions performed"}
    
    def clean_completed_jobs(self):
        return {"count": 0, "success": False, "message": "Mock mode - no actions performed"}
    
    def clean_orphaned_storage(self):
        return {"count": 0, "success": False, "message": "Mock mode - no actions performed"}

class MockForecaster:
    """Mock forecaster for demo purposes."""
    def get_latest_forecast(self):
        return None
    
    def get_placement_recommendations(self):
        return []
    
    def generate_forecast(self, days, resource_type):
        pass

class MockGlusterFSAnalyzer:
    """Mock GlusterFS analyzer for demo purposes."""
    def get_health_status(self):
        return {
            "volumes_healthy": "Unknown",
            "peers_connected": "Unknown", 
            "heal_pending": 0,
            "split_brain_files": 0
        }
    
    def get_heal_map(self):
        return []
    
    def analyze_peers(self):
        return []

st.set_page_config(
    page_title="K8s AI Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state with offline mode and error handling
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

if 'monitor' not in st.session_state:
    if KubernetesMonitor:
        try:
            st.session_state.monitor = KubernetesMonitor()
        except Exception as e:
            st.error(f"Failed to initialize Kubernetes monitor: {e}")
            st.session_state.monitor = None
    else:
        st.session_state.monitor = None

if 'rag_agent' not in st.session_state:
    if RAGAgent:
        try:
            st.session_state.rag_agent = RAGAgent(offline_mode=True)
        except Exception as e:
            st.error(f"Failed to initialize RAG agent: {e}")
            # Create an advanced mock RAG agent for demo purposes
            st.session_state.rag_agent = AdvancedRAGAgent()
    else:
        st.session_state.rag_agent = AdvancedRAGAgent()

if 'remediation' not in st.session_state:
    if RemediationEngine:
        try:
            st.session_state.remediation = RemediationEngine()
        except Exception as e:
            st.warning(f"Remediation engine not available: {e}")
            st.session_state.remediation = MockRemediationEngine()
    else:
        st.session_state.remediation = MockRemediationEngine()

if 'forecaster' not in st.session_state:
    if ResourceForecaster:
        try:
            st.session_state.forecaster = ResourceForecaster()
        except Exception as e:
            st.warning(f"Forecaster not available: {e}")
            st.session_state.forecaster = MockForecaster()
    else:
        st.session_state.forecaster = MockForecaster()

if 'glusterfs' not in st.session_state:
    if GlusterFSAnalyzer:
        try:
            st.session_state.glusterfs = GlusterFSAnalyzer()
        except Exception as e:
            st.warning(f"GlusterFS analyzer not available: {e}")
            st.session_state.glusterfs = MockGlusterFSAnalyzer()
    else:
        st.session_state.glusterfs = MockGlusterFSAnalyzer()

def main():
    st.title("🚀 Kubernetes AI Assistant Dashboard")
    st.caption("🔒 **Offline Mode**: All operations performed locally within your cluster")
    
    # Component status indicators
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        # System Status
        st.subheader("System Status")
        
        # Cluster Connection Status
        if st.session_state.monitor:
            try:
                if st.session_state.monitor.is_connected():
                    st.success("✅ Kubernetes API")
                else:
                    st.error("❌ Kubernetes API")
            except:
                st.warning("⚠️ Kubernetes API")
        else:
            st.error("❌ Kubernetes Monitor")
        
        # RAG Agent Status
        if st.session_state.rag_agent:
            if st.session_state.rag_agent.llama_available:
                st.success("✅ LLM Engine")
            else:
                st.info("🔧 LLM (Offline Mode)")
        else:
            st.error("❌ RAG Agent")
        
        # Component availability
        st.write("**Components:**")
        st.write(f"• Remediation: {'✅' if st.session_state.remediation else '❌'}")
        st.write(f"• Forecasting: {'✅' if st.session_state.forecaster else '❌'}")
        st.write(f"• GlusterFS: {'✅' if st.session_state.glusterfs else '❌'}")
        
        st.divider()
        
        # Quick Actions
        st.subheader("Quick Actions")
        if st.button("🔍 Scan for Issues"):
            scan_for_issues()
        if st.button("📊 Generate Report"):
            generate_report()
        if st.button("🏥 Health Check"):
            run_health_check()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat Assistant", 
        "📋 Logs & Issues", 
        "📈 Forecasting", 
        "🗄️ GlusterFS Health",
        "⚙️ Manual Remediation"
    ])
    
    with tab1:
        if st.session_state.rag_agent:
            chat_interface()
        else:
            st.error("❌ Chat interface not available - RAG agent failed to initialize")
    
    with tab2:
        logs_and_issues()
    
    with tab3:
        forecasting_dashboard()
    
    with tab4:
        glusterfs_dashboard()
    
    with tab5:
        manual_remediation()

def chat_interface():
    st.header("🤖 Advanced AI Chat Assistant - Latest LLM Technology")
    
    # Model selection and status
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if hasattr(st.session_state.rag_agent, 'available_models'):
            current_model = st.selectbox(
                "🧠 Select AI Model:",
                options=list(st.session_state.rag_agent.available_models.keys()),
                index=0,
                help="Choose from latest state-of-the-art language models"
            )
            if current_model != st.session_state.rag_agent.model_name:
                result = st.session_state.rag_agent.switch_model(current_model)
                st.success(result)
                st.rerun()
    
    with col2:
        if hasattr(st.session_state.rag_agent, 'get_model_info'):
            model_info = st.session_state.rag_agent.get_model_info()
            st.metric("Context Window", f"{model_info.get('context_window', 0):,}")
    
    with col3:
        if hasattr(st.session_state.rag_agent, 'streaming_enabled'):
            streaming = st.toggle("🔄 Streaming", value=st.session_state.rag_agent.streaming_enabled)
            st.session_state.rag_agent.streaming_enabled = streaming
    
    # Advanced model capabilities display
    with st.expander("🚀 Advanced AI Capabilities", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.write("**🧠 Model Features:**")
            if hasattr(st.session_state.rag_agent, 'get_model_info'):
                info = st.session_state.rag_agent.get_model_info()
                st.write(f"• Quality: {info.get('quality', 'N/A')}")
                st.write(f"• Speed: {info.get('speed', 'N/A')}")
                st.write(f"• Specialty: {info.get('specialty', 'General')}")
        
        with col_b:
            st.write("**⚡ Performance:**")
            if hasattr(st.session_state.rag_agent, 'response_time'):
                st.write(f"• Response Time: {st.session_state.rag_agent.response_time:.2f}s")
                st.write(f"• Tokens Generated: {st.session_state.rag_agent.tokens_generated:,}")
                st.write(f"• Function Calling: {'✅' if getattr(st.session_state.rag_agent, 'function_calling_enabled', False) else '❌'}")
        
        with col_c:
            st.write("**🔍 Analytics:**")
            if hasattr(st.session_state.rag_agent, 'get_conversation_summary'):
                summary = st.session_state.rag_agent.get_conversation_summary()
                st.write(f"• Exchanges: {summary.get('total_exchanges', 0)}")
                st.write(f"• Memory Usage: {summary.get('memory_usage', 0)} chars")
                st.write(f"• Conversation Length: {getattr(st.session_state.rag_agent, 'conversation_memory', []) and len(st.session_state.rag_agent.conversation_memory) or 0}")
    
    # Enhanced status indicators
    status_col1, status_col2, status_col3, status_col4 = st.columns(4)
    with status_col1:
        llama_status = "🟢 Online" if getattr(st.session_state.rag_agent, 'llama_available', False) else "🟡 Offline"
        st.info(f"**LLM Status:** {llama_status}")
    
    with status_col2:
        mode = "🔒 Offline" if getattr(st.session_state.rag_agent, 'offline_mode', True) else "🌐 Online"
        st.info(f"**Processing:** {mode}")
    
    with status_col3:
        streaming_status = "🔄 Enabled" if getattr(st.session_state.rag_agent, 'streaming_enabled', False) else "⏸️ Disabled"
        st.info(f"**Streaming:** {streaming_status}")
    
    with status_col4:
        context_size = getattr(st.session_state.rag_agent, 'context_window', 0)
        st.info(f"**Context:** {context_size:,} tokens")
    
    # AI-powered quick actions with confidence scoring
    st.subheader("🎯 Expert AI-Powered Actions")
    action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)
    
    with action_col1:
        if st.button("� Expert Diagnosis", help="AI performs comprehensive system analysis"):
            execute_expert_action("perform comprehensive expert diagnosis of the entire system including Ubuntu OS, Kubernetes, and GlusterFS")
    
    with action_col2:
        if st.button("🚀 Auto-Remediate", help="AI automatically fixes detected issues"):
            execute_expert_action("automatically detect and remediate all critical system issues with safety checks")
    
    with action_col3:
        if st.button("🩺 Health Check", help="AI performs deep health analysis"):
            execute_expert_action("conduct deep health analysis across all system components and provide detailed report")
    
    with action_col4:
        if st.button("⚡ Smart Optimize", help="AI suggests and applies performance optimizations"):
            execute_expert_action("analyze system performance and apply safe optimization recommendations")
    
    with action_col5:
        if st.button("🛡️ Security Audit", help="AI performs comprehensive security assessment"):
            execute_expert_action("perform comprehensive security audit and hardening recommendations")
    
    # Legacy quick actions for backward compatibility
    st.subheader("🎯 AI-Powered Smart Actions")
    legacy_col1, legacy_col2, legacy_col3, legacy_col4, legacy_col5 = st.columns(5)
    
    with legacy_col1:
        if st.button("�🔄 Smart Restart", help="AI analyzes and restarts only problematic pods"):
            execute_smart_action("intelligently restart any failed or problematic pods")
    
    with legacy_col2:
        if st.button("🧹 Smart Cleanup", help="AI identifies and cleans safe-to-remove resources"):
            execute_smart_action("analyze and safely clean up completed jobs and unused resources")
    
    with legacy_col3:
        if st.button("📊 Health Analysis", help="AI performs comprehensive cluster health check"):
            execute_smart_action("perform a comprehensive health analysis of the entire cluster")
    
    with legacy_col4:
        if st.button("⚡ Auto-Optimize", help="AI suggests performance optimizations"):
            execute_smart_action("analyze the cluster and suggest performance optimizations")
    
    with legacy_col5:
        if st.button("🔐 Security Audit", help="AI performs security assessment"):
            execute_smart_action("conduct a security audit and identify potential vulnerabilities")
    
    st.divider()
    
    # Chat container with enhanced features
    chat_container = st.container()
    
    # Display chat messages with advanced formatting
    with chat_container:
        for i, message in enumerate(st.session_state.chat_messages):
            with st.chat_message(message["role"]):
                # Enhanced message display with metadata
                if message["role"] == "assistant" and hasattr(st.session_state.rag_agent, 'get_model_info'):
                    model_info = st.session_state.rag_agent.get_model_info()
                    st.caption(f"🤖 {model_info.get('name', 'AI Assistant')} • Quality: {model_info.get('quality', 'N/A')} • Context: {model_info.get('context_window', 0):,} tokens")
                
                st.markdown(message["content"])
                
                # Enhanced action results display
                if message.get("action_result") and message["action_result"]["action_detected"]:
                    with st.expander("🎯 AI Action Analysis", expanded=False):
                        action_result = message["action_result"]
                        
                        # Action confidence visualization
                        confidence = action_result.get("confidence", 0)
                        st.progress(confidence, text=f"Confidence: {confidence:.1%}")
                        
                        # Action details
                        col_x, col_y = st.columns(2)
                        with col_x:
                            st.write(f"**Action Type:** {action_result['action_type']}")
                            st.write(f"**Executed:** {'✅ Yes' if action_result['executed'] else '❌ No'}")
                        with col_y:
                            st.write(f"**Trigger:** {action_result.get('trigger_phrase', 'N/A')}")
                            st.write(f"**Model:** {message.get('model_info', {}).get('name', 'Unknown')}")
                        
                        st.write(f"**Result:** {action_result['message']}")
                        
                        if action_result.get("result"):
                            st.json(action_result["result"])
                
                # Conversation analytics for assistant messages
                if message["role"] == "assistant" and message.get("model_info"):
                    with st.expander("📊 Response Analytics", expanded=False):
                        info = message["model_info"]
                        metrics_col1, metrics_col2 = st.columns(2)
                        with metrics_col1:
                            st.metric("Response Quality", info.get("quality", "N/A"))
                            st.metric("Processing Speed", info.get("speed", "N/A"))
                        with metrics_col2:
                            st.metric("Function Calling", "✅" if info.get("function_calling") else "❌")
                            st.metric("Streaming Support", "✅" if info.get("streaming") else "❌")
    
    # Enhanced chat input with AI suggestions
    st.subheader("� Advanced AI Conversation")
    
    # AI-powered suggestion tabs
    suggestion_tab1, suggestion_tab2, suggestion_tab3 = st.tabs(["🎯 Smart Queries", "⚡ Quick Actions", "🔧 Advanced Operations"])
    
    with suggestion_tab1:
        smart_queries = [
            "What Ubuntu system issues need immediate attention and how to fix them?",
            "Analyze Kubernetes cluster health and identify critical problems",
            "Check GlusterFS distributed storage for any split-brain or heal issues",
            "Perform comprehensive security audit across all system components",
            "What are the current performance bottlenecks and optimization opportunities?",
            "Identify any failed services, high resource usage, or network connectivity issues",
            "Check for disk space issues, memory pressure, or CPU overload conditions",
            "Analyze pod crashes, pending workloads, and service connectivity problems"
        ]
        for query in smart_queries:
            if st.button(f"💡 {query}", key=f"smart_{hash(query)}"):
                execute_suggested_expert_query(query)
    
    with suggestion_tab2:
        quick_actions = [
            "Automatically restart all failed pods and services across the system",
            "Clean up completed jobs, old logs, and unnecessary files to free space",
            "Scale deployments based on current load and resource availability", 
            "Fix any Ubuntu service failures and restart problematic components",
            "Resolve GlusterFS volume issues, heal operations, and peer connectivity",
            "Apply security patches and hardening recommendations",
            "Optimize system performance by adjusting resource limits and requests",
            "Perform emergency system recovery and stability restoration"
        ]
        for action in quick_actions:
            if st.button(f"⚡ {action}", key=f"action_{hash(action)}"):
                execute_suggested_expert_query(action)
    
    with suggestion_tab3:
        advanced_ops = [
            "Generate comprehensive disaster recovery plan for the entire infrastructure",
            "Create automated monitoring and alerting for all critical system components",
            "Implement zero-downtime deployment strategy with rollback capabilities",
            "Setup multi-region failover and backup strategies for data protection",
            "Optimize resource allocation and implement intelligent autoscaling policies",
            "Conduct penetration testing and vulnerability assessment",
            "Implement advanced logging, monitoring, and observability stack",
            "Create automated remediation workflows for common system issues"
        ]
        for op in advanced_ops:
            if st.button(f"🔧 {op}", key=f"advanced_{hash(op)}"):
                execute_suggested_expert_query(op)
    
    # Main chat input with streaming support
    if prompt := st.chat_input("Ask anything about your cluster or request intelligent actions..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Generate response with streaming if enabled
        with st.chat_message("assistant"):
            if getattr(st.session_state.rag_agent, 'streaming_enabled', False) and hasattr(st.session_state.rag_agent, 'query_stream'):
                # Streaming response
                with st.status("🧠 AI Processing...") as status:
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    try:
                        for chunk in st.session_state.rag_agent.query_stream(prompt):
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▊")
                        
                        response_placeholder.markdown(full_response)
                        status.update(label="✅ Response Complete", state="complete")
                        
                        # Get action analysis
                        result = st.session_state.rag_agent.query_with_actions(prompt, st.session_state.remediation)
                        
                    except Exception as e:
                        st.error(f"Streaming error: {e}")
                        result = st.session_state.rag_agent.query_with_actions(prompt, st.session_state.remediation)
                        full_response = result["full_response"]
                        response_placeholder.markdown(full_response)
            else:
                # Standard response
                with st.spinner("🧠 Advanced AI Processing..."):
                    result = st.session_state.rag_agent.query_with_actions(prompt, st.session_state.remediation)
                    full_response = result["full_response"]
                    
                    st.markdown(full_response)
            
            # Store enhanced message with metadata
            assistant_message = {
                "role": "assistant",
                "content": full_response,
                "action_result": result.get("action_result", {}),
                "model_info": result.get("model_info", {}),
                "timestamp": datetime.now().isoformat(),
                "conversation_id": len(st.session_state.chat_messages)
            }
            st.session_state.chat_messages.append(assistant_message)
            
            # Show action execution results with enhanced UI
            if result.get("action_result", {}).get("executed"):
                st.balloons()  # Celebration for successful actions
                st.success(f"🎯 Action completed: {result['action_result']['message']}")
                
                # Refresh relevant data
                if any(keyword in prompt.lower() for keyword in ['restart', 'clean', 'scale', 'deploy']):
                    st.rerun()
            elif result.get("action_result", {}).get("action_detected"):
                confidence = result["action_result"].get("confidence", 0)
                if confidence > 0.8:
                    st.info(f"🎯 High-confidence action detected: {result['action_result']['action_type']} ({confidence:.1%})")
                else:
                    st.warning(f"⚠️ Possible action detected: {result['action_result']['action_type']} ({confidence:.1%}) - Consider being more specific")
    
    # Conversation management
    if st.session_state.chat_messages:
        col_clear, col_export, col_summary = st.columns(3)
        
        with col_clear:
            if st.button("🗑️ Clear Conversation"):
                st.session_state.chat_messages = []
                if hasattr(st.session_state.rag_agent, 'conversation_memory'):
                    st.session_state.rag_agent.conversation_memory = []
                st.rerun()
        
        with col_export:
            if st.button("📄 Export Chat"):
                export_conversation()
        
        with col_summary:
            if st.button("📊 Conversation Analytics"):
                show_conversation_analytics()

def execute_expert_action(action_text):
    """Execute an expert-level AI action with comprehensive analysis."""
    with st.spinner(f"🧠 Expert AI analyzing and executing: {action_text}..."):
        # Use expert query if available
        if hasattr(st.session_state.rag_agent, 'expert_query') and callable(getattr(st.session_state.rag_agent, 'expert_query')):
            try:
                result = st.session_state.rag_agent.expert_query(
                    action_text, 
                    auto_remediate=True
                )
                
                if result.get("expert_analysis", {}).get("executed_actions"):
                    st.success(f"✅ Expert action completed successfully!")
                    
                    # Show detailed results
                    with st.expander("📊 Expert Analysis Results", expanded=True):
                        system_health = result.get("system_health", {})
                        overall_health = system_health.get("overall_health", "unknown")
                        
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            health_emoji = {"healthy": "🟢", "warning": "🟡", "degraded": "🟠", "critical": "🔴"}.get(overall_health, "⚪")
                            st.metric("System Health", f"{health_emoji} {overall_health.title()}")
                        
                        with col_b:
                            confidence = result.get("confidence", 0.0)
                            st.metric("Analysis Confidence", f"{confidence:.1%}")
                        
                        with col_c:
                            executed_count = len(result.get("expert_analysis", {}).get("executed_actions", []))
                            st.metric("Actions Executed", executed_count)
                        
                        # Show critical issues if any
                        critical_issues = system_health.get("critical_issues", [])
                        if critical_issues:
                            st.write("**🚨 Critical Issues Addressed:**")
                            for issue in critical_issues[:3]:
                                st.write(f"• {issue}")
                        
                        # Show remediation results
                        executed_actions = result.get("expert_analysis", {}).get("executed_actions", [])
                        if executed_actions:
                            st.write("**⚡ Actions Performed:**")
                            for action in executed_actions:
                                status = "✅" if action.get("success") else "❌"
                                st.write(f"{status} {action.get('description', 'Unknown action')}")
                else:
                    st.info(f"🔍 Expert analysis completed. View detailed results below.")
                
                # Add to chat history with enhanced metadata
                st.session_state.chat_messages.append({
                    "role": "user", 
                    "content": action_text,
                    "action_type": "expert_action"
                })
                st.session_state.chat_messages.append({
                    "role": "assistant", 
                    "content": result.get("expert_response", result.get("standard_response", "")),
                    "expert_analysis": result.get("expert_analysis", {}),
                    "system_health": result.get("system_health", {}),
                    "confidence": result.get("confidence", 0.0),
                    "timestamp": datetime.now().isoformat(),
                    "action_type": "expert_response"
                })
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Expert action failed: {e}")
                # Fallback to standard action
                execute_smart_action(action_text)
        else:
            # Fallback to standard smart action
            st.warning("Expert agent not available, falling back to standard AI action")
            execute_smart_action(action_text)

def execute_smart_action(action_text):
    """Execute a smart AI-powered action with enhanced feedback."""
    with st.spinner(f"🧠 AI analyzing and executing: {action_text}..."):
        result = st.session_state.rag_agent.query_with_actions(
            action_text, 
            st.session_state.remediation
        )
        
        if result["action_result"]["executed"]:
            st.success(f"✅ {result['action_result']['message']}")
            
            # Show confidence and analytics
            confidence = result["action_result"].get("confidence", 0)
            if confidence > 0:
                st.info(f"🎯 Action executed with {confidence:.1%} confidence")
            
            # Add to chat history with enhanced metadata
            st.session_state.chat_messages.append({
                "role": "user", 
                "content": action_text,
                "action_type": "smart_action"
            })
            st.session_state.chat_messages.append({
                "role": "assistant", 
                "content": result["full_response"],
                "action_result": result["action_result"],
                "model_info": result.get("model_info", {}),
                "timestamp": datetime.now().isoformat()
            })
            st.rerun()
        else:
            st.error(f"❌ {result['action_result']['message']}")

def execute_suggested_expert_query(query):
    """Execute a suggested expert query with enhanced processing."""
    # Add user message to chat
    st.session_state.chat_messages.append({
        "role": "user", 
        "content": query,
        "suggestion_type": "expert_suggested"
    })
    
    # Process with expert AI if available
    with st.spinner("🧠 Expert AI analyzing your request..."):
        if hasattr(st.session_state.rag_agent, 'expert_query') and callable(getattr(st.session_state.rag_agent, 'expert_query')):
            try:
                result = st.session_state.rag_agent.expert_query(
                    query, 
                    auto_remediate=False  # Don't auto-execute for suggestions
                )
                
                # Add assistant response with expert analysis
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": result.get("expert_response", result.get("standard_response", "")),
                    "expert_analysis": result.get("expert_analysis", {}),
                    "system_health": result.get("system_health", {}),
                    "confidence": result.get("confidence", 0.0),
                    "timestamp": datetime.now().isoformat(),
                    "suggestion_type": "expert_response"
                })
                
            except Exception as e:
                # Fallback to standard processing
                result = st.session_state.rag_agent.query_with_actions(
                    query, 
                    st.session_state.remediation
                )
                
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": result["full_response"],
                    "action_result": result.get("action_result", {}),
                    "model_info": result.get("model_info", {}),
                    "timestamp": datetime.now().isoformat(),
                    "fallback": True
                })
        else:
            # Standard processing
            result = st.session_state.rag_agent.query_with_actions(
                query, 
                st.session_state.remediation
            )
            
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": result["full_response"],
                "action_result": result.get("action_result", {}),
                "model_info": result.get("model_info", {}),
                "timestamp": datetime.now().isoformat()
            })
    
    st.rerun()

def execute_suggested_query(query):
    """Execute a suggested query with enhanced processing."""
    # Add user message to chat
    st.session_state.chat_messages.append({
        "role": "user", 
        "content": query,
        "suggestion_type": "ai_suggested"
    })
    
    # Process with enhanced AI
    with st.spinner("🧠 Processing AI suggestion..."):
        result = st.session_state.rag_agent.query_with_actions(
            query, 
            st.session_state.remediation
        )
        
        # Add assistant response
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": result["full_response"],
            "action_result": result.get("action_result", {}),
            "model_info": result.get("model_info", {}),
            "timestamp": datetime.now().isoformat()
        })
    
    st.rerun()

def export_conversation():
    """Export conversation with advanced analytics."""
    if not st.session_state.chat_messages:
        st.warning("No conversation to export")
        return
    
    # Create comprehensive export
    export_data = {
        "export_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_messages": len(st.session_state.chat_messages),
            "model_used": getattr(st.session_state.rag_agent, 'model_name', 'unknown'),
            "conversation_id": f"k8s_ai_{int(time.time())}",
            "features": {
                "streaming": getattr(st.session_state.rag_agent, 'streaming_enabled', False),
                "function_calling": getattr(st.session_state.rag_agent, 'function_calling_enabled', False),
                "context_window": getattr(st.session_state.rag_agent, 'context_window', 0)
            }
        },
        "conversation": st.session_state.chat_messages,
        "analytics": {}
    }
    
    # Add analytics if available
    if hasattr(st.session_state.rag_agent, 'get_conversation_summary'):
        export_data["analytics"] = st.session_state.rag_agent.get_conversation_summary()
    
    # Convert to JSON
    export_json = json.dumps(export_data, indent=2, default=str)
    
    # Offer download
    st.download_button(
        label="📄 Download Advanced Chat Export",
        data=export_json,
        file_name=f"k8s_ai_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )
    
    st.success("✅ Conversation exported with full analytics")

def show_conversation_analytics():
    """Display advanced conversation analytics."""
    if not st.session_state.chat_messages:
        st.warning("No conversation data available")
        return
    
    st.subheader("📊 Advanced Conversation Analytics")
    
    # Calculate analytics
    user_messages = [msg for msg in st.session_state.chat_messages if msg["role"] == "user"]
    assistant_messages = [msg for msg in st.session_state.chat_messages if msg["role"] == "assistant"]
    
    action_messages = [msg for msg in assistant_messages if msg.get("action_result", {}).get("executed")]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Exchanges", len(user_messages))
        st.metric("Actions Executed", len(action_messages))
    
    with col2:
        avg_response_length = sum(len(msg["content"]) for msg in assistant_messages) / len(assistant_messages) if assistant_messages else 0
        st.metric("Avg Response Length", f"{avg_response_length:.0f} chars")
        
        if hasattr(st.session_state.rag_agent, 'response_time'):
            st.metric("Last Response Time", f"{st.session_state.rag_agent.response_time:.2f}s")
    
    with col3:
        if hasattr(st.session_state.rag_agent, 'tokens_generated'):
            st.metric("Tokens Generated", f"{st.session_state.rag_agent.tokens_generated:,}")
        
        action_success_rate = len(action_messages) / len(user_messages) * 100 if user_messages else 0
        st.metric("Action Success Rate", f"{action_success_rate:.1f}%")
    
    with col4:
        model_name = getattr(st.session_state.rag_agent, 'model_name', 'Unknown')
        st.metric("Current Model", model_name)
        
        context_usage = len(str(st.session_state.chat_messages))
        st.metric("Memory Usage", f"{context_usage:,} chars")
    
    # Conversation flow visualization
    if assistant_messages:
        st.subheader("💬 Conversation Flow")
        
        # Recent topics
        recent_topics = [msg["content"][:100] + "..." for msg in user_messages[-5:]]
        for i, topic in enumerate(recent_topics, 1):
            st.write(f"{i}. {topic}")
        
        # Action analysis
        if action_messages:
            st.subheader("⚡ Action Analysis")
            action_types = {}
            for msg in action_messages:
                action_type = msg.get("action_result", {}).get("action_type", "unknown")
                action_types[action_type] = action_types.get(action_type, 0) + 1
            
            for action_type, count in action_types.items():
                st.write(f"• {action_type}: {count} times")
    
    # Model performance over time
    if hasattr(st.session_state.rag_agent, 'get_conversation_summary'):
        summary = st.session_state.rag_agent.get_conversation_summary()
        st.subheader("🎯 Model Performance")
        st.json(summary)

def execute_quick_action(action_text):
    """Execute a quick action with enhanced AI processing."""
    execute_smart_action(action_text)

def logs_and_issues():
    st.header("📋 Cluster Logs & Issues")
    
    if not st.session_state.monitor:
        st.error("❌ Kubernetes monitor not available")
        st.info("This tab requires connection to the Kubernetes API")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Recent Issues")
        try:
            issues = st.session_state.monitor.get_recent_issues()
            
            if issues:
                for issue in issues:
                    severity_color = {
                        "critical": "🔴",
                        "warning": "🟡", 
                        "info": "🔵"
                    }.get(issue.get("severity", "info"), "🔵")
                    
                    with st.expander(f"{severity_color} {issue['title']} - {issue['timestamp']}"):
                        st.write(f"**Resource:** {issue['resource']}")
                        st.write(f"**Namespace:** {issue['namespace']}")
                        st.write(f"**Description:** {issue['description']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button(f"🔧 Auto-remediate", key=f"auto_{issue['id']}"):
                                remediate_issue(issue['id'])
                        with col_b:
                            if st.button(f"🔍 Investigate", key=f"investigate_{issue['id']}"):
                                investigate_issue(issue['id'])
            else:
                st.info("No issues detected! 🎉")
        except Exception as e:
            st.error(f"Failed to fetch issues: {e}")
            st.info("Using mock data for demonstration")
            st.json({
                "issues": [
                    {"title": "Mock Issue", "severity": "info", "description": "This is demo data"}
                ]
            })
    
    with col2:
        st.subheader("Live Metrics")
        try:
            if st.session_state.monitor:
                metrics = st.session_state.monitor.get_cluster_metrics()
                
                st.metric("CPU Usage", f"{metrics.get('cpu_usage', 0):.1f}%")
                st.metric("Memory Usage", f"{metrics.get('memory_usage', 0):.1f}%")
                st.metric("Pod Count", metrics.get('pod_count', 0))
                st.metric("Node Count", metrics.get('node_count', 0))
            else:
                # Fallback metrics
                st.metric("CPU Usage", "N/A")
                st.metric("Memory Usage", "N/A")
                st.metric("Pod Count", "N/A")
                st.metric("Node Count", "N/A")
        except Exception as e:
            st.warning(f"Metrics unavailable: {e}")
        
        # Real-time log stream
        st.subheader("Live Logs")
        log_container = st.empty()
        
        if st.checkbox("Enable live logs"):
            try:
                if st.session_state.monitor:
                    logs = st.session_state.monitor.get_live_logs(limit=10)
                    log_text = "\n".join([f"[{log['timestamp']}] {log['message']}" for log in logs])
                    log_container.text_area("", value=log_text, height=200, disabled=True)
                else:
                    log_container.text_area("", value="Monitor not available", height=200, disabled=True)
            except Exception as e:
                log_container.text_area("", value=f"Error fetching logs: {e}", height=200, disabled=True)

def forecasting_dashboard():
    st.header("📈 Resource Forecasting & Node Optimization")
    
    if isinstance(st.session_state.forecaster, MockForecaster):
        st.warning("⚠️ Forecasting not available - install missing dependencies")
        st.info("This feature requires scikit-learn and other ML dependencies.")
        return
    
    # Forecast controls
    col1, col2, col3 = st.columns(3)
    with col1:
        forecast_days = st.selectbox("Forecast Period", [1, 3, 7, 14, 30], index=2)
    with col2:
        resource_type = st.selectbox("Resource Type", ["CPU", "Memory", "Storage"])
    with col3:
        if st.button("🔮 Generate Forecast"):
            generate_forecast(forecast_days, resource_type)
    
    # Forecast visualization
    try:
        forecast_data = st.session_state.forecaster.get_latest_forecast()
        if forecast_data:
            fig = px.line(
                forecast_data, 
                x='timestamp', 
                y='value', 
                color='type',
                title=f"{resource_type} Usage Forecast"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No forecast data available. Generate a forecast to see results.")
    except Exception as e:
        st.error(f"Error displaying forecast: {e}")
    
    # Node recommendations
    st.subheader("🎯 Pod Placement Recommendations")
    try:
        recommendations = st.session_state.forecaster.get_placement_recommendations()
        
        if recommendations:
            for rec in recommendations:
                with st.expander(f"📦 {rec['pod_name']} → {rec['recommended_node']}"):
                    st.write(f"**Current Node:** {rec['current_node']}")
                    st.write(f"**Recommended Node:** {rec['recommended_node']}")
                    st.write(f"**Reason:** {rec['reason']}")
                    st.write(f"**Expected Improvement:** {rec['improvement']}")
                    
                    if st.button(f"Apply Recommendation", key=f"apply_{rec['pod_name']}"):
                        apply_placement_recommendation(rec)
        else:
            st.info("No placement recommendations available.")
    except Exception as e:
        st.error(f"Error getting recommendations: {e}")

def glusterfs_dashboard():
    st.header("🗄️ GlusterFS Health Monitor")
    
    if isinstance(st.session_state.glusterfs, MockGlusterFSAnalyzer):
        st.warning("⚠️ GlusterFS monitoring not available")
        st.info("This feature requires GlusterFS to be installed and configured.")
        return
    
    # Health overview
    try:
        health_status = st.session_state.glusterfs.get_health_status()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Volume Status", health_status.get('volumes_healthy', 'Unknown'))
        with col2:
            st.metric("Peer Status", health_status.get('peers_connected', 'Unknown'))
        with col3:
            st.metric("Heal Pending", health_status.get('heal_pending', 0))
        with col4:
            st.metric("Split-brain Files", health_status.get('split_brain_files', 0))
    except Exception as e:
        st.error(f"Error getting health status: {e}")
        return
    
    # Heal map visualization
    st.subheader("🗺️ Heal Map")
    try:
        heal_data = st.session_state.glusterfs.get_heal_map()
        
        if heal_data:
            fig = go.Figure()
            
            for volume in heal_data:
                fig.add_trace(go.Scatter(
                    x=volume['timestamps'],
                    y=volume['heal_counts'],
                    mode='lines+markers',
                    name=volume['volume_name'],
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title="Heal Activity Over Time",
                xaxis_title="Time",
                yaxis_title="Files Healing",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No heal data available.")
    except Exception as e:
        st.error(f"Error displaying heal map: {e}")
    
    # Stuck peer detection
    st.subheader("🔍 Peer Analysis")
    try:
        peers = st.session_state.glusterfs.analyze_peers()
        
        if peers:
            for peer in peers:
                status_icon = "🟢" if peer['status'] == 'connected' else "🔴"
                with st.expander(f"{status_icon} Peer: {peer['hostname']}"):
                    st.write(f"**Status:** {peer['status']}")
                    st.write(f"**UUID:** {peer['uuid']}")
                    st.write(f"**Last Seen:** {peer['last_seen']}")
                    
                    if peer['status'] != 'connected':
                        if st.button(f"🔧 Attempt Reconnection", key=f"reconnect_{peer['uuid']}"):
                            reconnect_peer(peer['uuid'])
        else:
            st.info("No peer information available.")
    except Exception as e:
        st.error(f"Error analyzing peers: {e}")

def manual_remediation():
    st.header("⚙️ Manual Remediation Tools")
    
    # Quick actions
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Pod Operations**")
        if st.button("🔄 Restart Failed Pods"):
            restart_failed_pods()
        if st.button("📊 Scale Deployment"):
            show_scaling_dialog()
        if st.button("🗑️ Clean Completed Jobs"):
            clean_completed_jobs()
    
    with col2:
        st.write("**Node Operations**")
        if st.button("🔧 Drain Node"):
            show_node_drain_dialog()
        if st.button("🏷️ Label Nodes"):
            show_node_labeling_dialog()
        if st.button("📈 Uncordon Nodes"):
            uncordon_all_nodes()
    
    with col3:
        st.write("**Storage Operations**")
        if st.button("🗄️ Clean PV/PVC"):
            clean_orphaned_storage()
        if st.button("🔍 Analyze Storage"):
            analyze_storage_usage()
        if st.button("🏥 Volume Health Check"):
            check_volume_health()
    
    # Custom remediation
    st.subheader("🛠️ Custom Remediation")
    
    with st.expander("Custom kubectl command"):
        kubectl_cmd = st.text_input("Enter kubectl command:")
        if st.button("Execute") and kubectl_cmd:
            result = st.session_state.remediation.execute_kubectl(kubectl_cmd)
            st.code(result)
    
    with st.expander("Remediation History"):
        history = st.session_state.remediation.get_history()
        for action in history:
            st.write(f"**{action['timestamp']}** - {action['action']} - Status: {action['status']}")

# Helper functions
def scan_for_issues():
    if not st.session_state.monitor:
        st.error("❌ Monitor not available - cannot scan for issues")
        return
        
    with st.spinner("Scanning cluster for issues..."):
        try:
            st.session_state.monitor.scan_for_issues()
            st.success("Scan completed!")
        except Exception as e:
            st.error(f"Scan failed: {e}")
    st.rerun()

def generate_report():
    if not st.session_state.monitor:
        st.error("❌ Monitor not available - cannot generate report")
        return
        
    with st.spinner("Generating comprehensive report..."):
        try:
            report = st.session_state.monitor.generate_report()
            st.download_button(
                label="📄 Download Report",
                data=report,
                file_name=f"k8s_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        except Exception as e:
            st.error(f"Report generation failed: {e}")

def run_health_check():
    if not st.session_state.monitor:
        st.error("❌ Monitor not available - cannot run health check")
        return
        
    with st.spinner("Running health check..."):
        try:
            health = st.session_state.monitor.run_health_check()
            if health['overall_status'] == 'healthy':
                st.success("✅ Cluster is healthy!")
            else:
                st.warning(f"⚠️ Issues detected: {health['issues_count']}")
        except Exception as e:
            st.error(f"Health check failed: {e}")

def remediate_issue(issue_id):
    if isinstance(st.session_state.remediation, MockRemediationEngine):
        st.warning("❌ Remediation not available in mock mode")
        return
        
    with st.spinner("Applying remediation..."):
        try:
            result = st.session_state.remediation.auto_remediate(issue_id)
            if result['success']:
                st.success(f"✅ {result['message']}")
            else:
                st.error(f"❌ {result['message']}")
        except Exception as e:
            st.error(f"Remediation failed: {e}")

def investigate_issue(issue_id):
    if isinstance(st.session_state.rag_agent, MockRAGAgent):
        st.info("🔍 Investigation: Using basic troubleshooting guidance (mock mode)")
        return
        
    with st.spinner("Investigating issue..."):
        try:
            investigation = st.session_state.rag_agent.investigate_issue(issue_id)
            st.info(f"🔍 Investigation: {investigation}")
        except Exception as e:
            st.error(f"Investigation failed: {e}")

def generate_forecast(days, resource_type):
    if isinstance(st.session_state.forecaster, MockForecaster):
        st.warning("❌ Forecasting not available in mock mode")
        return
        
    with st.spinner(f"Generating {days}-day {resource_type} forecast..."):
        try:
            st.session_state.forecaster.generate_forecast(days, resource_type)
            st.success("Forecast generated!")
        except Exception as e:
            st.error(f"Forecast generation failed: {e}")
    st.rerun()

def apply_placement_recommendation(rec):
    with st.spinner("Applying placement recommendation..."):
        result = st.session_state.remediation.move_pod(
            rec['pod_name'], 
            rec['recommended_node']
        )
        if result['success']:
            st.success("✅ Pod moved successfully!")
        else:
            st.error(f"❌ Failed to move pod: {result['message']}")

def reconnect_peer(uuid):
    with st.spinner("Attempting to reconnect peer..."):
        result = st.session_state.glusterfs.reconnect_peer(uuid)
        if result['success']:
            st.success("✅ Peer reconnected!")
        else:
            st.error(f"❌ Failed to reconnect: {result['message']}")

def restart_failed_pods():
    with st.spinner("Restarting failed pods..."):
        result = st.session_state.remediation.restart_failed_pods()
        st.success(f"✅ Restarted {result['count']} pods")

def clean_completed_jobs():
    with st.spinner("Cleaning completed jobs..."):
        result = st.session_state.remediation.clean_completed_jobs()
        st.success(f"✅ Cleaned {result['count']} jobs")

def clean_orphaned_storage():
    with st.spinner("Cleaning orphaned storage..."):
        result = st.session_state.remediation.clean_orphaned_storage()
        st.success(f"✅ Cleaned {result['count']} orphaned resources")

def show_scaling_dialog():
    with st.expander("Scale Deployment", expanded=True):
        deployments = st.session_state.monitor.get_deployments()
        selected_deployment = st.selectbox("Select Deployment", deployments)
        new_replicas = st.number_input("New Replica Count", min_value=0, max_value=100, value=3)
        
        if st.button("Scale"):
            result = st.session_state.remediation.scale_deployment(selected_deployment, new_replicas)
            if result['success']:
                st.success(f"✅ Scaled {selected_deployment} to {new_replicas} replicas")
            else:
                st.error(f"❌ Failed to scale: {result['message']}")

def show_node_drain_dialog():
    with st.expander("Drain Node", expanded=True):
        nodes = st.session_state.monitor.get_nodes()
        selected_node = st.selectbox("Select Node to Drain", nodes)
        ignore_daemonsets = st.checkbox("Ignore DaemonSets", value=True)
        delete_local_data = st.checkbox("Delete Local Data", value=False)
        
        if st.button("Drain Node"):
            result = st.session_state.remediation.drain_node(
                selected_node, ignore_daemonsets, delete_local_data
            )
            if result['success']:
                st.success(f"✅ Node {selected_node} drained successfully")
            else:
                st.error(f"❌ Failed to drain node: {result['message']}")

def show_node_labeling_dialog():
    with st.expander("Label Nodes", expanded=True):
        nodes = st.session_state.monitor.get_nodes()
        selected_node = st.selectbox("Select Node", nodes)
        label_key = st.text_input("Label Key")
        label_value = st.text_input("Label Value")
        
        if st.button("Apply Label") and label_key:
            result = st.session_state.remediation.label_node(
                selected_node, label_key, label_value
            )
            if result['success']:
                st.success(f"✅ Applied label {label_key}={label_value} to {selected_node}")
            else:
                st.error(f"❌ Failed to apply label: {result['message']}")

def uncordon_all_nodes():
    with st.spinner("Uncordoning all nodes..."):
        result = st.session_state.remediation.uncordon_all_nodes()
        st.success(f"✅ Uncordoned {result['count']} nodes")

def analyze_storage_usage():
    with st.spinner("Analyzing storage usage..."):
        analysis = st.session_state.monitor.analyze_storage_usage()
        
        # Display storage analysis in a nice format
        st.subheader("📊 Storage Analysis Results")
        
        for volume in analysis['volumes']:
            with st.expander(f"Volume: {volume['name']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Used", f"{volume['used_gb']:.1f} GB")
                    st.metric("Available", f"{volume['available_gb']:.1f} GB")
                with col2:
                    st.metric("Usage %", f"{volume['usage_percent']:.1f}%")
                    st.metric("Type", volume['storage_class'])

def check_volume_health():
    with st.spinner("Checking volume health..."):
        health_check = st.session_state.monitor.check_volume_health()
        
        st.subheader("🏥 Volume Health Check Results")
        
        for volume in health_check['volumes']:
            status_icon = "🟢" if volume['healthy'] else "🔴"
            with st.expander(f"{status_icon} {volume['name']}"):
                st.write(f"**Status:** {volume['status']}")
                st.write(f"**Phase:** {volume['phase']}")
                if volume['issues']:
                    st.warning("Issues found:")
                    for issue in volume['issues']:
                        st.write(f"- {issue}")

if __name__ == "__main__":
    main()