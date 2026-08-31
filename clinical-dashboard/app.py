import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from textwrap import dedent

from ai.generate_summary import generate_site_summary
from ai.agent_recommender import generate_agent_recommendations
from ai.nlq_agent import nlq_agent_interface  # Build 1: function-calling NLQ
from ai.review_agent import run_review           # Build 2: LangGraph review agent

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Clinical Trial Data Quality Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CUSTOM CSS - ENHANCED FOR ENTIRE PAGE
# =========================
st.markdown("""
<style>
    /* ===== GLOBAL STYLES ===== */
            
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
            
    /* Hide Streamlit multipage navigation */
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
            display: none;
        }
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {
    visibility: visible;
    height: 0px;
}

    
    /* ===== SIDEBAR ENHANCEMENT ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a365d 0%, #2d3748 100%) !important;
        border-right: 2px solid #4299e1 !important;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #e2e8f0 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stSlider {
        background-color: #2d3748 !important;
        border-radius: 10px !important;
        padding: 10px !important;
        border: 1px solid #4a5568 !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #4a5568 !important;
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stSlider > div {
        color: #e2e8f0 !important;
    }
    
    /* ===== MAIN CONTENT AREA ===== */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Main headers */
    h1, h2, h3, h4, h5, h6 {
        color: #1a365d !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    
    h1 {
        font-size: 2.8rem !important;
        background: linear-gradient(90deg, #1a365d, #4299e1) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        padding-bottom: 0.5rem !important;
        border-bottom: 3px solid #4299e1 !important;
    }
    
    h2 {
        font-size: 2rem !important;
        color: #2d3748 !important;
        border-left: 4px solid #4299e1 !important;
        padding-left: 1rem !important;
        margin-top: 2rem !important;
    }
    
    h3 {
        font-size: 1.5rem !important;
        color: #4a5568 !important;
    }
    
    /* Paragraph text */
    p, div, span {
        color: #2d3748 !important;
    }
    
    /* ===== KPI CARDS ENHANCEMENT ===== */
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f7fafc 100%) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08) !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.3s ease !important;
        text-align: center !important;
        min-height: 130px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    
    .kpi-card:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 15px 30px rgba(0, 0, 0, 0.12) !important;
        border-color: #4299e1 !important;
    }
    
    .kpi-card h3 {
        color: #718096 !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }
    
    .kpi-card h2 {
        color: #1a365d !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        margin: 0 !important;
        border: none !important;
        padding: 0 !important;
    }
    
    .kpi-card .trend {
        font-size: 0.85rem !important;
        margin-top: 5px !important;
        font-weight: 600 !important;
    }
    
    .kpi-card .trend.up {
        color: #38a169 !important;
    }
    
    .kpi-card .trend.down {
        color: #e53e3e !important;
    }
    
    /* ===== METRIC CARDS ===== */
    .metric-card {
        background: white !important;
        border-radius: 12px !important;
        padding: 15px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e2e8f0 !important;
        margin-bottom: 10px !important;
    }
    
    .metric-card h4 {
        color: #4a5568 !important;
        font-size: 0.9rem !important;
        margin-bottom: 5px !important;
        font-weight: 600 !important;
    }
    
    .metric-card .value {
        color: #1a365d !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    
    .metric-card .progress-bar {
        height: 6px !important;
        background: #e2e8f0 !important;
        border-radius: 3px !important;
        margin-top: 8px !important;
        overflow: hidden !important;
    }
    
    .metric-card .progress-fill {
        height: 100% !important;
        border-radius: 3px !important;
        transition: width 0.5s ease !important;
    }
    
    /* ===== CHART CONTAINERS ===== */
    .chart-container {
        background: white !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e2e8f0 !important;
        margin-bottom: 20px !important;
        height: 100% !important;
    }
    
    /* ===== DATA TABLES ENHANCEMENT ===== */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    .dataframe {
        background-color: white !important;
    }
    
    .dataframe th {
        background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 12px !important;
        border: none !important;
    }
    
    .dataframe td {
        padding: 10px !important;
        border: none !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }
    
    .dataframe tr:nth-child(even) {
        background-color: #f7fafc !important;
    }
    
    .dataframe tr:hover {
        background-color: #ebf8ff !important;
    }
    
    /* ===== SUCCESS/WARNING/ERROR MESSAGES ===== */
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05) !important;
    }
    
    /* ===== BUTTON ENHANCEMENT ===== */
    .stButton > button {
        background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 12px 28px !important;
        border-radius: 10px !important;
        border: none !important;
        font-size: 16px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(66, 153, 225, 0.2) !important;
        margin: 5px 0 !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 15px rgba(66, 153, 225, 0.3) !important;
        background: linear-gradient(135deg, #3182ce 0%, #2b6cb0 100%) !important;
    }
    
    /* ===== TABS ENHANCEMENT ===== */
    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: space-between !important;
        gap: 2px !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 30px 0 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        flex: 1 !important;
        height: 70px !important;
        white-space: nowrap !important;
        background: linear-gradient(135deg, #edf2f7 0%, #e2e8f0 100%) !important;
        border-radius: 12px 12px 0 0 !important;
        padding: 20px 10px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #4a5568 !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
        border: 2px solid #e2e8f0 !important;
        border-bottom: none !important;
        transition: all 0.3s ease !important;
        text-align: center !important;
        margin: 0 2px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%) !important;
        color: white !important;
        border-color: #3182ce !important;
        border-bottom: 3px solid #3182ce !important;
        box-shadow: 0 8px 20px rgba(66, 153, 225, 0.3) !important;
        font-weight: 700 !important;
        position: relative !important;
        z-index: 2 !important;
    }
    
    /* ===== CUSTOM CLASSES FOR CONTENT ===== */
    .content-card {
        background: white !important;
        border-radius: 16px !important;
        padding: 25px !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid #e2e8f0 !important;
        margin: 20px 0 !important;
    }
    
    /* ===== AI PRELOADER ===== */
    .ai-loader {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px;
        font-size: 18px;
        color: #4a5568;
    }
    .ai-loader .emoji {
        font-size: 48px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 0.4; }
        50% { opacity: 1; }
        100% { opacity: 0.4; }
    }
    
    /* ===== STATUS INDICATORS ===== */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-good { background-color: #38a169; }
    .status-warning { background-color: #d69e2e; }
    .status-critical { background-color: #e53e3e; }
    
    /* ===== BADGES ===== */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .badge-success { background-color: #c6f6d5; color: #22543d; }
    .badge-warning { background-color: #feebc8; color: #744210; }
    .badge-danger { background-color: #fed7d7; color: #742a2a; }
    .badge-info { background-color: #bee3f8; color: #2c5282; }
    
    /* ===== HEATMAP STYLING ===== */
    .heatmap-cell {
        padding: 8px;
        text-align: center;
        font-weight: 600;
        border-radius: 4px;
    }
            
.nav-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 30px;
}

/* Navigation button */
.nav-btn {
    display: block;
    padding: 14px 18px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0 !important;
    font-size: 15px;
    font-weight: 600;
    text-decoration: none !important;
    transition: all 0.25s ease;
    border-left: 4px solid transparent;
}

/* Hover */
.nav-btn:hover {
    background: rgba(66, 153, 225, 0.25);
    color: #ffffff !important;
    transform: translateX(6px);
    border-left: 4px solid #4299e1;
}

/* Active page highlight */
.nav-btn.active {
    background: linear-gradient(135deg, #4299e1, #3182ce);
    color: #ffffff !important;
    border-left: 4px solid #90cdf4;
    box-shadow: 0 4px 12px rgba(66, 153, 225, 0.4);
}
</style>
""", unsafe_allow_html=True)

