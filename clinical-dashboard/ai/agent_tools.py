"""
agent_tools.py
------------------------------------------------------------------------------
Deterministic, grounded computations over the CLEANED clinical dataframe
(the same frame app.py builds: columns site_id, patient_id, country,
subject_status, dqi, plus the renamed operational metrics).

There is NO LLM in this file. This is a hard rule: every number the review
agent ever puts in front of a user originates here, in Python. The LangGraph
LLM nodes only route and narrate what these functions return. That is the
whole grounding story, and it is the thing to say out loud in an interview:
"the model never computes a figure, it only phrases figures this module hands it."
------------------------------------------------------------------------------
"""
from __future__ import annotations

import pandas as pd

# DQI driver weights, keyed by the CLEAN column names used in app.py's
# COLUMN_MAP. These are qc_pipeline.CPID_DQI_WEIGHTS re-expressed against the
# renamed columns. Contribution of a metric = value * weight.
#
# HONESTY NOTE (say this if asked): these weights define the *raw* composite
# score (CPID_DQI_SCORE). The `dqi` shown in the app is a monotonic 0-100
# rescaling of that composite, so the *ordering* of drivers is faithful even
# though the absolute contribution units are not on the 0-100 scale. The tool
# therefore reports drivers as "what drags this site relative to its peers",
# a rank-valid statement, not "this many DQI points", which would overclaim.
DQI_DRIVER_WEIGHTS = {
    "crfs_frozen": 0.557811901,
    "crfs_require_sdv": 0.336395948,
    "missing_pages": 0.276865069,
    "field_monitor_queries": 0.258439072,
    "safety_queries": 0.236726864,
    "signs_overdue_90": 0.220676915,
    "crfs_signed": 0.203519043,
    "pds_confirmed": 0.202726625,
    "missing_visits": 0.18317448,
    "esae_safety_reviews": 0.157577803,
    "coded_terms": 0.116207858,
    "pages_entered": 0.098908453,
    "esae_dm_reviews": 0.0889794,
    "crfs_locked": 0.070773304,
    "clinical_queries": 0.064722432,
    "open_edrr_issues": 0.031069942,
    "total_queries": 0.023270543,
    "dm_queries": 0.00917528,
    "crfs_unlocked": -0.006439901,
    "signs_overdue_90_plus": -0.006663069,
    "expected_visits": -0.011812896,
    "broken_signatures": -0.015021751,
    "inactivated_forms": -0.024799977,
    "pds_proposed": -0.08340615,
    "open_lnr_issues": -0.097290657,
    "site_queries": -0.103078974,
    "uncoded_terms": -0.13614252,
    "crfs_not_frozen": -0.175684402,
    "medical_queries": -0.244027659,
    "crfs_never_signed": -0.285693574,
    "signs_overdue_45": -0.297879926,
    "non_conformant_pages": -0.328904988,
    "forms_verified": -0.336508856,
}

# Human-readable labels for the driver columns, for narration.
DRIVER_LABELS = {
    "non_conformant_pages": "pages with non-conformant data",
    "forms_verified": "forms verified (SDV)",
    "signs_overdue_45": "signatures overdue within 45 days",
    "crfs_never_signed": "CRFs never signed",
    "medical_queries": "open medical queries",
    "crfs_not_frozen": "CRFs not frozen",
    "uncoded_terms": "uncoded terms",
    "site_queries": "open site queries",
    "open_lnr_issues": "open lab-name/range issues",
    "missing_pages": "missing pages",
    "missing_visits": "missing visits",
    "field_monitor_queries": "field-monitor queries",
    "safety_queries": "safety queries",
    "crfs_require_sdv": "CRFs awaiting SDV",
    "esae_safety_reviews": "eSAE safety reviews pending",
}

CRITICAL_DQI = 40.0
LOW_DQI = 60.0


def _num(series: pd.Series) -> pd.Series:
    """Coerce to numeric, treat missing as 0 (matches the pipeline's fillna(0))."""
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def compute_kpis(df: pd.DataFrame) -> dict:
    """Portfolio-level KPIs for the current (already filtered) view."""
    if df.empty:
        return {"sites": 0, "patients": 0, "avg_dqi": None, "median_dqi": None,
                "critical_patients": 0, "low_dqi_patients": 0, "countries": 0}
    dqi = _num(df["dqi"])
    return {
        "sites": int(df["site_id"].nunique()),
        "patients": int(df["patient_id"].nunique()),
        "countries": int(df["country"].nunique()) if "country" in df.columns else 0,
        "avg_dqi": round(float(dqi.mean()), 1),
        "median_dqi": round(float(dqi.median()), 1),
        "critical_patients": int((dqi < CRITICAL_DQI).sum()),
        "low_dqi_patients": int((dqi < LOW_DQI).sum()),
    }


