# pages/upload_app.py
import streamlit as st
from pathlib import Path
import zipfile
import shutil
import time
from qc_pipeline.pipeline import run_qc_pipeline

# Load external CSS from ../assets/css/upload.css
def load_css():
    # When running from pages directory, we need to go up one level more
    script_dir = Path(__file__).parent.absolute()  # This gives /pages
    project_root = script_dir.parent.absolute()    # This gives the project root
    
    # Construct the path to the CSS file
    css_path = project_root / "assets" / "css" / "upload.css"
    
    try:
        with open(css_path, "r") as f:
            css_content = f.read()
            # Add additional CSS for full-width styling and white metric text
            css_content += """
            /* Full width layout */
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                max-width: 100% !important;
            }
            
            /* Wide table styling */
            .dataframe {
                width: 100% !important;
                max-width: none !important;
                font-size: 16px !important;
            }
            
            .dataframe th {
                background: rgba(66, 153, 225, 0.25) !important;
                color: #ffffff !important;
                font-weight: 700 !important;
                padding: 16px 12px !important;
                text-align: center !important;
                font-size: 15px !important;
                border: none !important;
            }
            
            .dataframe td {
                padding: 14px 12px !important;
                text-align: center !important;
                border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
                font-size: 15px !important;
                min-width: 80px !important;
            }
            
            .dataframe tr:hover {
                background: rgba(66, 153, 225, 0.15) !important;
            }
            
            /* Remove table borders */
            .stDataFrame {
                border: none !important;
            }
            
            /* Wide columns layout */
            .stHorizontalBlock {
                width: 100% !important;
                gap: 1.5rem !important;
            }
            
            .stHorizontalBlock > div {
                min-width: 200px !important;
            }
            
            /* Wide containers */
            .stContainer {
                max-width: 100% !important;
            }
            
            /* Metric cards - wider */
            .metric-card {
                background: rgba(255, 255, 255, 0.07);
                border-radius: 16px;
                padding: 25px 20px;
                text-align: center;
                border-left: 5px solid #4299e1;
                min-height: 140px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                width: 100% !important;
            }
            
            .metric-value {
                font-size: 3.2rem !important;
                font-weight: 800 !important;
                color: #4299e1;
                margin: 5px 0;
                line-height: 1.2;
            }
            
            .metric-label {
                font-size: 1.1rem !important;
                color: #a0aec0;
                font-weight: 500;
                margin-top: 5px;
            }
            
            /* Title styling */
            h1 {
                font-size: 2.8rem !important;
                margin-bottom: 0.5rem !important;
            }
            
            h3 {
                font-size: 1.8rem !important;
                margin-top: 2rem !important;
                margin-bottom: 1rem !important;
            }
            
            /* Button styling */
            .stButton button {
                font-size: 1.4rem !important;
                padding: 22px !important;
                border-radius: 14px !important;
            }
            
            /* File info card - wider */
            .file-info-card {
                padding: 25px !important;
                font-size: 1.05rem !important;
            }
            
            .file-info-title {
                font-size: 1.3rem !important;
            }
            
            .file-info-detail {
                font-size: 1.05rem !important;
            }
            
            /* Upload container - wider */
            .upload-container {
                padding: 50px 40px !important;
                margin: 30px 0 !important;
            }
            
            .upload-text {
                font-size: 1.8rem !important;
            }
            
            .upload-subtext {
                font-size: 1.2rem !important;
            }
            
            /* Processing container */
            .processing-container {
                padding: 60px 40px !important;
            }
            
            .processing-icon {
                font-size: 64px !important;
            }
            
            /* Success message */
            .success-message {
                padding: 30px !important;
                font-size: 1.1rem !important;
            }
            
            /* Adjust Streamlit default spacing */
            section.main > div {
                max-width: 100% !important;
                padding-left: 1% !important;
                padding-right: 1% !important;
            }
            
            /* Column spacing */
            [data-testid="column"] {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                width: 100% !important;
            }
            
            /* Make everything use full width */
            .stApp {
                max-width: 100vw !important;
                overflow-x: hidden !important;
            }
            
            /* Remove any max-width constraints */
            div[data-testid="stVerticalBlock"] > div {
                max-width: none !important;
            }
            
            /* Statistics metrics - WHITE TEXT FOR DARK BACKGROUND */
            div[data-testid="stMetricLabel"] {
                color: #e2e8f0 !important;
                font-size: 1.2rem !important;
                font-weight: 600 !important;
            }
            
            div[data-testid="stMetricValue"] {
                color: #ffffff !important;
                font-size: 3rem !important;
                font-weight: 700 !important;
            }
            
            div[data-testid="stMetricDelta"] {
                color: #90cdf4 !important;
                font-size: 1.1rem !important;
            }
            
            /* Style the metric containers */
            div[data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.05) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 12px !important;
                padding: 20px !important;
            }
            
            /* Download button */
            .stDownloadButton button {
                font-size: 1.3rem !important;
                padding: 20px !important;
                margin-top: 30px !important;
            }
            """
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            return True
    except FileNotFoundError:
        # Fallback inline CSS with wide layout
        fallback_css = """
        <style>
            .main .block-container {
                max-width: 100% !important;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .stApp { background: linear-gradient(135deg, #0d0d0f 0%, #1b1b24 100%); }
            .upload-container { border: 2px dashed #4299e1; padding: 50px; border-radius: 20px; }
            h1, h2, h3 { color: #4299e1; }
            .dataframe { width: 100% !important; max-width: none !important; }
            .dataframe th, .dataframe td { padding: 15px !important; font-size: 16px !important; }
            [data-testid="column"] { width: 100% !important; }
            section.main > div { max-width: 100% !important; }
            /* White text for metrics */
            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricValue"],
            div[data-testid="stMetricDelta"] {
                color: white !important;
            }
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)
        return False
    except Exception as e:
        st.error(f"Error loading CSS: {e}")
        return False

# Page config - should be at the top with WIDE layout
st.set_page_config(
    page_title="Upload & Process Study Data",
    layout="wide",  # This is already set, but ensure it's here
    initial_sidebar_state="collapsed"
)

# Load CSS
load_css()

# =========================
# PAGE TITLE & DESCRIPTION - FULL WIDTH
# =========================
# Use single column for full width
st.markdown("<h1 style='text-align: center; font-size: 3rem;'>📤 Data Upload & Processing</h1>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #a0aec0; margin-bottom: 40px; font-size: 1.2rem;'>
    Upload your clinical study data in ZIP format. Our AI-powered pipeline will 
    automatically extract, standardize, and perform quality checks on your data.
</div>
""", unsafe_allow_html=True)

