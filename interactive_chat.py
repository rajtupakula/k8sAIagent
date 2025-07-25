#!/usr/bin/env python3
"""
Interactive Kubernetes AI Chat - Step 1: Real Command Execution
This version focuses on making the AI Chat actually run kubectl commands
"""
import streamlit as st
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Configure page
st.set_page_config(
    page_title="🧠 Interactive Kubernetes AI",
    page_icon="🧠",
    layout="wide"
)

# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

class KubectlExecutor:
    """Executes kubectl commands and returns real system information"""
    
    def __init__(self):
        self.kubectl_available = self._check_kubectl()
        if not self.kubectl_available:
            # Try to find kubectl in common locations
            common_paths = [
                "/usr/local/bin/kubectl",
                "/usr/bin/kubectl", 
                "/bin/kubectl",
                "/opt/bin/kubectl"
            ]
            for path in common_paths:
                if os.path.exists(path):
                    os.environ["PATH"] = f"{os.path.dirname(path)}:{os.environ.get('PATH', '')}"
                    self.kubectl_available = self._check_kubectl()
                    if self.kubectl_available:
                        break
    
    def _check_kubectl(self) -> bool:
        """Check if kubectl is available"""
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute kubectl command and return results"""
        if not self.kubectl_available:
            return {
                "success": False,
                "error": "kubectl is not available. Please install and configure kubectl.",
                "output": ""
            }
        
        try:
            # Execute the command
            result = subprocess.run(command.split(), 
                                  capture_output=True, text=True, timeout=30)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.returncode != 0 else "",
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out",
                "output": "",
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "command": command
            }
    
    def get_pods(self, namespace: str = "all") -> Dict[str, Any]:
        """Get pod information"""
        if namespace == "all":
            command = "kubectl get pods --all-namespaces -o wide"
        else:
            command = f"kubectl get pods -n {namespace} -o wide"
        
        result = self.execute_command(command)
        
        if result["success"]:
            # Parse the output into a more readable format
            lines = result["output"].split('\n')
            if len(lines) > 1:
                header = lines[0]
                pods = lines[1:] if lines[1:] else []
                
                result["parsed_data"] = {
                    "header": header,
                    "pods": pods,
                    "total_pods": len(pods)
                }
        
        return result
    
    def get_nodes(self) -> Dict[str, Any]:
        """Get node information"""
        command = "kubectl get nodes -o wide"
        result = self.execute_command(command)
        
        if result["success"]:
            lines = result["output"].split('\n')
            if len(lines) > 1:
                result["parsed_data"] = {
                    "header": lines[0],
                    "nodes": lines[1:] if lines[1:] else [],
                    "total_nodes": len(lines[1:]) if len(lines) > 1 else 0
                }
        
        return result
    
    def get_services(self, namespace: str = "all") -> Dict[str, Any]:
        """Get service information"""
        if namespace == "all":
            command = "kubectl get svc --all-namespaces -o wide"
        else:
            command = f"kubectl get svc -n {namespace} -o wide"
        
        return self.execute_command(command)

class SmartAI:
    """Smart AI that understands queries and executes appropriate commands"""
    
    def __init__(self, executor: KubectlExecutor):
        self.executor = executor
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze user query and determine what action to take"""
        query_lower = query.lower()
        
        # Pod-related queries
        if any(word in query_lower for word in ["pod", "pods", "container"]):
            if "get" in query_lower or "list" in query_lower or "show" in query_lower:
                return {
                    "action": "get_pods",
                    "confidence": 0.95,
                    "explanation": "I'll get the current pod status from your cluster"
                }
            elif "restart" in query_lower:
                return {
                    "action": "restart_pods",
                    "confidence": 0.90,
                    "explanation": "I'll help you restart pods (this would require specific pod names)"
                }
        
        # Node-related queries
        elif any(word in query_lower for word in ["node", "nodes", "cluster"]):
            return {
                "action": "get_nodes",
                "confidence": 0.95,
                "explanation": "I'll get the current node status from your cluster"
            }
        
        # Service-related queries
        elif any(word in query_lower for word in ["service", "services", "svc"]):
            return {
                "action": "get_services",
                "confidence": 0.90,
                "explanation": "I'll get the current service status from your cluster"
            }
        
        # Status/health queries
        elif any(word in query_lower for word in ["status", "health", "check"]):
            return {
                "action": "cluster_status",
                "confidence": 0.85,
                "explanation": "I'll check the overall cluster status"
            }
        
        # Default - try to understand what they want
        else:
            return {
                "action": "general_help",
                "confidence": 0.60,
                "explanation": f"I'm not sure what specific action you want. You asked: '{query}'. Try asking about pods, nodes, or services."
            }
    
    def execute_action(self, action: str, query: str) -> Dict[str, Any]:
        """Execute the determined action and return results"""
        
        if action == "get_pods":
            result = self.executor.get_pods()
            if result["success"]:
                parsed = result.get("parsed_data", {})
                total_pods = parsed.get("total_pods", 0)
                
                response = f"**🚀 Pod Status from Your Cluster:**\n\n"
                response += f"Found **{total_pods} pods** running:\n\n"
                response += f"```\n{result.get('output', 'No output available')}\n```"
                
                if total_pods > 0:
                    response += f"\n**Summary:** {total_pods} pods are currently deployed across your cluster."
                
                return {
                    "success": True,
                    "response": response,
                    "raw_data": result
                }
            else:
                return {
                    "success": False,
                    "response": f"❌ **Error getting pods:** {result.get('error', 'Unknown error')}",
                    "raw_data": result
                }
        
        elif action == "get_nodes":
            result = self.executor.get_nodes()
            if result["success"]:
                parsed = result.get("parsed_data", {})
                total_nodes = parsed.get("total_nodes", 0)
                
                response = f"**🖥️ Node Status from Your Cluster:**\n\n"
                response += f"Found **{total_nodes} nodes** in your cluster:\n\n"
                response += f"```\n{result.get('output', 'No output available')}\n```"
                
                return {
                    "success": True,
                    "response": response,
                    "raw_data": result
                }
            else:
                return {
                    "success": False,
                    "response": f"❌ **Error getting nodes:** {result.get('error', 'Unknown error')}",
                    "raw_data": result
                }
        
        elif action == "get_services":
            result = self.executor.get_services()
            if result["success"]:
                response = f"**🌐 Service Status from Your Cluster:**\n\n"
                response += f"```\n{result.get('output', 'No output available')}\n```"
                
                return {
                    "success": True,
                    "response": response,
                    "raw_data": result
                }
            else:
                return {
                    "success": False,
                    "response": f"❌ **Error getting services:** {result.get('error', 'Unknown error')}",
                    "raw_data": result
                }
        
        elif action == "cluster_status":
            # Get comprehensive status
            pods_result = self.executor.get_pods()
            nodes_result = self.executor.get_nodes()
            
            response = "**🏥 Cluster Health Check:**\n\n"
            
            if nodes_result["success"]:
                nodes_data = nodes_result.get("parsed_data", {})
                total_nodes = nodes_data.get("total_nodes", 0)
                response += f"**Nodes:** {total_nodes} nodes in cluster\n"
            
            if pods_result["success"]:
                pods_data = pods_result.get("parsed_data", {})
                total_pods = pods_data.get("total_pods", 0)
                response += f"**Pods:** {total_pods} pods running\n\n"
                
                # Show detailed status
                response += "**Node Details:**\n"
                response += f"```\n{nodes_result.get('output', 'No node data available')}\n```\n\n"
                
                response += "**Pod Summary:**\n"
                response += f"```\n{pods_result.get('output', 'No pod data available')}\n```"
            
            return {
                "success": True,
                "response": response,
                "raw_data": {"pods": pods_result, "nodes": nodes_result}
            }
        
        else:
            return {
                "success": False,
                "response": "I'm not sure how to help with that. Try asking about:\n- 'get pods' or 'show me all pods'\n- 'get nodes' or 'show cluster nodes'\n- 'get services'\n- 'cluster status'"
            }

