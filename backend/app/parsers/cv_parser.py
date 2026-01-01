import re
import fitz
from pdf2image import convert_from_path
import pytesseract
from typing import Dict, Tuple, List
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util
import spacy

# LOAD NER MODEL
# Using spaCy's small English model
nlp = spacy.load("en_core_web_sm")

# PDF → TEXT + OCR FALLBACK
def pdf_to_text(path: str) -> str:
    """Extract text from digital PDFs."""
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            txt = page.get_text()
            if txt.strip():
                text += txt
        return text
    except:
        return ""


def pdf_to_text_ocr(path: str) -> str:
    """OCR extraction for scanned/image PDFs."""
    try:
        images = convert_from_path(path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
        return text
    except:
        return ""


def extract_text_from_pdf(path: str) -> str:
    """Automatic detection: digital first → else OCR."""
    text = pdf_to_text(path)
    if len(text.strip()) < 50:
        return pdf_to_text_ocr(path)
    return text

# SECTION EXTRACTION

HEADINGS = {
    "education": ["education", "academic background", "qualifications", "education & qualifications"],
    "experience": ["experience", "employment", "work history", "professional experience", "experience & employment"],
    "skills": ["skills", "technical skills", "core competencies", "skillset", "areas of expertise"],
    "projects": ["projects", "personal projects", "academic projects", "project", "portfolio"],
    "certifications": ["certifications", "certificates", "licenses", "coursework"],
    "summary": ["summary", "professional summary", "profile", "about"]
}

SECTION_PROTOTYPES = {
    "education": [
        "Bachelor of Science", "Master of Science", "university", "degree", "graduate"
    ],
    "experience": [
        "worked as", "experience at", "responsible for", "years of experience", "joined"
    ],
    "skills": [
        "skills", "proficient in", "programming languages", "technologies"
    ],
    "projects": [
        "project", "developed", "implemented", "built", "demonstrated", "portfolio"
    ],
    "certifications": [
        "certified", "certificate", "course completed", "issued by"
    ],
    "summary": [
        "summary", "profile", "objective", "about me", "undergraduate"
    ]
}

FUZZY_HEADING_THRESHOLD = 70
SEMANTIC_SIM_THRESHOLD = 0.45

_embed_model = SentenceTransformer("all-mpnet-base-v2")
_prototype_embeddings = {
    k: _embed_model.encode(" . ".join(v), convert_to_tensor=True)
    for k, v in SECTION_PROTOTYPES.items()
}

_heading_re = re.compile(r'^[A-Z][A-Z &/-]{2,}$')
_colon_re = re.compile(r':\s*$')


def is_likely_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if _heading_re.match(s) or _colon_re.search(s):
        return True
    if len(s.split()) <= 6 and any(any(k in s.lower() for k in variants) for variants in HEADINGS.values()):
        return True
    return False


def fuzzy_heading_match(line: str) -> Tuple[str, int]:
    line_l = line.lower()
    best = ("", 0)
    for sec, variants in HEADINGS.items():
        for v in variants:
            score = fuzz.token_sort_ratio(line_l, v)
            if score > best[1]:
                best = (sec, score)
    return best


def semantic_classify_paragraph(paragraph: str) -> Tuple[str, float]:
    if not paragraph.strip():
        return ("", 0.0)

    emb = _embed_model.encode(paragraph, convert_to_tensor=True)

    best_section, best_score = "", 0.0

    project_keywords = ["project", "developed", "built", "portfolio"]
    boost = 0.2 if any(k in paragraph.lower() for k in project_keywords) else 0.0

    for sec, proto_emb in _prototype_embeddings.items():
        sim = util.cos_sim(emb, proto_emb).item()
        if sec == "projects":
            sim += boost
        if sim > best_score:
            best_score, best_section = sim, sec

    return best_section, best_score


def improved_extract_sections(text: str) -> Dict[str, str]:
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [ln.rstrip() for ln in text.splitlines()]

    heading_positions = {}
    for i, ln in enumerate(lines):
        if is_likely_heading(ln):
            sec, score = fuzzy_heading_match(ln)
            if score >= FUZZY_HEADING_THRESHOLD:
                heading_positions[i] = sec
                continue
            if _heading_re.match(ln) or _colon_re.search(ln):
                sec2, score2 = fuzzy_heading_match(ln)
                heading_positions[i] = sec2 if score2 > 30 else "misc"

    sections = {k: "" for k in HEADINGS}
    sections["misc"] = ""
    current_sec = "misc"

    if heading_positions:
        for i, ln in enumerate(lines):
            if i in heading_positions:
                s = heading_positions[i]
                current_sec = s if s in sections else "misc"
                continue
            sections[current_sec] += ln + "\n"
    else:
        paragraphs = []
        buf = []
        for ln in lines:
            if ln.strip() == "":
                if buf:
                    paragraphs.append("\n".join(buf))
                    buf = []
                continue
            buf.append(ln)
        if buf:
            paragraphs.append("\n".join(buf))

        for para in paragraphs:
            sec, score = semantic_classify_paragraph(para)
            if score >= SEMANTIC_SIM_THRESHOLD:
                sections[sec] += para + "\n\n"
            else:
                sections["misc"] += para + "\n\n"

    return {k: v.strip() for k, v in sections.items() if v.strip()}

# CONTACT EXTRACTION (NER NAME + EMAIL/PHONE/LINKS)
# EMAIL
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

# PHONE REGEX
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-\.]?)?"      # optional country code
    r"(?:\(?\d{2,4}\)?[\s\-\.]?)?"   # optional area/initial code
    r"(?:\d{2,4}[\s\-\.]?){2,3}\d{2,4}"  # main number: 2–3 groups
)

