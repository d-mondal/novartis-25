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
import time

import pandas as pd
import streamlit as st
from google.genai import types

# Reuse the project's client + retry primitives (free Flash config, grounding).
from ai.gemini_client import (
    client, MODEL_NAME, _status_code, _retry_delay_seconds, _TRANSIENT,
)
from ai import agent_tools as T

# NLQ uses function calling, which the SDK recommends running through the Chat
# API (not generate_content). Keep it on the same model the app already uses;
# if flash-lite's narration is weak, bump this to a fuller flash model from your
# account (e.g. "models/gemini-2.5-flash") — it's a one-line knob.
NLQ_MODEL = MODEL_NAME


def _guard(fn, *args, **kwargs):
    """Run a tool; on failure print the full traceback to the terminal (so the
    exact failing line is visible) and return a short error to the model instead
    of a bare SDK 'internal error'."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        import sys, traceback
        traceback.print_exc(file=sys.stderr)
        return {"error": f"{type(e).__name__}: {e}"}

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
        return _guard(T.compute_kpis, df)

    def get_worst_sites(n: int = 5) -> list:
        """The n worst sites by severity (DQI shortfall + patient load). Each
        item has site_id, country, avg_dqi, patients, severity."""
        return _guard(T.rank_sites, df, n=int(n))

    def get_sites_below_dqi(threshold: float, n: int = 10) -> list:
        """List up to n sites whose average DQI is below the given threshold,
        worst first. Each item has site_id, avg_dqi, patients."""
        return _guard(T.sites_below_dqi, df, threshold=float(threshold), n=int(n))

    def explain_site(site_id: str) -> dict:
        """Explain why one site's DQI is low: returns the metrics dragging it
        down most relative to peer sites, with the site value and cohort value
        for each. Use the site_id exactly as returned by other tools."""
        return _guard(T.analyze_drivers, df, str(site_id))

    def get_country_breakdown(n: int = 15) -> list:
        """Per-country average DQI, site count and patient count, worst DQI
        first (up to n countries)."""
        return _guard(T.country_summary, df, n=int(n))

    return [get_portfolio_kpis, get_worst_sites, get_sites_below_dqi,
            explain_site, get_country_breakdown]


def _extract_text(resp) -> str | None:
    """Pull text out of a response even when .text is empty (walk the parts)."""
    t = getattr(resp, "text", None)
    if t and t.strip():
        return t.strip()
    try:
        parts = resp.candidates[0].content.parts or []
        joined = "".join((getattr(p, "text", "") or "") for p in parts).strip()
        return joined or None
    except Exception:
        return None


def _salvage_from_history(resp) -> str | None:
    """
    If the model ran the tools but produced no final text (common on small
    models), surface what the tools actually returned so the answer is still
    grounded and non-empty rather than 'No answer produced'.
    """
    try:
        hist = getattr(resp, "automatic_function_calling_history", None) or []
        results = []
        for content in hist:
            for part in getattr(content, "parts", []) or []:
                fr = getattr(part, "function_response", None)
                if fr is not None:
                    results.append((fr.name, dict(fr.response)))
        if results:
            lines = ["_The tools ran and returned this (model narration was empty):_"]
            for name, data in results[-3:]:
                lines.append(f"- **{name}** -> {data}")
            return "\n".join(lines)
    except Exception:
        pass
    return None


def answer_query(df: pd.DataFrame, question: str) -> str:
    """Run one agentic NLQ turn via the Chat API. Returns grounded answer text."""
    if df.empty:
        return "No data available for the selected filters."

    tools = _build_tools(df)
    config = types.GenerateContentConfig(
        tools=tools,
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0,
        http_options=types.HttpOptions(timeout=30000),  # ms; API floor is 10000
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=8
        ),
    )

    last_err = None
    for attempt in range(4):
        try:
            chat = client.chats.create(model=NLQ_MODEL, config=config)
            resp = chat.send_message(question)
            text = _extract_text(resp) or _salvage_from_history(resp)
            return text or "No answer produced (model returned no text and no tool output)."
        except Exception as e:
            last_err = e
            code = _status_code(e)
            if code not in _TRANSIENT or attempt == 3:
                raise
            wait = _retry_delay_seconds(e) or 2.0 * (2 ** attempt)
            time.sleep(min(wait, 30.0) + 0.5)
    raise last_err  # unreachable


def nlq_agent_interface(df: pd.DataFrame):
    """Drop-in replacement for the old nlq_interface(df). Same signature.

    Uses a form (single explicit submit) instead of on_change/on_click callbacks,
    so typing does not trigger reruns and the tab cannot get stuck refreshing.
    The LLM call runs in the main script flow, not a callback.
    """
    st.markdown("<h2>Natural Language Query (Agentic)</h2>", unsafe_allow_html=True)
    st.caption("Ask questions; the agent queries the live dataset with tools, "
               "not a fixed snapshot.")

    if "nlq_history" not in st.session_state:
        st.session_state.nlq_history = []

    with st.form("nlq_form", clear_on_submit=False):
        query = st.text_input(
            "Your question",
            placeholder="e.g., Which sites are below DQI 45, and what's dragging the worst one down?",
        )
        submitted = st.form_submit_button("Ask", use_container_width=True)

    if submitted and query.strip():
        with st.spinner("Agent querying the dataset..."):
            try:
                answer = answer_query(df, query.strip())
            except Exception as e:
                answer = f"Agent error: {e}"
        st.session_state.nlq_history.append({
            "query": query.strip(),
            "answer": answer,
            "timestamp": pd.Timestamp.now().strftime("%H:%M:%S"),
        })

    if st.session_state.nlq_history:
        latest = st.session_state.nlq_history[-1]
        st.markdown("### Answer")
        st.markdown(latest["answer"])

        st.markdown("---")
        st.markdown("### Query History")
        for i, item in enumerate(reversed(st.session_state.nlq_history[-5:])):
            preview = item["query"][:50] + ("..." if len(item["query"]) > 50 else "")
            with st.expander(f"Q: {preview} ({item['timestamp']})", expanded=(i == 0)):
                st.markdown(f"**Question:** {item['query']}")
                st.markdown("**Answer:**")
                st.markdown(item["answer"])
        if st.button("Clear History"):
            st.session_state.nlq_history = []
            st.rerun()
    else:
        st.info("No queries yet. Ask a question above.")