# Initialize components
@st.cache_resource
def get_executor():
    return KubectlExecutor()

@st.cache_resource
def get_ai():
    return SmartAI(get_executor())

def main():
    st.title("🧠 Interactive Kubernetes AI Chat")
    st.caption("Ask me about your cluster and I'll run real kubectl commands!")
    
    executor = get_executor()
    ai = get_ai()
    
    # Show connection status
    if executor.kubectl_available:
        st.success("✅ **Connected to Kubernetes cluster** - Ready to execute commands!")
    else:
        st.error("❌ **kubectl not available** - Please install and configure kubectl to use this feature")
        
        with st.expander("🔧 How to fix this"):
            st.markdown("""
            **For local development:**
            ```bash
            # Install kubectl (macOS)
            brew install kubectl
            
            # Install kubectl (Linux)
            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
            chmod +x kubectl
            sudo mv kubectl /usr/local/bin/
            
            # Configure cluster access
            kubectl config view
            ```
            
            **For container deployment:**
            - The Dockerfile should install kubectl automatically
            - Check if the container has proper RBAC permissions
            - Verify the ServiceAccount is configured correctly
            """)
        
        st.info("💡 **Note**: This interactive feature requires kubectl to be installed and configured to access your Kubernetes cluster.")
        st.stop()
    
    # Display chat history
    st.subheader("💬 Chat History")
    
    for i, chat in enumerate(st.session_state.chat_history):
        with st.container():
            st.markdown(f"**🙋 You:** {chat['query']}")
            
            if chat.get('success', True):
                st.markdown(f"**🧠 AI:** {chat['response']}")
            else:
                st.error(f"**🧠 AI:** {chat['response']}")
            
            # Show technical details in expander
            if chat.get('raw_data'):
                with st.expander("🔧 Technical Details"):
                    st.json(chat['raw_data'])
            
            st.divider()
    
    # Chat input
    st.subheader("💭 Ask About Your Cluster")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "What would you like to know?",
            placeholder="Examples: 'get all pods', 'show cluster nodes', 'cluster status'",
            key="user_query"
        )
    
    with col2:
        ask_button = st.button("🚀 Ask AI", type="primary")
    
    # Quick action buttons
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📋 Get All Pods"):
            query = "get all pods"
            ask_button = True
    
    with col2:
        if st.button("🖥️ Get Nodes"):
            query = "get nodes"
            ask_button = True
    
    with col3:
        if st.button("🌐 Get Services"):
            query = "get services"
            ask_button = True
    
    with col4:
        if st.button("🏥 Cluster Status"):
            query = "cluster status"
            ask_button = True
    
    # Process query
    if ask_button and query:
        with st.spinner("🔍 Analyzing query and executing commands..."):
            # Analyze what the user wants
            try:
                analysis = ai.analyze_query(query)
                
                # Ensure analysis is a dictionary
                if not isinstance(analysis, dict):
                    st.warning(f"Analysis returned {type(analysis)} instead of dict, using fallback")
                    analysis = {
                        'explanation': 'Processing your request with fallback analysis',
                        'confidence': 0.8,
                        'action': 'general_help'
                    }
                
                # Defensive programming - handle cases where analysis might not have expected keys
                explanation = analysis.get('explanation', 'Processing your request')
                confidence = analysis.get('confidence', 0.8)
                
                st.info(f"**Understanding:** {explanation} (Confidence: {confidence:.0%})")
                
                # Execute the action
                action = analysis.get('action', 'general_help')
                result = ai.execute_action(action, query)
                
            except Exception as e:
                st.error(f"❌ **Error analyzing query:** {str(e)}")
                # Show error details in an expandable section
                with st.expander("Show error details"):
                    import traceback
                    st.code(traceback.format_exc())
                
                # Fallback analysis
                analysis = {
                    'explanation': f'Error processing query: {str(e)}',
                    'confidence': 0.5,
                    'action': 'general_help'
                }
                result = {
                    'success': False,
                    'response': f"❌ **Error:** Failed to process your query. Error: {str(e)}"
                }
            
            # Add to chat history
            chat_entry = {
                "query": query,
                "response": result.get('response', 'No response'),
                "success": result.get('success', False),
                "raw_data": result.get('raw_data'),
                "timestamp": datetime.now().isoformat(),
                "action": analysis.get('action', 'unknown'),
                "confidence": analysis.get('confidence', 0.8)
            }
            
            st.session_state.chat_history.append(chat_entry)
        
        # Rerun to show new chat
        st.rerun()
    
    # Clear chat button
    if st.button("🧹 Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

if __name__ == "__main__":
    main()
