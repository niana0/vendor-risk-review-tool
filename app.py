"""
Vendor Security Assessment Tool - Streamlit UI
"""
import streamlit as st
import os
import re
import glob
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import our modules
from src.document_parser import DocumentParser
from src.evidence_extractor import EvidenceExtractor
from src.questionnaire_mapper import QuestionnaireMapper
from src.risk_assessor import RiskAssessor
from src.risk_summary_generator import RiskSummaryGenerator
from src.security_doc_reviewer import SecurityDocReviewer
from src.completed_questionnaire_reviewer import CompletedQuestionnaireReviewer


# Page config
st.set_page_config(
    page_title="Vendor Security Assessment Tool",
    page_icon=None,
    layout="wide"
)

# Initialize session state
if 'processed' not in st.session_state:
    st.session_state.processed = False
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'theme' not in st.session_state:
    st.session_state.theme = 'Dark'
if 'review_mode' not in st.session_state:
    st.session_state.review_mode = None

THEMES = {
    'Light': {
        'app_bg': '#ffffff',
        'secondary_bg': '#f0f2f6',
        'sidebar_bg': '#f0f2f6',
        'text': '#262730',
        'subtext': '#555770',
        'border': '#d0d3e0',
        'input_bg': '#ffffff',
    },
    'Dark': {
        'app_bg': '#0e1117',
        'secondary_bg': '#1a1d27',
        'sidebar_bg': '#262730',
        'text': '#fafafa',
        'subtext': '#a0a3b0',
        'border': '#3a3d4d',
        'input_bg': '#1e2130',
    },
}

