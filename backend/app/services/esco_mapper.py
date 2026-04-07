import logging
import re
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from rapidfuzz import fuzz, process

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

# Fuzzy match threshold for job title mapping
DEFAULT_JOB_TITLE_THRESHOLD = 85

# Fuzzy match threshold for skill mapping
DEFAULT_SKILL_THRESHOLD = 90

# Fuzzy match threshold for batch skill mapping
DEFAULT_BATCH_THRESHOLD = 75

# Match score assigned when a title is mapped via intern keyword stripping
STRIPPED_INTERN_SCORE = 95

# Match score assigned when mapped via fallback dictionary
FALLBACK_SCORE = 90

# Match score assigned when a tech skill has no ESCO entry but is valid
CUSTOM_SKILL_SCORE = 80

# Match score assigned when a skill falls through all matching strategies
UNMATCHED_FALLBACK_SCORE = 50

# Default skill match score returned when ESCO data is unavailable
ESCO_UNAVAILABLE_DEFAULT_SCORE = 0.5

# Keywords that indicate entry-level positions — stripped before ESCO mapping
INTERN_KEYWORDS = [
    "intern", "internship", "trainee", "graduate", "entry level", "entry-level"
]

# ============================================================
# ESCO MAPPER
# ============================================================


class ESCOMapper:
    """
    ESCO Ontology Mapper for job titles and skills.

    ESCO (European Skills, Competences, Qualifications and Occupations) is a
    multilingual classification system used to standardise skill and job title
    matching. This mapper loads the ESCO CSV datasets and provides fuzzy
    matching of free-text CV and JD content to ESCO concepts.

    Used during feature engineering to compute skill_match_score and
    title_match_score with semantic awareness, enabling partial credit
    for related skills (e.g. React → JavaScript) rather than exact keyword overlap.

    Capabilities:
        - Load ESCO occupations, skills, and occupation-skill relations
        - Exact and fuzzy match job titles to ESCO occupation concepts
        - Exact, fallback, and fuzzy match skills to ESCO skill concepts
        - Batch skill mapping for lists of CV or JD skills
        - Jaccard-based skill match scoring using ESCO-normalised URIs
    """

    def __init__(self, esco_data_dir: str = None):
        """
        Initialise the ESCO Mapper and load all datasets.

        Auto-detects the ESCO data directory relative to the project root
        if no path is provided. Builds lookup dictionaries for fast matching
        after loading.

        Args:
            esco_data_dir: Optional path to the directory containing ESCO CSV files.
                           Defaults to notebooks/.../data/esco_data relative to project root.
        """
        if esco_data_dir is None:
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent
            project_root = backend_dir.parent
            esco_data_dir = (
                project_root
                / "notebooks"
                / "fair-prehire-attrition-prediction"
                / "data"
                / "esco_data"
            )

        self.esco_data_dir = Path(esco_data_dir)

        self.occupations_df = self._load_occupations()
        self.skills_df = self._load_skills()
        self.occ_skill_relations_df = self._load_occ_skill_relations()

        self._build_lookup_dicts()

    # ============================================================
    # DATA LOADING
    # ============================================================

    def _load_occupations(self) -> pd.DataFrame:
        """
        Load and normalise the ESCO occupations dataset.

        Attempts comma then tab separator. Renames alternative column names
        to the expected standard schema. Returns an empty DataFrame on failure.
        """
        try:
            file_path = self.esco_data_dir / "occupations_en.csv"

            if not file_path.exists():
                logger.warning(f"ESCO occupations file not found: {file_path}")
                return pd.DataFrame()

            try:
                df = pd.read_csv(
                    file_path, sep=",", encoding="utf-8",
                    on_bad_lines="skip", low_memory=False
                )
            except Exception as e1:
                try:
                    df = pd.read_csv(
                        file_path, sep="\t", encoding="utf-8",
                        on_bad_lines="skip", low_memory=False
                    )
                    logger.debug("Loaded occupations with tab separator")
                except Exception as e2:
                    logger.error(f"Failed to load occupations with both separators: {e1}, {e2}")
                    return pd.DataFrame()

            # Normalise alternative column names to standard schema
            existing_cols = [
                c for c in ["conceptUri", "preferredLabel", "altLabels", "description"]
                if c in df.columns
            ]

            if not existing_cols:
                rename_map = {}
                if "uri" in df.columns:
                    rename_map["uri"] = "conceptUri"
                if "label" in df.columns:
                    rename_map["label"] = "preferredLabel"
                alt_col = next(
                    (c for c in ["alternative_labels", "alternativeLabel"] if c in df.columns),
                    None
                )
                if alt_col:
                    rename_map[alt_col] = "altLabels"
                if rename_map:
                    df.rename(columns=rename_map, inplace=True)
                    logger.debug(f"Renamed occupation columns: {rename_map}")

            available_cols = [
                c for c in ["conceptUri", "preferredLabel", "altLabels", "description"]
                if c in df.columns
            ]

            if available_cols:
                return df[available_cols]

            logger.warning(
                f"Could not find expected columns in occupations file. "
                f"Available: {df.columns.tolist()[:10]}"
            )
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading ESCO occupations: {e}")
            return pd.DataFrame()

    def _load_skills(self) -> pd.DataFrame:
        """
        Load and normalise the ESCO skills dataset.

        Attempts comma then tab separator. Renames alternative column names
        to the expected standard schema. Returns an empty DataFrame on failure.
        """
        try:
            file_path = self.esco_data_dir / "skills_en.csv"

            if not file_path.exists():
                logger.warning(f"ESCO skills file not found: {file_path}")
                return pd.DataFrame()

            try:
                df = pd.read_csv(
                    file_path, sep=",", encoding="utf-8",
                    on_bad_lines="skip", low_memory=False
                )
            except Exception as e1:
                try:
                    df = pd.read_csv(
                        file_path, sep="\t", encoding="utf-8",
                        on_bad_lines="skip", low_memory=False
                    )
                except Exception as e2:
                    logger.error(f"Failed to load skills with both separators: {e1}, {e2}")
                    return pd.DataFrame()

            rename_map = {}
            if "uri" in df.columns:
                rename_map["uri"] = "conceptUri"
            if "label" in df.columns:
                rename_map["label"] = "preferredLabel"
            alt_col = next(
                (c for c in ["alternative_labels", "alternativeLabel"] if c in df.columns),
                None
            )
            if alt_col:
                rename_map[alt_col] = "altLabels"
            if "type" in df.columns and "skillType" not in df.columns:
                rename_map["type"] = "skillType"
            if rename_map:
                df.rename(columns=rename_map, inplace=True)
                logger.debug(f"Renamed skills columns: {rename_map}")

            available_cols = [
                c for c in ["conceptUri", "preferredLabel", "altLabels", "skillType", "description"]
                if c in df.columns
            ]

            if available_cols:
                return df[available_cols]

            logger.warning(
                f"Could not find expected columns in skills file. "
                f"Available: {df.columns.tolist()[:10]}"
            )
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading ESCO skills: {e}")
            return pd.DataFrame()

    def _load_occ_skill_relations(self) -> pd.DataFrame:
        """
        Load the ESCO occupation-skill relations dataset.

        Contains mappings between occupation URIs and skill URIs with
        relation type (essential or optional). Used in get_skills_for_occupation.
        Returns an empty DataFrame on failure.
        """
        try:
            file_path = self.esco_data_dir / "occupationSkillRelations_en.csv"

            if not file_path.exists():
                logger.warning(f"ESCO relations file not found: {file_path}")
                return pd.DataFrame()

            try:
                df = pd.read_csv(
                    file_path, sep=",", encoding="utf-8",
                    on_bad_lines="skip", low_memory=False
                )
            except Exception:
                try:
                    df = pd.read_csv(
                        file_path, sep="\t", encoding="utf-8",
                        on_bad_lines="skip", low_memory=False
                    )
                except Exception as e:
                    logger.error(f"Failed to load occupation-skill relations: {e}")
                    return pd.DataFrame()

            essential_cols = ["occupationUri", "relationType", "skillType", "skillUri"]
            available_cols = [c for c in essential_cols if c in df.columns]

            if available_cols:
                return df[available_cols]

            logger.warning(
                f"Could not find expected relation columns. "
                f"Available: {df.columns.tolist()[:10]}"
            )
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading ESCO occupation-skill relations: {e}")
            return pd.DataFrame()

    def _build_lookup_dicts(self):
        """
        Build in-memory lookup dictionaries for fast fuzzy matching.

        Flattens both preferred labels and alternative labels into a single
        dictionary keyed by lowercase label string. Called once on initialisation.
        """
        if self.occupations_df.empty and self.skills_df.empty:
            logger.warning("No ESCO data loaded — skipping lookup dict creation")
            self.job_titles_lookup = {}
            self.skills_lookup = {}
            return

        # Build job titles lookup from preferred and alternative labels
        self.job_titles_lookup = {}
        for _, row in self.occupations_df.iterrows():
            preferred = row["preferredLabel"].lower() if pd.notna(row["preferredLabel"]) else ""
            alt_labels = (
                str(row["altLabels"]).lower().split("\n") if pd.notna(row["altLabels"]) else []
            )
            for label in [preferred] + [l.strip() for l in alt_labels if l.strip()]:
                if label:
                    self.job_titles_lookup[label] = {
                        "uri": row["conceptUri"],
                        "preferredLabel": row["preferredLabel"],
                    }

        # Build skills lookup from preferred and alternative labels
        self.skills_lookup = {}
        for _, row in self.skills_df.iterrows():
            preferred = row["preferredLabel"].lower() if pd.notna(row["preferredLabel"]) else ""
            alt_labels = (
                str(row["altLabels"]).lower().split("\n") if pd.notna(row["altLabels"]) else []
            )
            for label in [preferred] + [l.strip() for l in alt_labels if l.strip()]:
                if label:
                    self.skills_lookup[label] = {
                        "uri": row["conceptUri"],
                        "preferredLabel": row["preferredLabel"],
                        "skillType": row["skillType"],
                    }

        logger.info(
            f"ESCO lookup dicts built — "
            f"{len(self.job_titles_lookup)} job title entries, "
            f"{len(self.skills_lookup)} skill entries"
        )

    # ============================================================
    # JOB TITLE MAPPING
    # ============================================================

    # Curated fallback mappings for common IT job titles not in ESCO.
    # Maps modern/informal titles to the closest ESCO occupation label.
    _FALLBACK_JOB_TITLE_MAPPINGS = {
        "ai engineer": "software developer",
        "ai/ml engineer": "software developer",
        "ml engineer": "software developer",
        "machine learning engineer": "software developer",
        "data scientist": "data analyst",
        "data engineer": "database administrator",
        "data analyst": "data analyst",
        "business intelligence analyst": "data analyst",
        "mlops engineer": "software developer",
        "software engineer": "software developer",
        "software developer": "software developer",
        "full stack developer": "software developer",
        "fullstack developer": "software developer",
        "frontend developer": "web developer",
        "front-end developer": "web developer",
        "backend developer": "software developer",
        "back-end developer": "software developer",
        "web developer": "web developer",
        "mobile developer": "software developer",
        "android developer": "software developer",
        "ios developer": "software developer",
        "devops engineer": "systems administrator",
        "cloud engineer": "systems administrator",
        "platform engineer": "systems administrator",
        "site reliability engineer": "systems administrator",
        "sre": "systems administrator",
        "infrastructure engineer": "systems administrator",
        "security engineer": "ICT security administrator",
        "cybersecurity analyst": "ICT security administrator",
        "information security analyst": "ICT security administrator",
        "qa engineer": "ICT quality assurance tester",
        "test engineer": "ICT quality assurance tester",
        "automation engineer": "software developer",
        "product manager": "ICT project manager",
        "technical product manager": "ICT project manager",
        "scrum master": "ICT project manager",
        "project manager": "ICT project manager",
    }

    def map_job_title(
        self, job_title: str, threshold: int = DEFAULT_JOB_TITLE_THRESHOLD
    ) -> Optional[Dict[str, str]]:
        """
        Map a free-text job title to its closest ESCO occupation concept.

        Matching strategy (in order):
        1. Exact match against the full lookup dictionary
        2. Strip intern/trainee/entry-level keywords and retry exact match
        3. Curated fallback dictionary for common IT titles
        4. Fuzzy matching using rapidfuzz as a last resort

        Args:
            job_title: Raw job title string from CV or JD.
            threshold: Minimum fuzzy match score (0-100) to accept a result.

        Returns:
            Dict with uri, preferredLabel, and match metadata, or None if unmatched.
        """
        if not job_title or pd.isna(job_title):
            return None

        if not self.job_titles_lookup:
            return None

        job_title_lower = job_title.lower().strip()

        # 1. Exact match
        if job_title_lower in self.job_titles_lookup:
            return {
                "uri": self.job_titles_lookup[job_title_lower]["uri"],
                "preferredLabel": self.job_titles_lookup[job_title_lower]["preferredLabel"],
                "match_score": 100,
            }

        # 2. Strip intern/entry-level keywords and retry
        stripped_title = job_title_lower
        for keyword in INTERN_KEYWORDS:
            stripped_title = re.sub(
                rf"\b{keyword}\b", "", stripped_title, flags=re.IGNORECASE
            )
        stripped_title = re.sub(r"\s+", " ", stripped_title).strip()

        if stripped_title and stripped_title != job_title_lower:
            if stripped_title in self.job_titles_lookup:
                return {
                    "uri": self.job_titles_lookup[stripped_title]["uri"],
                    "preferredLabel": self.job_titles_lookup[stripped_title]["preferredLabel"],
                    "match_score": STRIPPED_INTERN_SCORE,
                    "original_title": job_title,
                    "mapped_via": "stripped_intern",
                }

        # 3. Curated fallback dictionary
        for title_key in [stripped_title, job_title_lower]:
            if title_key in self._FALLBACK_JOB_TITLE_MAPPINGS:
                fallback_title = self._FALLBACK_JOB_TITLE_MAPPINGS[title_key]
                if fallback_title and fallback_title in self.job_titles_lookup:
                    result = self.job_titles_lookup[fallback_title]
                    return {
                        "uri": result["uri"],
                        "preferredLabel": result["preferredLabel"],
                        "match_score": FALLBACK_SCORE,
                        "original_title": job_title,
                        "mapped_via": "fallback",
                        "mapped_to": fallback_title,
                    }

        # 4. Fuzzy matching as last resort
        query = stripped_title if stripped_title else job_title_lower
        matches = process.extract(
            query, self.job_titles_lookup.keys(), scorer=fuzz.ratio, limit=5
        )

        if matches and matches[0][1] >= threshold:
            matched_label = matches[0][0]
            return {
                "uri": self.job_titles_lookup[matched_label]["uri"],
                "preferredLabel": self.job_titles_lookup[matched_label]["preferredLabel"],
                "match_score": matches[0][1],
                "mapped_via": "fuzzy",
                "alternatives": [
                    {
                        "label": self.job_titles_lookup[m[0]]["preferredLabel"],
                        "score": m[1],
                    }
                    for m in matches[1:4]
                    if m[1] >= threshold
                ],
            }

        return None

    # ============================================================
    # SKILL MAPPING
    # ============================================================

    # Curated mappings for modern tech skills not covered by ESCO.
    # Maps informal/framework names to the closest ESCO skill label.
    # None values indicate skills with no reasonable ESCO equivalent —
    # they are handled as valid custom technical skills.
    _TECH_SKILL_MAPPINGS = {
        "python": "Python (computer programming)",
        "java": "Java (computer programming)",
        "javascript": "JavaScript",
        "typescript": "JavaScript",
        "c++": "C++",
        "c#": "C#",
        "go": "Go (computer programming)",
        "golang": "Go (computer programming)",
        "rust": None,
        "ruby": "Ruby (computer programming)",
        "php": "PHP",
        "react": "JavaScript",
        "angular": "JavaScript",
        "vue": "JavaScript",
        "vue.js": "JavaScript",
        "django": "Python (computer programming)",
        "flask": "Python (computer programming)",
        "spring boot": "Java (computer programming)",
        "spring": "Java (computer programming)",
        "node.js": "JavaScript",
        "nodejs": "JavaScript",
        "docker": "virtualization",
        "kubernetes": "cloud technologies",
        "jenkins": "continuous integration",
        "terraform": "infrastructure as code",
        "ansible": "configuration management",
        "git": "Git",
        "aws": "Amazon Web Services",
        "amazon web services": "Amazon Web Services",
        "azure": "Microsoft Azure",
        "gcp": "Google Cloud Platform",
        "google cloud": "Google Cloud Platform",
        "tensorflow": "machine learning",
        "pytorch": "machine learning",
        "scikit-learn": "machine learning",
        "sklearn": "machine learning",
        "pandas": "data analysis",
        "numpy": "scientific computing",
        "keras": "machine learning",
        "sql": "SQL",
        "mysql": "MySQL",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mongodb": "MongoDB",
        "redis": "database management",
        "sap": "SAP software products",
        "oracle": "Oracle software products",
        "agile": "Agile software development",
        "scrum": "SCRUM",
        "ci/cd": "continuous integration",
        "devops": "DevOps",
    }

    def map_skill(
        self, skill: str, threshold: int = DEFAULT_SKILL_THRESHOLD
    ) -> Optional[Dict[str, str]]:
        """
        Map a free-text skill to its closest ESCO skill concept.

        Matching strategy (in order):
        1. Exact match against the skills lookup dictionary
        2. Curated tech skill fallback mappings for modern tools/frameworks
        3. Fuzzy matching using rapidfuzz
        4. Custom fallback for skills not in ESCO — treated as valid technical skills

        Args:
            skill: Raw skill string from CV or JD text.
            threshold: Minimum fuzzy match score (0-100) to accept a result.

        Returns:
            Dict with uri, preferredLabel, skillType, and match metadata.
            Always returns a result — unmatched skills get a custom fallback.
        """
        if not skill or pd.isna(skill):
            return None

        if not self.skills_lookup:
            return None

        skill_lower = skill.lower().strip()

        # 1. Exact match
        if skill_lower in self.skills_lookup:
            return {
                "uri": self.skills_lookup[skill_lower]["uri"],
                "preferredLabel": self.skills_lookup[skill_lower]["preferredLabel"],
                "skillType": self.skills_lookup[skill_lower]["skillType"],
                "match_score": 100,
            }

        # 2. Curated tech skill fallback
        if skill_lower in self._TECH_SKILL_MAPPINGS:
            mapped_skill = self._TECH_SKILL_MAPPINGS[skill_lower]

            if mapped_skill is None:
                # Skill has no reasonable ESCO equivalent — treat as valid custom skill
                return {
                    "uri": f"custom:{skill_lower}",
                    "preferredLabel": skill.title(),
                    "skillType": "technical",
                    "match_score": CUSTOM_SKILL_SCORE,
                    "mapped_via": "custom_mapping",
                    "note": "Modern tech skill not in ESCO — treated as valid technical skill",
                }

            if mapped_skill.lower() in self.skills_lookup:
                result = self.skills_lookup[mapped_skill.lower()]
                return {
                    "uri": result["uri"],
                    "preferredLabel": result["preferredLabel"],
                    "skillType": result["skillType"],
                    "match_score": FALLBACK_SCORE,
                    "mapped_via": "tech_fallback",
                    "original_skill": skill,
                    "note": f"Mapped to broader ESCO concept: {mapped_skill}",
                }

        # 3. Fuzzy matching
        matches = process.extract(
            skill_lower, self.skills_lookup.keys(), scorer=fuzz.ratio, limit=3
        )

        if matches and matches[0][1] >= threshold:
            matched_label = matches[0][0]
            return {
                "uri": self.skills_lookup[matched_label]["uri"],
                "preferredLabel": self.skills_lookup[matched_label]["preferredLabel"],
                "skillType": self.skills_lookup[matched_label]["skillType"],
                "match_score": matches[0][1],
                "mapped_via": "fuzzy",
            }

        # 4. Unmatched fallback — skill not in ESCO but treated as valid
        return {
            "uri": f"custom:{skill_lower}",
            "preferredLabel": skill.title(),
            "skillType": "technical",
            "match_score": UNMATCHED_FALLBACK_SCORE,
            "mapped_via": "unmatched_fallback",
            "note": "Skill not in ESCO database — treated as valid technical skill",
        }

    def map_skills_batch(
        self, skills_list: List[str], threshold: int = DEFAULT_BATCH_THRESHOLD
    ) -> List[Dict[str, str]]:
        """
        Map a list of skills to ESCO concepts in bulk.

        Args:
            skills_list: List of raw skill strings from CV or JD.
            threshold: Minimum fuzzy match score for each skill.

        Returns:
            List of matched skill dicts (only successfully mapped skills included).
        """
        matched_skills = []
        for skill in skills_list:
            mapped = self.map_skill(skill, threshold)
            if mapped:
                matched_skills.append(mapped)
        return matched_skills

    # ============================================================
    # OCCUPATION-SKILL RELATIONS
    # ============================================================

    def get_skills_for_occupation(self, occupation_uri: str) -> List[Dict[str, str]]:
        """
        Retrieve the ESCO skills associated with a given occupation URI.

        Uses the occupation-skill relations dataset to find all essential
        and optional skills linked to the occupation.

        Args:
            occupation_uri: ESCO URI string for the target occupation.

        Returns:
            List of skill dicts including preferredLabel, skillType,
            and relationType (essential/optional).
        """
        if self.occ_skill_relations_df.empty:
            return []

        occ_relations = self.occ_skill_relations_df[
            self.occ_skill_relations_df["occupationUri"] == occupation_uri
        ]

        related_skills = []
        for _, rel in occ_relations.iterrows():
            skill_uri = rel["skillUri"]
            skill_row = self.skills_df[self.skills_df["conceptUri"] == skill_uri]

            if not skill_row.empty:
                related_skills.append(
                    {
                        "uri": skill_uri,
                        "preferredLabel": skill_row.iloc[0]["preferredLabel"],
                        "skillType": skill_row.iloc[0]["skillType"],
                        "relationType": rel["relationType"],
                    }
                )

        return related_skills

    # ============================================================
    # SKILL MATCH SCORING
    # ============================================================

    def calculate_esco_skill_match(
        self,
        cv_skills: List[str],
        jd_skills: List[str],
        threshold: int = DEFAULT_BATCH_THRESHOLD,
    ) -> float:
        """
        Compute a skill match score between CV and JD skills using ESCO normalisation.

        Maps both skill lists to ESCO URIs, then computes Jaccard similarity
        (intersection over JD skills). Using ESCO URIs means semantically related
        skills (e.g. React → JavaScript) are treated as matches rather than misses.

        Falls back to 0.5 if ESCO data is unavailable or no JD skills could be mapped.

        Args:
            cv_skills: List of skills extracted from the candidate's CV.
            jd_skills: List of skills extracted from the job description.
            threshold: Minimum fuzzy match score for skill mapping.

        Returns:
            Float between 0.0 and 1.0 representing the proportion of JD skills
            covered by the candidate's ESCO-normalised skill set.
        """
        if not self.skills_lookup:
            logger.warning("ESCO skills lookup empty. Returning default match score")
            return ESCO_UNAVAILABLE_DEFAULT_SCORE

        cv_esco_uris = set()
        for skill in cv_skills:
            mapped = self.map_skill(skill, threshold)
            if mapped:
                cv_esco_uris.add(mapped["uri"])

        jd_esco_uris = set()
        for skill in jd_skills:
            mapped = self.map_skill(skill, threshold)
            if mapped:
                jd_esco_uris.add(mapped["uri"])

        if not jd_esco_uris:
            logger.debug("No JD skills mapped to ESCO. Returning default match score")
            return ESCO_UNAVAILABLE_DEFAULT_SCORE

        intersection = len(cv_esco_uris & jd_esco_uris)
        match_score = intersection / len(jd_esco_uris)

        return round(match_score, 3)


# ============================================================
# SINGLETON ACCESSOR
# ============================================================

_esco_mapper = None


def get_esco_mapper() -> Optional[ESCOMapper]:
    """
    Return the shared ESCOMapper singleton instance.

    Initialises the mapper on first call. Returns None if the ESCO
    data files are missing or the mapper fails to load, allowing
    the feature engineering pipeline to fall back to traditional
    keyword-based skill matching.
    """
    global _esco_mapper

    if _esco_mapper is None:
        try:
            _esco_mapper = ESCOMapper()

            if _esco_mapper.occupations_df.empty and _esco_mapper.skills_df.empty:
                logger.warning("ESCO data is empty — falling back to non-ESCO mode")
                return None

        except Exception as e:
            logger.error(f"Failed to initialise ESCO Mapper: {e}")
            logger.warning("Falling back to non-ESCO skill matching mode")
            return None

    return _esco_mapper