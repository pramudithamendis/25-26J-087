import re
import fitz
from pdf2image import convert_from_path
import pytesseract
from typing import Dict, Tuple, List, Optional
from rapidfuzz import fuzz

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    import spacy
    _CV_ML_AVAILABLE = True
except ImportError:
    _CV_ML_AVAILABLE = False


_nlp = None
_embed_model = None
_prototype_embeddings = None

def get_nlp():
    if not _CV_ML_AVAILABLE:
        raise RuntimeError("spacy is not installed in this environment")
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def get_embed_model():
    if not _CV_ML_AVAILABLE:
        raise RuntimeError("sentence_transformers is not installed in this environment")
    global _embed_model, _prototype_embeddings
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-mpnet-base-v2")
        _prototype_embeddings = {
            k: _embed_model.encode(" . ".join(v), convert_to_tensor=True)
            for k, v in SECTION_PROTOTYPES.items()
        }
    return _embed_model, _prototype_embeddings

# =======================================================
# 1. PDF → TEXT + OCR FALLBACK
# =======================================================

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


# =======================================================
# 2. SECTION HEADINGS & PROTOTYPE KEYWORDS
# =======================================================

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
        sim = st_util.cos_sim(emb, proto_emb).item()
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


# =======================================================
# 3. CONTACT EXTRACTION (NER NAME + EMAIL/PHONE/LINKS)
# =======================================================

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-\.]?)?"
    r"(?:\(?\d{2,4}\)?[\s\-\.]?)?"
    r"(?:\d{2,4}[\s\-\.]?){2,3}\d{2,4}"
)

LINKEDIN_RE = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/[A-Za-z0-9\/\-_\.]+",
    re.IGNORECASE
)
GITHUB_RE = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?github\.com\/[A-Za-z0-9\-_.]+\/?",
    re.IGNORECASE
)
URL_RE = re.compile(r"https?:\/\/[A-Za-z0-9\-_\.]+\.[A-Za-z]{2,}[^ \n]*")

ADDRESS_RE = re.compile(
    r"\d{1,5}\s[\w\s]{2,30}(Street|St|Road|Rd|Lane|Ave|Avenue|Drive|Dr)\,?\s*[\w\s]{2,30}\,?\s*\w{2,10}",
    re.IGNORECASE
)


def extract_emails(text: str) -> List[str]:
    return list(set(re.findall(EMAIL_RE, text)))


def extract_phone_numbers(text: str) -> List[str]:
    matches = re.findall(PHONE_RE, text)
    cleaned = [re.sub(r"[^\d+]", "", m) for m in matches if 8 <= len(re.sub(r"[^\d+]", "", m)) <= 15]
    return list(set(cleaned))


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def extract_links(text: str) -> Dict[str, List[str]]:
    linkedin = list(set(re.findall(LINKEDIN_RE, text)))
    github = list(set(re.findall(GITHUB_RE, text)))
    all_urls = list(set(re.findall(URL_RE, text)))

    portfolio = [
        u for u in all_urls
        if "linkedin" not in u and "github" not in u
    ]

    linkedin  = [normalize_url(u) for u in linkedin]
    github    = [normalize_url(u) for u in github]
    portfolio = [normalize_url(u) for u in portfolio]

    return {
        "linkedin":  linkedin,
        "github":    github,
        "portfolio": portfolio
    }


def extract_name(text: str) -> str:
    lines = text.splitlines()
    # ALL CAPS detection
    for line in lines[:10]:
        l = line.strip()
        words = l.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() and w.isupper() for w in words):
            return l.title()
    # Proper case fallback
    for line in lines[:10]:
        l = line.strip()
        words = l.split()
        if 2 <= len(words) <= 4:
            bad = {"resume", "curriculum", "vitae", "profile", "streamlit"}
            if l.lower() not in bad and all(w[0].isupper() for w in words if w[0].isalpha()):
                return l
    # NER fallback
    doc = get_nlp()(text)
    persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
    blacklist = {"streamlit", "python", "developer", "resume"}
    persons = [p for p in persons if p.lower() not in blacklist]
    return persons[0] if persons else ""


def extract_address(text: str) -> Optional[str]:
    lines = text.splitlines()
    for line in lines[:15]:
        match = ADDRESS_RE.search(line)
        if match:
            return match.group(0).strip()
    return None


def extract_contact_info(text: str) -> Dict[str, any]:
    links = extract_links(text)
    return {
        "name":   extract_name(text),
        "emails": extract_emails(text),
        "phones": extract_phone_numbers(text),
        "address": extract_address(text),
        "links": {
            "linkedin":  links.get("linkedin", []),
            "github":    links.get("github", []),
            "portfolio": links.get("portfolio", [])
        }
    }


