import streamlit as st
import re
from io import StringIO
from PyPDF2 import PdfReader
import pdfplumber

# =========================
# THEME & PAGE CONFIG
# =========================
st.set_page_config(page_title="DD PM Level Tool", page_icon="📊", layout="centered")

DD_RED = "#EB1700"

# Global CSS (light/dark friendly, DoorDash-inspired)
st.markdown(
    f"""
<style>
:root {{
  --dd-red: {DD_RED};
  --bg: #ffffff;
  --card: #ffffff;
  --text: #1a1a1a;
  --muted: #6b7280; /* slate-500 */
  --border: #e5e7eb; /* gray-200 */
  --success: #10b981;
  --warn: #f59e0b;
  --code-bg: #0f172a; /* slate-900 */
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0f1115;
    --card: #12151b;
    --text: #f4f6f9;
    --muted: #9aa3af; /* slate-400 */
    --border: #242a36; /* slate-800 */
    --code-bg: #0b1020;
  }}
}}

/* base */
html, body, .stApp {{ background: var(--bg) !important; color: var(--text) !important; }}

/* Header */
.dd-hero {{
  border-radius: 20px;
  padding: 24px 28px;
  margin: 12px 0 20px;
  background: linear-gradient(135deg, var(--dd-red), #ff5a3c);
  color: #fff;
  box-shadow: 0 10px 24px rgba(0,0,0,0.15);
}}
.dd-hero h1 {{
  margin: 0 0 6px 0; font-size: 28px; line-height: 1.1; font-weight: 800;
}}
.dd-hero p {{ margin: 0; opacity: .95; font-size: 14px; }}

/* Card */
.dd-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px; padding: 20px; margin: 12px 0; 
  box-shadow: 0 8px 20px rgba(2,6,23,0.08);
}}

.badge {{
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: 999px; font-size: 12px;
  font-weight: 600; letter-spacing: .2px; background: rgba(235,23,0,.1); color: var(--dd-red);
}}
.badge.success {{ background: rgba(16,185,129,.1); color: #10b981; }}
.badge.medium {{ background: rgba(59,130,246,.1); color: #3b82f6; }}
.badge.low {{ background: rgba(245,158,11,.12); color: #f59e0b; }}

/* Buttons */
.stButton>button {{
  background: var(--dd-red); border: none; color: #fff; font-weight: 700;
  padding: 10px 16px; border-radius: 12px; cursor: pointer; transition: transform .05s ease;
}}
.stButton>button:hover {{ filter: brightness(1.02); }}
.stButton>button:active {{ transform: translateY(1px); }}

/* Inputs */
.stTextInput>div>div>input, .stSelectbox>div div {{ color: var(--text) !important; }}
.stFileUploader label {{ color: var(--text) !important; }}

/* Code block (notes) */
pre code, .stCodeBlock {{ background: var(--code-bg) !important; color: #e5e7eb !important; }}

/* Section titles */
.h-section {{ font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .12em; margin: 6px 0 8px; }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# HEADER
# =========================
st.markdown(
    """
<div class="dd-hero">
  <h1>DD PM Level Intelligence</h1>
  <p>Upload a resume or RPS notes. Get a suggested level + HM-ready notes.</p>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# INPUTS
# =========================
with st.container():
    st.markdown('<div class="h-section">Candidate Inputs</div>', unsafe_allow_html=True)
    c1, c2 = st.columns((1,1))
    with c1:
        resume_file = st.file_uploader("Resume / Notes (PDF or TXT)", type=["pdf", "txt"])
        company = st.selectbox(
            "Current company",
            ["", "Meta", "Amazon", "Google", "Lyft", "Uber", "Stripe", "Startup", "Other"],
            index=0,
        )
        title = st.text_input("Current title (e.g., Sr PM, Lead PM)")
    with c2:
        yoe = st.selectbox("Years of Product Experience", ["", "0-2", "2-4", "4-7", "7-10", "10+"], index=0)
        domain = st.selectbox(
            "Area of Expertise",
            ["", "Generalist", "Growth", "Risk", "ML", "Platform", "Ads", "Merchant", "Logistics"],
            index=0,
        )
        submitted = st.button("📊 Predict Level & Generate Notes")

# =========================
# PDF PARSING + INFERENCE HELPERS
# =========================

def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\u00a0", " ", text)
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text_from_pdf(uploaded_file) -> str:
    """Use pdfplumber first, fall back to PyPDF2. Returns normalized text."""
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            parts = []
            for page in pdf.pages:
                try:
                    pt = page.extract_text() or ""
                    parts.append(pt)
                except Exception:
                    continue
            text = "\n".join(parts)
    except Exception:
        text = ""

    if not text or len(_normalize_text(text)) < 40:
        try:
            reader = PdfReader(uploaded_file)
            parts = []
            for p in reader.pages:
                try:
                    pt = p.extract_text() or ""
                    parts.append(pt)
                except Exception:
                    continue
            text = "\n".join(parts)
        except Exception:
            text = ""

    return _normalize_text(text)


def infer_fields_from_text(text: str):
    inferred = {"title": "", "yoe": "", "company": "", "domain": ""}
    if not text:
        return inferred

    t = text.lower()

    # YoE
    m = re.search(r"(\d{1,2})\+?\s*(?:years|yrs)\s*(?:of)?\s*(?:product|pm|experience|exp)", t)
    if m:
        yrs = int(m.group(1))
        inferred["yoe"] = "0-2" if yrs <= 2 else "2-4" if yrs <= 4 else "4-7" if yrs <= 7 else "7-10" if yrs <= 10 else "10+"

    # Title (pick highest seniority we detect)
    titles = [
        "group product manager", "principal product manager", "staff product manager",
        "lead product manager", "senior product manager", "product lead", "product manager",
    ]
    for tkn in titles:
        if tkn in t:
            inferred["title"] = tkn.title()
            break

    # Company (simple list)
    companies = [
        "doordash","meta","facebook","amazon","google","alphabet","microsoft","lyft","uber",
        "stripe","square","block","airbnb","tiktok","bytedance","snap","spotify","pinterest",
        "chime","yelp","walmart","netflix","apple","youtube","sofi","attentive","paramount",
    ]
    for c in companies:
        if re.search(rf"\b{re.escape(c)}\b", t):
            inferred["company"] = "DoorDash" if c == "doordash" else c.capitalize()
            break

    # Domain
    domain_map = {
        "fraud": "Risk", "risk": "Risk", "machine learning": "ML", "ml": "ML",
        "platform": "Platform", "ads": "Ads", "advertising": "Ads",
        "merchant": "Merchant", "logistics": "Logistics", "growth": "Growth",
    }
    for k, v in domain_map.items():
        if k in t:
            inferred["domain"] = v
            break

    return inferred

# =========================
# LEVELING LOGIC (SIMPLE HEURISTICS)
# =========================

def recommend_level(company, title, yoe, domain):
    score = 0
    yoe_map = {"0-2": 3, "2-4": 4, "4-7": 5, "7-10": 6, "10+": 7}
    if yoe in yoe_map:
        score += yoe_map[yoe]

    tl = (title or "").lower()
    if re.search(r"lead|principal|group", tl):
        score += 1
    if re.search(r"director|head", tl):
        score += 2

    if company in ["Meta", "Amazon", "Google", "Stripe"]:
        score += 1

    if domain in ["Risk", "ML", "Platform"]:
        score += 1

    if score <= 3:
        return "I4", "Low"
    elif score <= 5:
        return "I5", "Medium"
    elif score <= 7:
        return "I6", "High"
    else:
        return "I7", "Medium"

# =========================
# SUBMIT & OUTPUT UI
# =========================
if 'notes_block' not in st.session_state:
    st.session_state['notes_block'] = ''

if submitted:
    if not resume_file and not (company and title and yoe):
        st.error("Please upload a resume or fill in the fields above.")
    else:
        resume_text = ""
        if resume_file:
            if resume_file.type == "application/pdf":
                resume_text = extract_text_from_pdf(resume_file)
            else:
                try:
                    resume_text = _normalize_text(StringIO(resume_file.getvalue().decode("utf-8")).read())
                except Exception:
                    resume_text = ""

        inferred = infer_fields_from_text(resume_text)
        eff_company = company or inferred.get("company", "")
        eff_title = title or inferred.get("title", "")
        eff_yoe = yoe or inferred.get("yoe", "")
        eff_domain = domain or inferred.get("domain", "")

        if resume_file and resume_file.type == "application/pdf" and len(resume_text) < 80:
            st.warning("PDF might be scanned/image-based. If possible, upload a digital PDF or paste RPS notes.")

        level, confidence = recommend_level(eff_company, eff_title, eff_yoe, eff_domain)

        st.markdown("<div class='h-section'>Recommendation</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
<div class=\"dd-card\">
  <div style=\"display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;\">
    <div style=\"font-size:22px;font-weight:800;\">Suggested Level: <span style=\"color:var(--dd-red);\">{level}</span></div>
    <div class=\"badge {'success' if confidence=='High' else 'medium' if confidence=='Medium' else 'low'}\">Confidence: {confidence}</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        with st.expander("Parsed/Detected (for transparency)"):
            st.write(
                {
                    "company_input": company,
                    "title_input": title,
                    "yoe_input": yoe,
                    "domain_input": domain,
                    "inferred_company": inferred.get("company"),
                    "inferred_title": inferred.get("title"),
                    "inferred_yoe": inferred.get("yoe"),
                    "inferred_domain": inferred.get("domain"),
                }
            )

        rationale = f"Candidate appears aligned with **{level}** based on experience in **{eff_domain or 'General PM'}" + ""
        if eff_company:
            rationale += f"**, previously at **{eff_company}**"
        if eff_yoe:
            rationale += f" with **{eff_yoe}** years of product experience"
        rationale += "."
        if confidence == "Low":
            rationale += "\n\n⚠️ Minimal signal — recommend closer evaluation or deeper review."
        elif confidence == "High":
            rationale += "\n\n✅ Mirrors successful past hires at this level."

        notes_block = f"""```markdown
**Suggested level:** {level}  
**Confidence:** {confidence}  
{rationale}
```"""
        st.session_state['notes_block'] = notes_block

        st.markdown("<div class='h-section'>Notes to HM</div>", unsafe_allow_html=True)
        st.markdown(notes_block)
        st.caption("Tip: Copy the block above straight into Greenhouse.")

else:
    st.markdown(
        """
<div class=\"dd-hero\">
  <h1>DD PM Level Intelligence</h1>
  <p>Upload a resume or RPS notes. Get a suggested level + HM-ready notes.</p>
</div>
<div class='dd-card' style='text-align:center;'>
  <div style='font-size:16px;color:var(--muted);'>Drop a PDF or paste RPS notes to get a level rec.</div>
</div>
""",
        unsafe_allow_html=True,
    )