def rank_sites(df: pd.DataFrame, n: int = 3) -> list[dict]:
    """
    Rank sites worst-first by a transparent severity score and return the top n.

    severity = DQI shortfall below the 60 target (clipped at 0)
             + 2 points per patient carried (load)
             + 15 bonus if the site is in the critical band (avg DQI < 40)

    All three terms are documented and cheap to defend; nothing is learned or
    hidden. This mirrors the intent of the existing severity heuristics in
    generate_summary.py / app.py, unified into one explainable formula.
    """
    if df.empty:
        return []
    g = (
        df.assign(_dqi=_num(df["dqi"]))
        .groupby("site_id")
        .agg(avg_dqi=("_dqi", "mean"),
             patients=("patient_id", "nunique"),
             country=("country", "first") if "country" in df.columns else ("site_id", "first"))
        .reset_index()
    )
    shortfall = (LOW_DQI - g["avg_dqi"]).clip(lower=0)
    crit_bonus = (g["avg_dqi"] < CRITICAL_DQI).astype(int) * 15
    g["severity"] = (shortfall + g["patients"] * 2 + crit_bonus).round(1)
    g["avg_dqi"] = g["avg_dqi"].round(1)
    g = g.sort_values("severity", ascending=False).head(n)
    return g[["site_id", "country", "avg_dqi", "patients", "severity"]].to_dict("records")


def analyze_drivers(df: pd.DataFrame, site_id, top_k: int = 5) -> dict:
    """
    Explain WHY a site's score is low, relative to the rest of the current view.

    For each driver metric we compute (site mean * weight) minus
    (cohort mean * weight). The most negative deltas are the metrics dragging
    this site below its peers. This is the only place the DQI weights are ever
    exposed to a user, and it is a genuinely new capability the dashboard did
    not have before.
    """
    present = [c for c in DQI_DRIVER_WEIGHTS if c in df.columns]
    site_df = df[df["site_id"] == site_id]
    if site_df.empty or not present:
        return {"site_id": site_id, "avg_dqi": None, "drivers": []}

    drivers = []
    for c in present:
        w = DQI_DRIVER_WEIGHTS[c]
        site_val = float(_num(site_df[c]).mean())
        cohort_val = float(_num(df[c]).mean())
        delta = (site_val - cohort_val) * w
        drivers.append({
            "metric": c,
            "label": DRIVER_LABELS.get(c, c.replace("_", " ")),
            "site_value": round(site_val, 2),
            "cohort_value": round(cohort_val, 2),
            "delta_contribution": round(delta, 3),
        })

    # Most negative delta_contribution first = biggest drag versus peers.
    drivers.sort(key=lambda d: d["delta_contribution"])
    return {
        "site_id": site_id,
        "avg_dqi": round(float(_num(site_df["dqi"]).mean()), 1),
        "patients": int(site_df["patient_id"].nunique()),
        "drivers": drivers[:top_k],
    }


def sites_below_dqi(df: pd.DataFrame, threshold: float, n: int = 10) -> list[dict]:
    """Sites whose average DQI is below `threshold`, worst first (up to n)."""
    if df.empty:
        return []
    g = (
        df.assign(_dqi=_num(df["dqi"]))
        .groupby("site_id")
        .agg(avg_dqi=("_dqi", "mean"), patients=("patient_id", "nunique"))
        .reset_index()
    )
    g = g[g["avg_dqi"] < threshold].sort_values("avg_dqi").head(n)
    g["avg_dqi"] = g["avg_dqi"].round(1)
    return g.to_dict("records")


def country_summary(df: pd.DataFrame, n: int = 15) -> list[dict]:
    """Per-country average DQI and patient counts, worst DQI first (up to n)."""
    if df.empty or "country" not in df.columns:
        return []
    g = (
        df.assign(_dqi=_num(df["dqi"]))
        .groupby("country")
        .agg(avg_dqi=("_dqi", "mean"),
             patients=("patient_id", "nunique"),
             sites=("site_id", "nunique"))
        .reset_index()
        .sort_values("avg_dqi")
        .head(n)
    )
    g["avg_dqi"] = g["avg_dqi"].round(1)
    return g.to_dict("records")


def collect_allowed_numbers(*grounded_objects) -> set[str]:
    """
    Walk any mix of dicts/lists/scalars from the tools above and return the set
    of numeric values that appear, as normalized strings. The grounding-check
    node uses this to catch figures the LLM invented (i.e. numbers in its prose
    that never came from a tool). Heuristic safety net, not a proof.
    """
    allowed: set[str] = set()

    def _add(x):
        try:
            f = float(x)
        except (TypeError, ValueError):
            return
        allowed.add(str(int(f)) if f.is_integer() else str(round(f, 1)))
        allowed.add(str(round(f, 2)))

    def _walk(o):
        if isinstance(o, dict):
            for v in o.values():
                _walk(v)
        elif isinstance(o, (list, tuple, set)):
            for v in o:
                _walk(v)
        elif isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            _add(o)

    for obj in grounded_objects:
        _walk(obj)

    # Structural constants the agent is allowed to say without them being "data":
    for k in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 40, 60, 100]:
        allowed.add(str(k))
    return allowed