# =======================================================
# 4. STRUCTURED SECTION PARSERS
# =======================================================

DATE_RANGE_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|"
    r"April|June|July|August|September|October|November|December)?\s*\d{4}"
    r"\s*[–\-—]\s*"
    r"(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|"
    r"April|June|July|August|September|October|November|December)?\s*\d{4}"
    r"|Present|present|Current|current)",
    re.IGNORECASE
)


def extract_date_range(text: str) -> Dict[str, str]:
    match = DATE_RANGE_RE.search(text)
    if not match:
        return {"start": "", "end": ""}
    full = match.group(0)
    parts = re.split(r"[–\-—]", full, maxsplit=1)
    return {
        "start": parts[0].strip() if len(parts) > 0 else "",
        "end":   parts[1].strip() if len(parts) > 1 else ""
    }


def parse_experience(text: str) -> List[Dict]:
    """
    Parses experience section text into a list of job dicts.
    Expects blocks like:
        Senior Software Engineer — DataSpark Inc.
        Jan 2022 – Present
        • bullet one
        • bullet two
    """
    if not text.strip():
        return []

    JOB_TITLE_RE = re.compile(r"^(?![•\-\*])(.+?)\s*[—\-–]\s*(.+)$")

    lines = text.splitlines()
    blocks: List[List[str]] = []
    current: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if (JOB_TITLE_RE.match(stripped)
                and not stripped.startswith(("•", "-", "*"))
                and not DATE_RANGE_RE.search(stripped)):
            if current:
                blocks.append(current)
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        blocks.append(current)

    jobs = []
    for block in blocks:
        if not block:
            continue

        title, company, start, end = "", "", "", ""
        bullets: List[str] = []

        for i, line in enumerate(block):
            if i == 0:
                m = JOB_TITLE_RE.match(line)
                if m:
                    title   = m.group(1).strip()
                    company = m.group(2).strip()
                continue

            if DATE_RANGE_RE.search(line) and not line.startswith(("•", "-", "*")):
                dates = extract_date_range(line)
                start, end = dates["start"], dates["end"]
                continue

            if line.startswith(("•", "-", "*")):
                bullets.append(line.lstrip("•-* ").strip())
            else:
                bullets.append(line.strip())

        if title or company:
            jobs.append({
                "position":  title,
                "name":      company,
                "startDate": start,
                "endDate":   end,
                "highlights": bullets
            })

    return jobs


def parse_education(text: str) -> List[Dict]:
    """
    Parses education section text into a list of education dicts.
    Expects blocks like:
        Bachelor of Science in Computer Science
        Aug 2014 – May 2018
        University of California, Berkeley · GPA 3.7 / 4.0
        Relevant coursework: Algorithms, ...
    """
    if not text.strip():
        return []

    DEGREE_KEYWORDS = re.compile(
        r"\b(Bachelor|Master|PhD|Doctor|Associate|B\.S|M\.S|B\.A|M\.A|BSc|MSc|BEng|MEng)\b",
        re.IGNORECASE
    )

    lines = text.splitlines()
    blocks: List[List[str]] = []
    current: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if DEGREE_KEYWORDS.search(stripped):
            if current:
                blocks.append(current)
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        blocks.append(current)

    entries = []
    for block in blocks:
        degree, institution, start, end, gpa, coursework = "", "", "", "", "", ""

        for i, line in enumerate(block):
            if i == 0:
                degree = line.strip()
                continue

            if DATE_RANGE_RE.search(line):
                dates = extract_date_range(line)
                start, end = dates["start"], dates["end"]
                continue

            if re.search(r"GPA|gpa", line):
                institution_part = re.split(r"[·•|]", line)[0].strip()
                institution = institution_part
                gpa_match = re.search(
                    r"GPA\s*[:\s]*([\d\.]+\s*/\s*[\d\.]+|[\d\.]+)", line, re.IGNORECASE
                )
                if gpa_match:
                    gpa = gpa_match.group(1).strip()
                continue

            if re.search(r"coursework|relevant|courses", line, re.IGNORECASE):
                coursework = re.sub(r"^[Rr]elevant\s+coursework\s*:\s*", "", line).strip()
                continue

            if not institution and not DATE_RANGE_RE.search(line):
                institution = line.strip()

        if degree:
            entries.append({
                "studyType":   degree,
                "institution": institution,
                "area":        "",  # Field not explicitly parsed yet
                "startDate":   start,
                "endDate":     end,
                "gpa":         gpa,
                "courses":     [coursework] if coursework else []
            })

    return entries


