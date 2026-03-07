from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from pydantic import ValidationError

from app.config import settings
from app.parsers.cv_parser import extract_text_from_pdf
from app.schemas.cv_schema import Basics, Certificate, CVParsed, Education, Project, Skill, Work

logger = logging.getLogger(__name__)

_openai_client: Optional[OpenAI] = None


class CVOpenAIExtractionError(RuntimeError):
    """Raised when OpenAI-based CV extraction fails and no fallback is desired."""


def get_openai_client() -> OpenAI:
    global _openai_client
    if not settings.OPENAI_API_KEY:
        raise CVOpenAIExtractionError("OPENAI_API_KEY is not configured")
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _file_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename or "")
    return (ext or "").lower().lstrip(".")


def extract_text_from_file(path: str, original_filename: str) -> str:
    """
    Extract raw text from an uploaded CV file based on its extension.
    Supports: pdf, txt, docx (docx requires python-docx).
    """
    ext = _file_ext(original_filename)

    if ext == "pdf":
        return extract_text_from_pdf(path)

    if ext == "txt":
        with open(path, "rb") as f:
            raw = f.read()
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except Exception:
                continue
        return raw.decode("utf-8", errors="ignore")

    if ext == "docx":
        try:
            from docx import Document  # type: ignore
        except Exception as e:
            raise CVOpenAIExtractionError(
                "DOCX parsing requires python-docx. Install it or upload a PDF."
            ) from e
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())

    raise CVOpenAIExtractionError(f"Unsupported file type: .{ext or '(unknown)'}")


def _truncate_text(text: str, max_chars: int = 14000) -> str:
    """
    Keep enough context while avoiding token blow-ups. If long, keep head+tail.
    """
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    head = t[: int(max_chars * 0.7)]
    tail = t[-int(max_chars * 0.3) :]
    return head + "\n\n--- TRUNCATED ---\n\n" + tail


def _ensure_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _ensure_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_optional_str(value: Any) -> Optional[str]:
    s = _ensure_str(value)
    return s or None


def _normalize_basics(basics: Dict[str, Any]) -> Dict[str, Any]:
    # Accept either null or string; treat "Not provided" and similar as null.
    def clean(v: Any) -> Optional[str]:
        s = _ensure_str(v)
        if not s:
            return None
        if s.lower() in {"not provided", "n/a", "na", "none", "null"}:
            return None
        return s

    return {
        "name": clean(basics.get("name")),
        "email": clean(basics.get("email")),
        "phone": clean(basics.get("phone")),
        "linkedin": clean(basics.get("linkedin")),
        "github": clean(basics.get("github")),
        "website": clean(basics.get("website")),
        "summary": clean(basics.get("summary")),
        "address": clean(basics.get("address")),
    }


def _build_prompt(cv_text: str) -> str:
    return f"""You are an expert CV/resume parser.

Extract data from the CV text and return ONLY valid JSON (no markdown).

CRITICAL RULES:
- The JSON MUST match the schema exactly (field names and nesting).
- Do not invent facts. If unknown, use null (for strings) or [] (for arrays).
- For dates: keep the original format found in the CV (e.g., \"January 2025\", \"2022 - Present\").
- Keep names/company/institution as written; do not merge unrelated lines.
- For skills: group into categories when obvious; otherwise use name=\"General\".
- For projects: split into separate projects if multiple are present.
- For certificates: list each certificate as its own entry.

JSON SCHEMA TO OUTPUT:
{{
  \"basics\": {{
    \"name\": string|null,
    \"email\": string|null,
    \"phone\": string|null,
    \"linkedin\": string|null,
    \"github\": string|null,
    \"website\": string|null,
    \"summary\": string|null,
    \"address\": string|null
  }},
  \"education\": [
    {{
      \"institution\": string|null,
      \"area\": string|null,
      \"studyType\": string|null,
      \"startDate\": string|null,
      \"endDate\": string|null,
      \"gpa\": string|null,
      \"courses\": [string, ...]
    }}
  ],
  \"work\": [
    {{
      \"name\": string|null,
      \"position\": string|null,
      \"startDate\": string|null,
      \"endDate\": string|null,
      \"summary\": string|null,
      \"highlights\": [string, ...]
    }}
  ],
  \"skills\": [
    {{
      \"name\": string|null,
      \"level\": string|null,
      \"keywords\": [string, ...]
    }}
  ],
  \"projects\": [
    {{
      \"name\": string|null,
      \"description\": string|null,
      \"highlights\": [string, ...],
      \"url\": string|null
    }}
  ],
  \"certificates\": [
    {{
      \"name\": string|null,
      \"issuer\": string|null,
      \"date\": string|null
    }}
  ]
}}

CV TEXT:
{cv_text}
"""