# =========================
# DATA LOADING & CLEANING
# =========================
@st.cache_data(ttl=600)
def load_data():
    BASE_DIR = Path(__file__).parent
    DATA_PATH = BASE_DIR / "data" / "master_dataset.csv"
    QUERIES_PATH = BASE_DIR / "data" / "queries.csv"
    
    # Load main dataset
    if not DATA_PATH.exists():
        st.error(f"Dataset not found at {DATA_PATH}")
        st.stop()
    
    df = pd.read_csv(DATA_PATH, low_memory=False)

    # Standardize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    
    # Column mapping
    COLUMN_MAP = {
        "project_name_|_unnamed:_0_level_1_|_unnamed:_0_level_2_|_responsible_lf_for_action": "study",
        "region_|_unnamed:_1_level_1_|_unnamed:_1_level_2_|_unnamed:_1_level_3": "region",
        "country_|_unnamed:_2_level_1_|_unnamed:_2_level_2_|_unnamed:_2_level_3": "country",
        "site_id_|_unnamed:_3_level_1_|_unnamed:_3_level_2_|_unnamed:_3_level_3": "site_id",
        "subject_id_|_unnamed:_4_level_1_|_unnamed:_4_level_2_|_unnamed:_4_level_3": "patient_id",
        "latest_visit_(sv)_(source:_rave_edc:_bo4)_|_unnamed:_5_level_1_|_unnamed:_5_level_2_|_unnamed:_5_level_3": "latest_visit",
        "subject_status_(source:_primary_form)_|_unnamed:_6_level_1_|_unnamed:_6_level_2_|_unnamed:_6_level_3": "subject_status",
        "input_files_|_missing_visits_|_unnamed:_7_level_2_|_unnamed:_7_level_3": "missing_visits",
        "input_files_|_missing_page_|_unnamed:_8_level_2_|_unnamed:_8_level_3": "missing_pages",
        "input_files_|_#_coded_terms_|_unnamed:_9_level_2_|_unnamed:_9_level_3": "coded_terms",
        "input_files_|_#_uncoded_terms_|_unnamed:_10_level_2_|_unnamed:_10_level_3": "uncoded_terms",
        "input_files_|_#_open_issues_in_lnr_|_unnamed:_11_level_2_|_unnamed:_11_level_3": "open_lnr_issues",
        "input_files_|_#_open_issues_reported_for_3rd_party_reconciliation_in_edrr_|_unnamed:_12_level_2_|_unnamed:_12_level_3": "open_edrr_issues",
        "input_files_|_inactivated_forms_and_folders_|_unnamed:_13_level_2_|_unnamed:_13_level_3": "inactivated_forms",
        "input_files_|_#_esae_dashboard_review_for_dm_|_unnamed:_14_level_2_|_unnamed:_14_level_3": "esae_dm_reviews",
        "input_files_|_#_esae_dashboard_review_for_safety_|_unnamed:_15_level_2_|_unnamed:_15_level_3": "esae_safety_reviews",
        "cpmd_|_visit_status_|_#_expected_visits_(rave_edc_:_bo4)_|_unnamed:_16_level_3": "expected_visits",
        "cpmd_|_page_status_(source:_(rave_edc_:_bo4))_|_#_pages_entered_|_unnamed:_17_level_3": "pages_entered",
        "cpmd_|_page_status_(source:_(rave_edc_:_bo4))_|_#_pages_with_non-conformant_data_|_site/cra": "non_conformant_pages",
        "cpmd_|_page_status_(source:_(rave_edc_:_bo4))_|_#_total_crfs_with_queries_&_non-conformant_data_|_unnamed:_19_level_3": "crfs_with_queries",
        "cpmd_|_page_status_(source:_(rave_edc_:_bo4))_|_#_total_crfs_without_queries_&_non-conformant_data_|_unnamed:_20_level_3": "crfs_without_queries",
        "cpmd_|_page_status_(source:_(rave_edc_:_bo4))_|_%_clean_entered_crf_|_unnamed:_21_level_3": "clean_crf_percent",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_dm_queries_|_dm": "dm_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_clinical_queries_|_cse/cdd": "clinical_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_medical_queries_|_cdmd/medical_lead": "medical_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_site_queries_|_site/cra": "site_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_field_monitor_queries_|_cra": "field_monitor_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_coding_queries_|_coder": "coding_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#_safety_queries_|_safety_team": "safety_queries",
        "cpmd_|_queries_status_(source:(rave_edc_:_bo4))_|_#total_queries_|_unnamed:_29_level_3": "total_queries",
        "cpmd_|_page_action_status_(source:_(rave_edc_:_bo4))_|_#_crfs_require_verification_(sdv)_|_cra": "crfs_require_sdv",
        "cpmd_|_page_action_status_(source:_(rave_edc_:_bo4))_|_#_forms_verified_|_unnamed:_31_level_3": "forms_verified",
        "cpmd_|_page_action_status_(source:_(rave_edc_:_bo4))_|_#_crfs_frozen_|_unnamed:_32_level_3": "crfs_frozen",
        "cpmd_|_page_action_status_(source:_(rave_edc_:_bo4))_|_#_crfs_not_frozen_|_dm": "crfs_not_frozen",
        "cpmd_|_page_action_status_(source:_(rave_edc_:_bo4))_|_#_crfs_locked_|_unnamed:_34_level_3": "crfs_locked",
        "cpmd_|_page_action_status_(source:_(rave_edc_:_bo4))_|_#_crfs_unlocked_|_unnamed:_35_level_3": "crfs_unlocked",
        "cpmd_|_protocol_deviations_(source:(rave_edc_:_bo4))_|_#_pds_confirmed_|_cd_lf": "pds_confirmed",
        "cpmd_|_protocol_deviations_(source:(rave_edc_:_bo4))_|_#_pds_proposed_|_unnamed:_37_level_3": "pds_proposed",
        "ssm_|_pi_signatures_(source:_(rave_edc_:_bo4))_|_#_crfs_signed_|_investigator": "crfs_signed",
        "ssm_|_pi_signatures_(source:_(rave_edc_:_bo4))_|_crfs_overdue_for_signs_within_45_days_of_data_entry_|_unnamed:_39_level_3": "signs_overdue_45",
        "ssm_|_pi_signatures_(source:_(rave_edc_:_bo4))_|_crfs_overdue_for_signs_between_45_to_90_days_of_data_entry_|_unnamed:_40_level_3": "signs_overdue_90",
        "ssm_|_pi_signatures_(source:_(rave_edc_:_bo4))_|_crfs_overdue_for_signs_beyond_90_days_of_data_entry_|_unnamed:_41_level_3": "signs_overdue_90_plus",
        "ssm_|_pi_signatures_(source:_(rave_edc_:_bo4))_|_broken_signatures_|_unnamed:_42_level_3": "broken_signatures",
        "ssm_|_pi_signatures_(source:_(rave_edc_:_bo4))_|_crfs_never_signed_|_unnamed:_43_level_3": "crfs_never_signed",
        "dqi": "dqi"
    }

    # Apply mapping safely
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    
    # Convert numeric columns
    numeric_cols = ['missing_visits', 'missing_pages', 'expected_visits', 'pages_entered', 
                    'non_conformant_pages', 'total_queries', 'dm_queries', 'clinical_queries',
                    'medical_queries', 'site_queries', 'field_monitor_queries', 'coding_queries',
                    'safety_queries', 'crfs_require_sdv', 'forms_verified', 'crfs_frozen',
                    'crfs_not_frozen', 'crfs_locked', 'crfs_unlocked', 'pds_confirmed',
                    'pds_proposed', 'crfs_signed', 'signs_overdue_45', 'signs_overdue_90',
                    'signs_overdue_90_plus', 'broken_signatures', 'crfs_never_signed', 'dqi']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Load queries dataset
    queries_df = None
    if QUERIES_PATH.exists():
        try:
            queries_df = pd.read_csv(QUERIES_PATH)
            
            # Clean column names
            queries_df.columns = queries_df.columns.str.strip()
            
            # Rename columns for consistency
            queries_rename_map = {
                'Subject Name': 'subject_name',
                'Open Queries': 'open_queries',
                'Closed Queries': 'closed_queries',
                'Average Query Close Duration (Days)': 'avg_resolution_days'
            }
            
            for old_col, new_col in queries_rename_map.items():
                if old_col in queries_df.columns:
                    queries_df = queries_df.rename(columns={old_col: new_col})
            
            # Convert to numeric
            if 'open_queries' in queries_df.columns:
                queries_df['open_queries'] = pd.to_numeric(queries_df['open_queries'], errors='coerce')
            if 'closed_queries' in queries_df.columns:
                queries_df['closed_queries'] = pd.to_numeric(queries_df['closed_queries'], errors='coerce')
            if 'avg_resolution_days' in queries_df.columns:
                queries_df['avg_resolution_days'] = pd.to_numeric(queries_df['avg_resolution_days'], errors='coerce')
            
            print(f"Loaded queries dataset with {len(queries_df)} subjects")
            print(f"Total open queries: {queries_df['open_queries'].sum()}")
            print(f"Total closed queries: {queries_df['closed_queries'].sum()}")
            
        except Exception as e:
            st.warning(f"Could not load queries.csv: {e}")
            queries_df = None
    else:
        st.warning(f"Queries dataset not found at {QUERIES_PATH}")
    
    return df, queries_df

