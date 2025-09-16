import streamlit as st
from typing import Literal
import re
import random
from io import StringIO
from PyPDF2 import PdfReader

# -------------------------
# STYLE
# -------------------------
DD_RED = "#EB1700"

st.set_page_config(page_title="DD PM Level Tool", page_icon="📊", layout="centered")

st.markdown(f"""
    <style>
        .stApp {{
            background-color: #fff;
            color: #111;
            font-family: 'Inter', sans-serif;
        }}
        .title {{
            color: {DD_RED};
            font-weight: 700;
            font-size: 2.5em;
            margin-bottom: 0.2em;
        }}
        .subtext {{
            color: #555;
            font-size: 1.1em;
            margin-bottom: 2em;
        }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="title">DD PM Level Intelligence Tool</div>
    <div class="subtext">Upload a resume or intake note. We'll suggest a level + generate notes to HM.</div>
""", unsafe_allow_html=True)

# -------------------------
# INPUT FIELDS
# -------------------------
resume_file = st.file_uploader("Upload resume or recruiter notes (PDF or TXT)", type=["txt", "pdf"])
company = st.selectbox("Current company", ["", "Meta", "Amazon", "Google", "Lyft", "Uber", "Stripe", "Startup", "Other"])
title = st.text_input("Current title (e.g., Sr PM, Lead PM)")
yoe = st.selectbox("Years of Product Experience", ["", "0-2", "2-4", "4-7", "7-10", "10+"])
domain = st.selectbox("Area of Expertise", ["", "Generalist", "Growth", "Risk", "ML", "Platform", "Ads", "Merchant", "Logistics"])

submitted = st.button("📊 Predict Level + Generate Notes")

# -------------------------
# HELPER: Parse PDF Resume
# -------------------------
def extract_text_from_pdf(uploaded_file):
    try:
        pdf = PdfReader(uploaded_file)
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text
    except Exception as e:
        st.warning("Couldn't read PDF. Try uploading a text version instead.")
        return ""

# -------------------------
# LEVELING LOGIC (SIMPLIFIED)
# -------------------------
def recommend_level(company, title, yoe, domain):
    score = 0

    # YoE weight
    yoe_map = {"0-2": 3, "2-4": 4, "4-7": 5, "7-10": 6, "10+": 7}
    if yoe in yoe_map:
        score += yoe_map[yoe]

    # Title signal
    if re.search(r"lead|principal|group", title.lower()):
        score += 1
    if re.search(r"director|head", title.lower()):
        score += 2

    # Company mapping
    if company in ["Meta", "Amazon", "Google", "Stripe"]:
        score += 1

    # Domain bump
    if domain in ["Risk", "ML", "Platform"]:
        score += 1

    # Convert score to DD level
    if score <= 3:
        return "I4", "Low"
    elif score <= 5:
        return "I5", "Medium"
    elif score <= 7:
        return "I6", "High"
    else:
        return "I7", "Medium"

# -------------------------
# OUTPUT
# -------------------------
if submitted:
    if not resume_file and not (company and title and yoe):
        st.error("Please upload a resume or fill in the fields above.")
    else:
        # Auto-extract some values if possible from resume
        resume_text = ""
        if resume_file:
            if resume_file.type == "application/pdf":
                resume_text = extract_text_from_pdf(resume_file)
            else:
                stringio = StringIO(resume_file.getvalue().decode("utf-8"))
                resume_text = stringio.read()

        # Optional: add logic here to extract fields like title/yoe from resume_text

        level, confidence = recommend_level(company, title, yoe, domain)

        st.markdown("---")
        st.success(f"✅ **Recommended Level: `{level}`**")
        st.markdown(f"**Confidence:** {confidence}")

        # NOTES TO HM (Greenhouse style)
        rationale = f"Candidate appears aligned with **{level}** based on experience in **{domain or 'General PM'}" + ""
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
