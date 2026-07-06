import streamlit as st
import requests
from datetime import date
import json

API_URL_CHAT = "http://127.0.0.1:8000/chat"
API_URL_VALIDATE = "http://127.0.0.1:8000/validate"
st.set_page_config(page_title="HR Agentic Portal", page_icon="👥", layout="wide")

st.markdown("""
    <style>
    .response-box { padding: 20px; border-radius: 10px; background-color: #ffffff; color: #1f1f1f !important; border: 1px solid #e0e0e0; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("👥 HR Agentic Portal")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("API Key", type="password", value="AgentAppWorks123@")
    
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

tab_form, tab_chat = st.tabs(["📝 Employee Form", "💬 Agent Chat"])

with tab_form:
    st.subheader("Structured Data Entry")
    st.markdown("Use this form for precise employee onboarding.")

    col1, col2 = st.columns(2)
    with col1:
        emp_id = st.text_input("Employee ID", placeholder="E999")
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email Address")
        dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date(2100, 1, 1))

    with col2:
        hire_date = st.date_input("Hire Date", min_value=date(1900, 1, 1), max_value=date(2100, 1, 1))
        dept = st.selectbox("Department", ["ENGINEERING", "HR", "SALES", "MARKETING"])
        manager_id = st.text_input("Manager ID", placeholder="E001")
        emp_type = st.selectbox("Employment Type", ["FULL_TIME", "PART_TIME", "CONTRACTOR"])

    if st.button("🚀 Process Employee Record"):
        if not emp_id or not first_name or not last_name:
            st.error("Please fill in required fields (ID, First Name, Last Name).")
        else:
            payload = {
                "payload": {
                    "employee_id": emp_id, "first_name": first_name, "last_name": last_name,
                    "email": email, "date_of_birth": str(dob), "hire_date": str(hire_date),
                    "department": dept, "manager_id": manager_id, "employment_type": emp_type
                }
            }
            headers = {"x-api-key": api_key, "Content-Type": "application/json"}
            
            with st.spinner("Agent is processing..."):
                try:
                    response = requests.post(API_URL_VALIDATE, json=payload, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        st.success("Request Processed Successfully!")
                        st.markdown(f'<div class="response-box"><b>AI:</b> {data["agent_response"]}</div>', unsafe_allow_html=True)
                        with st.expander("View Technical Details"):
                            st.json(data["validated_data"])
                    elif response.status_code == 401:
                        st.error("Invalid API Key.")
                    else:
                        st.error(f"Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

with tab_chat:
    st.subheader("Conversational Assistant")
    st.markdown("Ask the agent to find, create, update, or delete employee records.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] in ["user", "assistant"]:
                with st.chat_message(msg["role"]):
                    if msg.get("content"):
                        st.markdown(msg["content"])
                    # NEW: Display thought process if it exists in the message history
                    if msg.get("thought"):
                        with st.expander("View Thought Process"):
                            st.markdown(msg["thought"])

    if prompt := st.chat_input("e.g., 'Is Jordan Bell in the system?'"):
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("assistant"):
                # Open the status container
                with st.status("Agent is thinking...", expanded=True) as status:
                    
                    payload = {
                        "message": prompt, 
                        "history": st.session_state.messages[:-1] 
                    }
                    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
                    
                    try:
                        # CRITICAL: stream=True tells requests to not download everything at once
                        response = requests.post(API_URL_CHAT, json=payload, headers=headers, stream=True)
                        
                        if response.status_code == 200:
                            final_ai_answer = ""
                            final_thought = ""
                            
                            # Iterate over the stream line by line
                            for line in response.iter_lines():
                                if line:
                                    # Parse the JSON chunk
                                    chunk = json.loads(line.decode('utf-8'))
                                    
                                    if chunk.get("type") == "step":
                                        node = chunk["node"]
                                        detail = chunk.get("detail", "Processing...")
                                        if node == "agent":
                                            st.write(f"🧠 **Thought:** {detail}")
                                        elif node == "tools":
                                            st.write(f"🛠️ **Action:** {detail}")
                                    
                                    elif chunk.get("type") == "final":
                                        final_ai_answer = chunk.get("answer", "")
                                        final_thought = chunk.get("thought", "") # <--- ADD THIS LINE
                                    
                                    elif chunk.get("type") == "error":
                                        st.error(f"Agent Error: {chunk.get('message')}")
                            
                            status.update(label="Processing complete!", state="complete", expanded=False)
                            
                            if final_ai_answer:
                                st.markdown(final_ai_answer)
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": final_ai_answer,
                                    "thought": final_thought 
                                })
                            else:
                                st.error("Agent failed to produce a final answer.")
                                
                        elif response.status_code == 401:
                            status.update(label="Authentication Error", state="error")
                            st.error("Invalid API Key.")
                        else:
                            status.update(label="Server Error", state="error")
                            st.error(f"Error: {response.status_code}")
                    except Exception as e:
                        status.update(label="Connection Error", state="error")
                        st.error(f"Connection error: {e}")
        
        st.rerun()