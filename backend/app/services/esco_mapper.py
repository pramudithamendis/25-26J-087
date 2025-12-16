import re
import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz, process
from typing import Optional, List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class ESCOMapper:
    """
    ESCO Ontology Mapper for Job Titles and Skills
    
    Functionality:
    - Load ESCO occupations, skills, and relationships
    - Fuzzy match job titles to ESCO occupations
    - Fuzzy match skills to ESCO skill concepts
    - Get related skills for a given occupation
    """
    
    def __init__(self, esco_data_dir: str = None):
        """
        Initialize ESCO Mapper
        
        Args:
            esco_data_dir: Path to ESCO CSV files
        """
        if esco_data_dir is None:
            # Auto-detect path: backend/../notebooks/.../data/esco_data
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent  
            project_root = backend_dir.parent  
            esco_data_dir = project_root / "notebooks" / "fair-prehire-attrition-prediction" / "data" / "esco_data"
        
        self.esco_data_dir = Path(esco_data_dir)
        
        print(f" Loading ESCO data from: {self.esco_data_dir}")
        
        # Load ESCO datasets
        self.occupations_df = self._load_occupations()
        self.skills_df = self._load_skills()
        self.occ_skill_relations_df = self._load_occ_skill_relations()
        
        # Create lookup dictionaries for fast matching
        self._build_lookup_dicts()
        
        print(f" ESCO READY: {len(self.occupations_df)} occupations, {len(self.skills_df)} skills, {len(self.occ_skill_relations_df)} relations")
    
    def _load_occupations(self) -> pd.DataFrame:
        """Load occupations_en.csv with intelligent separator detection"""
        try:
            file_path = self.esco_data_dir / "occupations_en.csv"
            
            if not file_path.exists():
                print(f"   File not found: {file_path}")
                return pd.DataFrame()
            
            # Try comma separator first (ESCO standard format)
            try:
                df = pd.read_csv(file_path, sep=',', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                print(f"  Loaded with comma separator")
            except Exception as e1:
                # Fallback to tab separator
                try:
                    df = pd.read_csv(file_path, sep='\t', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                    print(f"   Loaded with tab separator")
                except Exception as e2:
                    print(f"   Failed both separators: {e1}, {e2}")
                    return pd.DataFrame()
            
            print(f"   Loaded {len(df)} rows with {len(df.columns)} columns")
            print(f"   First 5 columns: {df.columns.tolist()[:5]}")
            
            # Map to expected column names
            column_mapping = {
                'conceptUri': 'conceptUri',
                'preferredLabel': 'preferredLabel', 
                'altLabels': 'altLabels',
                'description': 'description'
            }
            
            # Check which columns exist
            existing_cols = [col for col in column_mapping.keys() if col in df.columns]
            
            # Try alternative column names if standard ones don't exist
            if not existing_cols:
                rename_map = {}
                if 'uri' in df.columns:
                    rename_map['uri'] = 'conceptUri'
                if 'label' in df.columns:
                    rename_map['label'] = 'preferredLabel'
                if 'alternative_labels' in df.columns or 'alternativeLabel' in df.columns:
                    alt_col = 'alternative_labels' if 'alternative_labels' in df.columns else 'alternativeLabel'
                    rename_map[alt_col] = 'altLabels'
                
                if rename_map:
                    df.rename(columns=rename_map, inplace=True)
                    print(f"   Renamed columns: {rename_map}")
            
            # Keep only columns that exist
            available_cols = [col for col in ['conceptUri', 'preferredLabel', 'altLabels', 'description'] if col in df.columns]
            
            if available_cols:
                df = df[available_cols]
                print(f"   Successfully loaded {len(df)} occupations")
                return df
            else:
                print(f"   Could not find expected columns in occupations file")
                print(f"  Available columns: {df.columns.tolist()[:10]}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"   Error loading occupations: {e}")
            return pd.DataFrame()
    
    def _load_skills(self) -> pd.DataFrame:
        """Load skills_en.csv with intelligent separator detection"""
        try:
            file_path = self.esco_data_dir / "skills_en.csv"
            
            if not file_path.exists():
                print(f"   File not found: {file_path}")
                return pd.DataFrame()
            
            # Try comma separator first (ESCO standard)
            try:
                df = pd.read_csv(file_path, sep=',', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                print(f"   Loaded skills with comma separator")
            except Exception as e1:
                # Fallback to tab separator
                try:
                    df = pd.read_csv(file_path, sep='\t', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                    print(f"   Loaded skills with tab separator")
                except Exception as e2:
                    print(f"   Failed both separators: {e1}, {e2}")
                    return pd.DataFrame()
            
            print(f"   Loaded {len(df)} rows with {len(df.columns)} columns")
            print(f"   First 5 columns: {df.columns.tolist()[:5]}")
            
            # Try alternative column names
            rename_map = {}
            if 'uri' in df.columns:
                rename_map['uri'] = 'conceptUri'
            if 'label' in df.columns:
                rename_map['label'] = 'preferredLabel'
            if 'alternative_labels' in df.columns or 'alternativeLabel' in df.columns:
                alt_col = 'alternative_labels' if 'alternative_labels' in df.columns else 'alternativeLabel'
                rename_map[alt_col] = 'altLabels'
            if 'type' in df.columns and 'skillType' not in df.columns:
                rename_map['type'] = 'skillType'
            
            if rename_map:
                df.rename(columns=rename_map, inplace=True)
                print(f"   Renamed columns: {rename_map}")
            
            # Keep essential columns
            available_cols = [col for col in ['conceptUri', 'preferredLabel', 'altLabels', 'skillType', 'description'] if col in df.columns]
            
            if available_cols:
                df = df[available_cols]
                print(f"   Successfully loaded {len(df)} skills")
                return df
            else:
                print(f"  Could not find expected columns in skills file")
                print(f"  Available columns: {df.columns.tolist()[:10]}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"   Error loading skills: {e}")
            return pd.DataFrame()
    
    def _load_occ_skill_relations(self) -> pd.DataFrame:
        """Load occupationSkillRelations_en.csv"""
        try:
            file_path = self.esco_data_dir / "occupationSkillRelations_en.csv"
            
            if not file_path.exists():
                print(f"   Relations file not found: {file_path}")
                return pd.DataFrame()
            
            # Try comma separator first
            try:
                df = pd.read_csv(file_path, sep=',', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                print(f"   Loaded relations with comma separator")
            except:
                try:
                    df = pd.read_csv(file_path, sep='\t', encoding='utf-8', on_bad_lines='skip', low_memory=False)
                    print(f"   Loaded relations with tab separator")
                except Exception as e:
                    print(f"   Failed to load relations: {e}")
                    return pd.DataFrame()
            
            print(f"   Loaded {len(df)} relations with {len(df.columns)} columns")
            
            # Keep only essential columns
            essential_cols = ['occupationUri', 'relationType', 'skillType', 'skillUri']
            available_cols = [col for col in essential_cols if col in df.columns]
            
            if available_cols:
                df = df[available_cols]
                print(f"   Successfully loaded {len(df)} occupation-skill relations")
                return df
            else:
                print(f"  Could not find expected relation columns")
                print(f"  Available columns: {df.columns.tolist()[:10]}")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"   Error loading occupation-skill relations: {e}")
            return pd.DataFrame()
    
    def _build_lookup_dicts(self):
        """Build lookup dictionaries for fast fuzzy matching"""
        
        if self.occupations_df.empty and self.skills_df.empty:
            print("   No ESCO data loaded, skipping lookup dict creation")
            self.job_titles_lookup = {}
            self.skills_lookup = {}
            return
        
        # Job titles lookup (preferredLabel and altLabels)
        self.job_titles_lookup = {}
        for _, row in self.occupations_df.iterrows():
            preferred = row['preferredLabel'].lower() if pd.notna(row['preferredLabel']) else ""
            alt_labels = str(row['altLabels']).lower().split('\n') if pd.notna(row['altLabels']) else []
            
            all_labels = [preferred] + [label.strip() for label in alt_labels if label.strip()]
            
            for label in all_labels:
                if label:
                    self.job_titles_lookup[label] = {
                        'uri': row['conceptUri'],
                        'preferredLabel': row['preferredLabel']
                    }
        
        print(f"   Built job titles lookup: {len(self.job_titles_lookup)} entries")
        
        # Skills lookup (preferredLabel and altLabels)
        self.skills_lookup = {}
        for _, row in self.skills_df.iterrows():
            preferred = row['preferredLabel'].lower() if pd.notna(row['preferredLabel']) else ""
            alt_labels = str(row['altLabels']).lower().split('\n') if pd.notna(row['altLabels']) else []
            
            all_labels = [preferred] + [label.strip() for label in alt_labels if label.strip()]
            
            for label in all_labels:
                if label:
                    self.skills_lookup[label] = {
                        'uri': row['conceptUri'],
                        'preferredLabel': row['preferredLabel'],
                        'skillType': row['skillType']
                    }
        
        print(f"   Built skills lookup: {len(self.skills_lookup)} entries")
    
    def map_job_title(self, job_title: str, threshold: int = 85) -> Optional[Dict[str, str]]:  
        """
        Map a job title to ESCO occupation with intern handling
        """
        if not job_title or pd.isna(job_title):
            return None
        
        if not self.job_titles_lookup:
            return None
        
        job_title_lower = job_title.lower().strip()
        
        # Try exact match first
        if job_title_lower in self.job_titles_lookup:
            return {
                'uri': self.job_titles_lookup[job_title_lower]['uri'],
                'preferredLabel': self.job_titles_lookup[job_title_lower]['preferredLabel'],
                'match_score': 100
            }
        
        # Strip intern/trainee/junior and retry
        intern_keywords = ['intern', 'internship', 'trainee', 'graduate', 'entry level', 'entry-level']
        stripped_title = job_title_lower
        
        for keyword in intern_keywords:
            stripped_title = re.sub(rf'\b{keyword}\b', '', stripped_title, flags=re.IGNORECASE)
        
        stripped_title = re.sub(r'\s+', ' ', stripped_title).strip()
        
        # Try stripped version in exact match
        if stripped_title and stripped_title != job_title_lower:
            if stripped_title in self.job_titles_lookup:
                return {
                    'uri': self.job_titles_lookup[stripped_title]['uri'],
                    'preferredLabel': self.job_titles_lookup[stripped_title]['preferredLabel'],
                    'match_score': 95,
                    'original_title': job_title,
                    'mapped_via': 'stripped_intern',
                    'note': f'Mapped by removing intern-level keywords'
                }
        
        # Enhanced fallback mappings
        fallback_mappings = {
            # AI/ML/Data Science
            'ai engineer': 'software developer',
            'ai/ml engineer': 'software developer',
            'ml engineer': 'software developer',
            'machine learning engineer': 'software developer',
            'data scientist': 'data analyst',
            'data engineer': 'database administrator',
            'data analyst': 'data analyst',
            'business intelligence analyst': 'data analyst',
            'mlops engineer': 'software developer',
            
            # Software Engineering
            'software engineer': 'software developer',
            'software developer': 'software developer',
            'full stack developer': 'software developer',
            'fullstack developer': 'software developer',
            'frontend developer': 'web developer',
            'front-end developer': 'web developer',
            'backend developer': 'software developer',
            'back-end developer': 'software developer',
            'web developer': 'web developer',
            'mobile developer': 'software developer',
            'android developer': 'software developer',
            'ios developer': 'software developer',
            
            # DevOps/Cloud/Infrastructure
            'devops engineer': 'systems administrator',
            'cloud engineer': 'systems administrator',
            'platform engineer': 'systems administrator',
            'site reliability engineer': 'systems administrator',
            'sre': 'systems administrator',
            'infrastructure engineer': 'systems administrator',
            
            # Security
            'security engineer': 'ICT security administrator',
            'cybersecurity analyst': 'ICT security administrator',
            'information security analyst': 'ICT security administrator',
            
            # QA/Testing
            'qa engineer': 'ICT quality assurance tester',
            'test engineer': 'ICT quality assurance tester',
            'automation engineer': 'software developer',
            
            # Product/Project
            'product manager': 'ICT project manager',
            'technical product manager': 'ICT project manager',
            'scrum master': 'ICT project manager',
            'project manager': 'ICT project manager',
        }
        
        # Try fallback mapping on stripped title
        if stripped_title in fallback_mappings:
            fallback_title = fallback_mappings[stripped_title]
            
            if fallback_title is None:
                return None
            
            if fallback_title in self.job_titles_lookup:
                result = self.job_titles_lookup[fallback_title]
                return {
                    'uri': result['uri'],
                    'preferredLabel': result['preferredLabel'],
                    'match_score': 90,
                    'original_title': job_title,
                    'mapped_via': 'fallback_stripped',
                    'mapped_to': fallback_title
                }
        
        # Try fallback on original title
        if job_title_lower in fallback_mappings:
            fallback_title = fallback_mappings[job_title_lower]
            
            if fallback_title is None:
                return None
            
            if fallback_title in self.job_titles_lookup:
                result = self.job_titles_lookup[fallback_title]
                return {
                    'uri': result['uri'],
                    'preferredLabel': result['preferredLabel'],
                    'match_score': 90,
                    'original_title': job_title,
                    'mapped_via': 'fallback',
                    'mapped_to': fallback_title
                }
        
        # Fuzzy matching (last resort)
        matches = process.extract(
            stripped_title if stripped_title else job_title_lower,
            self.job_titles_lookup.keys(),
            scorer=fuzz.ratio,
            limit=5
        )
        
        if matches and matches[0][1] >= threshold:
            matched_label = matches[0][0]
            return {
                'uri': self.job_titles_lookup[matched_label]['uri'],
                'preferredLabel': self.job_titles_lookup[matched_label]['preferredLabel'],
                'match_score': matches[0][1],
                'mapped_via': 'fuzzy',
                'alternatives': [
                    {
                        'label': self.job_titles_lookup[m[0]]['preferredLabel'],
                        'score': m[1]
                    } for m in matches[1:4] if m[1] >= threshold
                ]
            }
        
        return None


    def map_skill(self, skill: str, threshold: int = 90) -> Optional[Dict[str, str]]:
        """
        Map a skill to ESCO skill
        """
        if not skill or pd.isna(skill):
            return None
        
        if not self.skills_lookup:
            return None
        
        skill_lower = skill.lower().strip()
        
        # Try exact match first
        if skill_lower in self.skills_lookup:
            return {
                'uri': self.skills_lookup[skill_lower]['uri'],
                'preferredLabel': self.skills_lookup[skill_lower]['preferredLabel'],
                'skillType': self.skills_lookup[skill_lower]['skillType'],
                'match_score': 100
            }
        
        # Fallback for tech skills
        tech_skill_mappings = {
            # Programming languages
            'python': 'Python (computer programming)',
            'java': 'Java (computer programming)',
            'javascript': 'JavaScript',
            'typescript': 'JavaScript', 
            'c++': 'C++',
            'c#': 'C#',
            'go': 'Go (computer programming)', 
            'golang': 'Go (computer programming)',
            'rust': None, 
            'ruby': 'Ruby (computer programming)',
            'php': 'PHP',
            
            # Frameworks/Libraries - Map to base language if no match
            'react': 'JavaScript',
            'angular': 'JavaScript',
            'vue': 'JavaScript',
            'vue.js': 'JavaScript',
            'django': 'Python (computer programming)',
            'flask': 'Python (computer programming)',
            'spring boot': 'Java (computer programming)',
            'spring': 'Java (computer programming)',
            'node.js': 'JavaScript',
            'nodejs': 'JavaScript',
            
            # DevOps/Cloud tools
            'docker': 'virtualization',  
            'kubernetes': 'cloud technologies',
            'jenkins': 'continuous integration',
            'terraform': 'infrastructure as code',
            'ansible': 'configuration management',
            'git': 'Git',
            
            # Cloud platforms
            'aws': 'Amazon Web Services',
            'amazon web services': 'Amazon Web Services',
            'azure': 'Microsoft Azure',
            'gcp': 'Google Cloud Platform',
            'google cloud': 'Google Cloud Platform',
            
            # Data Science/ML
            'tensorflow': 'machine learning',
            'pytorch': 'machine learning',
            'scikit-learn': 'machine learning',
            'sklearn': 'machine learning',
            'pandas': 'data analysis',
            'numpy': 'scientific computing',
            'keras': 'machine learning',
            
            # Databases
            'sql': 'SQL',
            'mysql': 'MySQL',
            'postgresql': 'PostgreSQL',
            'postgres': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'redis': 'database management',
            
            # Enterprise
            'sap': 'SAP software products',
            'oracle': 'Oracle software products',
            
            # General
            'agile': 'Agile software development',
            'scrum': 'SCRUM',
            'ci/cd': 'continuous integration',
            'devops': 'DevOps',
        }
        
        # Try tech skill mapping
        if skill_lower in tech_skill_mappings:
            mapped_skill = tech_skill_mappings[skill_lower]
            
            if mapped_skill is None:
                
                return {
                    'uri': f'custom:{skill_lower}',
                    'preferredLabel': skill.title(),
                    'skillType': 'technical',
                    'match_score': 80,
                    'mapped_via': 'custom_mapping',
                    'note': 'Modern tech skill not in ESCO, mapped to generic equivalent'
                }
            
            # Try to find mapped skill
            if mapped_skill.lower() in self.skills_lookup:
                result = self.skills_lookup[mapped_skill.lower()]
                return {
                    'uri': result['uri'],
                    'preferredLabel': result['preferredLabel'],
                    'skillType': result['skillType'],
                    'match_score': 85,
                    'mapped_via': 'tech_fallback',
                    'original_skill': skill,
                    'note': f'Mapped to broader concept: {mapped_skill}'
                }
        
        # Fuzzy matching
        matches = process.extract(
            skill_lower,
            self.skills_lookup.keys(),
            scorer=fuzz.ratio,
            limit=3
        )
        
        if matches and matches[0][1] >= threshold:
            matched_label = matches[0][0]
            return {
                'uri': self.skills_lookup[matched_label]['uri'],
                'preferredLabel': self.skills_lookup[matched_label]['preferredLabel'],
                'skillType': self.skills_lookup[matched_label]['skillType'],
                'match_score': matches[0][1],
                'mapped_via': 'fuzzy'
            }
        
        # Still no match - return useful fallback
        return {
            'uri': f'custom:{skill_lower}',
            'preferredLabel': skill.title(),
            'skillType': 'technical',
            'match_score': 50,
            'mapped_via': 'unmatched_fallback',
            'note': 'Skill not in ESCO database, treating as valid technical skill'
        }
    
    def map_skills_batch(self, skills_list: List[str], threshold: int = 75) -> List[Dict[str, str]]:
        """
        Map a list of skills to ESCO concepts
        
        Args:
            skills_list: List of raw skill strings
            threshold: Fuzzy matching threshold
        
        Returns:
            List of matched skill dicts
        """
        matched_skills = []
        for skill in skills_list:
            mapped = self.map_skill(skill, threshold)
            if mapped:
                matched_skills.append(mapped)
        
        return matched_skills
    
    def get_skills_for_occupation(self, occupation_uri: str) -> List[Dict[str, str]]:
        """
        Get related skills for a given ESCO occupation URI
        
        Args:
            occupation_uri: ESCO occupation URI
        
        Returns:
            List of related skills with type (essential/optional)
        """
        if self.occ_skill_relations_df.empty:
            return []
        
        # Filter relations by occupation
        occ_relations = self.occ_skill_relations_df[
            self.occ_skill_relations_df['occupationUri'] == occupation_uri
        ]
        
        related_skills = []
        for _, rel in occ_relations.iterrows():
            skill_uri = rel['skillUri']
            
            # Get skill details
            skill_row = self.skills_df[self.skills_df['conceptUri'] == skill_uri]
            
            if not skill_row.empty:
                related_skills.append({
                    'uri': skill_uri,
                    'preferredLabel': skill_row.iloc[0]['preferredLabel'],
                    'skillType': skill_row.iloc[0]['skillType'],
                    'relationType': rel['relationType']  # essential/optional
                })
        
        return related_skills
    
    def calculate_esco_skill_match(
        self,
        cv_skills: List[str],
        jd_skills: List[str],
        threshold: int = 75
    ) -> float:
        """
        Calculate skill match score using ESCO semantic matching
        
        Args:
            cv_skills: List of skills from CV
            jd_skills: List of skills from job description
            threshold: Fuzzy matching threshold
        
        Returns:
            Match score (0.0 to 1.0)
        """
        if not self.skills_lookup:
            # ESCO not available, return default
            return 0.5
        
        # Map CV skills to ESCO
        cv_esco_skills = set()
        for skill in cv_skills:
            mapped = self.map_skill(skill, threshold)
            if mapped:
                cv_esco_skills.add(mapped['uri'])
        
        # Map JD skills to ESCO
        jd_esco_skills = set()
        for skill in jd_skills:
            mapped = self.map_skill(skill, threshold)
            if mapped:
                jd_esco_skills.add(mapped['uri'])
        
        # Calculate Jaccard similarity
        if not jd_esco_skills:
            return 0.5  # Default if no JD skills mapped
        
        intersection = len(cv_esco_skills & jd_esco_skills)
        union = len(cv_esco_skills | jd_esco_skills)
        
        match_score = intersection / union if union > 0 else 0.0
        
        return round(match_score, 3)


# Singleton instance
_esco_mapper = None

def get_esco_mapper() -> Optional[ESCOMapper]:
    """Get or create ESCOMapper singleton instance"""
    global _esco_mapper
    
    if _esco_mapper is None:
        try:
            _esco_mapper = ESCOMapper()
            
            # Validate that ESCO loaded successfully
            if _esco_mapper.occupations_df.empty and _esco_mapper.skills_df.empty:
                print(f" ESCO data is empty - falling back to non-ESCO mode")
                return None
                
        except Exception as e:
            print(f" Failed to initialize ESCO Mapper: {e}")
            print("  Falling back to non-ESCO mode")
            return None
    
    return _esco_mapper