# LINKS
LINKEDIN_RE = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/[A-Za-z0-9\/\-_\.]+",
    re.IGNORECASE
)
GITHUB_RE = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?github\.com\/[A-Za-z0-9\-_.]+\/?",
    re.IGNORECASE
)
URL_RE = re.compile(r"https?:\/\/[A-Za-z0-9\-_\.]+\.[A-Za-z]{2,}[^ \n]*")


def extract_emails(text: str) -> List[str]:
    return list(set(re.findall(EMAIL_RE, text)))


def extract_phone_numbers(text: str) -> List[str]:
    matches = re.findall(PHONE_RE, text)
    cleaned = []

    for m in matches:
        num = re.sub(r"[^\d+]", "", m)
        if 8 <= len(num) <= 15:
            cleaned.append(num)

    return list(set(cleaned))


def extract_links(text: str) -> Dict[str, List[str]]:
    linkedin = list(set(re.findall(LINKEDIN_RE, text)))
    github = list(set(re.findall(GITHUB_RE, text)))
    all_urls = list(set(re.findall(URL_RE, text)))

    # Remove LinkedIn/GitHub from generic URLs
    portfolio = [
        u for u in all_urls
        if "linkedin" not in u and "github" not in u
    ]

    return {
        "linkedin": linkedin,
        "github": github,
        "portfolio": portfolio
    }

def extract_name(text: str) -> str:
    lines = text.splitlines()

    # ---- 1. Detect ALL CAPS names ----
    for line in lines[:10]:  # only top lines
        l = line.strip()

        if not l:
            continue

        # Must be 2–4 words
        words = l.split()
        if not (2 <= len(words) <= 4):
            continue

        # All alphabetic words must be UPPERCASE
        if all(w.isalpha() and w.isupper() for w in words):
            return l.title()  # Convert to normal title case

    # ---- 2. Fallback: Proper case (First letter capital only) ----
    for line in lines[:10]:
        l = line.strip()

        if not l:
            continue

        words = l.split()

        if not (2 <= len(words) <= 4):
            continue

        # Skip generic words
        bad = {"resume", "curriculum", "vitae", "profile", "streamlit"}
        if l.lower() in bad:
            continue

        # Each word starts with capital letter
        if all(w[0].isupper() for w in words if w[0].isalpha()):
            return l

    # ---- 3. NER fallback ----
    doc = nlp(text)
    persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]

    blacklist = {"streamlit", "python", "developer", "resume"}
    persons = [p for p in persons if p.lower() not in blacklist]

    if persons:
        return persons[0]

    return ""

def extract_contact_info(text: str) -> Dict[str, any]:
    return {
        "name": extract_name(text),
        "emails": extract_emails(text),
        "phones": extract_phone_numbers(text),
        "links": extract_links(text)
    }

# FULL PIPELINE

def parse_resume(pdf_path: str) -> Dict[str, any]:
    text = extract_text_from_pdf(pdf_path)
    sections = improved_extract_sections(text)
    contacts = extract_contact_info(text)

    return {
        "raw_text": text,
        "contacts": contacts,
        "sections": sections
    }
