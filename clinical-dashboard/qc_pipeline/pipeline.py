# qc_pipeline/pipeline.py
from pathlib import Path
import pandas as pd
import re
import os
import numpy as np
from datetime import datetime
import shutil
import zipfile

# =================================================
# HELPERS
# =================================================

def extract_study_number(name: str):
    """Extract first integer from a string."""
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else None

# =================================================
# STAGE 1 — FOLDER STANDARDISATION
# =================================================

def rename_study_folders(root_dir: Path):
    DRY_RUN = False

    for folder_name in os.listdir(root_dir):
        old_path = root_dir / folder_name
        if not old_path.is_dir():
            continue

        study_number = extract_study_number(folder_name)
        if study_number is None:
            continue

        study_number = str(study_number).zfill(2)
        new_folder_name = f"Study {study_number} CPID Input Files"
        new_path = root_dir / new_folder_name

        if old_path == new_path:
            continue

        if not DRY_RUN:
            os.rename(old_path, new_path)


# =================================================
# STAGE 2 — FILE STANDARDISATION
# =================================================

def rename_files_in_study_folder(study_dir: Path):

    DRY_RUN = False

    CATEGORIES = {
        "CPID_EDC_Metrics": [
            "cpid_edc",
            "cpid edc",
            "cpid"
        ],
        "Visit Projection Tracker": [
            "visit projection",
            "missing visit",
            "visit"
        ],
        "Missing Lab Name and Missing Ranges": [
            "missing_lab_name",
            "missing lab & range",
            "missing lab &",
            "missing lab name",
            "missing_lab_name_and_missing_ranges",
            "missing lnr",
        ],
        "SAE Dashboard": [
            "sae dashboard",
            "esae",
            "dm_safety",
        ],
        "Inactivated Forms and Folders": [
            "inactivated folders",
            "inactivated form folder",
            "inactivated forms and folders",
            "inactivated report",
            "inactivated page",
            "inactivated pages",
            "inactivated forms and folder",
            "inactivated"
        ],
        "Global Missing Pages Report": [
            "missing pages",
            "missing_page_report",
            "missing page report",
            "global missing pages",
            "global_missing_pages",
            "missing_page_report_",
            "missing_page",
            "global missing pages report",
        ],
        "Compiled EDRR": [
            "compiled_edrr",
            "compiled edrr",
        ],
        "GlobalCodingReport_MedDRA": [
            "meddra",
            "medra",
            "medra codingreport",
            "codingreport_medra",
            "globalcodingreport meddra",
            "globalcodingreport_medra",
            "globalcodingreport_medra codingreport",
        ],
        "GlobalCodingReport_WHODD": [
            "whodd",
            "whodrug",
            "who drug",
            "whodra",
        ],
    }

    def detect_category(file_name: str):
        """
        Decide category from filename (case-insensitive).
        Returns canonical category or None.
        """
        name_lower = file_name.lower()

        # Skip already-standard filenames
        for category in CATEGORIES:
            if name_lower.startswith("study ") and f"- {category.lower()}" in name_lower:
                return None

        matches = []
        for category, patterns in CATEGORIES.items():
            for pat in patterns:
                if pat in name_lower:
                    matches.append(category)
                    break

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"  [WARN] Ambiguous category for '{file_name}' -> {matches}, skipping")
            return None
        else:
            return None

    study_num = extract_study_number(study_dir.name)

    if study_num is None:
        print(f"[WARN] Could not find study number in {study_dir.name}")
        return

    used_categories = set()

    for f in study_dir.iterdir():
        if not f.is_file():
            continue

        category = detect_category(f.name)
        if category is None:
            continue

        if category in used_categories:
            continue

        new_name = f"Study {study_num} - {category}.xlsx"
        new_path = f.with_name(new_name)

        if new_path.exists():
            used_categories.add(category)
            continue

        if DRY_RUN:
            print(f"[DRY RUN] {f.name} → {new_name}")
        else:
            f.rename(new_path)

        used_categories.add(category)


# =================================================
# STAGE 3 — ADD STUDY KEY
# =================================================

def add_study_key(root_dir: Path):
    print("Adding Study Key to all Excel files...")
    DRY_RUN = False

    for study_dir in root_dir.iterdir():
        if not study_dir.is_dir():
            continue

        study_key = extract_study_number(study_dir.name)
        if study_key is None:
            continue

        for file in study_dir.glob("*.xlsx"):
            try:
                sheets = pd.read_excel(file, sheet_name=None)
                
                for sheet, df in sheets.items():
                    df["Study Key"] = study_key
                    sheets[sheet] = df

                if not DRY_RUN:
                    with pd.ExcelWriter(file, engine="openpyxl", mode="w") as writer:
                        for sheet, df in sheets.items():
                            df.to_excel(writer, sheet_name=sheet, index=False)
            except Exception as e:
                print(f"Error processing {file}: {e}")
                continue


# =================================================
# STAGE 4 — METRIC EXTRACTION
# =================================================

