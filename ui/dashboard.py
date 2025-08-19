import streamlit as st
from agent.expert_remediation_agent import ExpertRemediationAgent

st.set_page_config(layout="wide")
agent = ExpertRemediationAgent()

st.title("🧠 Expert LLM System - AI Troubleshooting")

log_input = st.text_area("📋 Paste System Logs / Errors", height=300)
if st.button("🔍 Analyze & Remediate") and log_input:
    result = agent.expert_query(log_input)

    if result["matched_issue"]:
        st.success(f"🎯 Issue Type Detected: `{result['matched_issue']}`")
        st.write(f"🔎 Confidence: `{result['confidence'] * 100:.1f}%`")
        st.info(f"🧠 Root Cause Prediction: {result['root_cause_prediction']}")
        st.markdown("### 🛠️ Remediation Plan")
        for step in result["remediation_plan"]:
            st.code(step)
    else:
        st.warning("No matching issue found. Try expanding logs or refining input.")