def apply_theme():
    t = THEMES[st.session_state.theme]
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {t['app_bg']};
            color: {t['text']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']};
        }}
        section[data-testid="stSidebar"] * {{
            color: {t['text']} !important;
        }}
        .stApp * {{
            color: {t['text']};
        }}
        .stTextInput > div > div, .stSelectbox > div > div,
        .stMultiSelect > div > div, .stFileUploader > div {{
            background-color: {t['input_bg']};
            border-color: {t['border']};
            color: {t['text']};
        }}
        .stExpander {{
            background-color: {t['secondary_bg']};
            border-color: {t['border']};
        }}
        [data-testid="stMetric"] {{
            background-color: {t['secondary_bg']};
            border-radius: 8px;
            padding: 12px;
        }}
        .stInfo, .stSuccess, .stWarning, .stError {{
            background-color: {t['secondary_bg']};
        }}
        hr {{
            border-color: {t['border']};
        }}
        caption, .stCaption {{
            color: {t['subtext']} !important;
        }}
        [data-testid="stHeader"] {{
            background-color: {t['app_bg']};
        }}
    </style>
    """, unsafe_allow_html=True)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

def get_latest_review_path() -> str | None:
    """Return the path of the most recently modified initial *_review.md file, or None.
    Excludes generated output files such as *_final_vendor_risk_review.md."""
    pattern = os.path.join(OUTPUT_DIR, "*_review.md")
    files = [
        f for f in glob.glob(pattern)
        if not os.path.basename(f).endswith("_final_vendor_risk_review.md")
    ]
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def load_initial_review() -> str:
    """Load the most recent vendor risk review saved by Claude via SKILL.md."""
    path = get_latest_review_path()
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_uploaded_file(uploaded_file, directory):
    """Save uploaded file to directory"""
    file_path = os.path.join(directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def _get_vendor_slug() -> str:
    review_path = get_latest_review_path()
    return os.path.basename(review_path).replace("_review.md", "") if review_path else "vendor"


# ── Process functions ──────────────────────────────────────────────────────────

def process_vendor_docs(vendor_files, progress_bar, status_text) -> dict | None:
    """Pipeline: DocumentParser → EvidenceExtractor → SecurityDocReviewer → RiskSummaryGenerator"""
    results = {}
    try:
        temp_dir = tempfile.mkdtemp()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        vendor_slug = _get_vendor_slug()

        status_text.text("📁 Saving uploaded files...")
        progress_bar.progress(10)
        vendor_paths = [save_uploaded_file(vf, temp_dir) for vf in vendor_files]

        status_text.text("📄 Parsing vendor documents...")
        progress_bar.progress(20)
        parser = DocumentParser()
        parsed_docs = parser.parse_all(vendor_paths)

        status_text.text("🔍 Extracting security evidence...")
        progress_bar.progress(40)
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all(parsed_docs)

        status_text.text("🔐 Reviewing security documents (SOC, pen test, policies)...")
        progress_bar.progress(70)
        sec_reviewer = SecurityDocReviewer()
        sec_reviewer.review(parsed_docs)
        results['sec_findings'] = sec_reviewer.findings

        status_text.text("📊 Saving reports...")
        progress_bar.progress(90)
        sec_doc_path = os.path.join(OUTPUT_DIR, f"{vendor_slug}_security_doc_review.docx")
        sec_reviewer.to_docx(sec_doc_path)
        results['sec_doc_path'] = sec_doc_path

        # Final Vendor Risk Review only when an initial review exists
        if load_initial_review():
            status_text.text("📝 Generating Final Vendor Risk Review...")
            progress_bar.progress(85)
            summary_generator = RiskSummaryGenerator()
            summary_generator.generate([], evidence)
            results['risk_summary'] = summary_generator.summary

            risk_summary_path = os.path.join(OUTPUT_DIR, f"{vendor_slug}_vendor_risk_summary.docx")
            summary_generator.to_docx(risk_summary_path)
            md_path = os.path.join(OUTPUT_DIR, f"{vendor_slug}_final_vendor_risk_review.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(summary_generator.summary)
            results['risk_summary_path'] = risk_summary_path
            results['risk_summary_md_path'] = md_path

        shutil.rmtree(temp_dir)
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")
        return results

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def process_completed_questionnaire(cq_file, progress_bar, status_text) -> dict | None:
    """Pipeline: load_questionnaire → CompletedQuestionnaireReviewer → save docx"""
    results = {}
    try:
        temp_dir = tempfile.mkdtemp()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        vendor_slug = _get_vendor_slug()

        status_text.text("📁 Saving uploaded file...")
        progress_bar.progress(20)
        cq_path = os.path.join(temp_dir, cq_file.name)
        with open(cq_path, "wb") as f:
            f.write(cq_file.read())

        status_text.text("📋 Loading questionnaire...")
        progress_bar.progress(50)
        cq_reviewer = CompletedQuestionnaireReviewer()
        qa_pairs = cq_reviewer.load_questionnaire(cq_path)

        status_text.text("🔍 Reviewing answers for security findings...")
        progress_bar.progress(80)
        cq_reviewer.review(qa_pairs)
        results['cq_findings'] = cq_reviewer.findings

        status_text.text("📊 Saving report...")
        progress_bar.progress(90)
        cq_excel_path = os.path.join(OUTPUT_DIR, f"{vendor_slug}_questionnaire_findings.xlsx")
        cq_reviewer.to_excel(cq_excel_path)
        results['cq_excel_path'] = cq_excel_path

        shutil.rmtree(temp_dir)
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")
        return results

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def process_fill_questionnaire(vendor_files, questionnaire_file, progress_bar, status_text) -> dict | None:
    """Pipeline: DocumentParser → EvidenceExtractor → QuestionnaireMapper → RiskAssessor"""
    results = {}
    try:
        temp_dir = tempfile.mkdtemp()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        vendor_slug = _get_vendor_slug()

        status_text.text("📁 Saving uploaded files...")
        progress_bar.progress(10)
        vendor_paths = [save_uploaded_file(vf, temp_dir) for vf in vendor_files]

        status_text.text("📄 Parsing vendor documents...")
        progress_bar.progress(20)
        parser = DocumentParser()
        parsed_docs = parser.parse_all(vendor_paths)

        status_text.text("🔍 Extracting security evidence...")
        progress_bar.progress(40)
        extractor = EvidenceExtractor()
        evidence = extractor.extract_all(parsed_docs)

        status_text.text("📋 Mapping evidence to questionnaire questions...")
        progress_bar.progress(65)
        questionnaire_path = save_uploaded_file(questionnaire_file, temp_dir)
        mapper = QuestionnaireMapper()
        questions = mapper.load_questionnaire(questionnaire_path)
        if not questions:
            st.error("Could not find questions in the questionnaire file. Please check the format.")
            return None
        mappings = mapper.map_evidence_to_questions(questions, evidence)
        results['mappings'] = mappings
        results['questions_count'] = len(mappings)

        status_text.text("⚠️ Performing risk assessment...")
        progress_bar.progress(80)
        assessor = RiskAssessor()
        risk_assessment = assessor.assess(mappings)
        results['risk_assessment'] = risk_assessment

        status_text.text("📊 Saving questionnaire...")
        progress_bar.progress(90)
        excel_path = os.path.join(OUTPUT_DIR, f"{vendor_slug}_completed_questionnaire.xlsx")
        mapper.to_excel(excel_path)
        results['excel_path'] = excel_path

        shutil.rmtree(temp_dir)
        progress_bar.progress(100)
        status_text.text("✅ Processing complete!")
        return results

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


# ── Display helpers ────────────────────────────────────────────────────────────

def _display_initial_review():
    """Show the initial vendor risk review block if present."""
    initial_review = load_initial_review()
    if initial_review:
        st.header("📄 Initial Vendor Risk Review")
        with st.expander("View Initial Vendor Risk Review", expanded=False):
            st.caption("Generated by Claude via the /vendor-risk-review skill.")
            st.markdown(initial_review)
        st.markdown("---")


def _render_sec_findings(sec_findings):
    """Render security document findings expanders."""
    if sec_findings:
        for finding in sec_findings:
            doc_type = finding.get('document_type', 'Document')
            filename = finding.get('filename', '')
            with st.expander(f"{doc_type}: {filename}"):
                if doc_type == "SOC Report":
                    st.markdown(f"**Company:** {finding.get('company_name', 'N/A')}")
                    st.markdown(f"**Report Type:** {finding.get('report_type', 'N/A')}")
                    st.markdown(f"**Audit Period:** {finding.get('audit_period', 'N/A')}")
                    st.markdown(f"**Auditing Firm:** {finding.get('auditor_company', 'N/A')}")
                    st.markdown(f"**Scope:** {finding.get('scope', 'N/A')}")
                    st.markdown(f"**Auditor's Opinion:** {finding.get('auditors_opinion', 'N/A')}")
                    st.markdown(f"**Exceptions:** {finding.get('exceptions', 'N/A')}")
                elif doc_type == "Penetration Test Report":
                    st.markdown(f"**Company:** {finding.get('company_name', 'N/A')}")
                    st.markdown(f"**Testing Period:** {finding.get('testing_period', 'N/A')}")
                    st.markdown(f"**Pen Tester:** {finding.get('pentester_company', 'N/A')}")
                    st.markdown(f"**Scope:** {finding.get('scope', 'N/A')}")
                    findings_list = finding.get('findings', [])
                    st.markdown("**Findings:**")
                    if isinstance(findings_list, list) and findings_list:
                        import pandas as pd
                        df = pd.DataFrame(findings_list)
                        if 'severity' in df.columns and 'description' in df.columns:
                            severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Informational': 4}
                            df['_order'] = df['severity'].map(lambda s: severity_order.get(s, 5))
                            df = df.sort_values('_order').drop(columns='_order')
                            df.columns = ['Severity', 'Description']
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            for item in findings_list:
                                st.markdown(f"- {item}")
                    else:
                        st.markdown(str(findings_list) if findings_list else "No findings listed.")
                    st.markdown(f"**Remediation Status:** {finding.get('remediation_status', 'N/A')}")
                elif doc_type == "Policy / Other Document":
                    st.markdown(f"**Document Title:** {finding.get('document_title', 'N/A')}")
                    st.markdown(f"**Category:** {finding.get('document_category', 'N/A')}")
                    st.markdown(f"**Company:** {finding.get('company_name', 'N/A')}")
                    st.markdown(f"**Effective / Approval Date:** {finding.get('effective_date', 'N/A')}")
                    st.markdown(f"**Summary:** {finding.get('summary', 'N/A')}")
                    key_points = finding.get('key_points', [])
                    if key_points:
                        st.markdown("**Key Points:**")
                        for point in key_points:
                            st.markdown(f"- {point}")
    else:
        st.info("No security documents detected in the uploaded files.")


def _split_what_changed(risk_summary: str):
    """Split risk_summary into (what_changed_md, full_review_md).

    Returns (None, full_text) if no What Changed section is present.
    """
    marker = "## What Changed from Initial Review"
    if marker not in risk_summary:
        return None, risk_summary

    idx = risk_summary.index(marker)
    after_marker = risk_summary[idx:]

    # The two parts are separated by a --- line
    sep = "\n---\n"
    if sep in after_marker:
        split_pos = after_marker.index(sep)
        what_changed = after_marker[:split_pos].strip()
        full_review = after_marker[split_pos + len(sep):].strip()
    else:
        # Fallback: split at the first top-level heading after the table
        lines = after_marker.split("\n")
        wc, rev, in_wc = [], [], True
        for line in lines[1:]:  # skip the marker line itself
            if in_wc and line.startswith("# ") and not line.startswith("## What"):
                in_wc = False
            (wc if in_wc else rev).append(line)
        what_changed = marker + "\n" + "\n".join(wc).strip()
        full_review = "\n".join(rev).strip()

    return what_changed, full_review


def _render_what_changed(what_changed: str):
    """Render the What Changed block."""
    st.markdown(what_changed)


def display_vendor_docs_results(results):
    """Display results for Tab 1 — Vendor Documentation Review."""
    _display_initial_review()

    # Final Vendor Risk Review — only when generated from an initial review
    if results.get('risk_summary'):
        st.header("📋 Final Vendor Risk Review")

        # Also try loading from saved MD file in case session state predates the prompt change
        risk_text = results['risk_summary']
        if "## What Changed from Initial Review" not in risk_text:
            vendor_slug = _get_vendor_slug()
            md_path = os.path.join(OUTPUT_DIR, f"{vendor_slug}_final_vendor_risk_review.md")
            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    risk_text = f.read()

        what_changed, full_review = _split_what_changed(risk_text)

        if what_changed:
            with st.expander("View Full Final Vendor Risk Review", expanded=False):
                st.info(
                    "Updated based on the uploaded vendor documents. "
                    "Actions resolved by the provided documentation have been removed. "
                    "Controls and risk summaries reflect what the documents confirm or reveal."
                )
                st.markdown(full_review)
            _render_what_changed(what_changed)
        else:
            st.info(
                "Updated based on the uploaded vendor documents. "
                "Actions resolved by the provided documentation have been removed. "
                "Controls and risk summaries reflect what the documents confirm or reveal."
            )
            st.markdown(risk_text)

        st.markdown("---")

    # Security Documentation Review
    st.header("🔐 Security Documentation Review")
    _render_sec_findings(results.get('sec_findings'))

    # Downloads
    st.subheader("📥 Download Reports")
    download_items = []
    if results.get('risk_summary_path') and os.path.exists(results['risk_summary_path']):
        download_items.append((results['risk_summary_path'], "📋 Download Final Vendor Risk Review (Word)",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    if results.get('sec_doc_path') and os.path.exists(results['sec_doc_path']):
        download_items.append((results['sec_doc_path'], "🔐 Download Security Doc Review (Word)",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    if download_items:
        cols = st.columns(len(download_items))
        for i, (path, label, mime) in enumerate(download_items):
            with cols[i]:
                with open(path, 'rb') as f:
                    st.download_button(label, f, file_name=os.path.basename(path), mime=mime)


SEV_CONFIG = {
    "High":          {"color": "#e74c3c", "bg": "#2d0a0a", "emoji": "🔴"},
    "Medium":        {"color": "#e67e22", "bg": "#2d1500", "emoji": "🟠"},
    "Low":           {"color": "#27ae60", "bg": "#0a2d15", "emoji": "🟢"},
    "Informational": {"color": "#3498db", "bg": "#0a1a2d", "emoji": "🔵"},
}

def _sev_badge(severity: str) -> str:
    cfg = SEV_CONFIG.get(severity, {"color": "#888", "bg": "#222"})
    return (
        f'<span style="background:{cfg["bg"]};color:{cfg["color"]};'
        f'border:1px solid {cfg["color"]};border-radius:4px;'
        f'padding:2px 8px;font-size:0.78em;font-weight:600;">'
        f'{severity}</span>'
    )


def display_cq_results(results):
    """Display results for Tab 2 — Completed Questionnaire Review."""
    _display_initial_review()

    st.header("🔍 Completed Questionnaire — Security Findings")

    all_entries = results.get('cq_findings', [])
    findings = [f for f in all_entries if f.get('is_finding')]
    info_items = [f for f in all_entries if f.get('is_informational')]

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Questions", len(all_entries))
    col2.metric("Findings", len(findings))
    col3.metric("🔴 High",   sum(1 for f in findings if f.get('severity') == 'High'))
    col4.metric("🟠 Medium", sum(1 for f in findings if f.get('severity') == 'Medium'))
    col5.metric("🟢 Low",    sum(1 for f in findings if f.get('severity') == 'Low'))
    col6.metric("🔵 Info",   len(info_items))

    st.markdown("")

    if findings:
        for severity in ["High", "Medium", "Low"]:
            sev_findings = [f for f in findings if f.get('severity') == severity]
            if not sev_findings:
                continue
            cfg = SEV_CONFIG[severity]
            st.markdown(
                f'<h3 style="color:{cfg["color"]};margin-top:1.2em;">'
                f'{cfg["emoji"]} {severity} <span style="font-weight:400;font-size:0.8em;">({len(sev_findings)})</span>'
                f'</h3>',
                unsafe_allow_html=True
            )
            for f in sev_findings:
                label = f"{cfg['emoji']} {f['question_id']} — {f.get('finding_title', '')}"
                with st.expander(label):
                    st.markdown(
                        f"**Severity:** {_sev_badge(severity)}",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**Question:** {f['question']}")
                    st.markdown(f"*Vendor answer: {f['vendor_answer']}*")
                    st.markdown(f"**Finding:** {f['description']}")
                    st.markdown(f"**Recommendation:** {f['recommendation']}")
    else:
        st.info("No security findings identified.")

    if info_items:
        cfg = SEV_CONFIG["Informational"]
        st.markdown(
            f'<h3 style="color:{cfg["color"]};margin-top:1.2em;">'
            f'{cfg["emoji"]} Informational <span style="font-weight:400;font-size:0.8em;">({len(info_items)})</span>'
            f'</h3>',
            unsafe_allow_html=True
        )
        for f in info_items:
            label = f"{cfg['emoji']} {f['question_id']} — {f.get('info_title', 'Document Referenced')}"
            with st.expander(label):
                st.markdown(
                    f"**Status:** {_sev_badge('Informational')}",
                    unsafe_allow_html=True
                )
                st.markdown(f"**Question:** {f['question']}")
                st.markdown(f"*Vendor answer: {f['vendor_answer']}*")
                st.markdown("**Note:** Vendor indicates a document has been provided. No finding raised.")
                st.markdown(f"**Recommendation:** {f['recommendation']}")

    # Downloads
    st.markdown("---")
    st.subheader("📥 Download Reports")
    if results.get('cq_excel_path') and os.path.exists(results['cq_excel_path']):
        with open(results['cq_excel_path'], 'rb') as f:
            st.download_button(
                "📊 Download Questionnaire with Findings (Excel)", f,
                file_name=os.path.basename(results['cq_excel_path']),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


def display_fill_questionnaire_results(results):
    """Display results for Tab 3 — Auto-Fill Questionnaire."""
    _display_initial_review()

    st.header("📋 Questionnaire Details")

    mappings = results.get('mappings', [])
    total = len(mappings)
    high = sum(1 for m in mappings if m['confidence'] == 'HIGH')
    medium = sum(1 for m in mappings if m['confidence'] == 'MEDIUM')
    low = sum(1 for m in mappings if m['confidence'] == 'LOW')
    not_found = sum(1 for m in mappings if m['confidence'] == 'NOT_FOUND')

    col_t, col_h, col_m, col_l, col_n = st.columns(5)
    col_t.metric("Total Questions", total)
    col_h.metric("🟢 High Confidence", high)
    col_m.metric("🟡 Medium Confidence", medium)
    col_l.metric("🟠 Low Confidence", low)
    col_n.metric("🔴 Not Answered", not_found)

    st.markdown("")

    filter_conf = st.multiselect(
        "Filter by Confidence Level",
        ['HIGH', 'MEDIUM', 'LOW', 'NOT_FOUND'],
        default=['HIGH', 'MEDIUM', 'LOW', 'NOT_FOUND']
    )

    def sort_key(m):
        qid = m.get('question_id', '')
        nums = re.findall(r'\d+', qid)
        return int(nums[0]) if nums else qid

    filtered_mappings = sorted(
        [m for m in mappings if m['confidence'] in filter_conf],
        key=sort_key
    )

    st.caption(f"Showing {len(filtered_mappings)} of {total} questions")

    for mapping in filtered_mappings:
        conf_emoji = {'HIGH': '🟢', 'MEDIUM': '🟡', 'LOW': '🟠', 'NOT_FOUND': '🔴'}.get(mapping['confidence'], '⚪')
        with st.expander(f"{conf_emoji} {mapping['question_id']}: {mapping['question']}"):
            st.write(f"**Answer:** {mapping['answer']}")
            st.write(f"**Confidence:** {mapping['confidence']}")
            if mapping['evidence']:
                st.write("**Evidence:**")
                for ev in mapping['evidence'][:2]:
                    st.write(f"- {ev['source']}")
                    st.caption(f"  {ev['evidence_text'][:200]}...")

    # Downloads
    st.markdown("---")
    st.subheader("📥 Download Reports")
    if results.get('excel_path') and os.path.exists(results['excel_path']):
        with open(results['excel_path'], 'rb') as f:
            st.download_button(
                "📊 Download Completed Questionnaire (Excel)", f,
                file_name=os.path.basename(results['excel_path']),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# Main UI
def main():
    st.title("Vendor Security Assessment Tool")
    st.markdown("---")

    apply_theme()

    # Sidebar
    with st.sidebar:
        theme_choice = st.radio("Theme", ['Light', 'Dark'], horizontal=True,
                                index=1 if st.session_state.theme == 'Dark' else 0)
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()

        st.markdown("---")
        st.header("About")
        st.markdown("""
        **Step 1 — Initial GRC Review**
        Run `/vendor-risk-review <ticket-id>` in Claude Code to generate an initial vendor risk review from Jira. The review will appear here automatically.

        **Step 2 — Choose a Review Type**

        - **Vendor Documentation Review** — Upload vendor security docs (SOC 2, pen test, policies) to get structured summaries and an updated risk review.
        - **Completed Questionnaire Review** — Upload a questionnaire the vendor has already filled out. The tool reads their answers and flags security findings.
        - **Auto-Fill Questionnaire** — Upload vendor docs and our blank questionnaire. The tool uses RAG to answer each question from the docs.

        **Step 3 — Download Reports**
        Download Word or Excel outputs ready for your GRC review.
        """)

        st.markdown("---")
        st.caption("Built with Streamlit & Claude Code")

    # "Start New Review" shown when processed or initial review exists
    if st.session_state.processed or load_initial_review():
        if st.button("🔄 Start New Review", type="secondary"):
            st.session_state.processed = False
            st.session_state.review_mode = None
            st.session_state.results = {}
            review_path = get_latest_review_path()
            if review_path and os.path.exists(review_path):
                os.remove(review_path)
            st.rerun()
        st.markdown("---")

    if not st.session_state.processed:
        # Show initial review if present
        initial_review = load_initial_review()
        if initial_review:
            st.header("📄 Initial Vendor Risk Review")
            st.caption("Generated by Claude via the /vendor-risk-review skill.")
            st.markdown(initial_review)
            st.markdown("---")

        # Three-tab upload section
        st.header("📤 Select Review Type")
        tab1, tab2, tab3 = st.tabs([
            "📄 Vendor Documentation Review",
            "🔍 Completed Questionnaire Review",
            "📋 Auto-Fill Questionnaire"
        ])

        with tab1:
            st.caption("Upload vendor security documentation to get structured summaries and an updated risk review.")
            vendor_files_1 = st.file_uploader(
                "Upload vendor documents (PDF, Excel)",
                type=['pdf', 'xlsx', 'xls'],
                accept_multiple_files=True,
                key="tab1_vendor_files"
            )
            if vendor_files_1:
                st.success(f"✅ {len(vendor_files_1)} file(s) uploaded")
                for vf in vendor_files_1:
                    st.caption(f"- {vf.name}")

            can_process_1 = bool(vendor_files_1)
            if st.button("Review Documents", type="primary", disabled=not can_process_1,
                         use_container_width=True, key="btn_tab1"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                with st.spinner("Processing..."):
                    results = process_vendor_docs(vendor_files_1, progress_bar, status_text)
                if results:
                    st.session_state.review_mode = 'vendor_docs'
                    st.session_state.processed = True
                    st.session_state.results = results
                    st.rerun()

        with tab2:
            st.caption("Upload a questionnaire the vendor has already filled out. The tool reads their answers and flags security findings.")
            cq_file = st.file_uploader(
                "Upload vendor-completed questionnaire (Excel)",
                type=['xlsx', 'xls'],
                key="tab2_cq_file"
            )
            if cq_file:
                st.success(f"✅ {cq_file.name}")

            can_process_2 = bool(cq_file)
            if st.button("Review Questionnaire", type="primary", disabled=not can_process_2,
                         use_container_width=True, key="btn_tab2"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                with st.spinner("Processing..."):
                    results = process_completed_questionnaire(cq_file, progress_bar, status_text)
                if results:
                    st.session_state.review_mode = 'completed_questionnaire'
                    st.session_state.processed = True
                    st.session_state.results = results
                    st.rerun()

        with tab3:
            st.caption("Upload vendor security documentation and our blank questionnaire. The tool uses RAG to answer each question from the docs.")
            vendor_files_3 = st.file_uploader(
                "Upload vendor documents (PDF, Excel)",
                type=['pdf', 'xlsx', 'xls'],
                accept_multiple_files=True,
                key="tab3_vendor_files"
            )
            if vendor_files_3:
                st.success(f"✅ {len(vendor_files_3)} file(s) uploaded")
                for vf in vendor_files_3:
                    st.caption(f"- {vf.name}")

            questionnaire_file = st.file_uploader(
                "Upload our blank questionnaire (Excel)",
                type=['xlsx', 'xls'],
                key="tab3_questionnaire"
            )
            if questionnaire_file:
                st.success(f"✅ {questionnaire_file.name}")

            can_process_3 = bool(vendor_files_3) and bool(questionnaire_file)
            if st.button("Auto-Fill Questionnaire", type="primary", disabled=not can_process_3,
                         use_container_width=True, key="btn_tab3"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                with st.spinner("Processing..."):
                    results = process_fill_questionnaire(vendor_files_3, questionnaire_file, progress_bar, status_text)
                if results:
                    st.session_state.review_mode = 'fill_questionnaire'
                    st.session_state.processed = True
                    st.session_state.results = results
                    st.rerun()

    else:
        mode = st.session_state.review_mode
        if mode == 'vendor_docs':
            display_vendor_docs_results(st.session_state.results)
        elif mode == 'completed_questionnaire':
            display_cq_results(st.session_state.results)
        elif mode == 'fill_questionnaire':
            display_fill_questionnaire_results(st.session_state.results)


if __name__ == "__main__":
    main()