# =========================
# CALCULATION FUNCTIONS
# =========================
def calculate_metrics(df, queries_df):
    """Calculate all derived metrics"""
    
    # Patient Clean Status
    df['clean_patient'] = (
    # Completeness
    (df['missing_visits'].fillna(0) == 0) &
    (df['missing_pages'].fillna(0) == 0) &
    
    # Verification: nothing pending
    (df['crfs_require_sdv'].fillna(0) == 0) &
    
    # Signatures: nothing missing or broken
    (df['crfs_never_signed'].fillna(0) == 0) &
    (df['broken_signatures'].fillna(0) == 0) 
    
    
).astype(int)

    
    # Percentages
    df['missing_visits_pct'] = (df['missing_visits'].fillna(0) / df['expected_visits']) * 100
    df['missing_pages_pct'] = (df['missing_pages'].fillna(0) / df['pages_entered']) * 100
    df['non_conformant_pct'] = (df['non_conformant_pages'].fillna(0) / df['pages_entered'].replace(0, 1)) * 100
    total_verified = df['forms_verified'].sum()
    total_sdv_population = (
    df['forms_verified'] + df['crfs_require_sdv']
    ).sum()

    verification_pct = (
    total_verified / total_sdv_population * 100
    if total_sdv_population > 0 else np.nan
)
    df['verification_pct'] = verification_pct


    df['signature_pct'] = (df['crfs_signed'].fillna(0) / (df['crfs_signed'] + df['crfs_never_signed']).replace(0, 1)) * 100
    
    # Query metrics from queries dataset
    if queries_df is not None and 'open_queries' in queries_df.columns and 'closed_queries' in queries_df.columns:
        # Calculate query statistics from queries dataset
        total_open_queries = queries_df['open_queries'].sum()
        total_closed_queries = queries_df['closed_queries'].sum()
        total_queries = total_open_queries + total_closed_queries
        
        # Query resolution rate
        query_resolution_rate = (total_closed_queries / total_queries * 100) if total_queries > 0 else 0
        
        # Average resolution time
        avg_resolution_days = queries_df['avg_resolution_days'].mean() if 'avg_resolution_days' in queries_df.columns else 0
        
        # Add to df for consistency (these will be used in visualizations)
        df['total_queries_from_csv'] = total_queries
        df['open_queries_from_csv'] = total_open_queries
        df['closed_queries_from_csv'] = total_closed_queries
        df['query_resolution_rate'] = query_resolution_rate
        df['avg_resolution_days'] = avg_resolution_days
        
        # Calculate query-related percentages per site (if patient_id can be mapped to site_id)
        # For now, we'll add these as global metrics
        print(f"Query metrics: Open={total_open_queries}, Closed={total_closed_queries}, Rate={query_resolution_rate:.1f}%, Avg Days={avg_resolution_days:.1f}")
    else:
        # Fallback to original calculation if queries dataset not available
        total_queries = df['total_queries'].sum()
        df['query_resolution_rate'] = 100 - (df['total_queries'].fillna(0) / (df['total_queries'] + 10).replace(0, 1)) * 100
        df['avg_resolution_days'] = 0  # Not available in original dataset
    
    # Data readiness score (composite)
    df['data_readiness_score'] = (
        df['clean_crf_percent'].fillna(0) * 0.3 +
        df['query_resolution_rate'].fillna(0) * 0.2 +
        (100 - df['missing_visits_pct'].fillna(0)) * 0.2 +
        df['verification_pct'].fillna(0) * 0.15 +
        df['signature_pct'].fillna(0) * 0.15
    )
    
    return df, queries_df

# =========================
# VISUALIZATION FUNCTIONS
# =========================
def create_gauge_chart(value, title, color_scheme='RdYlGn'):
    """Create a gauge chart for metrics"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 16}},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#2d3748"},
            'bar': {'color': "#3182ce"},
            'steps': [
                {'range': [0, 40], 'color': '#fc8181'},
                {'range': [40, 70], 'color': '#fbd38d'},
                {'range': [70, 100], 'color': '#9ae6b4'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='white',
        font={'color': "#2d3748"}
    )
    
    return fig

def create_heatmap(df, metric_col, title):
    """Create a heatmap of sites vs metrics"""
    heatmap_data = df.groupby('site_id')[metric_col].mean().sort_values(ascending=False).head(20)
    
    fig = go.Figure(data=go.Heatmap(
        z=[heatmap_data.values],
        x=heatmap_data.index,
        y=[''],
        colorscale='RdYlGn_r',
        showscale=True,
        hoverongaps=False,
        text=[heatmap_data.values.round(1)],
        texttemplate='%{text}%',
        textfont={"size": 12, "color": "white"}
    ))
    
    fig.update_layout(
        title=title,
        height=120,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Site ID",
        paper_bgcolor='white'
    )
    
    return fig

def create_query_visualizations(queries_df):
    """Create visualizations from queries dataset"""
    if queries_df is None or queries_df.empty:
        return None, None, None
    
    # 1. Query Status Distribution
    total_open = queries_df['open_queries'].sum() if 'open_queries' in queries_df.columns else 0
    total_closed = queries_df['closed_queries'].sum() if 'closed_queries' in queries_df.columns else 0
    
    status_data = pd.DataFrame({
        'Status': ['Open', 'Closed'],
        'Count': [total_open, total_closed]
    })
    
    fig_status = px.pie(
        status_data,
        names='Status',
        values='Count',
        title='Query Status Distribution',
        color='Status',
        color_discrete_map={'Open': '#e53e3e', 'Closed': '#38a169'},
        hole=0.4
    )
    
    # 2. Top Subjects with Open Queries
    if 'subject_name' in queries_df.columns and 'open_queries' in queries_df.columns:
        top_open = queries_df.nlargest(10, 'open_queries')[['subject_name', 'open_queries']]
        fig_top_open = px.bar(
            top_open,
            x='subject_name',
            y='open_queries',
            title='Top 10 Subjects with Open Queries',
            labels={'subject_name': 'Subject', 'open_queries': 'Open Queries'},
            color='open_queries',
            color_continuous_scale='Reds'
        )
    else:
        fig_top_open = None
    
    # 3. Resolution Time Distribution
    if 'avg_resolution_days' in queries_df.columns:
        resolution_data = queries_df[queries_df['avg_resolution_days'].notna()]
        if not resolution_data.empty:
            fig_resolution = px.histogram(
                resolution_data,
                x='avg_resolution_days',
                title='Query Resolution Time Distribution',
                labels={'avg_resolution_days': 'Resolution Time (Days)'},
                nbins=20
            )
        else:
            fig_resolution = None
    else:
        fig_resolution = None
    
    return fig_status, fig_top_open, fig_resolution

# =========================
# LOAD DATA
# =========================
df_full, queries_df_full = load_data()
df_full, queries_df_full = calculate_metrics(df_full, queries_df_full)
df = df_full.copy()
queries_df = queries_df_full.copy()

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.markdown("""
<div class="nav-container">
    <a href="/" class="nav-btn">📊 Dashboard</a>
    <a href="/Data_Upload" class="nav-btn">Data_Upload</a>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h2 style='color: #e2e8f0;'>🔍 Filters</h2>", unsafe_allow_html=True)

region_sel = st.sidebar.selectbox(
    "Region",
    ["All"] + sorted(df_full["region"].dropna().unique()),
    key="region_filter"
)

country_sel = st.sidebar.selectbox(
    "Country",
    ["All"] + sorted(df_full["country"].dropna().unique()),
    key="country_filter"
)

site_sel = st.sidebar.selectbox(
    "Site",
    ["All"] + sorted(df_full["site_id"].dropna().unique()),
    key="site_filter"
)