# =========================
# UPLOAD SECTION - FULL WIDTH
# =========================
st.markdown("""
<div class="upload-container" id="uploadContainer" style="width: 100%;">
    <div class="upload-icon">📁</div>
    <div class="upload-text">Drag & Drop Your ZIP File</div>
    <div class="upload-subtext">or click to browse (supports .zip format)</div>
</div>
""", unsafe_allow_html=True)

uploaded_zip = st.file_uploader(
    "",
    type=["zip"],
    key="file_uploader",
    label_visibility="collapsed"
)

BASE_UPLOAD_DIR = Path("uploaded_data")
BASE_UPLOAD_DIR.mkdir(exist_ok=True)

# =========================
# FILE PROCESSING - FULL WIDTH
# =========================
if uploaded_zip:
    # File info display - full width
    st.markdown(f"""
    <div class="file-info-card" style="width: 100%;">
        <div class="file-info-title">📄 File Uploaded Successfully</div>
        <div class="file-info-detail"><strong>Filename:</strong> {uploaded_zip.name}</div>
        <div class="file-info-detail"><strong>Size:</strong> {uploaded_zip.size / 1024 / 1024:.2f} MB</div>
        <div class="file-info-detail"><strong>Type:</strong> ZIP Archive</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create extraction directory
    extract_dir = BASE_UPLOAD_DIR / uploaded_zip.name.replace(".zip", "")
    
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    
    # Extract ZIP file
    with st.spinner("📂 Extracting ZIP archive..."):
        progress_bar = st.progress(0)
        with zipfile.ZipFile(uploaded_zip, "r") as zip_ref:
            file_list = zip_ref.namelist()
            total_files = len(file_list)
            
            for i, file in enumerate(file_list):
                zip_ref.extract(file, extract_dir)
                progress_bar.progress((i + 1) / total_files)
        
        progress_bar.empty()
    
    st.markdown(f"""
    <div class="success-message" style="width: 100%;">
        ✅ <strong>Extraction Complete!</strong><br>
        Files extracted to: <code>{extract_dir}</code><br>
        <small>Found {total_files} files in the archive</small>
    </div>
    """, unsafe_allow_html=True)
    
    # =========================
    # PROCESSING BUTTON - FULL WIDTH
    # =========================
    if st.button("🚀 **RUN QC PIPELINE**", use_container_width=True):
        # Create a processing container with animation
        processing_placeholder = st.empty()
        progress_bar = st.progress(0)
        results_placeholder = st.empty()
        
        try:
            # Show processing animation
            processing_placeholder.markdown("""
            <div class="processing-container" style="width: 100%;">
                <div class="processing-icon">⚙️</div>
                <h3 style="font-size: 2rem;">Analyzing Data...</h3>
                <p style="color: #a0aec0; font-size: 1.2rem;">
                    Running comprehensive quality checks on clinical data<br>
                    This may take a few moments
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Simulate processing with progress updates
            for i in range(1, 101, 5):
                progress_bar.progress(i)
                time.sleep(0.1)
            
            # Run the actual pipeline
            print(f"Starting QC pipeline on: {extract_dir}")
            final_qc_df = run_qc_pipeline(root_dir=extract_dir)
            
            # Complete progress
            progress_bar.progress(100)
            
            # Clear processing animation
            processing_placeholder.empty()
            
            # Show success message
            st.markdown(f"""
            <div class="success-message" style="text-align: center; width: 100%;">
                <div style="font-size: 64px;">🎉</div>
                <div style="font-size: 2rem; font-weight: 600; margin: 20px 0;">
                    Analysis Complete!
                </div>
                <div style="color: #a0aec0; font-size: 1.2rem;">
                    Successfully processed {len(final_qc_df)} rows of clinical data
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Display results
            with results_placeholder.container():
                st.markdown("### 📋 QC Analysis Results")
                
                # Summary metrics in cards - use 4 columns
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Create wider metric cards
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_studies = final_qc_df["Study Key"].nunique()
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{total_studies}</div>
                        <div class="metric-label">Total Studies</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    total_subjects = final_qc_df["Subject"].nunique()
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{total_subjects}</div>
                        <div class="metric-label">Total Subjects</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    coded_terms = final_qc_df["Coded"].sum() if "Coded" in final_qc_df.columns else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{coded_terms}</div>
                        <div class="metric-label">Coded Terms</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    uncoded_terms = final_qc_df["UnCoded"].sum() if "UnCoded" in final_qc_df.columns else 0
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{uncoded_terms}</div>
                        <div class="metric-label">Uncoded Terms</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # Dataframe with FULL WIDTH
                st.markdown("### 📊 Detailed Analysis Table")
                st.markdown("""
                <div style="margin: 20px 0; color: #a0aec0; font-size: 1.1rem;">
                    Complete quality check results for all studies
                </div>
                """, unsafe_allow_html=True)
                
                # Configure column display for better width
                column_config = {}
                for col in final_qc_df.columns:
                    if col == "Study Key":
                        column_config[col] = st.column_config.NumberColumn(
                            "Study ID", 
                            width="large",
                            help="Unique study identifier"
                        )
                    elif col == "Subject":
                        column_config[col] = st.column_config.TextColumn(
                            "Subject ID", 
                            width="xlarge",
                            help="Patient/subject identifier"
                        )
                    elif col in ["Coded", "UnCoded", "LnR", "EDRR", "Inactivated", "DM", "Safety", "Missing Pages", "Missing Visits"]:
                        column_config[col] = st.column_config.NumberColumn(
                            col, 
                            width="medium",
                            help=f"{col} metrics"
                        )
                    else:
                        column_config[col] = st.column_config.Column(width="medium")
                
                # Display dataframe with MAXIMUM width and height
                st.dataframe(
                    final_qc_df,
                    use_container_width=True,
                    height=700,  # Even taller for more rows
                    column_config=column_config,
                    hide_index=True
                )
                
                # Additional summary statistics with WHITE TEXT
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📈 Summary Statistics")
                
                # Use 3 columns for stats
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if "DM" in final_qc_df.columns:
                        total_dm = final_qc_df["DM"].sum()
                        avg_dm = final_qc_df["DM"].mean()
                        st.metric("Total DM Reviews", f"{total_dm:,}", f"Average: {avg_dm:.1f}")
                
                with col2:
                    if "Safety" in final_qc_df.columns:
                        total_safety = final_qc_df["Safety"].sum()
                        avg_safety = final_qc_df["Safety"].mean()
                        st.metric("Total Safety Reviews", f"{total_safety:,}", f"Average: {avg_safety:.1f}")
                
                with col3:
                    issues_total = 0
                    if "LnR" in final_qc_df.columns:
                        issues_total += final_qc_df["LnR"].sum()
                    if "EDRR" in final_qc_df.columns:
                        issues_total += final_qc_df["EDRR"].sum()
                    st.metric("Total Issues Found", f"{issues_total:,}")
                
                # Download button
                st.markdown("<br><br>", unsafe_allow_html=True)
                csv_data = final_qc_df.to_csv(index=False)
                st.download_button(
                    label="📥 **DOWNLOAD FULL ANALYSIS REPORT (CSV)**",
                    data=csv_data,
                    file_name=f"qc_analysis_report_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
        except Exception as e:
            st.error(f"❌ Error during processing: {str(e)}")
            import traceback
            with st.expander("See error details"):
                st.code(traceback.format_exc())

# =========================
# FOOTER - FULL WIDTH
# =========================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #718096; padding: 30px; font-size: 1rem; width: 100%;">
    <p style="font-size: 1.1rem;">🔒 Your data is processed locally and never stored on external servers</p>
    <p style="font-size: 0.9rem; margin-top: 15px;">
        Clinical Trial Data Quality System | v1.0
    </p>
</div>
""", unsafe_allow_html=True)

# Additional JavaScript to ensure full width (optional)
st.markdown("""
<script>
    // Ensure all elements use full width
    document.addEventListener('DOMContentLoaded', function() {
        // Remove any max-width constraints
        const containers = document.querySelectorAll('div[data-testid="stVerticalBlock"]');
        containers.forEach(container => {
            container.style.maxWidth = '100%';
            container.style.width = '100%';
        });
        
        // Make table containers full width
        const tables = document.querySelectorAll('.stDataFrame');
        tables.forEach(table => {
            table.style.width = '100%';
            table.style.maxWidth = 'none';
        });
        
        // Adjust column widths
        const columns = document.querySelectorAll('[data-testid="column"]');
        columns.forEach(col => {
            col.style.width = '100%';
            col.style.maxWidth = 'none';
        });
        
        // Ensure metric text is white
        const metricLabels = document.querySelectorAll('[data-testid="stMetricLabel"]');
        const metricValues = document.querySelectorAll('[data-testid="stMetricValue"]');
        const metricDeltas = document.querySelectorAll('[data-testid="stMetricDelta"]');
        
        metricLabels.forEach(label => label.style.color = '#e2e8f0');
        metricValues.forEach(value => value.style.color = '#ffffff');
        metricDeltas.forEach(delta => delta.style.color = '#90cdf4');
    });
</script>
""", unsafe_allow_html=True)