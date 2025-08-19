import streamlit as st
from agent.llama_connector import LlamaConnector
from agent.expert_remediation_agent import ExpertRemediationAgent

st.set_page_config(page_title="Expert LLM Chat", layout="wide")
st.title("🧠 Expert AI Agent for Kubernetes | Ubuntu | GlusterFS")

agent = ExpertRemediationAgent()
llm = LlamaConnector()

if "chat" not in st.session_state:
    st.session_state.chat = []

log_input = st.text_area("📝 Paste system logs or describe the problem", height=200)

if st.button("🤖 Ask Agent"):
    agent_result = agent.expert_query(log_input)
    if agent_result["matched_issue"]:
        system_info = (
                f"System detected issue type: {agent_result['matched_issue']}\n"
                f"Confidence: {agent_result['confidence']}\n"
                f"Predicted root cause: {agent_result['root_cause_prediction']}\n"
                f"Suggested remediation:\n"
                + "\n".join(agent_result["remediation_plan"])
        )
    else:
        system_info = "No known issue detected. Consulting LLM for deep diagnosis."

    user_prompt = (
        f"Logs:\n{log_input}\n\n{system_info}\n\n"
        "Give advanced analysis, remediation suggestions, and what commands to run next."
    )

    response = llm.query(user_prompt)
    st.session_state.chat.append({"user": log_input, "assistant": response})

st.markdown("### 💬 Chat History")
for entry in st.session_state.chat[::-1]:
    st.markdown("**🧑 You:**")
    st.info(entry["user"])
    st.markdown("**🤖 Assistant:**")
    st.success(entry["assistant"])