def extract_cols(root_dir):
    """Extract metrics from standardized files with robust error handling"""
    
    # =================================================
    # Helpers
    # =================================================

    def standardise_subject_column(df):
        """Standardize subject column names across different file formats"""
        SUBJECT_ALIASES = [
            "subject",
            "subject name",
            "subject id",
            "patient",
            "patient id",
            "subjid",
            "participant id",
            "subjectname"
        ]

        if df is None or df.empty:
            return df

        for col in df.columns:
            if col.lower().strip() in SUBJECT_ALIASES:
                return df.rename(columns={col: "Subject"})

        # If no subject column found, try to create one from available columns
        if "Subject" not in df.columns:
            # Check if there's any column that might contain subject IDs
            for col in df.columns:
                if "id" in col.lower() or "name" in col.lower():
                    df = df.rename(columns={col: "Subject"})
                    break
        
        return df

    def group_count(file_path, col_name):
        """Group by Study Key and Subject and count occurrences"""
        try:
            df = pd.read_excel(file_path)
            df = standardise_subject_column(df)
            
            if df is None or df.empty:
                return None
                
            # Ensure required columns exist
            if "Study Key" not in df.columns:
                # Try to extract study key from file path
                study_num = extract_study_number(str(file_path))
                if study_num:
                    df["Study Key"] = study_num
                else:
                    return None
            
            if "Subject" not in df.columns:
                return None
                
            df["Study Key"] = df["Study Key"].astype(str)
            df["Subject"] = df["Subject"].astype(str)

            return (
                df.groupby(["Study Key", "Subject"])
                .size()
                .reset_index(name=col_name)
            )
        except Exception as e:
            print(f"Error in group_count for {file_path}: {e}")
            return None

    def clean_grouping_columns(df, cols):
        """Clean grouping columns to ensure consistent merging"""
        if df is None or df.empty:
            return df
            
        for col in cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .replace(["", "nan", "NA", "None"], "Unknown")
                )
        return df

    def standardise_merge_keys(df):
        """Ensure merge keys are standardized"""
        if df is None or df.empty:
            return df
            
        if "Study Key" in df.columns:
            df["Study Key"] = df["Study Key"].astype(str)
        if "Subject" in df.columns:
            df["Subject"] = df["Subject"].astype(str)
        return df

    def coded_uncoded_from_file(file_path):
        """Extract coded and uncoded terms from coding reports"""
        try:
            df = pd.read_excel(file_path)
            df = standardise_subject_column(df)
            
            if df is None or df.empty:
                return None
                
            if "Coding Status" not in df.columns:
                return None
                
            df["_is_coded"] = df["Coding Status"].fillna("").eq("Coded Term")
            df["_is_uncoded"] = ~df["_is_coded"]

            return (
                df.groupby(["Study Key", "Subject"])
                .agg(
                    Coded_Terms=("_is_coded", "sum"),
                    UnCoded_Terms=("_is_uncoded", "sum")
                )
                .reset_index()
            )
        except Exception as e:
            print(f"Error in coded_uncoded_from_file for {file_path}: {e}")
            return None

    def sae_dashboard_summary_from_file(file_path):
        """Extract SAE dashboard summaries"""
        try:
            sheets = pd.read_excel(file_path, sheet_name=None)
            summaries = {}

            for sheet_name, df in sheets.items():
                df = standardise_subject_column(df)
                
                if df is None or df.empty:
                    continue
                    
                df = clean_grouping_columns(df, ["Study Key", "Subject"])

                # Check for Review Status column
                if "Review Status" not in df.columns:
                    continue
                    
                df["_is_completed"] = df["Review Status"].fillna("").eq("Review Completed")

                label = "DM" if "dm" in sheet_name.lower() else "Safety"

                summary = (
                    df.groupby(["Study Key", "Subject"])["_is_completed"]
                    .sum()
                    .reset_index(name=label)
                )

                summaries[label] = summary

            # ---- Outer merge (superset) ----
            merged = None
            for summary in summaries.values():
                if summary is not None and not summary.empty:
                    if merged is None:
                        merged = summary
                    else:
                        merged = merged.merge(
                            summary,
                            on=["Study Key", "Subject"],
                            how="outer"
                        )

            return merged
        except Exception as e:
            print(f"Error in sae_dashboard_summary_from_file for {file_path}: {e}")
            return None

    def edrr_summary_from_file(file_path):
        """Extract EDRR summaries"""
        try:
            df = pd.read_excel(file_path)
            df = standardise_subject_column(df)
            
            if df is None or df.empty:
                return None
                
            df = clean_grouping_columns(df, ["Study Key", "Subject"])

            if "Total Open issue Count per subject" not in df.columns:
                return None
                
            return df[[
                "Study Key",
                "Subject",
                "Total Open issue Count per subject"
            ]].rename(columns={
                "Total Open issue Count per subject": "EDRR"
            })
        except Exception as e:
            print(f"Error in edrr_summary_from_file for {file_path}: {e}")
            return None

    # =================================================
    # Main processing function
    # =================================================

    def process_study_folder(study_dir):
        """Process a single study folder and extract all metrics"""
        coding_summary = None
        missing_lab_summary = None
        inactivated_logs_summary = None
        sae_dashboard_summary = None
        edrr_summary = None
        missing_pages_summary = None
        missing_visits_summary = None

        # ---- Find all files ----
        meddra = list(study_dir.glob("*GlobalCodingReport_MedDRA.xlsx"))
        whodd = list(study_dir.glob("*GlobalCodingReport_WHODD.xlsx"))
        missing_lab = list(study_dir.glob("*Missing Lab Name and Missing Ranges.xlsx"))
        inactivated_logs = list(study_dir.glob("*Inactivated Forms and Folders.xlsx"))
        sae_dashboard = list(study_dir.glob("*SAE Dashboard.xlsx"))
        edrr = list(study_dir.glob("*Compiled EDRR.xlsx"))
        missing_pages = list(study_dir.glob("*Global Missing Pages Report.xlsx"))
        missing_visits = list(study_dir.glob("*Visit Projection Tracker.xlsx"))

        # ---- Coding (MedDRA + WHODD) ----
        if meddra:
            coding_summary = coded_uncoded_from_file(meddra[0])

        if whodd:
            whodd_summary = coded_uncoded_from_file(whodd[0])

            if coding_summary is None:
                coding_summary = whodd_summary
            elif whodd_summary is not None:
                coding_summary = coding_summary.merge(
                    whodd_summary,
                    on=["Study Key", "Subject"],
                    how="outer",
                    suffixes=("", "_whodd")
                )

                coding_summary["Coded_Terms"] = (
                    coding_summary["Coded_Terms"].fillna(0) +
                    coding_summary["Coded_Terms_whodd"].fillna(0)
                )

                coding_summary["UnCoded_Terms"] = (
                    coding_summary["UnCoded_Terms"].fillna(0) +
                    coding_summary["UnCoded_Terms_whodd"].fillna(0)
                )

                coding_summary = coding_summary[
                    ["Study Key", "Subject", "Coded_Terms", "UnCoded_Terms"]
                ]

        # ---- Missing Lab ----
        if missing_lab:
            missing_lab_summary = group_count(missing_lab[0], "Open Issues Count LNR")

        # ---- Inactivated Logs ----
        if inactivated_logs:
            inactivated_logs_summary = group_count(inactivated_logs[0], "Inactivated Logs")

        # ---- SAE Dashboard ----
        if sae_dashboard:
            sae_dashboard_summary = sae_dashboard_summary_from_file(sae_dashboard[0])

        # ---- EDRR ----
        if edrr:
            edrr_summary = edrr_summary_from_file(edrr[0])

        # ---- Missing Pages ----
        if missing_pages:
            missing_pages_summary = group_count(missing_pages[0], "Missing Pages")

        # ---- Missing Visits ----
        if missing_visits:
            missing_visits_summary = group_count(missing_visits[0], "Missing Visits")

        return (
            coding_summary, missing_lab_summary, edrr_summary, 
            inactivated_logs_summary, sae_dashboard_summary, 
            missing_pages_summary, missing_visits_summary
        )

    # =================================================
    # Main loop - collect all summaries
    # =================================================

    all_coding_summaries = []
    missing_lab_summaries = []
    inactivated_logs_summaries = []
    sae_dashboard_summaries = []
    edrr_summaries = []
    missing_pages_summaries = []
    missing_visits_summaries = []

    for study_dir in root_dir.iterdir():
        if not study_dir.is_dir():
            continue

        coding, missing_lab, edrr, inactivated, sae, missing_pages, missing_visits = process_study_folder(study_dir)

        if coding is not None and not coding.empty:
            all_coding_summaries.append(coding)

        if missing_lab is not None and not missing_lab.empty:
            missing_lab_summaries.append(missing_lab)

        if inactivated is not None and not inactivated.empty:
            inactivated_logs_summaries.append(inactivated)

        if sae is not None and not sae.empty:
            sae_dashboard_summaries.append(sae)

        if edrr is not None and not edrr.empty:
            edrr_summaries.append(edrr)

        if missing_pages is not None and not missing_pages.empty:
            missing_pages_summaries.append(missing_pages)

        if missing_visits is not None and not missing_visits.empty:
            missing_visits_summaries.append(missing_visits)

    # =================================================
    #final outputs
    #===========================================
    
    # Create final dataframes with error handling
    # =================================================

    def safe_concat(dataframes_list, description=""):
        """Safely concatenate a list of dataframes, handling empty lists"""
        if not dataframes_list:
            # Return an empty dataframe with expected columns
            return pd.DataFrame(columns=["Study Key", "Subject"])
        
        # Filter out None values
        valid_dfs = [df for df in dataframes_list if df is not None and not df.empty]
        
        if not valid_dfs:
            return pd.DataFrame(columns=["Study Key", "Subject"])
            
        try:
            return pd.concat(valid_dfs, ignore_index=True)
        except Exception as e:
            print(f"Error concatenating {description}: {e}")
            return pd.DataFrame(columns=["Study Key", "Subject"])

    # Create final summaries with safe concatenation
    final_coding_summary = safe_concat(all_coding_summaries, "coding summaries")
    final_missing_lab_summary = safe_concat(missing_lab_summaries, "missing lab summaries")
    final_inactivated_logs_summary = safe_concat(inactivated_logs_summaries, "inactivated logs summaries")
    final_sae_dashboard_summary = safe_concat(sae_dashboard_summaries, "SAE dashboard summaries")
    final_edrr_summary = safe_concat(edrr_summaries, "EDRR summaries")
    final_missing_pages_summary = safe_concat(missing_pages_summaries, "missing pages summaries")
    final_missing_visits_summary = safe_concat(missing_visits_summaries, "missing visits summaries")

    # =================================================
    # Prepare dataframes for merging
    # =================================================

    # Rename columns for consistency
    coding_df = final_coding_summary.rename(columns={
        "Coded_Terms": "Coded",
        "UnCoded_Terms": "UnCoded"
    }) if not final_coding_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "Coded", "UnCoded"])

    lnr_df = final_missing_lab_summary.rename(columns={
        "Open Issues Count LNR": "LnR"
    }) if not final_missing_lab_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "LnR"])

    inactivated_df = final_inactivated_logs_summary.rename(columns={
        "Inactivated Logs": "Inactivated"
    }) if not final_inactivated_logs_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "Inactivated"])

    edrr_df = final_edrr_summary if not final_edrr_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "EDRR"])
    
    sae_df = final_sae_dashboard_summary if not final_sae_dashboard_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "DM", "Safety"])
    
    missing_pages_df = final_missing_pages_summary if not final_missing_pages_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "Missing Pages"])
    
    missing_visits_df = final_missing_visits_summary if not final_missing_visits_summary.empty else pd.DataFrame(columns=["Study Key", "Subject", "Missing Visits"])

    # =================================================
    # Standardize merge keys
    # =================================================

    tables = []
    
    for df, name in [
        (coding_df, "Coding"),
        (lnr_df, "LNR"),
        (edrr_df, "EDRR"),
        (inactivated_df, "Inactivated"),
        (sae_df, "SAE"),
        (missing_pages_df, "Missing Pages"),
        (missing_visits_df, "Missing Visits")
    ]:
        if not df.empty:
            df = standardise_merge_keys(df)
            tables.append(df)
            print(f"Added {name} table with {len(df)} rows")
        else:
            print(f"Skipping empty {name} table")

    # =================================================
    # Merge all tables
    # =================================================

    if not tables:
        print("No data found in any tables")
        return pd.DataFrame(columns=["Study Key", "Subject"])

    # Start with first table
    final_master_qc = tables[0]
    
    # Merge remaining tables
    for i, df in enumerate(tables[1:], 1):
        try:
            final_master_qc = pd.merge(
                final_master_qc,
                df,
                on=["Study Key", "Subject"],
                how="outer"
            )
        except Exception as e:
            print(f"Error merging table {i}: {e}")
            continue

    # =================================================
    # Final processing
    # =================================================

    # Define all possible metric columns
    all_metric_cols = [
        "Coded", "UnCoded", "LnR", "EDRR", "Inactivated", 
        "DM", "Safety", "Missing Pages", "Missing Visits"
    ]

    # Add missing columns with 0 values
    for col in all_metric_cols:
        if col not in final_master_qc.columns:
            final_master_qc[col] = 0

    # Fill NaN values with 0
    final_master_qc = final_master_qc.fillna(0)

    # Convert metric columns to integers
    for col in all_metric_cols:
        if col in final_master_qc.columns:
            final_master_qc[col] = final_master_qc[col].astype(int)

    # Sort and order columns
    final_master_qc = final_master_qc[
        ["Study Key", "Subject"] + all_metric_cols
    ].sort_values(["Study Key", "Subject"])

    print(f"Final QC DataFrame shape: {final_master_qc.shape}")
    print(f"Final QC DataFrame columns: {final_master_qc.columns.tolist()}")
    
    return final_master_qc

