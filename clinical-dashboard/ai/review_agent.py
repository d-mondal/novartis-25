"""
review_agent.py
------------------------------------------------------------------------------
Build 2: a LangGraph "Clinical Data Review" agent.

Given the current (already filtered) dashboard dataframe and a goal, it runs a
stateful, multi-step workflow with real control flow:

    START
      -> compute_kpis          (deterministic tool)
      -> rank_sites            (deterministic tool: worst sites, severity score)
      -> route_by_severity     (CONDITIONAL edge: critical band or not?)
            critical  -> analyze_drivers  (deterministic: why each site is low)
            routine   -> (skip driver deep-dive)
      -> synthesize_review     (LLM: executive review, numbers from tools only)
      -> validate_grounding    (deterministic: did the LLM invent a figure?)
            not grounded & retries left -> back to synthesize_review (self-correct)
            grounded / out of retries   -> continue
      -> draft_action_plan     (LLM: role-specific Immediate/High/Routine plan)
      -> draft_sponsor_email   (LLM: a DRAFT for a human to send, never auto-sent)
      -> END

Two things make this genuinely agentic rather than a fixed pipeline:
  1. route_by_severity is a conditional edge whose direction depends on the data.
  2. validate_grounding -> synthesize_review is a feedback LOOP: the agent checks
     its own output against the source numbers and regenerates if it hallucinated
     one, up to a bounded number of retries. The model's output changes the
     control flow. That loop is the headline interview talking point.

The LLM only ever narrates figures produced by agent_tools.py. No autonomous
side effects: the email is returned as a draft.
------------------------------------------------------------------------------
"""
from __future__ import annotations

import re
from typing import Any, Optional, TypedDict

import pandas as pd
from langgraph.graph import StateGraph, START, END

from ai import agent_tools as T

# The LLM call. We reuse the project's existing grounded client so the same
# anti-hallucination model config applies. Swap this import for your module path
# when dropping into the repo (e.g. `from ai.gemini_client import gemini_call`).
try:
    from ai.gemini_client import gemini_call
except Exception:  # allows this file to be imported for offline testing
    def gemini_call(prompt: str) -> str:  # pragma: no cover
        raise RuntimeError("gemini_call not wired; inject a real client.")


# ------------------------------------------------------------------ state ----
class ReviewState(TypedDict, total=False):
    # inputs
    df: pd.DataFrame
    goal: str
    n_sites: int
    max_retries: int
    # computed (grounded facts)
    kpis: dict
    ranked_sites: list
    severity_mode: str
    site_drivers: list
    allowed_numbers: list
    # LLM outputs
    review_text: str
    action_plan: str
    sponsor_email: str
    # control
    retry_count: int
    grounding_ok: bool
    validation_notes: str
    llm_failed: bool


# ------------------------------------------------------------------ nodes ----
def node_compute_kpis(state: ReviewState) -> dict:
    return {"kpis": T.compute_kpis(state["df"])}


def node_rank_sites(state: ReviewState) -> dict:
    ranked = T.rank_sites(state["df"], n=state.get("n_sites", 3))
    return {"ranked_sites": ranked}


def route_by_severity(state: ReviewState) -> str:
    """Conditional edge. Critical if any flagged site sits in the <40 band."""
    ranked = state.get("ranked_sites", [])
    critical = any((s.get("avg_dqi") or 100) < T.CRITICAL_DQI for s in ranked)
    return "deep_dive" if critical else "routine"


def node_analyze_drivers(state: ReviewState) -> dict:
    df = state["df"]
    drivers = [T.analyze_drivers(df, s["site_id"]) for s in state.get("ranked_sites", [])]
    return {"site_drivers": drivers, "severity_mode": "critical"}


def node_mark_routine(state: ReviewState) -> dict:
    return {"site_drivers": [], "severity_mode": "routine"}


def _allowed(state: ReviewState) -> list:
    if "allowed_numbers" in state:
        return state["allowed_numbers"]
    allowed = T.collect_allowed_numbers(
        state.get("kpis", {}), state.get("ranked_sites", []), state.get("site_drivers", [])
    )
    return sorted(allowed)


def _is_llm_error(text: str) -> bool:
    """gemini_client.gemini_call returns '[Gemini Error] ...' on API failure."""
    return isinstance(text, str) and text.lstrip().startswith("[Gemini Error]")