patient_sel = st.sidebar.selectbox(
    "Patient",
    ["All"] + sorted(df_full["patient_id"].dropna().unique()),
    key="patient_filter"
)

st.sidebar.markdown("---")

critical_threshold = st.sidebar.slider(
    "Critical DQI Alert Threshold",
    0, 100, 40,
    key="critical_threshold"
)

high_perf_threshold = st.sidebar.slider(
    "High Performing DQI Threshold",
    0, 100, 50,
    key="high_perf_threshold"
)

# =========================
# APPLY FILTERS
# =========================
df = df_full.copy()

if region_sel != "All":
    df = df[df["region"] == region_sel]

if country_sel != "All":
    df = df[df["country"] == country_sel]

if site_sel != "All":
    df = df[df["site_id"] == site_sel]

if patient_sel != "All":
    df = df[df["patient_id"] == patient_sel]

# =========================
# TITLE
# =========================
st.markdown("<h1>📊 Clinical Trial Data Quality Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 1.2rem; color: #4a5568;'>Comprehensive data quality monitoring with advanced analytics</p>", unsafe_allow_html=True)

# =========================
# OVERALL KPI CARDS
# =========================
st.markdown("##  Key Performance Indicators")
col1, col2, col3, col4, col5, col6 = st.columns(6)

total_patients = df['patient_id'].nunique()
clean_patients = df['clean_patient'].sum() if 'clean_patient' in df.columns else 0
clean_patient_pct = (clean_patients / total_patients * 100) if total_patients > 0 else 0

# Get query metrics from queries dataset
if queries_df is not None:
    total_open_queries = queries_df['open_queries'].sum() if 'open_queries' in queries_df.columns else 0
    total_closed_queries = queries_df['closed_queries'].sum() if 'closed_queries' in queries_df.columns else 0
    total_queries = total_open_queries + total_closed_queries
    query_resolution_rate = (total_closed_queries / total_queries * 100) if total_queries > 0 else 0
    avg_resolution_days = queries_df['avg_resolution_days'].mean() if 'avg_resolution_days' in queries_df.columns else 0
else:
    total_queries = 0
    total_open_queries = 0
    query_resolution_rate = 0
    avg_resolution_days = 0

col1.markdown(
    f"""<div class='kpi-card'>
        <h3>Sites</h3>
        <h2>{df['site_id'].nunique():,}</h2>
    </div>""",
    unsafe_allow_html=True
)

col2.markdown(
    f"""<div class='kpi-card'>
        <h3>Patients</h3>
        <h2>{total_patients:,}</h2>
    </div>""",
    unsafe_allow_html=True
)

col3.markdown(
    f"""<div class='kpi-card'>
        <h3>Clean Patients</h3>
        <h2>{clean_patients:,}</h2>
        <div class='trend {"up" if clean_patient_pct > 50 else "down"}'>
            {clean_patient_pct:.1f}% clean
        </div>
    </div>""",
    unsafe_allow_html=True
)

col4.markdown(
    f"""<div class='kpi-card'>
        <h3>Avg DQI</h3>
        <h2>{df['dqi'].mean():.1f}</h2>
        <div class='trend {"up" if df['dqi'].mean() > 60 else "down"}'>
            {df['dqi'].mean() - 60:+.1f} vs target
        </div>
    </div>""",
    unsafe_allow_html=True
)

col5.markdown(
    f"""<div class='kpi-card'>
        <h3>Open Queries</h3>
        <h2>{total_open_queries:,}</h2>
        <div class='trend {"down" if total_open_queries > 0 else "up"}'>
            {total_closed_queries:,} closed
        </div>
    </div>""",
    unsafe_allow_html=True
)

col6.markdown(
    f"""<div class='kpi-card'>
        <h3>Query Resolution</h3>
        <h2>{query_resolution_rate:.1f}%</h2>
        <div class='trend {"up" if avg_resolution_days < 10 else "down"}'>
            Avg {avg_resolution_days:.1f} days
        </div>
    </div>""",
    unsafe_allow_html=True
)


# =========================
# 🌍 WORLD MAP (KEEPING ORIGINAL)
# =========================
st.markdown("## 🌍 Global Data Quality Overview")

map_df = (
    df.groupby("country")
    .agg(avg_dqi=("dqi", "mean"))
    .reset_index()
)

def dqi_band(score, critical_threshold, high_perf_threshold):
    if score >= high_perf_threshold:
        return "High Performing"
    elif score >= critical_threshold:
        return "Average"
    else:
        return "Critical"

map_df["DQI Level"] = map_df["avg_dqi"].apply(
    lambda x: dqi_band(x, critical_threshold, high_perf_threshold)
)

fig_map = px.choropleth(
    map_df,
    locations="country",
    locationmode="ISO-3",
    color="DQI Level",
    hover_name="country",
    hover_data={"avg_dqi": ":.1f"},
    color_discrete_map={
        "High Performing": "#38a169",
        "Average": "#d69e2e",
        "Critical": "#e53e3e"
    },
    title="Global DQI Distribution"
)

fig_map.update_layout(
    template="plotly_white",
    height=500,
    margin=dict(l=0, r=0, t=50, b=0),
    plot_bgcolor="white",
    paper_bgcolor="white",
    title_font=dict(size=20, color="#1a365d"),
    legend=dict(
        font=dict(color="#4a5568"),
        title_font=dict(color="#2d3748"),
        bgcolor="white",
        bordercolor="#e2e8f0",
        borderwidth=1
    ),
    geo=dict(
        bgcolor="white",
        lakecolor="white",
        landcolor="#f7fafc",
        subunitcolor="#e2e8f0"
    )
)

st.plotly_chart(fig_map, use_container_width=True)

# =========================
# DATA QUALITY METRICS SECTION
# =========================
st.markdown("##  Data Quality Metrics")

# Row 1: Gauge Charts
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.plotly_chart(create_gauge_chart(
        df['clean_crf_percent'].mean(),
        "Clean CRF %"
    ), use_container_width=True)

with col2:
    st.plotly_chart(create_gauge_chart(
        df['query_resolution_rate'].mean() if 'query_resolution_rate' in df.columns else 0,
        "Query Resolution %"
    ), use_container_width=True)

with col3:
    st.plotly_chart(create_gauge_chart(
        100 - df['missing_visits_pct'].mean(),
        "Visit Completeness %"
    ), use_container_width=True)

with col4:
    st.plotly_chart(create_gauge_chart(
        df['verification_pct'].mean(),
        "Verification %"
    ), use_container_width=True)

# =========================
# ISSUE ANALYSIS SECTION - UPDATED WITH QUERIES DATASET
# =========================
st.markdown("##🔍 Issue Analysis")