def parse_skills(text: str) -> List[Dict]:
    """
    Parses skills section text into a list of category/items dicts.
    Expects lines like:
        Programming Languages: Python, JavaScript, TypeScript
    Or plain comma-separated lists.
    """
    if not text.strip():
        return []

    skills = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            category, _, items_str = line.partition(":")
            items = [s.strip() for s in re.split(r"[,;]", items_str) if s.strip()]
            skills.append({
                "name":     category.strip(),
                "keywords": items
            })
        else:
            items = [s.strip() for s in re.split(r"[,;•\-]", line) if s.strip()]
            if items:
                skills.append({
                    "name":     "General",
                    "keywords": items
                })

    return skills


def parse_projects(text: str) -> List[Dict]:
    """
    Parses projects section text into a list of project dicts.
    Expects blocks like:
        ProjectName (optional-url)
        Description line(s)...
    """
    if not text.strip():
        return []

    BULLET_RE  = re.compile(r"^[•\-\*]")
    URL_INLINE = re.compile(r"\(?(https?://[^\s\)]+|[\w\-]+\.[\w]{2,}[^\s\)]*)\)?")

    lines = text.splitlines()
    blocks: List[List[str]] = []
    current: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(current)
                current = []
            continue
        if not BULLET_RE.match(stripped) and len(stripped.split()) <= 10 and not current:
            current = [stripped]
        elif not current:
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        blocks.append(current)

    projects = []
    for block in blocks:
        if not block:
            continue
        name_line  = block[0]
        url_match  = URL_INLINE.search(name_line)
        url        = url_match.group(1) if url_match else ""
        name       = URL_INLINE.sub("", name_line).strip().strip("()")
        description = " ".join(
            l.lstrip("•-* ").strip() for l in block[1:] if l.strip()
        )

        if name:
            projects.append({
                "name":        name,
                "url":         url,
                "description": description,
                "highlights":  []  # Schema expects highlights
            })

    return projects


def parse_certifications(text: str) -> List[Dict]:
    """
    Parses certifications section text into a list of cert dicts.
    Expects lines like:
        AWS Certified Solutions Architect – Associate — Issued by Amazon Web Services, 2023
    """
    if not text.strip():
        return []

    YEAR_RE   = re.compile(r"\b(20\d{2}|19\d{2})\b")
    ISSUER_RE = re.compile(
        r"(?:issued\s+by|certified\s+by|certificate\s+(?:issued\s+)?by"
        r"|course\s+completed\s+on)\s+(.+?)(?:,\s*\d{4})?$",
        re.IGNORECASE
    )

    certs = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts  = re.split(r"\s*[—–]\s*", line, maxsplit=1)
        name   = parts[0].strip()
        detail = parts[1].strip() if len(parts) > 1 else ""

        year_match   = YEAR_RE.search(detail or line)
        year         = year_match.group(0) if year_match else ""

        issuer_match = ISSUER_RE.search(detail or line)
        issuer       = issuer_match.group(1).strip() if issuer_match else ""
        issuer       = re.sub(r",?\s*\d{4}$", "", issuer).strip()

        if name:
            certs.append({
                "name":   name,
                "issuer": issuer,
                "date":   year
            })

    return certs


def structure_sections(sections: Dict[str, str]) -> Dict[str, list]:
    """Convert raw section strings into structured lists."""
    return {
        "work":         parse_experience(sections.get("experience", "")),
        "education":    parse_education(sections.get("education", "")),
        "skills":       parse_skills(sections.get("skills", "")),
        "projects":     parse_projects(sections.get("projects", "")),
        "certificates": parse_certifications(sections.get("certifications", "")),
    }


# =======================================================
# 5. FULL PIPELINE
# =======================================================

def parse_resume(pdf_path: str) -> Dict[str, any]:
    text     = extract_text_from_pdf(pdf_path)
    sections = improved_extract_sections(text)
    contacts = extract_contact_info(text)

    # Ensure all expected keys exist with defaults
    sections_defaults = {k: "" for k in ["education", "experience", "skills", "projects", "certifications", "summary"]}
    sections_defaults.update(sections)

    links_defaults = {k: [] for k in ["linkedin", "github", "portfolio"]}
    links_defaults.update(contacts.get("links", {}))

    contacts_defaults = {
        "name":    contacts.get("name", ""),
        "emails":  contacts.get("emails", []),
        "phones":  contacts.get("phones", []),
        "address": contacts.get("address", ""),
        "links":   links_defaults
    }

    # Parse raw section strings into structured arrays
    structured = structure_sections(sections_defaults)

    return {
        "raw_text":     text,
        "contacts":     contacts_defaults,
        "sections":     sections_defaults,
        "work":         structured["work"],
        "education":    structured["education"],
        "skills":       structured["skills"],
        "projects":     structured["projects"],
        "certificates": structured["certificates"],
    }