def node_synthesize(state: ReviewState) -> dict:
    facts = {
        "goal": state.get("goal"),
        "severity_mode": state.get("severity_mode"),
        "kpis": state.get("kpis"),
        "worst_sites": state.get("ranked_sites"),
        "site_drivers": state.get("site_drivers"),
    }
    correction = ""
    if state.get("validation_notes"):
        correction = (
            "\n\nIMPORTANT CORRECTION: your previous draft used numbers that are "
            f"NOT in the data: {state['validation_notes']}. Rewrite using ONLY the "
            "figures present in FACTS below. Do not introduce any other number."
        )
    prompt = f"""You are a Senior Clinical Trial Data Manager writing a concise
site-monitoring review for the current filtered view of a study portfolio.

FACTS (every number you may use is here; these were computed in Python):
{facts}

Write:
- Executive summary (<= 100 words).
- The 2-3 worst sites, each with the single biggest driver dragging it down
  (use the 'label' fields from site_drivers).
- One line on overall data-quality posture (critical vs routine).

RULES:
- Use ONLY numbers that appear in FACTS. Never invent or estimate a figure.
- If something is not in FACTS, describe it qualitatively instead.
- Professional, specific, no filler.{correction}"""
    out = gemini_call(prompt)
    if _is_llm_error(out):
        # LLM is down (e.g. bad/leaked key). Don't run the grounding loop on an
        # error string; surface a clean message and let the graph finish. The
        # grounded facts already in state (KPIs, drivers) stay valid and render.
        return {
            "review_text": "LLM narration unavailable (check GEMINI_API_KEY). "
                           "The grounded figures below are still valid.",
            "llm_failed": True,
            "grounding_ok": True,
            "retry_count": state.get("retry_count", 0) + 1,
            "allowed_numbers": _allowed(state),
        }
    return {
        "review_text": out,
        "retry_count": state.get("retry_count", 0) + 1,
        "allowed_numbers": _allowed(state),
    }


def node_validate(state: ReviewState) -> dict:
    """Deterministic grounding check: flag numbers in the prose not in FACTS."""
    if state.get("llm_failed"):
        return {"grounding_ok": True, "validation_notes": ""}
    allowed = set(state.get("allowed_numbers") or _allowed(state))
    text = state.get("review_text", "")
    found = re.findall(r"\d+\.?\d*", text.replace(",", ""))
    invented = []
    for tok in found:
        try:
            f = float(tok)
        except ValueError:
            continue
        norm = str(int(f)) if f.is_integer() else str(round(f, 1))
        if norm not in allowed and str(round(f, 2)) not in allowed:
            invented.append(tok)
    invented = sorted(set(invented))
    return {
        "grounding_ok": len(invented) == 0,
        "validation_notes": ", ".join(invented),
    }


def route_validation(state: ReviewState) -> str:
    if state.get("grounding_ok"):
        return "ok"
    if state.get("retry_count", 0) >= state.get("max_retries", 2):
        return "give_up"  # bounded: stop burning quota, pass the last draft on
    return "retry"


def node_action_plan(state: ReviewState) -> dict:
    if state.get("llm_failed"):
        return {"action_plan": ""}
    prompt = f"""You are a Clinical Operations Lead. From this grounded review,
produce a prioritized action plan.

REVIEW:
{state.get('review_text')}

WORST SITES + DRIVERS:
{state.get('site_drivers')}

For each item give: urgency (Immediate / High / Routine), the responsible role
(CRA, DM, Site, Sponsor), and a one-line action. Do not invent metrics."""
    return {"action_plan": gemini_call(prompt)}


def node_draft_email(state: ReviewState) -> dict:
    if state.get("llm_failed"):
        return {"sponsor_email": ""}
    prompt = f"""Draft a short sponsor-facing email (subject + body) summarizing
this site-monitoring review and the immediate actions. This is a DRAFT a human
will review before sending. Do not invent metrics; use only what is below.

REVIEW:
{state.get('review_text')}

ACTION PLAN:
{state.get('action_plan')}"""
    return {"sponsor_email": gemini_call(prompt)}


# ------------------------------------------------------------------ graph ----
def build_graph():
    g = StateGraph(ReviewState)
    g.add_node("compute_kpis", node_compute_kpis)
    g.add_node("rank_sites", node_rank_sites)
    g.add_node("analyze_drivers", node_analyze_drivers)
    g.add_node("mark_routine", node_mark_routine)
    g.add_node("synthesize_review", node_synthesize)
    g.add_node("validate_grounding", node_validate)
    g.add_node("draft_action_plan", node_action_plan)
    g.add_node("draft_sponsor_email", node_draft_email)

    g.add_edge(START, "compute_kpis")
    g.add_edge("compute_kpis", "rank_sites")
    g.add_conditional_edges(
        "rank_sites", route_by_severity,
        {"deep_dive": "analyze_drivers", "routine": "mark_routine"},
    )
    g.add_edge("analyze_drivers", "synthesize_review")
    g.add_edge("mark_routine", "synthesize_review")
    g.add_edge("synthesize_review", "validate_grounding")
    g.add_conditional_edges(
        "validate_grounding", route_validation,
        {"retry": "synthesize_review", "ok": "draft_action_plan", "give_up": "draft_action_plan"},
    )
    g.add_edge("draft_action_plan", "draft_sponsor_email")
    g.add_edge("draft_sponsor_email", END)
    return g.compile()


def run_review(df: pd.DataFrame, goal: str = "Weekly site-monitoring priorities",
               n_sites: int = 3, max_retries: int = 2) -> dict:
    """Entry point for Streamlit / CLI. Returns the final state."""
    graph = build_graph()
    return graph.invoke({
        "df": df, "goal": goal, "n_sites": n_sites,
        "max_retries": max_retries, "retry_count": 0,
    })
