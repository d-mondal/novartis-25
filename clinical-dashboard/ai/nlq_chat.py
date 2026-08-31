import streamlit as st
import pandas as pd
from ai.gemini_client import gemini_call


def nlq_interface(df: pd.DataFrame):
    st.markdown("<h2>💬 Natural Language Query</h2>", unsafe_allow_html=True)
    st.caption("Ask questions over the current analytical snapshot")
    
    # Initialize session state
    if "nlq_history" not in st.session_state:
        st.session_state.nlq_history = []
    if "current_answer" not in st.session_state:
        st.session_state.current_answer = ""
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False
    
    # Function to handle form submission
    def handle_ask():
        query = st.session_state.nlq_query_input
        
        if not query.strip():
            st.session_state.show_answer = False
            return
        
        if df.empty:
            st.warning("No data available for the selected filters.")
            st.session_state.show_answer = False
            return
        
        # Create snapshot
        snapshot = {
            "scope": {
                "sites": int(df["site_id"].nunique()),
                "patients": int(df["patient_id"].nunique()),
                "countries": sorted(df["country"].dropna().unique().tolist())
            },
            "data_quality": {
                "average_dqi": round(df["dqi"].mean(), 2),
                "median_dqi": round(df["dqi"].median(), 2),
                "critical_patients": int((df["dqi"] < 40).sum()),
                "low_dqi_patients": int((df["dqi"] < 60).sum())
            },
            "site_patterns": {
                "lowest_dqi_sites": (
                    df.groupby("site_id")["dqi"]
                    .mean()
                    .sort_values()
                    .head(5)
                    .round(2)
                    .to_dict()
                ),
                "highest_dqi_sites": (
                    df.groupby("site_id")["dqi"]
                    .mean()
                    .sort_values(ascending=False)
                    .head(5)
                    .round(2)
                    .to_dict()
                )
            }
        }
        
        prompt = f"""
You are an LLM integrated into a clinical analytics platform.

You are given a SNAPSHOT of pre-computed analytical data.
Answer ONLY based on this snapshot.

SNAPSHOT:
{snapshot}

QUESTION:
{query}

RULES:
- Do not invent metrics
- If the snapshot cannot answer the question, say so
- Be concise and professional
- Format your answer with bullet points when listing items
- Use clear section headers if needed
"""
        
        with st.spinner("🤖 Querying snapshot..."):
            try:
                answer = gemini_call(prompt)
                
                # Store in history
                st.session_state.nlq_history.append({
                    "query": query,
                    "answer": answer,
                    "timestamp": pd.Timestamp.now().strftime("%H:%M:%S")
                })
                
                # Set current answer
                st.session_state.current_answer = answer
                st.session_state.show_answer = True
                
            except Exception as e:
                st.error(f"Error getting response: {str(e)}")
                st.session_state.show_answer = False
    
    # Input field with callback
    query_input = st.text_input(
        "Your question",
        key="nlq_query_input",
        placeholder="e.g., Which sites have the lowest DQI?",
        on_change=handle_ask
    )
    
    # Or use a button with callback
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Ask", key="ask_button", on_click=handle_ask, use_container_width=True):
            pass
    
    # Display current answer if available
    if st.session_state.show_answer and st.session_state.current_answer:
        st.markdown("### 📊 Answer")
        st.markdown(st.session_state.current_answer)
    
    # Display query history
    if st.session_state.nlq_history:
        st.markdown("---")
        st.markdown("### 📜 Query History")
        
        # Show last 5 queries (most recent first)
        for i, item in enumerate(reversed(st.session_state.nlq_history[-5:])):
            query_preview = item['query'][:50] + ("..." if len(item['query']) > 50 else "")
            
            with st.expander(f"Q: {query_preview} ({item['timestamp']})", expanded=(i == 0)):
                st.markdown(f"**Question:** {item['query']}")
                st.markdown("**Answer:**")
                st.markdown(item['answer'])
        
        # Clear history button
        if st.button("Clear History"):
            st.session_state.nlq_history = []
            st.session_state.current_answer = ""
            st.session_state.show_answer = False
            st.rerun()
    else:
        st.info("📝 No query history yet. Ask a question above!")