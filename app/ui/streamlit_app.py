import streamlit as st
import json
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

st.set_page_config(
    page_title="Multi-Source Candidate Data Transformer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Base */
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"], .stApp {
    font-family: 'Inter', sans-serif !important;
    background: #e8f4ff !important;
    color: #0f2a52 !important;
}
.main .block-container {
    background: #ffffff !important;
    padding: 2rem 2.5rem 3rem !important;
    max-width: 1280px !important;
    border-left: 1px solid #c9dff7;
    min-height: 100vh;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: #1a3a6b !important;
    border-right: none !important;
    box-shadow: 3px 0 16px rgba(15,42,82,.22) !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.8rem 1.3rem !important; }
.sb-title {
    font-size: 15px; font-weight: 700; color: #e8f2ff;
    letter-spacing: -.1px; padding: .1rem 0;
}
.sb-label {
    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(180,210,255,.45);
    margin: 1.5rem 0 .55rem; display: block;
}
.sb-rule { border: none; border-top: 1px solid rgba(255,255,255,.08); margin: 1rem 0; }

/* Sidebar labels — tightly scoped */
[data-testid="stSidebar"] .stCheckbox > label,
[data-testid="stSidebar"] .stSlider > label,
[data-testid="stSidebar"] .stSelectbox > label {
    color: rgba(220,236,255,.88) !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stCheckbox p {
    color: rgba(220,236,255,.88) !important;
    font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255,255,255,.08) !important;
    border: 1px solid rgba(255,255,255,.15) !important;
    border-radius: 7px !important; color: #dceeff !important; font-size: 12.5px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:hover { border-color: rgba(99,162,255,.65) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill: rgba(255,255,255,.45) !important; }
[data-testid="stSidebar"] [data-baseweb="menu"] {
    background: #1e4580 !important; border: 1px solid rgba(255,255,255,.1) !important; border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="menu"] li { color: rgba(220,236,255,.9) !important; font-size: 12.5px !important; }
[data-testid="stSidebar"] [data-baseweb="menu"] li:hover { background: rgba(99,162,255,.2) !important; }

/* MAIN AREA — force readable dark text */
[data-testid="stMain"] { color: #0f2a52 !important; }
[data-testid="stMain"] p { color: #1e3d70 !important; }
[data-testid="stMain"] label { color: #0f2a52 !important; }
[data-testid="stMain"] .stCheckbox label,
[data-testid="stMain"] .stCheckbox p,
[data-testid="stMain"] .stCheckbox span:not([data-baseweb]) {
    color: #0f2a52 !important; font-size: 13.5px !important; font-weight: 500 !important;
}

/* Page header */
.page-title {
    font-size: 2rem; font-weight: 800; line-height: 1.2;
    margin-bottom: .45rem; color: #0f2a52; letter-spacing: -.4px;
}
.page-title .hl { color: #2563eb; }
.page-sub { font-size: 13px; color: #4a6a9e; margin-bottom: 1.6rem; line-height: 1.65; }

/* Section header */
.sec-header { display: flex; align-items: center; gap: .6rem; margin-bottom: .85rem; }
.sec-tag {
    font-size: 9.5px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    padding: 3px 9px; border-radius: 4px; display: inline-block;
}
.tag-s { background: #dbeafe; color: #1d4ed8; }
.tag-u { background: #ede9fe; color: #5b21b6; }
.sec-name { font-size: .95rem; font-weight: 700; color: #0f2a52; }

/* Upload card */
.upload-card {
    background: #f0f8ff; border: 1.5px solid #c0d8f5;
    border-radius: 10px; padding: 1.2rem 1.3rem; margin-bottom: .9rem;
    transition: border-color .15s, box-shadow .15s;
}
.upload-card:hover { border-color: #3b82f6; box-shadow: 0 2px 10px rgba(59,130,246,.1); }
.card-label {
    font-size: 10.5px; font-weight: 700; color: #6a8ab0;
    margin-bottom: .55rem; letter-spacing: .6px; text-transform: uppercase;
}

/* File uploader */
.stFileUploader label { display: none !important; }
[data-testid="stFileUploaderDropzone"] {
    background: #f7fbff !important; border: 1.5px dashed #a8c8f0 !important;
    border-radius: 8px !important; min-height: 96px !important; padding: 1rem !important;
    transition: all .15s !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #3b82f6 !important; background: #eaf3ff !important; }
[data-testid="stFileUploaderDropzone"] svg   { color: #7aaed4 !important; }
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] p     { color: #7aaed4 !important; font-size: 12px !important; }
[data-testid="stFileUploaderDropzone"] button {
    background: #2563eb !important; border: none !important;
    color: #ffffff !important; border-radius: 6px !important;
    font-size: 12px !important; font-weight: 600 !important; padding: 5px 14px !important;
}
[data-testid="stFileUploaderDropzone"] button:hover { background: #1d4ed8 !important; }
[data-testid="stFileUploaderFile"] {
    background: #dbeafe !important; border: 1px solid #93c5fd !important; border-radius: 6px !important;
}
[data-testid="stFileUploaderFile"] span { color: #1d4ed8 !important; font-size: 12px !important; }

/* Text input */
.stTextInput > label {
    font-size: 10.5px !important; font-weight: 700 !important;
    color: #6a8ab0 !important; letter-spacing: .6px !important; text-transform: uppercase !important;
}
.stTextInput > div > div > input {
    background: #f7fbff !important; border: 1.5px solid #c0d8f5 !important;
    border-radius: 8px !important; color: #0f2a52 !important;
    font-size: 13px !important; padding: .6rem .9rem !important;
}
.stTextInput > div > div > input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,.12) !important; }
.stTextInput > div > div > input::placeholder { color: #a8c8e8 !important; }

/* Divider */
.main-rule { border: none; border-top: 1px solid #d0e5f7; margin: 1.4rem 0; }

/* Alert bars */
.bar {
    padding: .72rem 1rem; border-radius: 7px; font-size: 13px;
    display: flex; align-items: flex-start; gap: .5rem; margin: .5rem 0 .9rem;
}
.bar-info    { background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; border-left: 3px solid #3b82f6; }
.bar-warn    { background: #fff7ed; border: 1px solid #fed7aa; color: #92400e; border-left: 3px solid #f59e0b; }
.bar-success { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; border-left: 3px solid #22c55e; }
.bar-empty   { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; border-left: 3px solid #ef4444; }

/* Run button */
.stButton > button {
    width: 100% !important; background: #2563eb !important;
    border: none !important; border-radius: 8px !important;
    color: #fff !important; font-size: 13.5px !important; font-weight: 700 !important;
    letter-spacing: .15px !important; padding: .72rem !important;
    box-shadow: 0 1px 3px rgba(37,99,235,.3), 0 4px 12px rgba(37,99,235,.16) !important;
    transition: background .15s, transform .1s !important;
}
.stButton > button:hover { background: #1d4ed8 !important; transform: translateY(-1px) !important; }
.stButton > button:active  { transform: translateY(0) !important; }
.stButton > button:disabled {
    background: #dbeafe !important; color: #93c5fd !important;
    box-shadow: none !important; cursor: not-allowed !important; border: 1.5px solid #bfdbfe !important;
}

/* Progress */
.stProgress > div > div {
    background: linear-gradient(90deg, #2563eb, #60a5fa) !important; border-radius: 3px !important;
}

/* Confidence badge */
.conf-badge {
    display: inline-flex; align-items: center; gap: .4rem;
    padding: 4px 11px; border-radius: 5px; font-size: 11.5px; font-weight: 700;
}
.cg { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.ca { background: #fff7ed; color: #b45309; border: 1px solid #fcd34d; }
.cr { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

/* Metrics */
[data-testid="stMetric"] {
    background: #f0f8ff; border: 1px solid #c0d8f5; border-radius: 8px;
    padding: .9rem 1.1rem; position: relative; overflow: hidden;
}
[data-testid="stMetric"]::before {
    content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: #3b82f6;
}
[data-testid="stMetricLabel"] { color: #6a8ab0 !important; font-size: 10px !important; text-transform: uppercase; letter-spacing: .9px; font-weight: 700 !important; }
[data-testid="stMetricValue"] { color: #0f2a52 !important; font-size: 1.4rem !important; font-weight: 800 !important; }

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid #c0d8f5 !important; border-radius: 8px !important;
    background: #f0f8ff !important; overflow: hidden;
}
[data-testid="stExpander"] summary { font-size: 12.5px !important; font-weight: 600 !important; color: #2563eb !important; padding: .65rem 1rem !important; }
[data-testid="stExpander"] summary:hover { color: #1d4ed8 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #dbeafe !important; border-radius: 8px !important;
    padding: 3px !important; gap: 3px !important; border: 1px solid #bfdbfe !important;
}
.stTabs [data-baseweb="tab"] { border-radius: 6px !important; color: #3b5998 !important; font-size: 12.5px !important; font-weight: 600 !important; padding: .42rem 1.1rem !important; }
.stTabs [aria-selected="true"] { background: #ffffff !important; color: #2563eb !important; box-shadow: 0 1px 3px rgba(37,99,235,.15) !important; }
.stJson { background: #f0f8ff !important; border: 1px solid #bfdbfe !important; border-radius: 8px !important; }

/* Download button */
.stDownloadButton > button {
    background: #ffffff !important; border: 1.5px solid #2563eb !important;
    color: #2563eb !important; border-radius: 8px !important;
    font-size: 13px !important; font-weight: 600 !important; width: 100% !important;
    transition: all .15s !important;
}
.stDownloadButton > button:hover { background: #2563eb !important; color: #ffffff !important; }

/* Top header / toolbar — make Deploy button visible */
[data-testid="stHeader"],
header[data-testid="stHeader"] {
    background: #ffffff !important;
    border-bottom: 1px solid #c9dff7 !important;
    box-shadow: 0 1px 4px rgba(15,42,82,.08) !important;
}
[data-testid="stHeader"] button,
[data-testid="stHeader"] a,
[data-testid="stHeader"] span,
[data-testid="stHeader"] p,
[data-testid="stToolbar"] button,
[data-testid="stToolbar"] span {
    color: #1a3a6b !important;
    opacity: 1 !important;
}
[data-testid="stHeader"] button:hover,
[data-testid="stToolbar"] button:hover {
    background: #e8f4ff !important;
    color: #0f2a52 !important;
}
/* Hamburger menu icon lines */
[data-testid="stHeader"] svg path,
[data-testid="stToolbar"] svg path {
    fill: #1a3a6b !important;
    stroke: #1a3a6b !important;
}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — all controls live here
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="sb-title">Candidate Transformer</div>', unsafe_allow_html=True)
    st.markdown('<hr class="sb-rule">', unsafe_allow_html=True)

    # ── Input Sources ────────────────────────────────────────────────────────
    st.markdown('<div class="sb-label">Input Sources</div>', unsafe_allow_html=True)
    use_csv      = st.checkbox("Recruiter CSV",  value=True,  key="use_csv")
    use_json     = st.checkbox("JSON File",       value=False, key="use_json")
    use_pdf      = st.checkbox("Resume PDF",      value=True,  key="use_pdf")
    use_linkedin = st.checkbox("LinkedIn Link",   value=False, key="use_linkedin")
    use_github   = False

    st.markdown('<hr class="sb-rule">', unsafe_allow_html=True)

    # ── Output Fields ────────────────────────────────────────────────────────
    st.markdown('<div class="sb-label">Output Fields</div>', unsafe_allow_html=True)
    show_name       = st.checkbox("Full Name",        value=True,  key="sf_name")
    show_email      = st.checkbox("Email",            value=True,  key="sf_email")
    show_phone      = st.checkbox("Phone",            value=True,  key="sf_phone")
    show_location   = st.checkbox("Location",         value=True,  key="sf_location")
    show_headline   = st.checkbox("Headline / Title", value=True,  key="sf_headline")
    show_skills     = st.checkbox("Skills",           value=True,  key="sf_skills")
    show_experience = st.checkbox("Work Experience",  value=True,  key="sf_exp")
    show_education  = st.checkbox("Education",        value=True,  key="sf_edu")

    st.markdown('<hr class="sb-rule">', unsafe_allow_html=True)

    # ── Export Format ────────────────────────────────────────────────────────
    st.markdown('<div class="sb-label">Export Format</div>', unsafe_allow_html=True)
    export_format = st.selectbox(
        "Download as",
        options=["JSON (Full)", "JSON (Projected)", "CSV (Flat)"],
        key="export_format",
        label_visibility="collapsed",
    )

    # Internal config
    min_confidence    = 0.5
    include_exec_meta = True
    load_sample       = False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA — Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="page-title">Multi-Source <span class="hl">Candidate Data</span> Transformer</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="page-sub">'
    'Upload your files using the selected sources on the left. '
    'The pipeline merges, deduplicates and normalises all sources automatically.'
    '</div>',
    unsafe_allow_html=True,
)

any_selected = any([use_csv, use_json, use_pdf, use_linkedin])
if not any_selected:
    st.markdown(
        '<div class="bar bar-empty">⚠️ Select at least one input source in the left panel to get started.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Upload widgets ───────────────────────────────────────────────────────────
col_struct, col_unstruct = st.columns(2, gap="large")

csv_file = json_file = pdf_file = None
linkedin_url = ""

with col_struct:
    st.markdown(
        '<div class="sec-header">'
        '<span class="sec-tag tag-s">Structured</span>'
        '<span class="sec-name">File Inputs</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    if use_csv:
        with st.container():
            st.markdown('<div class="upload-card"><div class="card-label">Recruiter CSV</div>', unsafe_allow_html=True)
            csv_file = st.file_uploader("csv", type=["csv"], key="csv_up", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
    if use_json:
        with st.container():
            st.markdown('<div class="upload-card"><div class="card-label">JSON File</div>', unsafe_allow_html=True)
            json_file = st.file_uploader("json", type=["json"], key="json_up", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)

with col_unstruct:
    st.markdown(
        '<div class="sec-header">'
        '<span class="sec-tag tag-u">Unstructured</span>'
        '<span class="sec-name">Documents & Links</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    if use_pdf:
        with st.container():
            st.markdown('<div class="upload-card"><div class="card-label">Resume PDF</div>', unsafe_allow_html=True)
            pdf_file = st.file_uploader("pdf", type=["pdf"], key="pdf_up", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
    if use_linkedin:
        with st.container():
            st.markdown('<div class="upload-card"><div class="card-label">LinkedIn Profile URL</div>', unsafe_allow_html=True)
            linkedin_url = st.text_input("linkedin_url", placeholder="https://linkedin.com/in/username",
                                         key="li_url", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<hr class="main-rule">', unsafe_allow_html=True)

# ─── Run button ───────────────────────────────────────────────────────────────
run_disabled = not any([csv_file, json_file, pdf_file, linkedin_url])
run = st.button(
    "⚡  Run Transformation Pipeline",
    disabled=run_disabled,
    use_container_width=True,
)
if run_disabled and not run:
    st.markdown(
        '<div class="bar bar-info">ℹ️ Upload at least one file or paste a URL above, then click Run.</div>',
        unsafe_allow_html=True,
    )

# ─── Pipeline execution ───────────────────────────────────────────────────────
if run:
    progress = st.progress(0)
    status   = st.empty()

    try:
        # ── Write temp files ──────────────────────────────────────────────────
        status.markdown('<div class="bar bar-info">⚙️ Writing temp files…</div>', unsafe_allow_html=True)
        progress.progress(15)

        csv_path = resume_path = json_path = linkedin_path = ""

        if csv_file:
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
            tf.write(csv_file.read()); tf.flush(); tf.close()
            csv_path = tf.name

        if json_file:
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            tf.write(json_file.read()); tf.flush(); tf.close()
            json_path = tf.name

        if pdf_file:
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tf.write(pdf_file.read()); tf.flush(); tf.close()
            resume_path = tf.name

        if linkedin_url.strip():
            linkedin_path = linkedin_url.strip()

        # ── Build temp configs ────────────────────────────────────────────────
        progress.progress(30)
        proj_config = {
            "candidate_id": "candidate_id",
            "candidate_name": "full_name",
            "primary_email": "emails[0]",
            "all_emails": "emails",
            "primary_phone": "phones[0]",
            "city": "location.city",
            "region": "location.region",
            "country": "location.country",
            "headline": "experience[0].title",
            "skills_count": "skills|length",
        }
        merge_config = {
            "strategy": "priority_order",
            "source_priority": ["resume", "csv", "linkedin"],
            "dedup_threshold": 85,
            "conflict_resolution": "highest_confidence",
        }

        tf_proj  = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
        json.dump(proj_config, tf_proj); tf_proj.flush(); tf_proj.close()
        tmp_config = tf_proj.name

        tf_merge = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
        json.dump(merge_config, tf_merge); tf_merge.flush(); tf_merge.close()
        tmp_merge = tf_merge.name

        # ── Run pipeline ──────────────────────────────────────────────────────
        status.markdown('<div class="bar bar-info">🔀 Running pipeline…</div>', unsafe_allow_html=True)
        progress.progress(50)

        import importlib
        import app.services.transformation_service as _ts_mod
        importlib.reload(_ts_mod)
        TransformationService = _ts_mod.TransformationService

        result = TransformationService().transform(
            csv_path          = csv_path if os.path.isfile(csv_path) else "",
            resume_path       = resume_path if os.path.isfile(resume_path) else "",
            config_path       = tmp_config,
            linkedin_path     = linkedin_path,
            merge_config_path = tmp_merge,
        )

        progress.progress(95)
        status.empty()
        progress.progress(100)

        # ── Results ───────────────────────────────────────────────────────────
        report  = result.get("data_quality_report", {})
        profile = result["canonical_profile"]
        conf    = profile.get("overall_confidence", 0.0)

        st.markdown(
            f'<div class="bar bar-success">✅ Transformation complete — '
            f'{len(report.get("sources_processed", []))} source(s) merged.</div>',
            unsafe_allow_html=True,
        )

        if conf >= 0.85:
            bcls, btxt = "cg", f"● HIGH  {conf:.0%}"
        elif conf >= min_confidence:
            bcls, btxt = "ca", f"◐ MODERATE  {conf:.0%}"
        else:
            bcls, btxt = "cr", f"○ LOW — below threshold ({min_confidence:.0%})"
        st.markdown(
            f'<div style="margin:.8rem 0 1.2rem">'
            f'<span class="conf-badge {bcls}">{btxt}</span></div>',
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Sources Processed", len(report.get("sources_processed", [])))
        m2.metric("Sources Failed",    len(report.get("sources_failed", [])))
        m3.metric("Skills Detected",   report.get("skill_count", 0))
        m4.metric("Confidence",        f"{conf:.1%}")


        with st.expander("📊 Data Quality Report", expanded=False):
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown("**Sources Processed**")
                for s in report.get("sources_processed", []):
                    st.markdown(f"- ✅ `{s}`")
                for s in report.get("sources_failed", []):
                    st.markdown(f"- ❌ `{s}` (skipped)")
            with rc2:
                miss = report.get("fields_missing", [])
                if miss:
                    st.markdown("**Missing Fields**")
                    for f in miss:
                        st.markdown(f"- `{f}`")



        tab1, tab2, tab3 = st.tabs(["Canonical Profile", "Projected Output", "Raw JSON"])
        with tab1: st.json(profile)
        with tab2: st.json(result["projected_output"])
        with tab3: st.json(result)

        if export_format == "JSON (Full)":
            dl_data, dl_name, dl_mime = json.dumps(result, indent=4, default=str), "candidate_full.json", "application/json"
        elif export_format == "JSON (Projected)":
            dl_data, dl_name, dl_mime = json.dumps(result["projected_output"], indent=4, default=str), "candidate_projected.json", "application/json"
        else:
            import csv, io as _io
            flat = {**result["projected_output"]}
            flat["skills"] = " | ".join(s["name"] if isinstance(s, dict) else str(s) for s in profile.get("skills", []))
            buf = _io.StringIO()
            w   = csv.DictWriter(buf, fieldnames=list(flat.keys()))
            w.writeheader()
            w.writerow({k: (str(v) if v is not None else "") for k, v in flat.items()})
            dl_data, dl_name, dl_mime = buf.getvalue(), "candidate_flat.csv", "text/csv"

        st.download_button(
            label=f"⬇  Download — {export_format}",
            data=dl_data, file_name=dl_name, mime=dl_mime, use_container_width=True,
        )

    except Exception as exc:
        import traceback
        st.markdown(
            f'<div class="bar bar-warn">❌ Pipeline error: {exc}</div>',
            unsafe_allow_html=True,
        )
        with st.expander("Full traceback"):
            st.code(traceback.format_exc(), language="python")