"""
nlq_agent.py
------------------------------------------------------------------------------
Build 1: an agentic Natural Language Query interface.

This replaces the old nlq_chat.py approach (answer from a FIXED precomputed
snapshot) with real tool use: Gemini is given a set of typed Python tools that
query the live dataframe on demand, and the SDK's automatic function calling
lets the model decide which tool(s) to call, with what arguments, and chain
them, before composing an answer.

Grounding is preserved exactly as before: the model never computes a number.
Each tool runs deterministic pandas (agent_tools.py) and returns real figures;
the model only picks tools and phrases their results. Because the tools query
the whole frame, questions the old fixed snapshot could not answer
("which sites are below DQI 45 with high patient load?") now work.

This keeps the same public entry point, `nlq_agent_interface(df)`, so app.py
only changes one import line.
------------------------------------------------------------------------------
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from google.genai import types

# Reuse the project's existing client + model (free Flash) and grounding config.
from ai.gemini_client import client, MODEL_NAME
from ai import agent_tools as T

SYSTEM_INSTRUCTION = (
    "You are a clinical data-quality analyst embedded in a dashboard. "
    "Answer questions about the CURRENT filtered dataset ONLY by calling the "
    "provided tools and reporting what they return. You must NEVER invent, "
    "estimate, or infer a number that a tool did not give you. If the tools "
    "cannot answer, say so plainly. Be concise and professional; use bullet "
    "points when listing sites or metrics. DQI is a 0-100 data-quality index; "
    "below 40 is critical, below 60 is low."
)


def _build_tools(df: pd.DataFrame):
    """
    Return a list of plain Python functions bound to the current df. The
    google-genai SDK reads each function's type hints + docstring to build the
    tool schema, calls them automatically when the model requests, and feeds
    results back. Keep each tool narrow and clearly named: models route better
    to several small tools than to one general one.
    """

    def get_portfolio_kpis() -> dict:
        """Overall KPIs for the current view: number of sites and patients,
        average and median DQI, and counts of critical (<40) and low (<60)
        DQI patients."""
        return T.compute_kpis(df)

    def get_worst_sites(n: int = 5) -> list:
        """The n worst sites by severity (DQI shortfall + patient load). Each
        item has site_id, country, avg_dqi, patients, severity."""
        return T.rank_sites(df, n=n)

    def get_sites_below_dqi(threshold: float, n: int = 10) -> list:
        """List up to n sites whose average DQI is below the given threshold,
        worst first. Each item has site_id, avg_dqi, patients."""
        return T.sites_below_dqi(df, threshold=threshold, n=n)

    def explain_site(site_id: str) -> dict:
        """Explain why one site's DQI is low: returns the metrics dragging it
        down most relative to peer sites, with the site value and cohort value
        for each. Use the site_id exactly as returned by other tools."""
        return T.analyze_drivers(df, site_id)

    def get_country_breakdown(n: int = 15) -> list:
        """Per-country average DQI, site count and patient count, worst DQI
        first (up to n countries)."""
        return T.country_summary(df, n=n)

    return [get_portfolio_kpis, get_worst_sites, get_sites_below_dqi,
            explain_site, get_country_breakdown]


def answer_query(df: pd.DataFrame, question: str) -> str:
    """Run one agentic NLQ turn. Returns the model's grounded answer text."""
    if df.empty:
        return "No data available for the selected filters."

    tools = _build_tools(df)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=question,
        config=types.GenerateContentConfig(
            tools=tools,
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0,
            # bound the tool-call loop so a runaway can't drain the free quota
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=6
            ),
        ),
    )
    return response.text or "No answer produced."


def nlq_agent_interface(df: pd.DataFrame):
    """Drop-in replacement for the old nlq_interface(df). Same signature."""
    st.markdown("<h2>💬 Natural Language Query (Agentic)</h2>", unsafe_allow_html=True)
    st.caption("Ask questions; the agent queries the live dataset with tools, "
               "not a fixed snapshot.")

    if "nlq_history" not in st.session_state:
        st.session_state.nlq_history = []

    def handle_ask():
        query = st.session_state.get("nlq_query_input", "").strip()
        if not query:
            return
        with st.spinner("🤖 Agent querying the dataset…"):
            try:
                answer = answer_query(df, query)
            except Exception as e:  # keep the app alive on quota/API errors
                st.error(f"Agent error: {e}")
                return
        st.session_state.nlq_history.append({
            "query": query,
            "answer": answer,
            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
        })

    st.text_input(
        "Your question",
        key="nlq_query_input",
        placeholder="e.g., Which sites are below DQI 45, and what's dragging the worst one down?",
        on_change=handle_ask,
    )
    if st.button("Ask", key="ask_button", on_click=handle_ask, use_container_width=True):
        pass

    if st.session_state.nlq_history:
        latest = st.session_state.nlq_history[-1]
        st.markdown("### 📊 Answer")
        st.markdown(latest["answer"])

        st.markdown("---")
        st.markdown("### 📜 Query History")
        for i, item in enumerate(reversed(st.session_state.nlq_history[-5:])):
            preview = item["query"][:50] + ("…" if len(item["query"]) > 50 else "")
            with st.expander(f"Q: {preview} ({item['timestamp']})", expanded=(i == 0)):
                st.markdown(f"**Question:** {item['query']}")
                st.markdown("**Answer:**")
                st.markdown(item["answer"])
        if st.button("Clear History"):
            st.session_state.nlq_history = []
            st.rerun()
    else:
        st.info("📝 No queries yet. Ask a question above!")
