import streamlit as st
from typing import Literal
import re
from io import StringIO
from PyPDF2 import PdfReader

# -------------------------
# CONFIG
# -------------------------
DD_RED = "#EB1700"
st.set_page_config(page_title="DD PM Level Tool", page_icon="📊", layout="centered")

# -------------------------
# STYLE (DOORDASH THEME + DARK MODE)
# -------------------------
st.markdown(f"""
<style>
  :root {{
    --dd-red: {DD_RED};
    --bg: #ffffff;
    --surface: #ffffff;
    --text: #111111;
    --muted: #6b7280;
    --border: #e5e7eb;
    --shadow: 0 8px 24px rgba(2,6,23,.08);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f1115;
      --surface: #141922;
      --text: #f4f6f9;
      --muted: #9aa3af;
      --border: #232a36;
      --shadow: 0 10px 28px rgba(0,0,0,.35);
    }}
  }}

  .stApp {{
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  }}
  .title {{
    color: var(--text);
    font-weight: 800;
    font-size: clamp(28px, 4vw, 40px);
    margin-bottom: .2em;
  }}
  .subtext {{
    color: var(--muted);
    font-size: 1.05rem;
    margin-bottom: 1.6rem;
  }}
  .dd-hero {{
    background: linear-gradient(135deg, var(--dd-red), #ff5a3c);
    color: #fff;
    border-radius: 22px;
    padding: 26px 28px;
    margin: 6px 0 18px;
    box-shadow: 0 16px 36px rgba(235,23,0,.25);
  }}
  .dd-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px;
    box-shadow: var(--shadow);
  }}
  input, select, textarea {{
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow);
  }}
  .stTextInput input,
  .stSelectbox > div div,
  .stFileUploader label {{
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow);
  }}
  .stButton>button {{
    background: var(--dd-red) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700;
    padding: 10px 16px;
    box-shadow: 0 10px 24px rgba(235,23,0,.25);
    transition: transform .06s ease, filter .1s ease;
  }}
  .stButton>button:hover {{ filter: brightness(1.05); transform: translateY(-1px); }}
  .stButton>button:active {{ transform: translateY(0); }}
  pre code, .stCodeBlock {{
    background: #0f172a !important;
    color: #e5e7eb !important;
    border-radius: 14px !important;
    box-shadow: var(--shadow);
  }}
  @media (prefers-color-scheme: dark) {{
    pre code, .stCodeBlock {{ background: #0b1020 !important; }}
  }}
</style>
""", unsafe_allow_html=True)

# -------------------------
# HEADER
# -------------------------
st.markdown(f"""
<div class="dd-hero">
  <h1>DD PM Level Intelligence Tool</h1>
  <p>Upload a resume or intake note. We'll suggest a level + generate notes to HM.</p>
</div>
""", unsafe_allow_html=True)

# -------------------------
# INPUTS
# -------------------------
resume_file = st.file_uploader("Upload resume or recruiter notes (PDF or TXT)", type=["txt", "pdf"])
company = st.selectbox("Current company", ["", "Meta", "Amazon", "Google", "Lyft", "Uber", "Stripe", "Startup", "Other"])
title = st.text_input("Current title (e.g., Sr PM, Lead PM)")
yoe = st.selectbox("Years of Product Experience", ["", "0-2", "2-4", "4-7", "7-10", "10+"])
domain = st.selectbox("Area of Expertise", ["", "Generalist", "Growth", "Risk", "ML", "Platform", "Ads", "Merchant", "Logistics"])

submitted = st.button("📊 Predict Level + Generate Notes")

# -------------------------
# PDF PARSING
# -------------------------
def extract_text_from_pdf(uploaded_file):
    try:
        pdf = PdfReader(uploaded_file)
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text
    except Exception:
        st.warning("Couldn't read PDF. Try uploading a text version instead.")
        return ""

# -------------------------
# LEVELING LOGIC
# -------------------------
def recommend_level(company, title, yoe, domain):
    score = 0
    yoe_map = {"0-2": 3, "2-4": 4, "4-7": 5, "7-10": 6, "10+": 7}
    if yoe in yoe_map: score += yoe_map[yoe]
    if re.search(r"lead|principal|group", title.lower()): score += 1
    if re.search(r"director|head", title.lower()): score += 2
    if company in ["Meta", "Amazon", "Google", "Stripe"]: score += 1
    if domain in ["Risk", "ML", "Platform"]: score += 1
    if score <= 3: return "I4", "Low"
    elif score <= 5: return "I5", "Medium"
    elif score <= 7: return "I6", "High"
    else: return "I7", "Medium"

# -------------------------
# OUTPUT
# -------------------------
if submitted:
    if not resume_file and not (company and title and yoe):
        st.error("Please upload a resume or fill in the fields above.")
    else:
        resume_text = ""
        if resume_file:
            if resume_file.type == "application/pdf":
                resume_text = extract_text_from_pdf(resume_file)
            else:
                stringio = StringIO(resume_file.getvalue().decode("utf-8"))
                resume_text = stringio.read()

        level, confidence = recommend_level(company, title, yoe, domain)

        st.markdown("---")
        st.success(f"✅ **Recommended Level: `{level}`**")
        st.markdown(f"**Confidence:** {confidence}")

        rationale = f"Candidate appears aligned with **{level}** based on experience in **{domain or 'General PM'}"
        if company:
            rationale += f"**, previously at **{company}**"
        if yoe:
            rationale += f" with **{yoe}** years of product experience"
        rationale += "."
        if confidence == "Low":
            rationale += "\n\n⚠️ Minimal signal — recommend closer evaluation or deeper review."
        elif confidence == "High":
            rationale += "\n\n✅ Mirrors successful past hires at this level."

        st.markdown("### 📝 Notes to HM (Greenhouse-ready)")
        st.markdown(f"""
        ```markdown
        **Suggested level:** {level}  
        **Confidence:** {confidence}  
        {rationale}
        ```
        """)
        st.markdown("---")
        st.info("This is a beta version. Please validate against your team’s judgment.")