def extract_cv_structured_openai(raw_text: str) -> Dict[str, Any]:
    """
    Call OpenAI once to extract a fully structured CV aligned to `CVParsed` fields.
    Returns a dict containing: basics, education, work, skills, projects, certificates.
    """
    cv_text = _truncate_text(raw_text, max_chars=14000)
    if not cv_text:
        raise CVOpenAIExtractionError("No text extracted from the uploaded CV")

    client = get_openai_client()
    model = getattr(settings, "OPENAI_CV_MODEL", None) or settings.OPENAI_MODEL
    temperature = getattr(settings, "OPENAI_CV_TEMPERATURE", None)
    temperature = 0.1 if temperature is None else float(temperature)

    prompt = _build_prompt(cv_text)
    logger.info("Calling OpenAI for structured CV extraction (model=%s)...", model)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Return ONLY valid JSON matching the provided schema. No markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
            max_tokens=3500,
        )
        content = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        raise CVOpenAIExtractionError(f"OpenAI request failed: {str(e)}") from e

    # Defensive strip for occasional fences (even with response_format)
    if content.startswith("```"):
        content = content.strip("`").strip()
        if content.lower().startswith("json"):
            content = content[4:].strip()

    try:
        data = json.loads(content)
    except Exception as e:
        raise CVOpenAIExtractionError(f"OpenAI returned invalid JSON: {str(e)}") from e

    if not isinstance(data, dict):
        raise CVOpenAIExtractionError("OpenAI response JSON is not an object")

    return data


def map_openai_to_cv_parsed_fields(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize OpenAI output into a structure compatible with `CVParsed`
    (excluding cv_id/uploaded_at/user_email which are set by the API layer).
    """
    basics = extracted.get("basics") if isinstance(extracted.get("basics"), dict) else {}
    basics = _normalize_basics(basics)

    def norm_education(item: Any) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        return {
            "institution": _coerce_optional_str(item.get("institution")),
            "area": _coerce_optional_str(item.get("area")),
            "studyType": _coerce_optional_str(item.get("studyType")),
            "startDate": _coerce_optional_str(item.get("startDate")),
            "endDate": _coerce_optional_str(item.get("endDate")),
            "gpa": _coerce_optional_str(item.get("gpa")),
            "courses": [
                _ensure_str(c)
                for c in _ensure_list(item.get("courses"))
                if _ensure_str(c)
            ],
        }

    def norm_work(item: Any) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        return {
            "name": _coerce_optional_str(item.get("name")),
            "position": _coerce_optional_str(item.get("position")),
            "startDate": _coerce_optional_str(item.get("startDate")),
            "endDate": _coerce_optional_str(item.get("endDate")),
            "summary": _coerce_optional_str(item.get("summary")),
            "highlights": [
                _ensure_str(h)
                for h in _ensure_list(item.get("highlights"))
                if _ensure_str(h)
            ],
        }

    def norm_skill(item: Any) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        keywords = [_ensure_str(k) for k in _ensure_list(item.get("keywords")) if _ensure_str(k)]
        # Deduplicate keywords preserving order
        keywords = list(dict.fromkeys(keywords))
        name = _coerce_optional_str(item.get("name")) or ("General" if keywords else None)
        return {
            "name": name,
            "level": _coerce_optional_str(item.get("level")),
            "keywords": keywords,
        }

    def norm_project(item: Any) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        return {
            "name": _coerce_optional_str(item.get("name")),
            "description": _coerce_optional_str(item.get("description")),
            "highlights": [
                _ensure_str(h)
                for h in _ensure_list(item.get("highlights"))
                if _ensure_str(h)
            ],
            "url": _coerce_optional_str(item.get("url")),
        }

    def norm_cert(item: Any) -> Dict[str, Any]:
        item = item if isinstance(item, dict) else {}
        return {
            "name": _coerce_optional_str(item.get("name")),
            "issuer": _coerce_optional_str(item.get("issuer")),
            "date": _coerce_optional_str(item.get("date")),
        }

    education = [norm_education(x) for x in _ensure_list(extracted.get("education"))]
    work = [norm_work(x) for x in _ensure_list(extracted.get("work"))]
    skills = [norm_skill(x) for x in _ensure_list(extracted.get("skills"))]
    projects = [norm_project(x) for x in _ensure_list(extracted.get("projects"))]
    certificates = [norm_cert(x) for x in _ensure_list(extracted.get("certificates"))]

    return {
        "basics": basics,
        "education": education,
        "work": work,
        "skills": skills,
        "projects": projects,
        "certificates": certificates,
    }


def extract_cv_to_schema_fields(file_path: str, original_filename: str) -> Tuple[Dict[str, Any], str]:
    """
    High-level helper used by the API:
    - Extract raw text from file
    - OpenAI structured extraction
    - Normalize to schema-compatible fields
    Returns (cv_fields, raw_text).
    """
    raw_text = extract_text_from_file(file_path, original_filename)
    extracted = extract_cv_structured_openai(raw_text)
    cv_fields = map_openai_to_cv_parsed_fields(extracted)

    # Validate shape early (helps catch prompt regressions)
    try:
        CVParsed(
            cv_id="__validate_only__",
            basics=Basics(**(cv_fields.get("basics") or {})),
            education=[Education(**e) for e in (cv_fields.get("education") or [])],
            work=[Work(**w) for w in (cv_fields.get("work") or [])],
            skills=[Skill(**s) for s in (cv_fields.get("skills") or [])],
            projects=[Project(**p) for p in (cv_fields.get("projects") or [])],
            certificates=[Certificate(**c) for c in (cv_fields.get("certificates") or [])],
            raw_text=raw_text,
        )
    except ValidationError as e:
        raise CVOpenAIExtractionError(f"Extracted CV failed schema validation: {str(e)}") from e

    return cv_fields, raw_text

