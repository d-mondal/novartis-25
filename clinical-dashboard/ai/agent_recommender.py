from ai.gemini_client import gemini_call
import pandas as pd


def generate_agent_recommendations(df: pd.DataFrame) -> str:
    if df.empty:
        return "No data to evaluate agentic recommendations."

    # -------------------------------
    # CORE SIGNALS (SAFE)
    # -------------------------------
    avg_dqi = df["dqi"].mean()

    # Define alerts as low DQI records
    alert_count = (df["dqi"] < 40).sum()

    # Identify heavy operational load using numeric columns
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    operational_cols = [c for c in numeric_cols if c not in ["dqi"]]

    high_load = False
    if operational_cols:
        load_score = df[operational_cols].sum(axis=1).mean()
        high_load = load_score > df[operational_cols].mean().mean()

    # -------------------------------
    # RULE ENGINE
    # -------------------------------
    rules = []

    if avg_dqi < 60:
        rules.append(
            "Average Data Quality Index is below acceptable threshold, indicating systemic site-level quality risk."
        )

    if alert_count > 0:
        rules.append(
            f"{alert_count} subjects exhibit critically low DQI (<40), requiring immediate corrective action."
        )

    if high_load:
        rules.append(
            "Operational workload indicators are elevated, increasing the likelihood of delayed data entry and unresolved queries."
        )

    if not rules:
        rules.append(
            "No critical operational or data quality risks detected based on current filtered view."
        )

    rule_summary = "\n".join(f"- {r}" for r in rules)

    # -------------------------------
    # LLM ENHANCEMENT
    # -------------------------------
    llm_prompt = f"""
You are a Senior Clinical Operations Lead.

The following rule-based signals were derived from the
CURRENT FILTERED dashboard view:

{rule_summary}

TASK:
- Convert these signals into a prioritized, actionable agent plan
- Assign urgency levels (Immediate / High / Routine)
- Recommend responsible roles (CRA, DM, Site, Sponsor)
- Maintain professional clinical operations tone

Do NOT invent metrics.
"""

    return gemini_call(llm_prompt)
