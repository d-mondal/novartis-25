from ai.gemini_client import gemini_call
import pandas as pd


def compute_ai_metrics(df: pd.DataFrame) -> dict:
    """
    Compute compact, AI-oriented diagnostics from FULL filtered data.
    """

    site_summary = (
        df.groupby("site_id")
        .agg(
            avg_dqi=("dqi", "mean"),
            patients=("patient_id", "nunique"),
        )
        .reset_index()
    )

    # ---- Risk Fingerprint (top 5 risky sites) ----
    top_risk = site_summary.sort_values("avg_dqi").head(5)

    risk_fingerprint = []
    for _, row in top_risk.iterrows():
        risk_fingerprint.append({
            "site_id": row["site_id"],
            "low_dqi": row["avg_dqi"] < 50,
            "high_load": row["patients"] >= 3,
            "severity": round(
                (50 - row["avg_dqi"]) + (row["patients"] * 2), 1
            )
        })

    # ---- Confidence Meter (0–100) ----
    critical_pct = (df["dqi"] < 60).mean()
    confidence_score = int(max(0, 100 * (1 - critical_pct)))

    # ---- Action Priority Stack ----
    action_stack = (
        site_summary
        .assign(severity=lambda x: (60 - x["avg_dqi"]) + (x["patients"] * 2))
        .sort_values("severity", ascending=False)
        .head(5)[["site_id", "avg_dqi", "patients", "severity"]]
        .round(2)
        .to_dict(orient="records")
    )

    return {
        "risk_fingerprint": risk_fingerprint,
        "confidence_score": confidence_score,
        "action_stack": action_stack,
        "context": {
            "sites": int(df["site_id"].nunique()),
            "patients": int(df["patient_id"].nunique())
        }
    }


def generate_site_summary(df: pd.DataFrame) -> dict:
    """
    Returns AI diagnostics + Gemini narrative.
    """

    if df.empty:
        return {
            "metrics": {},
            "narrative": "No data available for the selected filters."
        }

    metrics = compute_ai_metrics(df)

    prompt = f"""
You are a Senior Clinical Trial Risk Analyst.

The following diagnostics were COMPUTED IN PYTHON
from the CURRENT FILTERED dashboard view.

DIAGNOSTICS:
{metrics}

===========================
OUTPUT FORMAT (STRICT)
===========================

SECTION A — AI RISK INTELLIGENCE (CONCISE)
• Executive Insight (≤120 words)
• Main Risk Drivers
• Confidence Score Interpretation
• Top Action Priorities (bullet points)

SECTION B — DETAILED ANALYTICAL APPENDIX
1. Overall Site Performance Summary
   - Mention studies, regions, and site-level disparities
2. DQI Insights
   - Critical DQI sites
   - Variability patterns
   - Screening vs Active vs Discontinued risks
3. Emerging Risks
   - Data backlog
   - Discontinued subject risks
   - Early-cycle DQI failures
4. CRA Action Plan
   - Immediate actions (site-specific)
   - Standard actions (cross-site)
5. Sponsor Communication Draft
   - Subject line
   - Clear risk articulation
   - Next steps & timelines

RULES:
- Do NOT invent numbers
- Use metrics provided
- Be specific where possible, general where data is insufficient
- Maintain professional clinical tone
"""


    narrative = gemini_call(prompt)

    return {
        "metrics": metrics,
        "narrative": narrative
    }