tab1, tab2, tab3, tab4 = st.tabs(["Missing Data", "Query Analysis", "Protocol Deviations", "Query Resolution Time"])

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(dedent("""
        <div class="chart-container">
            <h3> Sites with Most Missing Visits</h3>
        """), unsafe_allow_html=True)

        missing_visits_by_site = (
            df.groupby('site_id')['missing_visits']
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        fig = px.bar(
            x=missing_visits_by_site.index,
            y=missing_visits_by_site.values,
            labels={'x': 'Site ID', 'y': 'Missing Visits'},
            color=missing_visits_by_site.values,
            color_continuous_scale='Reds'
        )
        fig.update_layout(showlegend=False, height=300)

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(dedent("""
        <div class="chart-container">
            <h3> Sites with Most Missing Pages</h3>
        """), unsafe_allow_html=True)

        missing_pages_by_site = (
            df.groupby('site_id')['missing_pages']
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        fig = px.bar(
            x=missing_pages_by_site.index,
            y=missing_pages_by_site.values,
            labels={'x': 'Site ID', 'y': 'Missing Pages'},
            color=missing_pages_by_site.values,
            color_continuous_scale='Oranges'
        )
        fig.update_layout(showlegend=False, height=300)

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    if queries_df is not None and not queries_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(dedent("""
            <div class="chart-container">
                <h3> Query Status Distribution</h3>
            """), unsafe_allow_html=True)

            total_open = queries_df['open_queries'].sum() if 'open_queries' in queries_df.columns else 0
            total_closed = queries_df['closed_queries'].sum() if 'closed_queries' in queries_df.columns else 0
            
            status_data = pd.DataFrame({
                'Status': ['Open', 'Closed'],
                'Count': [total_open, total_closed]
            })

            fig = px.pie(
                status_data,
                names='Status',
                values='Count',
                color='Status',
                color_discrete_map={'Open': '#e53e3e', 'Closed': '#38a169'},
                hole=0.4
            )
            fig.update_layout(height=350)

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown(dedent("""
            <div class="chart-container">
                <h3> Top Subjects with Open Queries</h3>
            """), unsafe_allow_html=True)

            if 'subject_name' in queries_df.columns and 'open_queries' in queries_df.columns:
                top_open = queries_df.nlargest(10, 'open_queries')[['subject_name', 'open_queries']]
                
                fig = px.bar(
                    top_open,
                    x='subject_name',
                    y='open_queries',
                    labels={'subject_name': 'Subject', 'open_queries': 'Open Queries'},
                    color='open_queries',
                    color_continuous_scale='Reds'
                )
                fig.update_layout(showlegend=False, height=300, xaxis_tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Subject name or open queries data not available in queries dataset")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No query data available. Please ensure queries.csv is in the data folder.")

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(dedent("""
        <div class="chart-container">
            <h3>⚠️ Protocol Deviations by Site</h3>
        """), unsafe_allow_html=True)

        pds_by_site = (
            df.groupby('site_id')['pds_confirmed']
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        fig = px.bar(
            x=pds_by_site.index,
            y=pds_by_site.values,
            labels={'x': 'Site ID', 'y': 'Confirmed PDs'},
            color=pds_by_site.values,
            color_continuous_scale='Reds'
        )
        fig.update_layout(showlegend=False, height=300)

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    if queries_df is not None and 'avg_resolution_days' in queries_df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(dedent("""
            <div class="chart-container">
                <h3> Query Resolution Time Distribution</h3>
            """), unsafe_allow_html=True)

            resolution_data = queries_df[queries_df['avg_resolution_days'].notna()]
            
            if not resolution_data.empty:
                fig = px.histogram(
                    resolution_data,
                    x='avg_resolution_days',
                    labels={'avg_resolution_days': 'Resolution Time (Days)'},
                    nbins=20,
                    color_discrete_sequence=['#3182ce']
                )
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No resolution time data available")

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown(dedent("""
            <div class="chart-container">
                <h3> Resolution Time Statistics</h3>
            """), unsafe_allow_html=True)

            if not resolution_data.empty:
                avg_days = resolution_data['avg_resolution_days'].mean()
                median_days = resolution_data['avg_resolution_days'].median()
                std_days = resolution_data['avg_resolution_days'].std()
                min_days = resolution_data['avg_resolution_days'].min()
                max_days = resolution_data['avg_resolution_days'].max()
                
                stats_html = f"""
                <div style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>Average:</span>
                        <span style="font-weight: bold; color: #3182ce;">{avg_days:.1f} days</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>Median:</span>
                        <span style="font-weight: bold; color: #3182ce;">{median_days:.1f} days</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>Fastest:</span>
                        <span style="font-weight: bold; color: #38a169;">{min_days:.1f} days</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>Slowest:</span>
                        <span style="font-weight: bold; color: #e53e3e;">{max_days:.1f} days</span>
                    </div>
                </div>
                """
                st.markdown(stats_html, unsafe_allow_html=True)
            else:
                st.info("No resolution time statistics available")

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No resolution time data available in queries dataset")

# =========================
# SITE PERFORMANCE HEATMAPS
# =========================
st.markdown("##  Site Performance Heatmaps")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        <div class="chart-container">
            <h3>Clean CRF Percentage by Site</h3>
        """,
        unsafe_allow_html=True
    )
    st.plotly_chart(
        create_heatmap(df, 'clean_crf_percent', ''),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        """
        <div class="chart-container">
            <h3>✅ Data Readiness Score by Site</h3>
        """,
        unsafe_allow_html=True
    )
    st.plotly_chart(
        create_heatmap(df, 'data_readiness_score', ''),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# CRITICAL ALERTS SECTION - UPDATED WITH QUERY METRICS
# =========================
st.markdown("##  Critical Alerts & Immediate Attention")

# Calculate critical metrics
site_summary = df.groupby('site_id').agg({
    'dqi': 'mean',
    'region': 'first',
    'missing_visits': 'sum',
    'missing_pages': 'sum',
    'pds_confirmed': 'sum',
    'clean_patient': 'sum',
    'patient_id': 'nunique'
}).reset_index()

site_summary['clean_patient_pct'] = (site_summary['clean_patient'] / site_summary['patient_id']) * 100

# Add query metrics if available
if queries_df is not None:
    # Note: This is a simplified approach. In a real scenario, you'd need to map subjects to sites
    # For now, we'll add average query metrics per site
    site_summary['open_queries'] = total_open_queries / len(site_summary)  # Simplified distribution
    site_summary['closed_queries'] = total_closed_queries / len(site_summary)  # Simplified distribution
    site_summary['avg_resolution_days'] = avg_resolution_days  # Same for all sites
else:
    site_summary['open_queries'] = 0
    site_summary['closed_queries'] = 0
    site_summary['avg_resolution_days'] = 0

# Create a better priority score including query metrics
def calculate_priority_score(row):
    score = 0
    
    # DQI score (0-100, lower is worse)
    if row['dqi'] < 20: score += 40
    elif row['dqi'] < 40: score += 30
    elif row['dqi'] < 60: score += 20
    
    # Clean patient percentage
    if pd.notna(row['clean_patient_pct']):
        if row['clean_patient_pct'] < 20: score += 30
        elif row['clean_patient_pct'] < 50: score += 20
        elif row['clean_patient_pct'] < 80: score += 10
    
    # Open queries
    if pd.notna(row['open_queries']):
        if row['open_queries'] > 10: score += 20
        elif row['open_queries'] > 5: score += 15
        elif row['open_queries'] > 2: score += 10
    
    # Missing visits
    if pd.notna(row['missing_visits']):
        if row['missing_visits'] > 20: score += 10
    
    # Resolution time
    if pd.notna(row['avg_resolution_days']):
        if row['avg_resolution_days'] > 20: score += 15
        elif row['avg_resolution_days'] > 10: score += 10
    
    return score

site_summary['priority_score'] = site_summary.apply(calculate_priority_score, axis=1)

# Categorize priority
def categorize_priority(score):
    if score >= 60:
        return "🔴 Critical", "#feb2b2"
    elif score >= 40:
        return "🟠 High", "#fbd38d"
    elif score >= 20:
        return "🟡 Medium", "#fefcbf"
    else:
        return "🟢 Low", "#c6f6d5"

site_summary['priority_info'] = site_summary['priority_score'].apply(
    lambda x: categorize_priority(x)
)
site_summary['priority'] = site_summary['priority_info'].apply(lambda x: x[0])
site_summary['priority_color'] = site_summary['priority_info'].apply(lambda x: x[1])

# Determine DQI status
site_summary['dqi_status'] = site_summary['dqi'].apply(
    lambda x: ("🔴 Critical", "#e53e3e") if x < 40 else 
              ("🟠 Warning", "#d69e2e") if x < 60 else 
              ("🟢 Good", "#38a169")
)
site_summary['dqi_status_text'] = site_summary['dqi_status'].apply(lambda x: x[0])
site_summary['dqi_color'] = site_summary['dqi_status'].apply(lambda x: x[1])

# Top 10 sites needing attention
critical_sites = site_summary.sort_values(
    ['priority_score', 'dqi', 'open_queries', 'missing_visits'], 
    ascending=[False, True, False, False]
).head(10)

# Display using Streamlit's metric cards
#st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("### ⚠️ Sites Requiring Immediate Attention")

# Create a simpler table view
show_n = st.selectbox(
    "Show sites",
    options=[5, 10, 15, "All"],
    index=0
)

if show_n == "All":
    sites_to_show = critical_sites
else:
    sites_to_show = critical_sites.head(show_n)

for _, site in sites_to_show.iterrows():    
    col1, col2, col3, col4,col5 = st.columns([2, 2, 2, 2,2])
    
    with col1:
        st.metric(
            label=f"Site {site['site_id']}",
            value=f"DQI: {site['dqi']:.1f}",
            delta="Critical" if site['dqi'] < 40 else "Warning" if site['dqi'] < 60 else "Good",
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
        label="Region",
        value=site['region'],
        delta_color="off"
    )
    with col3:
        clean_pct = f"{site['clean_patient_pct']:.1f}%" if pd.notna(site['clean_patient_pct']) else "N/A"
        st.metric(
            label="Clean Patients",
            value=clean_pct,
            delta_color="off")
        
    
    with col4:
        open_queries_val = int(site['open_queries']) if pd.notna(site['open_queries']) else 0
        st.metric(
            label="Open Queries",
            value=open_queries_val,
            delta_color="off"
        )
    
    with col5:
        # Create a colored priority badge
        priority_text, priority_color = categorize_priority(site['priority_score'])
        st.markdown(f"""
        <div style='background-color: {priority_color}; 
                    padding: 10px; 
                    border-radius: 8px; 
                    text-align: center;
                    font-weight: bold;
                    color: #2d3748;'>
            {priority_text}
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# DATA READINESS FOR ANALYSIS - UPDATED WITH QUERY METRICS
# =========================
st.markdown("##  Data Readiness for Statistical Analysis")

col1, col2, col3 = st.columns(3)

with col1:
    #st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("### 🔬 Interim Analysis Readiness")
    
    # Calculate readiness score with query metrics
    try:
        readiness_score = (
            (df['clean_crf_percent'].mean() * 0.25) +
            (100 - df['missing_visits_pct'].mean() * 0.2) +
            (df['verification_pct'].mean() * 0.2) +
            (df['signature_pct'].mean() * 0.15) +
            (df['query_resolution_rate'].mean() * 0.2)  # Increased weight for query resolution
        )
    except:
        readiness_score = 0
    
    readiness_level = "✅ Ready" if readiness_score > 80 else "⚠️ Needs Work" if readiness_score > 60 else "❌ Not Ready"
    readiness_color = "#38a169" if readiness_score > 80 else "#d69e2e" if readiness_score > 60 else "#e53e3e"
    display_score = readiness_score-100

    
    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <div style="font-size: 3rem; font-weight: 800; color: {readiness_color}; margin-bottom: 10px;">
            {display_score:.1f}%
        </div>
        <div style="font-size: 1.2rem; color: #4a5568; margin-bottom: 20px;">
            {readiness_level}
        </div>
        <div style="font-size: 0.9rem; color: #718096;">
            Based on CRF cleanliness, verification, and query resolution
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
   # st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("###  Submission Readiness Checklist")
    
    # Define checklist with query metrics
    checklist_items = []
    
    # Check each condition with try-except
    try:
        checklist_items.append(("CRF Cleanliness > 85%", df['clean_crf_percent'].mean() > 85))
    except:
        checklist_items.append(("CRF Cleanliness > 85%", False))
    
    try:
        checklist_items.append(("Missing Visits < 5%", df['missing_visits_pct'].mean() < 5))
    except:
        checklist_items.append(("Missing Visits < 5%", False))
    
    try:
        checklist_items.append(("Verification > 90%", df['verification_pct'].mean() > 90))
    except:
        checklist_items.append(("Verification > 90%", False))
    
    try:
        checklist_items.append(("Signatures > 95%", df['signature_pct'].mean() > 95))
    except:
        checklist_items.append(("Signatures > 95%", False))
    
    try:
        checklist_items.append(("Query Resolution > 80%", df['query_resolution_rate'].mean() > 80))
    except:
        checklist_items.append(("Query Resolution > 80%", False))
    
    try:
        checklist_items.append(("Avg Resolution Time < 10 days", avg_resolution_days < 10))
    except:
        checklist_items.append(("Avg Resolution Time < 10 days", False))
    
    try:
        checklist_items.append(("PDs Resolved", df['pds_confirmed'].mean() > 0))
    except:
        checklist_items.append(("PDs Resolved", False))
    
    checklist_html = ""
    for item, status in checklist_items:
        icon = "✅" if status else "❌"
        color = "#38a169" if status else "#e53e3e"
        checklist_html += f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px; padding: 8px; background-color: {'#f0fff4' if status else '#fff5f5'}; border-radius: 8px;">
            <span style="font-size: 1.2rem; margin-right: 10px; color: {color};">{icon}</span>
            <span style="color: #2d3748;">{item}</span>
        </div>
        """
    
    st.markdown(checklist_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
   # st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("###  Current Data Snapshot")
    
    # Calculate snapshot data including query metrics
    total_patients = df['patient_id'].nunique()
    clean_patients = df['clean_patient'].sum() if 'clean_patient' in df.columns else 0
    
    snapshot_data = [
        ("Total Sites", df['site_id'].nunique()),
        ("Total Patients", total_patients),
        ("Clean Patients", clean_patients),
        ("Open Queries", int(total_open_queries)),
        ("Closed Queries", int(total_closed_queries)),
        ("Avg Resolution Time", f"{avg_resolution_days:.1f} days"),
        ("Missing Visits", int(df['missing_visits'].sum())),
        ("Protocol Deviations", int(df['pds_confirmed'].sum()))
    ]
    
    snapshot_html = ""
    for label, value in snapshot_data:
        snapshot_html += f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0;">
            <span style="color: #4a5568; font-weight: 500;">{label}</span>
            <span style="color: #1a365d; font-weight: 700; font-size: 1.1rem;">{value}</span>
        </div>
        """
    
    st.markdown(snapshot_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
#  AI TOOLS SECTION (KEEPING ORIGINAL)
# =========================
st.markdown("## AI Tools")

# Create beautifully styled tabs
ai_tab1, ai_tab2, ai_tab3, ai_tab4 = st.tabs([
    " SITE SUMMARY", 
    " AGENT RECOMMENDATIONS", 
    " NATURAL LANGUAGE QUERY",
    " SITE REVIEW AGENT"
])

# Use the currently filtered DataFrame
drill_df = df.copy()

# Tab 1: Site Summary (keeping original)
with ai_tab1:
    st.markdown("### AI-Powered Site Summary Generator")
    st.markdown("<p style='color: #4a5568; font-size: 16px;'>Generate comprehensive site performance analysis with risk intelligence and actionable insights.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(" Generate Site Summary", key="gen_site_summary", use_container_width=True):
            try:
                placeholder = st.empty()
                with placeholder.container():
                    st.markdown("""
                    <div class="ai-loader">
                        <div class="emoji">⏳</div>
                        <b>Generating AI Site Summary…</b>
                        <div style="font-size:14px;">Analyzing risks, trends & actions</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with st.spinner("Processing…"):
                    result = generate_site_summary(drill_df)
                
                placeholder.empty()
                
                # Display results
                st.markdown('<div class="content-card">', unsafe_allow_html=True)
                st.markdown("##  Executive Summary")
                
                if isinstance(result, dict) and "narrative" in result:
                    narrative = result["narrative"]
                    if "SECTION A" in narrative and "SECTION B" in narrative:
                        sections = narrative.split("SECTION B")
                        exec_summary = sections[0].replace("SECTION A — AI RISK INTELLIGENCE (CONCISE)", "").strip()
                        details = "SECTION B" + sections[1] if len(sections) > 1 else ""
                        
                        with st.expander(" View Executive Summary", expanded=True):
                            exec_summary = exec_summary.replace("Executive Insight (≤120 words)", "**Key Insights**")
                            st.markdown(exec_summary)
                        
                        if details:
                            with st.expander(" View Detailed Analysis", expanded=False):
                                st.markdown(details)
                    else:
                        st.markdown("### Key Insights")
                        st.write(narrative)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # =====================================================
                # 📊 CONFIDENCE METER & RISK FINGERPRINT
                # =====================================================
                if isinstance(result, dict) and "metrics" in result:
                    metrics = result["metrics"]
                    
                    # ---- Confidence Meter ----
                    if "confidence_score" in metrics:
                        st.markdown('<div class="content-card">', unsafe_allow_html=True)
                        st.markdown("### 📊 Data Readiness Confidence")
                        confidence = metrics["confidence_score"]
                        
                        # Color code based on confidence
                        if confidence >= 70:
                            color = "green"
                        elif confidence >= 40:
                            color = "orange"
                        else:
                            color = "red"
                        
                        st.markdown(f"""
                        <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border-left:5px solid {color}; border: 1px solid #e2e8f0;">
                            <h4 style="margin:0; color:#2d3748;">Confidence Score: <span style="color:{color}; font-weight:bold;">{confidence}%</span></h4>
                            <div style="width:100%; background-color:#e2e8f0; border-radius:5px; margin-top:10px;">
                                <div style="width:{confidence}%; background-color:{color}; height:20px; border-radius:5px;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Interpretation
                        if confidence < 40:
                            st.warning("⚠️ Low confidence score indicates need for manual validation and deeper analysis.")
                        elif confidence < 70:
                            st.info("ℹ️ Moderate confidence score - some areas may need attention.")
                        else:
                            st.success("✅ High confidence score - data is reliable for analysis.")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # ---- Risk Fingerprint ----
                    if "risk_fingerprint" in metrics and metrics["risk_fingerprint"]:
                        st.markdown('<div class="content-card">', unsafe_allow_html=True)
                        st.markdown("### 🔎 Risk Fingerprint (Top Sites)")
                        rf_df = pd.DataFrame(metrics["risk_fingerprint"])
                        
                        if not rf_df.empty and "site_id" in rf_df.columns:
                            # Create a formatted table
                            display_df = rf_df.copy()
                            
                            # Add risk indicators
                            if "low_dqi" in display_df.columns:
                                display_df["DQI Status"] = display_df["low_dqi"].apply(
                                    lambda x: "🔴 Critical" if x else "🟢 Good"
                                )
                            
                            if "high_load" in display_df.columns:
                                display_df["Load Status"] = display_df["high_load"].apply(
                                    lambda x: "🔴 High" if x else "🟢 Normal"
                                )
                            
                            # Select and rename columns for display
                            display_cols = ["site_id"]
                            rename_map = {"site_id": "Site ID"}
                            
                            if "DQI Status" in display_df.columns:
                                display_cols.append("DQI Status")
                                rename_map["DQI Status"] = "DQI Status"
                            
                            if "Load Status" in display_df.columns:
                                display_cols.append("Load Status")
                                rename_map["Load Status"] = "Load Status"
                            
                            if "severity" in display_df.columns:
                                display_cols.append("severity")
                                rename_map["severity"] = "Severity Score"
                            
                            # Display table with custom styling
                            st.dataframe(
                                display_df[display_cols].rename(columns=rename_map),
                                use_container_width=True,
                                height=250
                            )
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # ---- Action Priority Stack ----
                    if "action_stack" in metrics and metrics["action_stack"]:
                        st.markdown('<div class="content-card">', unsafe_allow_html=True)
                        st.markdown("### 🚨 Action Priority (Next 7 Days)")
                        
                        for i, item in enumerate(metrics["action_stack"][:5], start=1):  # Show top 5
                            if isinstance(item, dict):
                                # Create a card for each action item
                                with st.container():
                                    cols = st.columns([1, 4])
                                    with cols[0]:
                                        st.markdown(f"<h3 style='text-align: center; color: #4299e1;'>#{i}</h3>", unsafe_allow_html=True)
                                    with cols[1]:
                                        details = []
                                        if "site_id" in item:
                                            details.append(f"**Site:** {item['site_id']}")
                                        if "avg_dqi" in item:
                                            # Color code DQI
                                            dqi = item['avg_dqi']
                                            color = "#e53e3e" if dqi < 40 else "#d69e2e" if dqi < 60 else "#38a169"
                                            details.append(f"**DQI:** <span style='color:{color}; font-weight:bold;'>{dqi:.1f}</span>")
                                        if "patients" in item:
                                            details.append(f"**Patients:** {item['patients']}")
                                        if "severity" in item:
                                            # Color code severity
                                            severity = item['severity']
                                            severity_color = "#e53e3e" if severity > 7 else "#d69e2e" if severity > 4 else "#38a169"
                                            details.append(f"**Severity:** <span style='color:{severity_color}; font-weight:bold;'>{severity:.1f}/10</span>")
                                        
                                        st.markdown(" • ".join(details), unsafe_allow_html=True)
                                        
                                        # Action description if available
                                        if "action" in item:
                                            st.markdown(f"**Action:** {item['action']}")
                                        
                                    st.markdown("---")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                
                # =====================================================
                # 📋 OVERALL SITE PERFORMANCE SUMMARY
                # =====================================================
                st.markdown('<div class="content-card">', unsafe_allow_html=True)
                st.markdown("## 📋 Overall Site Performance Summary")
                
                # Check if required columns exist
                required_cols = ["site_id", "patient_id", "dqi"]
                missing_cols = [col for col in required_cols if col not in drill_df.columns]
                
                if missing_cols:
                    st.warning(f"Missing columns: {missing_cols}. Cannot generate site performance summary.")
                else:
                    # Group by site
                    agg_dict = {
                        "total_subjects": ("patient_id", "nunique"),
                        "avg_dqi": ("dqi", "mean"),
                    }
                    
                    # Add subject_status if it exists
                    if "subject_status" in drill_df.columns:
                        agg_dict["active_subjects"] = ("subject_status", lambda x: (x == "On Trial").sum())
                        agg_dict["screen_failures"] = ("subject_status", lambda x: (x == "Screen Failure").sum())
                    
                    site_perf = (
                        drill_df.groupby("site_id")
                        .agg(**agg_dict)
                        .reset_index()
                        .round(1)
                    )
                    
                    # Function to determine observation
                    def site_observation(row):
                        if row["avg_dqi"] < 40:
                            return "🔴 Critical DQI Risk"
                        elif "screen_failures" in row and row["screen_failures"] > row["total_subjects"] / 2:
                            return "🟠 High Screen Failure Rate"
                        elif row["avg_dqi"] < 60:
                            return "🟡 Needs Attention"
                        else:
                            return "🟢 Good Performance"
                    
                    site_perf["Status"] = site_perf.apply(site_observation, axis=1)
                    
                    # Rename columns
                    rename_dict = {
                        "site_id": "Site ID",
                        "total_subjects": "Total Subjects",
                        "avg_dqi": "Avg DQI",
                        "Status": "Status"
                    }
                    
                    if "active_subjects" in site_perf.columns:
                        rename_dict["active_subjects"] = "Active Subjects"
                    if "screen_failures" in site_perf.columns:
                        rename_dict["screen_failures"] = "Screen Failures"
                    
                    site_perf = site_perf.rename(columns=rename_dict)
                    
                    # Display with sorting by DQI (worst first)
                    display_df = site_perf.sort_values("Avg DQI", ascending=True).head(20)
                    
                    # Apply color formatting
                    def color_dqi(val):
                        if val < 40:
                            color = "#e53e3e"
                        elif val < 60:
                            color = "#d69e2e"
                        elif val < 85:
                            color = "#d69e2e"
                        else:
                            color = "#38a169"
                        return f"color: {color}; font-weight: bold"
                    
                    # Apply styling
                    styled_df = display_df.style.apply(lambda x: ['background-color: #f7fafc' if i % 2 == 0 else '' for i in range(len(x))], axis=0)
                    
                    # Display
                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        height=350
                    )
                    
                    # Summary stats
                    st.markdown("### 📈 Performance Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Sites", len(site_perf))
                    
                    with col2:
                        critical_sites = len(site_perf[site_perf["Avg DQI"] < 60])
                        st.metric("Sites Needing Attention", critical_sites)
                    
                    with col3:
                        avg_dqi = site_perf["Avg DQI"].mean()
                        st.metric("Average DQI", f"{avg_dqi:.1f}")
                    
                    with col4:
                        if "Active Subjects" in site_perf.columns:
                            active_total = site_perf["Active Subjects"].sum()
                            st.metric("Active Subjects", active_total)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # =====================================================
                # 📊 COMPOSITION PIE CHARTS
                # =====================================================
                st.markdown('<div class="content-card">', unsafe_allow_html=True)
                st.markdown("## 📊 Composition Overview")
                
                c1, c2 = st.columns(2)
                
                # ---- Subject Status Pie ----
                with c1:
                    # Check for different possible column names
                    status_col = None
                    for col in drill_df.columns:
                        if "status" in col.lower() and "subject" in col.lower():
                            status_col = col
                            break
                    
                    if status_col:
                        status_counts = drill_df[status_col].value_counts().reset_index()
                        status_counts.columns = ["Status", "Count"]
                        
                        fig_status = px.pie(
                            status_counts,
                            names="Status",
                            values="Count",
                            hole=0.45,
                            title="Subject Status Distribution",
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig_status.update_layout(
                            height=350,
                            paper_bgcolor='white',
                            plot_bgcolor='white',
                            font=dict(color="#2d3748")
                        )
                        st.plotly_chart(fig_status, use_container_width=True)
                    else:
                        st.info("Subject status data not available")
                
                # ---- DQI Band Pie ----
                with c2:
                    if "dqi" in drill_df.columns:
                        dqi_bins = pd.cut(
                            drill_df["dqi"],
                            bins=[0, 40, 60, 85, 100],
                            labels=[
                                "Critical (<40)",
                                "At Risk (40–59)",
                                "Acceptable (60–84)",
                                "High Quality (85+)"
                            ]
                        )
                        dqi_dist = dqi_bins.value_counts().reset_index()
                        dqi_dist.columns = ["DQI Band", "Count"]
                        
                        color_map = {
                            "Critical (<40)": "#e53e3e",
                            "At Risk (40–59)": "#d69e2e",
                            "Acceptable (60–84)": "#4299e1",
                            "High Quality (85+)": "#38a169"
                        }
                        
                        fig_dqi = px.pie(
                            dqi_dist,
                            names="DQI Band",
                            values="Count",
                            hole=0.45,
                            title="DQI Quality Breakdown",
                            color="DQI Band",
                            color_discrete_map=color_map
                        )
                        fig_dqi.update_layout(
                            height=350,
                            paper_bgcolor='white',
                            plot_bgcolor='white',
                            font=dict(color="#2d3748")
                        )
                        st.plotly_chart(fig_dqi, use_container_width=True)
                    else:
                        st.info("DQI data not available")
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # =====================================================
                # ⬇ DOWNLOAD OPTIONS
                # =====================================================
                if 'site_perf' in locals():
                    st.markdown('<div class="content-card">', unsafe_allow_html=True)
                    st.markdown("## ⬇ Download Options")
                    
                    # Prepare data for download
                    csv_data = site_perf.to_csv(index=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            "📥 Download Site Performance (CSV)",
                            csv_data,
                            "site_performance_summary.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        # Create a summary report
                        report_text = f"""CLINICAL TRIAL SITE PERFORMANCE REPORT
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

============================================

OVERALL SUMMARY
---------------
Total Sites: {len(site_perf)}
Total Subjects: {site_perf['Total Subjects'].sum():,}
Average DQI: {site_perf['Avg DQI'].mean():.1f}
Sites Needing Attention (DQI < 60): {len(site_perf[site_perf['Avg DQI'] < 60])}

TOP 10 SITES NEEDING ATTENTION
------------------------------
{site_perf.sort_values('Avg DQI').head(10).to_string(index=False)}

AI EXECUTIVE INSIGHTS
---------------------
{result.get('narrative', 'No narrative available')[:500]}...

DATA QUALITY CONFIDENCE
-----------------------
Confidence Score: {metrics.get('confidence_score', 'N/A') if isinstance(result, dict) and 'metrics' in result else 'N/A'}%

RISK FINGERPRINT SITES
----------------------
{rf_df.to_string(index=False) if 'rf_df' in locals() and not rf_df.empty else 'No risk sites identified'}

ACTION PRIORITIES
-----------------
{chr(10).join([f"{i+1}. Site {item.get('site_id', 'N/A')} - DQI: {item.get('avg_dqi', 'N/A'):.1f}" for i, item in enumerate(metrics.get('action_stack', [])[:3])]) if isinstance(result, dict) and 'metrics' in result else 'No action priorities'}

============================================
Report generated by Clinical Data Quality Dashboard
"""
                        st.download_button(
                            "📥 Download Executive Report (TXT)",
                            report_text,
                            "clinical_site_summary.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"❌ Error generating site summary: {str(e)}")
                import traceback
                with st.expander("See error details"):
                    st.code(traceback.format_exc())
        else:
            st.info("Click the button above to generate a comprehensive site summary analysis.")
# Tab 2: Agent Recommendations (keeping original)
with ai_tab2:
    st.markdown("### AI Agent Recommendations")
    st.markdown("<p style='color: #4a5568; font-size: 16px;'>Get personalized agent deployment recommendations based on data quality patterns.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(" Generate Agent Recommendations", key="gen_agent_recs", use_container_width=True):
            placeholder = st.empty()
            with placeholder.container():
                st.markdown("""
                <div class="ai-loader">
                    <div class="emoji">⏳</div>
                    <b>Generating Agent Recommendations…</b>
                    <div style="font-size:14px;">Evaluating workload & risk signals</div>
                </div>
                """, unsafe_allow_html=True)
            
            with st.spinner("Analyzing…"):
                result = generate_agent_recommendations(drill_df)
            
            placeholder.empty()
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown("##  Recommendations")
            st.markdown(result)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Download button
            st.download_button(
                "Download Recommendations",
                result,
                "agent_recommendations.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("Click the button above to generate agent deployment recommendations.")

# Tab 3: Natural Language Query (keeping original)
with ai_tab3:
    st.markdown("### Natural Language Query")
    st.markdown("<p style='color: #4a5568; font-size: 16px;'>Ask questions about your data in plain English and get instant insights.</p>", unsafe_allow_html=True)
    
    # Call the NLQ interface directly
    nlq_agent_interface(drill_df)


# Tab 4: Clinical Data Review Agent (Build 2 - LangGraph)
with ai_tab4:
    st.markdown("### Clinical Data Review Agent")
    st.markdown("<p style='color:#4a5568;font-size:16px;'>A LangGraph agent that ranks the worst sites, "
                "explains what's dragging each down, and drafts a role-specific action plan and a sponsor email. "
                "Every number is computed in Python; the agent self-corrects if it invents a figure.</p>",
                unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        n_sites = st.slider("Sites to review", 1, 5, 3, key="review_n_sites")
    with col_b:
        goal = st.text_input("Review goal", value="Weekly site-monitoring priorities", key="review_goal")

    if st.button(" Run Site Review Agent", key="run_review_agent", use_container_width=True):
        with st.spinner("Agent running: KPIs -> worst sites -> drivers -> review -> action plan -> email…"):
            try:
                result = run_review(drill_df, goal=goal, n_sites=n_sites)
            except Exception as e:
                st.error(f"Review agent error: {e}")
                result = None

        if result:
            k = result.get("kpis", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Sites", k.get("sites", "-"))
            c2.metric("Avg DQI", k.get("avg_dqi", "-"))
            c3.metric("Critical patients", k.get("critical_patients", "-"))
            c4.metric("Mode", result.get("severity_mode", "-"))

            if not result.get("grounding_ok", True):
                st.warning("Grounding check flagged unverified figures after max retries: "
                           f"{result.get('validation_notes')}")

            st.markdown("####  Executive Review")
            st.markdown(result.get("review_text", ""))
            st.markdown("####  Action Plan")
            st.markdown(result.get("action_plan", ""))
            with st.expander(" Draft sponsor email (review before sending)"):
                st.markdown(result.get("sponsor_email", ""))

            if result.get("site_drivers"):
                st.markdown("####  Worst-site drivers (grounded, from weights)")
                for sd in result["site_drivers"]:
                    st.markdown(f"**{sd['site_id']}** — avg DQI {sd['avg_dqi']}, {sd.get('patients','?')} patients")
                    rows = [{"Driver": d["label"], "Site": d["site_value"],
                             "Cohort": d["cohort_value"], "Delta": d["delta_contribution"]}
                            for d in sd["drivers"]]
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Set the scope and click Run to generate a grounded site review.")

# =========================
# FOOTER
# =========================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #718096; padding: 20px; font-size: 14px;">
    <p> Clinical Trial Data Quality Dashboard | Powered by AI Analytics</p>
    <p style="font-size: 12px; margin-top: 10px;">Data refreshed automatically | Last updated: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)