# Agentic AI additions (Build 1 + Build 2)

Two agents were added on top of the existing grounded GenAI layer. Both keep the
project's core discipline: **every number is computed in Python; the LLM only
narrates.** Model: free Gemini Flash (reused from `ai/gemini_client.py`).

## New files (in `ai/`)
- `agent_tools.py` — deterministic, LLM-free pandas tools over the cleaned
  dataframe (KPIs, worst-site ranking, DQI driver decomposition using the
  learned weights, country/threshold queries). Both agents call these.
- `nlq_agent.py` — **Build 1**: agentic Natural Language Query. Uses google-genai
  automatic function calling: Gemini chooses which tools to call, chains them,
  and answers. Replaces the old fixed-snapshot `nlq_chat.py`. Same entry point
  `nlq_agent_interface(df)`.
- `review_agent.py` — **Build 2**: a LangGraph "Clinical Data Review" agent.
  Graph: compute_kpis -> rank_sites -> [conditional: critical vs routine] ->
  (analyze_drivers) -> synthesize_review -> validate_grounding
  (self-correction loop back to synthesize if it invents a figure) ->
  draft_action_plan -> draft_sponsor_email. Entry point `run_review(df, ...)`.

## Wiring in `app.py` (already applied)
- imports swapped to `nlq_agent_interface` + `run_review`
- AI section now has a 4th tab, "SITE REVIEW AGENT"
- NLQ tab now calls the agentic version

## Setup
1. `pip install -r requirements.txt`  (adds `langgraph`)
2. Rotate your Gemini key (the old one was committed). Copy `.env.example` to
   `.env`, paste the NEW key. `.env` is now gitignored.
3. `streamlit run app.py`

## What is / isn't claimed (for interviews)
- Build 2 driver analysis reports drivers *relative to peers* (rank-valid),
  not absolute DQI points, because the weights define the raw composite that
  `dqi` monotonically rescales.
- Build 2 is a stateful workflow with conditional branching + a grounding
  self-correction loop — not open-ended autonomy. The sponsor email is a DRAFT.
- Build 1 is genuine dynamic tool selection (function calling).
- Free Flash rate-limits under repeated runs; loops are bounded to protect quota.