def find_cpid_file(study_dir: Path):
    cpid_files = [
        f for f in study_dir.iterdir()
        if f.is_file()
        and f.suffix.lower() == ".xlsx"
        and "cpid" in f.name.lower()
    ]

    if not cpid_files:
        raise FileNotFoundError("No CPID file found in study folder")

    if len(cpid_files) > 1:
        print("⚠ Multiple CPID files found, using first one")

    return cpid_files[0]

def collapse_cpid_headers(cpid_file: Path):
    print(f"Collapsing headers for: {cpid_file.name}")

    df = pd.read_excel(
        cpid_file,
        sheet_name=0,
        header=[0, 1, 2, 3]
    )

    df.columns = [
        " | ".join(
            [str(x).strip() for x in col if str(x) != "nan"]
        )
        for col in df.columns
    ]

    # OVERWRITE (as requested)
    df.to_excel(cpid_file, index=False)

    print("✔ CPID headers collapsed and overwritten")

    return df
# =================================================
def populate_cpid_with_qc(cpid_df: pd.DataFrame, final_qc_df: pd.DataFrame):

    # --------------------------------------------------
    # COLUMN NAMES (UNCHANGED)
    # --------------------------------------------------

    study_col = (
        "Project Name | Unnamed: 0_level_1 | Unnamed: 0_level_2 | Responsible LF for action"
    )

    subject_col = (
        "Subject ID | Unnamed: 4_level_1 | Unnamed: 4_level_2 | Unnamed: 4_level_3"
    )

    final_qc = final_qc_df.copy()

    final_qc["Study Key"] = final_qc["Study Key"].astype(str).str.strip()
    final_qc["Subject"] = final_qc["Subject"].astype(str).str.strip()

    # --------------------------------------------------
    # EXTRACT STUDY & SUBJECT FROM CPID
    # --------------------------------------------------

    cpid_df["_Study Key"] = (
        cpid_df[study_col]
        .astype(str)
        .str.extract(r"(\d+)")
    )

    cpid_df["_Subject"] = (
        cpid_df[subject_col]
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------
    # MERGE QC
    # --------------------------------------------------

    cpid_df = cpid_df.merge(
        final_qc,
        how="left",
        left_on=["_Study Key", "_Subject"],
        right_on=["Study Key", "Subject"]
    )

    # --------------------------------------------------
    # MAP QC → CPID INPUT FILE COLUMNS
    # --------------------------------------------------

    # FIXED: Look for columns with ANY of these patterns in the hierarchy
    QC_TO_CPID_MAP = {
        "Missing Pages": ["missing page", "unnamed: 8"],  # Added pattern for Unnamed: 8
        "Missing Visits": ["missing visits", "unnamed: 7"],
        "Coded": ["# coded terms", "unnamed: 9"],
        "UnCoded": ["# uncoded terms", "unnamed: 10"],
        "LnR": ["open issues in lnr", "unnamed: 11"],
        "EDRR": ["reconciliation in edrr", "unnamed: 12"],
        "Inactivated": ["inactivated forms and folders", "unnamed: 13"],
        "DM": ["dashboard review for dm", "unnamed: 14"],
        "Safety": ["dashboard review for safety", "unnamed: 15"],
    }

    # Get all columns that might be input file columns
    # Look for columns containing ANY of the QC hints in ANY part of the column name
    all_columns = cpid_df.columns.tolist()
    
    print(f"🔍 Looking for QC columns to map in {len(all_columns)} total columns")
    
    for qc_col, hints in QC_TO_CPID_MAP.items():
        target_cols = []
        
        # Try each hint for this QC column
        for hint in hints:
            for col in all_columns:
                if isinstance(col, str) and hint.lower() in col.lower():
                    target_cols.append(col)
        
        # Remove duplicates while preserving order
        target_cols = list(dict.fromkeys(target_cols))
        
        if target_cols:
            print(f"   ✓ '{qc_col}' -> found {len(target_cols)} target(s) with hints {hints}: {target_cols}")
            
            for col in target_cols:
                if qc_col in cpid_df.columns:
                    cpid_df[col] = (
                        cpid_df[qc_col]
                        .fillna(0)
                        .astype(int)
                    )
                    print(f"      Set '{col}' = '{qc_col}' (value range: {cpid_df[qc_col].min()} to {cpid_df[qc_col].max()})")
                else:
                    print(f"      ⚠ QC column '{qc_col}' not found in cpid_df after merge")
        else:
            print(f"   ✗ '{qc_col}' -> NO MATCHING COLUMN FOUND for hints {hints}")
            # Show what columns are available
            print(f"      Searching in {len(all_columns)} columns...")

    # Also check for columns that might already contain "input files" pattern
    input_file_cols = [
        c for c in cpid_df.columns
        if isinstance(c, str) and any(hint in c.lower() for hint in [
            "input files", "unnamed: 7", "unnamed: 8", "unnamed: 9", "unnamed: 10",
            "unnamed: 11", "unnamed: 12", "unnamed: 13", "unnamed: 14", "unnamed: 15"
        ])
    ]
    
    if input_file_cols:
        print(f"\n🔍 Found {len(input_file_cols)} potential input file columns")
        for col in input_file_cols:
            print(f"   - {col}")
        
        # Convert to int
        cpid_df[input_file_cols] = (
            cpid_df[input_file_cols]
            .fillna(0)
            .astype(int)
        )
        print(f"   Converted {len(input_file_cols)} input file columns to int")
    else:
        print(f"\n⚠ No potential input file columns found!")

    #####################################################
    # CRF (SAFE NUMERIC COMPUTATION) - FIXED COLUMN NAMES
    #####################################################

    # Fixed column names based on your actual CPID structure
    SIGNED_COL = (
        "SSM | PI Signatures (Source: (Rave EDC : BO4)) | # CRFs Signed | Investigator"
    )

    NC_COL = (
        "Unnamed: 18 | Unnamed: 18_level_1 | # Pages with Non-Conformant data | Site/CRA"
    )

    TOTAL_QUERIES_COL = (
        "Unnamed: 29 | Unnamed: 29_level_1 | #Total Queries | Unnamed: 29_level_3"
    )

    CRF_ISSUES_COL = (
        "Unnamed: 19 | Unnamed: 19_level_1 | # Total CRFs with queries & Non-Conformant data | Unnamed: 19_level_3"
    )

    CRF_CLEAN_COL = (
        "Unnamed: 20 | Unnamed: 20_level_1 | # Total CRFs without queries & Non-Conformant data | Unnamed: 20_level_3"
    )

    PCT_CLEAN_COL = (
        "Unnamed: 21 | Unnamed: 21_level_1 | % Clean Entered CRF | Unnamed: 21_level_3"
    )

    required_cols = [SIGNED_COL, NC_COL, TOTAL_QUERIES_COL]

    if all(col in cpid_df.columns for col in required_cols):
        print(f"\n✅ All CRF columns found, computing derived metrics...")

        # 🔑 force numeric
        for col in required_cols:
            cpid_df[col] = pd.to_numeric(
                cpid_df[col],
                errors="coerce"
            ).fillna(0)
            print(f"   Converted '{col.split('|')[-1].strip()}' to numeric")

        cpid_df[CRF_ISSUES_COL] = np.maximum(
            cpid_df[NC_COL],
            cpid_df[TOTAL_QUERIES_COL]
        )

        cpid_df[CRF_CLEAN_COL] = (
            cpid_df[SIGNED_COL] - cpid_df[CRF_ISSUES_COL]
        ).clip(lower=0)

        cpid_df[PCT_CLEAN_COL] = np.where(
            cpid_df[SIGNED_COL] > 0,
            100 * cpid_df[CRF_CLEAN_COL] / cpid_df[SIGNED_COL],
            0.0
        ).round(2)
        
        print(f"   CRF_ISSUES_COL computed: sample values {cpid_df[CRF_ISSUES_COL].head().tolist()}")
        print(f"   CRF_CLEAN_COL computed: sample values {cpid_df[CRF_CLEAN_COL].head().tolist()}")
        print(f"   PCT_CLEAN_COL computed: sample values {cpid_df[PCT_CLEAN_COL].head().tolist()}")

    else:
        missing_cols = [col for col in required_cols if col not in cpid_df.columns]
        print(f"\nℹ CRF derived metrics skipped (required columns missing)")
        print(f"   Missing columns: {missing_cols}")
        print(f"   Looking for:")
        print(f"     - SIGNED_COL: '{SIGNED_COL}' -> {'FOUND' if SIGNED_COL in cpid_df.columns else 'NOT FOUND'}")
        print(f"     - NC_COL: '{NC_COL}' -> {'FOUND' if NC_COL in cpid_df.columns else 'NOT FOUND'}")
        print(f"     - TOTAL_QUERIES_COL: '{TOTAL_QUERIES_COL}' -> {'FOUND' if TOTAL_QUERIES_COL in cpid_df.columns else 'NOT FOUND'}")

    # --------------------------------------------------
    # CLEANUP
    # --------------------------------------------------
    
    # Check what columns exist before dropping
    columns_to_drop = ["Study Key", "Subject", "_Study Key", "_Subject"]
    existing_columns_to_drop = [col for col in columns_to_drop if col in cpid_df.columns]
    
    if existing_columns_to_drop:
        print(f"\n🔍 Dropping temporary columns: {existing_columns_to_drop}")
        cpid_df.drop(
            columns=existing_columns_to_drop,
            errors="ignore",
            inplace=True
        )
    else:
        print(f"\n🔍 No temporary columns found to drop")

    # Also drop the original QC columns if they exist
    qc_cols_to_drop = [c for c in QC_TO_CPID_MAP.keys() if c in cpid_df.columns]
    if qc_cols_to_drop:
        print(f"🔍 Dropping original QC columns: {qc_cols_to_drop}")
        cpid_df.drop(
            columns=qc_cols_to_drop,
            errors="ignore",
            inplace=True
        )
    else:
        print(f"🔍 No original QC columns found to drop")

    # Drop rows with NaN in study_col
    if study_col in cpid_df.columns:
        before_count = len(cpid_df)
        cpid_df.dropna(
            subset=[study_col],
            inplace=True
        )
        after_count = len(cpid_df)
        if before_count > after_count:
            print(f"🔍 Dropped {before_count - after_count} rows with NaN in '{study_col.split('|')[0].strip()}'")

    print(f"\n✅ populate_cpid_with_qc completed successfully")
    print(f"   Final shape: {cpid_df.shape}")
    
    return cpid_df
    

CPID_DQI_WEIGHTS = {
    "CPMD | Page Action Status (Source: (Rave EDC : BO4)) | # CRFs Frozen | Unnamed: 32_level_3": 0.557811901,
    "CPMD | Page Action Status (Source: (Rave EDC : BO4)) | # CRFs Require Verification (SDV) | CRA": 0.336395948,
    "Input files | Missing Page | Unnamed: 8_level_2 | Unnamed: 8_level_3": 0.276865069,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | # Field Monitor Queries | CRA": 0.258439072,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | # Safety Queries | Safety Team": 0.236726864,
    "SSM | PI Signatures (Source: (Rave EDC : BO4)) | CRFs overdue for signs between 45 to 90 days of Data entry | Unnamed: 40_level_3": 0.220676915,
    "SSM | PI Signatures (Source: (Rave EDC : BO4)) | # CRFs Signed | Investigator": 0.203519043,
    "CPMD | Protocol Deviations (Source:(Rave EDC : BO4)) | # PDs Confirmed | CD LF": 0.202726625,
    "Input files | Missing Visits | Unnamed: 7_level_2 | Unnamed: 7_level_3": 0.18317448,
    "Input files | # eSAE dashboard review for safety | Unnamed: 15_level_2 | Unnamed: 15_level_3": 0.157577803,
    "Input files | # Coded terms | Unnamed: 9_level_2 | Unnamed: 9_level_3": 0.116207858,
    "CPMD | Page status (Source: (Rave EDC : BO4)) | # Pages Entered | Unnamed: 17_level_3": 0.098908453,
    "Input files | # eSAE dashboard review for DM | Unnamed: 14_level_2 | Unnamed: 14_level_3": 0.0889794,
    "CPMD | Page Action Status (Source: (Rave EDC : BO4)) | # CRFs Locked | Unnamed: 34_level_3": 0.070773304,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | # Clinical Queries | CSE/CDD": 0.064722432,
    "Input files | # Open Issues reported for 3rd party reconciliation in EDRR | Unnamed: 12_level_2 | Unnamed: 12_level_3": 0.031069942,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | #Total Queries | Unnamed: 29_level_3": 0.023270543,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | # DM Queries | DM": 0.00917528,
    "CPMD | Page Action Status (Source: (Rave EDC : BO4)) | # CRFs Unlocked | Unnamed: 35_level_3": -0.006439901,
    "SSM | PI Signatures (Source: (Rave EDC : BO4)) | CRFs overdue for signs beyond 90 days of Data entry | Unnamed: 41_level_3": -0.006663069,
    "CPMD | Visit status | # Expected Visits (Rave EDC : BO4) | Unnamed: 16_level_3": -0.011812896,
    "SSM | PI Signatures (Source: (Rave EDC : BO4)) | Broken Signatures | Unnamed: 42_level_3": -0.015021751,
    "Input files | Inactivated forms and folders | Unnamed: 13_level_2 | Unnamed: 13_level_3": -0.024799977,
    "CPMD | Protocol Deviations (Source:(Rave EDC : BO4)) | # PDs Proposed | Unnamed: 37_level_3": -0.08340615,
    "Input files | # Open issues in LNR | Unnamed: 11_level_2 | Unnamed: 11_level_3": -0.097290657,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | # Site Queries | Site/CRA": -0.103078974,
    "Input files | # Uncoded Terms | Unnamed: 10_level_2 | Unnamed: 10_level_3": -0.13614252,
    "CPMD | Page Action Status (Source: (Rave EDC : BO4)) | # CRFs Not Frozen | DM": -0.175684402,
    "CPMD | Queries status (Source:(Rave EDC : BO4)) | # Medical Queries | CDMD/Medical Lead": -0.244027659,
    "SSM | PI Signatures (Source: (Rave EDC : BO4)) | CRFs Never Signed | Unnamed: 43_level_3": -0.285693574,
    "SSM | PI Signatures (Source: (Rave EDC : BO4)) | CRFs overdue for signs within 45 days of Data entry | Unnamed: 39_level_3": -0.297879926,
    "CPMD | Page status (Source: (Rave EDC : BO4)) | # Pages with Non-Conformant data | Site/CRA": -0.328904988,
    "CPMD | Page Action Status (Source: (Rave EDC : BO4)) | # Forms Verified | Unnamed: 31_level_3": -0.336508856
}

def compute_cpid_dqi(cpid_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes CPID DQI score on a fully populated CPID dataframe.
    """

    cpid_df = cpid_df.copy()
    cpid_df["CPID_DQI_SCORE"] = 0.0

    for metric_hint, weight in CPID_DQI_WEIGHTS.items():

        # find matching columns (robust)
        matching_cols = [
            col for col in cpid_df.columns
            if isinstance(col, str) and metric_hint.lower() in col.lower()
        ]

        for col in matching_cols:
            cpid_df[col] = pd.to_numeric(
                cpid_df[col],
                errors="coerce"
            ).fillna(0)

            cpid_df["CPID_DQI_SCORE"] += cpid_df[col] * weight

    # Optional: round for dashboard
    cpid_df["CPID_DQI_SCORE"] = cpid_df["CPID_DQI_SCORE"].round(3)

    return cpid_df

def process_uploaded_study(study_dir: Path, final_qc_df: pd.DataFrame):
    # 1️⃣ Find CPID file automatically
    cpid_file = find_cpid_file(study_dir)

    # 2️⃣ Collapse headers & overwrite
    cpid_df = collapse_cpid_headers(cpid_file)

    # 3️⃣ Populate CPID with QC metrics
    cpid_df = populate_cpid_with_qc(cpid_df, final_qc_df)
    print(f"📊 CPID after QC population shape: {cpid_df.shape}")

# Set display options to show everything
    pd.set_option('display.max_columns', None)  # Show all columns
    pd.set_option('display.max_rows', None)     # Show all rows (for head)
    pd.set_option('display.width', None)        # Auto-detect terminal width
    pd.set_option('display.max_colwidth', None) # Show full column content

    print("First 2 rows with all columns:")
    print(cpid_df.head(2).to_string())  # Use to_string() for full output

    # Reset to default if needed
    pd.reset_option('display.max_columns')
    pd.reset_option('display.max_rows')
    pd.reset_option('display.width')
    pd.reset_option('display.max_colwidth')
    

    cpid_df = compute_cpid_dqi(cpid_df)

    # 4️⃣ Overwrite CPID again with populated values
    cpid_df.to_excel(cpid_file, index=False)

    print("✅ CPID updated with QC metrics")

    return cpid_df

def process_all_studies(root_dir: Path, final_qc_df: pd.DataFrame):

    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"Invalid root directory: {root_dir}")

    print(f"🚀 Processing all studies in: {root_dir}")

    for study_dir in root_dir.iterdir():

        if not study_dir.is_dir():
            continue

        print(f"\n📂 Study folder: {study_dir.name}")

        try:
            process_uploaded_study(study_dir, final_qc_df)
        except FileNotFoundError as e:
            print(f"⚠ Skipping {study_dir.name}: {e}")
        except Exception as e:
            print(f"❌ Error processing {study_dir.name}: {e}")

    print("\n✅ All studies processed.")

def create_final_output(root_dir: Path, output_path: Path = None):
    """
    Create final merged output from all processed CPID files.
    """
    merged_dfs = []
    
    # Sort study folders numerically
    study_folders = sorted(
        [d for d in root_dir.iterdir() if d.is_dir()],
        key=lambda d: extract_study_number(d.name) if extract_study_number(d.name) else float('inf')
    )
    
    for study_dir in study_folders:
        print(f"📂 Reading {study_dir.name}")
        
        # Find CPID file
        cpid_files = [
            f for f in study_dir.iterdir()
            if f.is_file()
            and f.suffix.lower() == ".xlsx"
            and "cpid" in f.name.lower()
        ]
        
        if not cpid_files:
            print(f"⚠ No CPID file found in {study_dir.name}")
            continue
        
        cpid_file = cpid_files[0]
        print(f"   → {cpid_file.name}")
        
        try:
            df = pd.read_excel(cpid_file)
            merged_dfs.append(df)
        except Exception as e:
            print(f"   ❌ Error reading {cpid_file.name}: {e}")
            continue
    
    if not merged_dfs:
        print("❌ No CPID files found to merge")
        return None
    
    # Concatenate in order
    final_merged_df = pd.concat(merged_dfs, ignore_index=True)
    
    # Save if output path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_merged_df.to_excel(output_path, index=False)
        print(f"\n✅ Merged {len(merged_dfs)} CPID files into:")
        print(f"   {output_path}")
    
    return final_merged_df

def load_or_create_master_dataset(master_csv_path: Path):
    """
    Load existing master dataset or create a new one if it doesn't exist.
    """
    if master_csv_path.exists():
        print(f"📂 Loading existing master dataset from: {master_csv_path}")
        master_df = pd.read_csv(master_csv_path)
        print(f"   Loaded {len(master_df)} rows from master dataset")
    else:
        print(f"📝 Creating new master dataset at: {master_csv_path}")
        master_df = pd.DataFrame()
        master_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    return master_df

def update_master_dataset(master_df: pd.DataFrame, new_cpid_df: pd.DataFrame, master_csv_path: Path):
    """
    Update master dataset with new CPID data.
    
    Strategy:
    1. If master is empty, use new data
    2. Otherwise, append new rows (avoiding duplicates based on key columns if possible)
    """
    if new_cpid_df.empty:
        print("⚠ No new data to add to master dataset")
        return master_df
    
    # Define key columns for identifying duplicates (adjust based on your data)
    key_columns = ["Study Key", "Subject"]
    
    # Find actual key columns that exist in both dataframes
    available_keys = [col for col in key_columns 
                     if col in master_df.columns and col in new_cpid_df.columns]
    
    if master_df.empty:
        # First time - use new data
        updated_master = new_cpid_df.copy()
        print("✨ Created new master dataset with uploaded data")
    else:
        # Check if we have any overlapping data
        if available_keys:
            # Merge and keep only new rows
            existing_keys = set(zip(*[master_df[col] for col in available_keys]))
            new_rows_mask = []
            
            for idx, row in new_cpid_df.iterrows():
                row_key = tuple(row[col] for col in available_keys)
                new_rows_mask.append(row_key not in existing_keys)
            
            new_rows_only = new_cpid_df[new_rows_mask].copy()
            
            if len(new_rows_only) > 0:
                updated_master = pd.concat([master_df, new_rows_only], ignore_index=True)
                print(f"📈 Added {len(new_rows_only)} new rows to master dataset")
            else:
                updated_master = master_df.copy()
                print("📊 All data already exists in master dataset")
        else:
            # No key columns - just append
            updated_master = pd.concat([master_df, new_cpid_df], ignore_index=True)
            print(f"📈 Appended {len(new_cpid_df)} rows to master dataset")
    
    # Save updated master
    updated_master.to_csv(master_csv_path, index=False)
    print(f"💾 Master dataset saved to: {master_csv_path}")
    print(f"   Total rows: {len(updated_master)}")
    
    return updated_master

# =================================================
# MAIN PIPELINE ENTRY
# =================================================
def process_all_studies(root_dir: Path, final_qc_df: pd.DataFrame):
    """
    Process all studies and return list of processed CPID file paths.
    """
    if not root_dir.exists() or not root_dir.is_dir():
        raise ValueError(f"Invalid root directory: {root_dir}")

    print(f"🚀 Processing all studies in: {root_dir}")
    
    processed_cpid_files = []  # Track which files were processed

    for study_dir in root_dir.iterdir():
        if not study_dir.is_dir():
            continue

        print(f"\n📂 Study folder: {study_dir.name}")

        try:
            cpid_df = process_uploaded_study(study_dir, final_qc_df)
            if cpid_df is not None:
                # Find the CPID file that was just processed
                cpid_files = [
                    f for f in study_dir.iterdir()
                    if f.is_file()
                    and f.suffix.lower() == ".xlsx"
                    and "cpid" in f.name.lower()
                ]
                if cpid_files:
                    processed_cpid_files.append(cpid_files[0])
                    
        except FileNotFoundError as e:
            print(f"⚠ Skipping {study_dir.name}: {e}")
        except Exception as e:
            print(f"❌ Error processing {study_dir.name}: {e}")

    print("\n✅ All studies processed.")
    return processed_cpid_files


def create_final_output_from_files(cpid_file_paths: list, output_path: Path = None):
    """
    Create final merged output from specific CPID files.
    """
    if not cpid_file_paths:
        print("❌ No CPID files provided to merge")
        return None
    
    merged_dfs = []
    
    for cpid_file in cpid_file_paths:
        print(f"📂 Reading {cpid_file.name}")
        
        try:
            df = pd.read_excel(cpid_file)
            merged_dfs.append(df)
            print(f"   ✓ Successfully read {len(df)} rows")
        except Exception as e:
            print(f"   ❌ Error reading {cpid_file.name}: {e}")
            continue
    
    if not merged_dfs:
        print("❌ No CPID files could be read")
        return None
    
    # Concatenate in order
    final_merged_df = pd.concat(merged_dfs, ignore_index=True)
    
    # Save if output path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_merged_df.to_excel(output_path, index=False)
        print(f"\n✅ Merged {len(merged_dfs)} CPID files into:")
        print(f"   {output_path}")
    
    return final_merged_df


def get_latest_cpid_data(processed_cpid_files: list):
    """
    Get merged data from only the latest processed CPID files.
    """
    if not processed_cpid_files:
        print("⚠ No CPID files were processed in this run")
        return None
    
    print(f"\n📊 Getting data from {len(processed_cpid_files)} newly processed CPID files")
    return create_final_output_from_files(processed_cpid_files)


# =================================================
# MAIN PIPELINE ENTRY - UPDATED
# =================================================

def run_qc_pipeline(root_dir):
    """
    Entry point used by Streamlit.
    root_dir: Path or str - This is the extracted directory from uploaded ZIP
    """
    root_dir = Path(root_dir)
    
    if not root_dir.exists():
        raise ValueError(f"Directory does not exist: {root_dir}")
    
    print(f"Running QC pipeline on: {root_dir}")
    
    try:
        # Stage 1: Rename folders
        print("Stage 1: Renaming study folders...")
        rename_study_folders(root_dir)
        
        # Stage 2: Rename files
        print("Stage 2: Renaming files in study folders...")
        for study_dir in root_dir.iterdir():
            if study_dir.is_dir():
                rename_files_in_study_folder(study_dir)
        
        # Stage 3: Add study key
        print("Stage 3: Adding study keys...")
        add_study_key(root_dir)
        
        # Stage 4: Extract metrics
        print("Stage 4: Extracting metrics...")
        final_qc_df = extract_cols(root_dir)
        
        if final_qc_df.empty:
            print("Warning: No data extracted. Check input files.")
        else:
            print(f"Extracted {len(final_qc_df)} rows")
            print(final_qc_df.head())
        
        # Stage 5: Process CPID files and track which ones were processed
        print("\nStage 5: Processing CPID files...")
        processed_cpid_files = process_all_studies(root_dir, final_qc_df)
        
        # Stage 6: Create final merged output from ONLY newly processed files
        print("\nStage 6: Creating final output from newly processed files...")
        
        # Create output directory in the same location as uploaded data
        output_dir = root_dir.parent / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Create timestamped output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"QC_Results_{timestamp}.xlsx"
        
        # Get merged CPID data from ONLY the files we just processed
        merged_cpid_df = get_latest_cpid_data(processed_cpid_files)
        
        if merged_cpid_df is not None and not merged_cpid_df.empty:
            # Also save to the timestamped output file
            merged_cpid_df.to_excel(output_file, index=False)
            print(f"\n✅ Saved new QC results to: {output_file}")
        
        # Stage 7: Update master dataset with ONLY newly processed data
        print("\nStage 7: Updating master dataset with new data...")
        
        # Define master dataset path (relative to project root)
        project_root = Path(__file__).parent.parent.absolute()
        master_csv_path = project_root / "data" / "master_dataset.csv"
        
        # Load or create master dataset
        master_df = load_or_create_master_dataset(master_csv_path)
        
        if merged_cpid_df is not None and not merged_cpid_df.empty:
            # Update master dataset with new CPID data
            updated_master = update_master_dataset(master_df, merged_cpid_df, master_csv_path)
            print(f"✅ Master dataset updated with {len(merged_cpid_df)} NEW rows from this upload")
        else:
            print("⚠ No new CPID data to add to master dataset")
        
        # Also create a backup of the processed data
        backup_dir = output_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / f"processed_data_backup_{timestamp}.zip"
        
        # Create a zip backup of the processed folder
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in root_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(root_dir.parent)
                    zipf.write(file_path, arcname)
        
        print(f"📦 Backup created at: {backup_file}")
        
        # Return the QC dataframe for display in Streamlit
        return final_qc_df
        
    except Exception as e:
        print(f"Error in QC pipeline: {e}")
        import traceback
        traceback.print_exc()
        raise