"""
Critic Agent for CV evaluation.

Reviews judge scores for accuracy, verifies evidence claims exist in source text,
checks for contradictions, and adjusts scores if evidence is weak.
Currently critic.py is a stub - this implements full functionality.
"""

from typing import Dict, List, Optional
import logging
import json
from .base_agent import BaseAgent
from .state import EvaluationState

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """
    Critic agent that reviews and validates judge scores.
    
    Implements full critic functionality:
    - Verifies evidence claims exist in source text
    - Checks for contradictions
    - Adjusts scores if evidence is weak or missing
    - Flags inconsistencies
    """
    
    def __init__(self):
        """Initialize critic agent"""
        system_prompt = """You are a critic agent for CV evaluation system. Your role is to:
1. Review judge scores for accuracy
2. Verify that evidence claims actually exist in the source text (CV/LinkedIn)
3. Check for contradictions between different data sources
4. Adjust scores if evidence is weak or missing
5. Flag inconsistencies for human review

Always be thorough and critical. If evidence doesn't support a score, adjust it.
Respond with JSON in this format:
{
  "judge_scores": [
    {
      "criterion": "APIs",
      "score": 4,
      "original_score": 5,
      "evidence": "Verified evidence from source",
      "adjusted": true,
      "adjustment_reason": "Original evidence not found in CV text"
    }
  ],
  "contradictions": ["description of contradictions"],
  "flags": ["warnings or issues found"]
}"""
        
        super().__init__(
            name="CriticAgent",
            system_prompt=system_prompt,
            temperature=0.2,  # Lower temperature for more critical analysis
            max_tokens=2000
        )
    
    def review_scores(self, judge_output: Dict, merged_json: Dict) -> Dict:
        """
        Review judge scores and validate evidence.
        
        Args:
            judge_output: Output from judge agent
            merged_json: Merged candidate and job description data
        
        Returns:
            Reviewed and potentially adjusted scores
        """
        judge_scores = judge_output.get("judge_scores", [])
        candidate = merged_json.get("candidate", {})
        job_desc = merged_json.get("job_description", {})
        
        # Get source text for verification
        cv_text = ""
        linkedin_text = ""
        
        # Try to get CV text from preprocessed data if available
        # For now, build text from extracted data
        if candidate.get("experience"):
            cv_text += " ".join([
                f"{exp.get('title', '')} at {exp.get('company', '')} " + 
                " ".join(exp.get("highlights", []))
                for exp in candidate.get("experience", [])
            ])
        
        if candidate.get("skills_raw"):
            cv_text += " " + " ".join(candidate.get("skills_raw", []))
        
        reviewed_scores = []
        contradictions = []
        flags = []
        
        for score_entry in judge_scores:
            criterion = score_entry.get("criterion", "")
            original_score = score_entry.get("score", 0)
            evidence = score_entry.get("evidence", "")
            
            # Verify evidence exists in source text
            evidence_verified = self.verify_evidence(evidence, cv_text + " " + linkedin_text)
            
            adjusted_score = original_score
            adjusted = False
            adjustment_reason = None
            
            if not evidence_verified and original_score > 0:
                # Evidence not found - reduce score
                adjusted_score = max(0, original_score - 1)
                adjusted = True
                adjustment_reason = "Evidence not found in source text"
                flags.append(f"{criterion}: Evidence claim not verified")
            
            reviewed_scores.append({
                "criterion": criterion,
                "score": adjusted_score,
                "original_score": original_score,
                "evidence": evidence,
                "adjusted": adjusted,
                "adjustment_reason": adjustment_reason,
                "evidence_verified": evidence_verified
            })
        
        # Check for contradictions
        cv_data = merged_json.get("candidate", {}).get("cv_data", {})
        linkedin_data = merged_json.get("candidate", {}).get("linkedin_data", {})
        
        if cv_data and linkedin_data:
            detected_contradictions = self.detect_contradictions(cv_data, linkedin_data)
            contradictions.extend(detected_contradictions)
        
        return {
            "judge_scores": reviewed_scores,
            "contradictions": contradictions,
            "flags": flags
        }
    
    def verify_evidence(self, evidence: str, source_text: str) -> bool:
        """
        Verify that evidence claim exists in source text.
        
        Args:
            evidence: Evidence claim to verify
            source_text: Source text to search
        
        Returns:
            True if evidence found in source text
        """
        if not evidence or not source_text:
            return False
        
        # Simple keyword matching (could be enhanced with semantic search)
        evidence_lower = evidence.lower()
        source_lower = source_text.lower()
        
        # Check if key terms from evidence appear in source
        # Extract key terms (words longer than 4 chars, excluding common words)
        common_words = {"the", "and", "or", "but", "with", "from", "that", "this", "was", "were", "been", "have", "has"}
        evidence_terms = [
            word for word in evidence_lower.split() 
            if len(word) > 4 and word not in common_words
        ]
        
        if not evidence_terms:
            # If no key terms, check if evidence substring exists
            return evidence_lower in source_lower
        
        # Check if at least 50% of key terms appear in source
        matches = sum(1 for term in evidence_terms if term in source_lower)
        return matches >= len(evidence_terms) * 0.5
    
    def detect_contradictions(self, cv_data: Dict, linkedin_data: Dict) -> List[str]:
        """
        Detect contradictions between CV and LinkedIn data.
        
        Args:
            cv_data: CV extracted data
            linkedin_data: LinkedIn extracted data
        
        Returns:
            List of contradiction descriptions
        """
        contradictions = []
        
        # Check experience dates
        cv_experience = cv_data.get("experience", [])
        linkedin_experience = linkedin_data.get("experience", [])
        
        if cv_experience and linkedin_experience:
            # Check for overlapping companies with different dates
            cv_companies = {exp.get("company", "").lower(): exp for exp in cv_experience if exp.get("company")}
            linkedin_companies = {exp.get("company", "").lower(): exp for exp in linkedin_experience if exp.get("company")}
            
            for company, cv_exp in cv_companies.items():
                if company in linkedin_companies:
                    linkedin_exp = linkedin_companies[company]
                    cv_start = cv_exp.get("start", "")
                    linkedin_start = linkedin_exp.get("start", "")
                    
                    if cv_start and linkedin_start and cv_start != linkedin_start:
                        contradictions.append(
                            f"Date mismatch for {company}: CV shows {cv_start}, LinkedIn shows {linkedin_start}"
                        )
        
        # Check education
        cv_education = cv_data.get("education", [])
        linkedin_education = linkedin_data.get("education", [])
        
        if cv_education and linkedin_education:
            # Simple check: if completely different institutions
            cv_institutions = set(edu.lower() for edu in cv_education)
            linkedin_institutions = set(edu.lower() for edu in linkedin_education)
            
            if cv_institutions and linkedin_institutions:
                overlap = cv_institutions.intersection(linkedin_institutions)
                if not overlap and len(cv_institutions) > 0 and len(linkedin_institutions) > 0:
                    contradictions.append("No overlapping education institutions between CV and LinkedIn")
        
        return contradictions
    
    def adjust_scores(self, judge_scores: List[Dict], issues: List[str]) -> List[Dict]:
        """
        Adjust scores based on detected issues.
        
        Args:
            judge_scores: Original judge scores
            issues: List of issues/contradictions found
        
        Returns:
            Adjusted judge scores
        """
        if not issues:
            return judge_scores
        
        adjusted_scores = []
        for score_entry in judge_scores:
            adjusted_entry = score_entry.copy()
            
            # Reduce score by 1 for each major issue (min 0)
            # Only adjust if there are significant contradictions
            major_issues = [issue for issue in issues if "mismatch" in issue.lower() or "contradiction" in issue.lower()]
            if major_issues:
                original_score = adjusted_entry.get("score", 0)
                adjusted_entry["score"] = max(0, original_score - 1)
                adjusted_entry["adjusted"] = True
                adjusted_entry["adjustment_reason"] = f"Adjusted due to {len(major_issues)} contradictions"
            
            adjusted_scores.append(adjusted_entry)
        
        return adjusted_scores
    
    def execute(self, state: Dict) -> Dict:
        """
        Execute critic agent.
        
        Args:
            state: Current evaluation state or review request
        
        Returns:
            Reviewed and adjusted scores
        """
        if isinstance(state, EvaluationState):
            # Review judge scores from state
            judge_output = {"judge_scores": state.judge_scores or []}
            
            # Build merged_json from state
            merged_json = {
                "candidate": {
                    "skills_canonical": state.normalized_skills or [],
                    "skills_raw": [],
                    "experience": [],
                    "education": [],
                    "github": state.github_data or {},
                    "cv_data": state.cv_data or {},
                    "linkedin_data": state.linkedin_data or {}
                },
                "job_description": state.jd_data or {}
            }
            
            # Populate from extracted data
            if state.cv_data:
                merged_json["candidate"]["skills_raw"] = state.cv_data.get("skills_raw", [])
                merged_json["candidate"]["experience"] = state.cv_data.get("experience", [])
                merged_json["candidate"]["education"] = state.cv_data.get("education", [])
        else:
            # Direct review request
            judge_output = state.get("judge_output", {})
            merged_json = state.get("merged_json", {})
        
        return self.review_scores(judge_output, merged_json)

