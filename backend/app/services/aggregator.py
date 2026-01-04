from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from app.services.technology_mismatch_detector import detect_technology_mismatch
from app.services.semantic import get_embeddings, cosine_similarity
import re
import logging

logger = logging.getLogger(__name__)

def aggregate_scores(
    semantic_features: Dict,
    judge_scores: Dict,
    github_info: Dict,
    experience_info: List[Dict],
    merged_json: Dict
) -> Dict:
    """
    Aggregate all scores into a 0-100 total score
    
    Includes validation and error recovery for edge cases.
    """
    # Validate inputs
    if not semantic_features:
        logger.warning("semantic_features is empty, using defaults")
        semantic_features = {"sim_profile_to_jd": 0.0, "sim_github_to_jd": 0.0}
    
    if not judge_scores:
        logger.warning("judge_scores is empty, using defaults")
        judge_scores = {"judge_scores": []}
    
    if not merged_json:
        logger.warning("merged_json is empty, using defaults")
        merged_json = {"candidate": {}, "job_description": {}}
    
    # Validate candidate data
    candidate = merged_json.get("candidate", {})
    candidate_skills = candidate.get("skills_raw", []) + candidate.get("skills_canonical", [])
    if not candidate_skills:
        logger.warning("No candidate skills - will result in low score (neutral, not error)")
    
    # Validate job description
    job_desc = merged_json.get("job_description", {})
    if not job_desc.get("must_have"):
        logger.warning("No must-have skills in JD - cannot evaluate properly (using nice-to-have or empty)")
    
    """
    Aggregate all scores into a 0-100 total score
    
    Combines:
    - Semantic fit: 30 pts (from similarity scores)
    - Role competency: 30 pts (from judge scores, average * 6)
    - Experience recency: 15 pts (time-decay on last 3 years)
    - GitHub evidence: 15 pts (activity, relevance, quality)
    - Bonus/Malus: ±10 pts (awards, contradictions, keyword stuffing)
    - Skill mismatch penalty: 0-30 pts (missing must-have skills)
    - Technology mismatch penalty: 0-15 pts (framework mismatches)
    
    Args:
        semantic_features: Dictionary with similarity scores
        judge_scores: Dictionary with judge_scores list
        github_info: Dictionary with GitHub data (can also extract from merged_json if empty)
        experience_info: List of experience entries
        merged_json: Full merged JSON for context
    
    Returns:
        Dictionary with total_score and breakdown
    """
    # Extract GitHub info from merged_json if not provided
    if not github_info or not github_info.get("repos"):
        candidate = merged_json.get("candidate", {})
        github_from_candidate = candidate.get("github", {})
        if github_from_candidate and github_from_candidate.get("repos"):
            logger.info("Extracting GitHub info from merged_json candidate data")
            github_info = github_from_candidate
    
    # Log GitHub info for debugging
    if github_info:
        repos_count = len(github_info.get("repos", []))
        commits = github_info.get("commits_last_12m", 0)
        prs = github_info.get("external_prs_merged", 0)
        logger.info(f"GitHub info for scoring: {repos_count} repos, {commits} commits, {prs} PRs")
    else:
        logger.warning("No GitHub info available for scoring")
    
    # 1. Semantic fit (30 pts max)
    sim_profile = semantic_features.get("sim_profile_to_jd", 0.0)
    sim_github = semantic_features.get("sim_github_to_jd", 0.0)
    semantic_fit = (sim_profile * 0.7 + sim_github * 0.3) * 30
    
    # Calculate technology mismatch penalty early (used for both semantic fit adjustment and final penalty)
    technology_mismatch_penalty = calculate_technology_mismatch_penalty(merged_json)
    
    # Apply technology mismatch penalty to semantic fit (reduce if frameworks don't match)
    if technology_mismatch_penalty > 0:
        # Reduce semantic fit by 50% if there's a technology mismatch
        semantic_fit = semantic_fit * 0.5  # Reduce by 50% for framework mismatches
        logger.info(f"Reducing semantic fit due to technology mismatch: {semantic_fit:.1f}")
    
    semantic_fit = round(semantic_fit, 1)
    
    # 2. Role competency (30 pts max)
    # Average judge scores and scale to 30
    # Handles variable criteria count (4-8 criteria) - scales consistently
    # CRITICAL: Use original scores (not adjusted by critic) for consistent calculation
    scores_list = judge_scores.get("judge_scores", [])
    if scores_list:
        # Extract scores, handling both original format and critic-reviewed format
        score_values = []
        criteria_names = []
        for score_entry in scores_list:
            # Handle both formats: {"score": X} or {"score": X, "original_score": Y}
            score = score_entry.get("score", 0)
            # If this is a critic-reviewed score with original_score, use original for consistency
            # But for now, use the score as-is since we're using judge_scores (not critic_scores)
            score_values.append(score)
            criteria_names.append(score_entry.get("criterion", "N/A"))
        
        avg_score = sum(score_values) / len(score_values) if score_values else 0
        role_competency = (avg_score / 5.0) * 30  # Scale from 0-5 to 0-30 (works for any criteria count)
        logger.info(f"Role competency: {len(scores_list)} criteria ({', '.join(criteria_names[:5])}{'...' if len(criteria_names) > 5 else ''}), avg={avg_score:.2f}, scaled={role_competency:.1f}")
        logger.debug(f"  Individual scores: {[f'{name}: {val}' for name, val in zip(criteria_names, score_values)]}")
    else:
        role_competency = 0
        logger.warning("No judge scores available for role competency calculation")
    role_competency = round(role_competency, 1)
    
    # 3. Experience recency (15 pts max)
    # Time-decay: more recent experience = higher score
    experience_recency = calculate_experience_recency(experience_info)
    experience_recency = round(experience_recency, 1)
    
    # 4. GitHub evidence (15 pts max)
    github_evidence = calculate_github_score(github_info)
    github_evidence = round(github_evidence, 1)
    
    # 5. Bonus/Malus (±10 pts)
    bonus_malus = calculate_bonus_malus(merged_json)
    bonus_malus = round(bonus_malus, 1)
    
    # 6. Skill mismatch penalty (if candidate has NONE of the must-have skills)
    skill_mismatch_penalty = calculate_skill_mismatch_penalty(merged_json)
    
    # 7. Technology mismatch penalty (already calculated above for semantic fit adjustment)
    # The penalty is applied both to semantic fit (reduction) and as a direct penalty
    
    # 8. Role match bonus (based on predicted role vs job title)
    role_match_bonus = calculate_role_match_bonus(merged_json)
    
    # Build breakdown first
    breakdown = {
        "semantic_fit": semantic_fit,
        "role_competency": role_competency,
        "experience_recency": experience_recency,
        "github_evidence": github_evidence,
        "bonus_malus": bonus_malus,
        "role_match_bonus": round(role_match_bonus, 1),
        "skill_mismatch_penalty": round(skill_mismatch_penalty, 1),
        "technology_mismatch_penalty": round(technology_mismatch_penalty, 1)
    }
    
    # Calculate total score from breakdown components
    calculated_total = (
        breakdown["semantic_fit"] +
        breakdown["role_competency"] +
        breakdown["experience_recency"] +
        breakdown["github_evidence"] +
        breakdown["bonus_malus"] +
        breakdown["role_match_bonus"] -
        breakdown["skill_mismatch_penalty"] -
        breakdown["technology_mismatch_penalty"]
    )
    
    # Log calculation breakdown for debugging
    logger.info(f"Score calculation: {semantic_fit} + {role_competency} + {experience_recency} + {github_evidence} + {bonus_malus} + {role_match_bonus} - {skill_mismatch_penalty} - {technology_mismatch_penalty} = {calculated_total}")
    
    # Clamp to 0-100 and round to integer
    total_score = max(0, min(100, int(round(calculated_total))))
    
    # Validate final score matches breakdown sum (allow small floating point differences)
    if abs(total_score - calculated_total) > 1.0:
        logger.warning(f"Score mismatch detected: total={total_score}, calculated={calculated_total:.2f}, difference={abs(total_score - calculated_total):.2f}")
        logger.warning(f"  Using calculated value: {int(round(calculated_total))}")
        total_score = int(round(calculated_total))
    
    logger.info(f"Final score: {total_score} (from breakdown components)")
    
    # Final validation: ensure breakdown components are valid
    validated_breakdown = {}
    for key, value in breakdown.items():
        if isinstance(value, (int, float)):
            if key.endswith("_penalty"):
                validated_breakdown[key] = round(max(0, min(30, value)), 1)
            else:
                validated_breakdown[key] = round(max(0, min(100, value)), 1)
        else:
            validated_breakdown[key] = value
    
    return {
        "total_score": total_score,
        "breakdown": validated_breakdown
    }

def calculate_experience_recency(experience: List[Dict]) -> float:
    """Calculate experience recency score (0-15 pts)
    
    Calculates the percentage of total experience that falls within the last 3 years.
    Only counts months that actually overlap with the recent period.
    """
    if not experience:
        return 0.0
    
    now = datetime.now()
    three_years_ago = now - timedelta(days=3*365)
    
    total_months = 0
    recent_months = 0
    
    for exp in experience:
        start_str = exp.get("start", "")
        end_str = exp.get("end", "")
        
        if not start_str:
            continue
        
        # Parse dates (YYYY-MM format)
        try:
            start_date = datetime.strptime(start_str[:7], "%Y-%m")
            # Handle "Present" properly
            if not end_str or end_str.lower() == "present":
                end_date = now
            else:
                end_date = datetime.strptime(end_str[:7], "%Y-%m")
            
            # Calculate total months for this experience
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            # Ensure at least 1 month if dates are in the same month
            if months == 0:
                months = 1
            total_months += months
            
            # Calculate how many months are within the recent period (last 3 years)
            # Only count months that overlap with the recent period
            recent_start = max(start_date, three_years_ago)
            recent_end = min(end_date, now)
            
            if recent_start <= recent_end:
                recent_months_for_exp = (recent_end.year - recent_start.year) * 12 + (recent_end.month - recent_start.month)
                # Ensure at least 0 (don't count negative)
                if recent_months_for_exp < 0:
                    recent_months_for_exp = 0
                recent_months += recent_months_for_exp
            # If no overlap, recent_months_for_exp remains 0 (already initialized)
            
        except Exception as e:
            logger.warning(f"Error parsing experience dates: {start_str} to {end_str}: {str(e)}")
            continue
    
    if total_months == 0:
        return 0.0
    
    # Score based on percentage of recent experience
    recent_ratio = recent_months / total_months if total_months > 0 else 0
    score = recent_ratio * 15
    
    logger.info(f"Experience recency calculation: {recent_months}/{total_months} months recent = {recent_ratio:.2%} → {score:.1f} pts")
    
    return score

def calculate_github_score(github_info: Dict) -> float:
    """Calculate GitHub evidence score (0-15 pts)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Handle None or empty dict
    if not github_info or github_info is None:
        logger.warning("GitHub info is empty or None")
        return 0.0
    
    # Ensure repos is a list
    repos = github_info.get("repos", [])
    if not isinstance(repos, list):
        logger.warning(f"GitHub repos is not a list: {type(repos)}")
        repos = []
    
    commits = github_info.get("commits_last_12m", 0) or 0
    prs = github_info.get("external_prs_merged", 0) or 0
    
    # Convert to int if needed
    try:
        commits = int(commits) if commits else 0
        prs = int(prs) if prs else 0
    except (ValueError, TypeError):
        logger.warning(f"Invalid GitHub commits/PRs: commits={commits}, prs={prs}")
        commits = 0
        prs = 0
    
    logger.info(f"GitHub score calculation: repos={len(repos)}, commits={commits}, prs={prs}")
    
    score = 0.0
    
    # Repos: up to 5 pts (34 repos = 5 pts)
    if repos and len(repos) > 0:
        repo_count = len(repos)
        repo_score = min(5.0, repo_count * 0.5)
        score += repo_score
        logger.info(f"Repo score: {repo_score} (from {repo_count} repos)")
    
    # Commits: up to 5 pts (100+ commits = 5 pts)
    if commits and commits > 0:
        commit_score = min(5.0, (commits / 100.0) * 5)
        score += commit_score
        logger.info(f"Commit score: {commit_score} (from {commits} commits)")
    
    # External PRs: up to 5 pts (5+ PRs = 5 pts, 10 PRs = 5 pts)
    if prs and prs > 0:
        pr_score = min(5.0, float(prs))
        score += pr_score
        logger.info(f"PR score: {pr_score} (from {prs} PRs)")
    
    logger.info(f"Total GitHub score: {score:.1f}")
    return round(score, 1)

def calculate_bonus_malus(merged_json: Dict) -> float:
    """Calculate bonus/malus score (±10 pts)"""
    score = 0.0
    
    candidate = merged_json.get("candidate", {})
    
    # Bonus: Certifications (+1 pt each, max +5)
    certifications = candidate.get("certifications", [])
    logger.info(f"Bonus/Malus: Found {len(certifications) if certifications else 0} certifications: {certifications}")
    if certifications:
        cert_bonus = min(5, len(certifications))
        score += cert_bonus
        logger.info(f"Bonus/Malus: Added {cert_bonus} pts for certifications")
    
    # Bonus: LinkedIn endorsements (+0.5 pt per 5 endorsements, max +3)
    linkedin = candidate.get("linkedin", {})
    if linkedin:
        endorsements = linkedin.get("endorsements", [])
        if endorsements:
            endorsement_bonus = min(3, len(endorsements) * 0.1)
            score += endorsement_bonus
            logger.debug(f"Bonus/Malus: Added {endorsement_bonus} pts for {len(endorsements)} endorsements")
    
    # Also check certifications in linkedin_data
    linkedin_data = candidate.get("linkedin_data", {})
    if linkedin_data:
        linkedin_certs = linkedin_data.get("certifications", [])
        if linkedin_certs and not certifications:  # Only use if not already counted
            cert_bonus = min(5, len(linkedin_certs))
            score += cert_bonus
            logger.info(f"Bonus/Malus: Added {cert_bonus} pts for LinkedIn certifications: {linkedin_certs}")
    
    # Malus: Check for potential keyword stuffing (too many skills)
    skills = candidate.get("skills_raw", [])
    if skills and len(skills) > 50:  # Suspiciously high
        score -= 2
        logger.debug(f"Bonus/Malus: Subtracted 2 pts for keyword stuffing ({len(skills)} skills)")
    
    # Malus: Check for contradictions (future: implement actual contradiction detection)
    # For now, no malus for contradictions
    
    # CRITICAL: Clamp to ±10 BEFORE returning
    score = max(-10.0, min(10.0, score))
    
    logger.info(f"Bonus/Malus final score: {score} (clamped to ±10)")
    return round(score, 1)

def match_skill_semantically(required_skill: str, candidate_skills: List[str], threshold: float = 0.7) -> Tuple[bool, Optional[str], float]:
    """
    Match a required skill to candidate skills using semantic similarity (embeddings).
    
    Useful for conceptual skills like "data analysis" matching "Data Analytics & Visualization".
    
    Args:
        required_skill: The required skill to match
        candidate_skills: List of candidate skills to search
        threshold: Minimum similarity score (0-1) to consider a match
    
    Returns:
        Tuple of (found, matched_skill, similarity_score)
        - found: True if a match was found above threshold
        - matched_skill: The candidate skill that matched (or None)
        - similarity_score: The similarity score (0-1)
    """
    if not required_skill or not candidate_skills:
        return (False, None, 0.0)
    
    try:
        # Generate embedding for required skill
        required_embedding = get_embeddings(required_skill)
        
        if required_embedding is None or len(required_embedding) == 0:
            return (False, None, 0.0)
        
        best_match = None
        best_similarity = 0.0
        
        # Compare with each candidate skill
        for candidate_skill in candidate_skills:
            if not candidate_skill or not candidate_skill.strip():
                continue
            
            try:
                candidate_embedding = get_embeddings(candidate_skill)
                if candidate_embedding is None or len(candidate_embedding) == 0:
                    continue
                
                similarity = cosine_similarity(required_embedding, candidate_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate_skill
            except Exception as e:
                logger.debug(f"Error computing similarity for '{candidate_skill}': {str(e)}")
                continue
        
        if best_similarity >= threshold:
            logger.debug(f"Semantic match: '{required_skill}' ~ '{best_match}' (similarity: {best_similarity:.3f})")
            return (True, best_match, best_similarity)
        else:
            return (False, best_match, best_similarity)
            
    except Exception as e:
        logger.warning(f"Error in semantic skill matching for '{required_skill}': {str(e)}")
        return (False, None, 0.0)

def has_required_skills(
    candidate_skills: List[str], 
    required_skills: List[str],
    skill_types: Optional[Dict[str, str]] = None,
    use_semantic_matching: bool = True
) -> Tuple[bool, Dict]:
    """
    Check if candidate has all required skills (case-insensitive, normalized).
    
    This function normalizes both candidate and required skills and checks for presence.
    Handles variations (e.g., "Power BI" matches "Power Bi", "Powerbi").
    Uses semantic matching for conceptual skills.
    
    Args:
        candidate_skills: List of candidate skill strings (can be raw or canonical)
        required_skills: List of required skill strings from job description
        skill_types: Optional dict mapping skill names to their types (technical, soft, concept, etc.)
        use_semantic_matching: Whether to use semantic matching for conceptual skills
    
    Returns:
        Tuple of (has_all_skills, details_dict)
        details_dict contains: found_skills, missing_skills, match_methods
    """
    if not required_skills:
        return (True, {
            "found_skills": [],
            "missing_skills": [],
            "match_methods": {}
        })
    
    if not candidate_skills:
        logger.warning("Candidate has no skills - missing all required skills")
        return (False, {
            "found_skills": [],
            "missing_skills": required_skills,
            "match_methods": {}
        })
    
    # Import skill categorizer
    from app.services.skill_categorizer import categorize_skill
    
    # Normalize all skills to lowercase for comparison
    candidate_normalized = [s.lower().strip() for s in candidate_skills if s and s.strip()]
    required_normalized = [s.lower().strip() for s in required_skills if s and s.strip()]
    
    # Keep original case for semantic matching (more accurate)
    candidate_original = [s.strip() for s in candidate_skills if s and s.strip()]
    
    found_skills = []
    missing_skills = []
    match_methods = {}  # Track how each skill was matched
    
    # Check each required skill
    for idx, required_skill in enumerate(required_normalized):
        required_original = required_skills[idx] if idx < len(required_skills) else required_skill
        found = False
        matched_candidate_skill = None
        match_method = "none"
        
        # Determine skill type
        skill_type = None
        if skill_types and required_original in skill_types:
            skill_type = skill_types[required_original]
        else:
            skill_type = categorize_skill(required_original)
        
        # CRITICAL: For single-character skills (like "R", "C"), use strict matching
        # Single characters are almost always specific technologies and should match exactly
        # Allow matching "R" to "R Programming" or "R Language" but NOT to "relational" or "react"
        is_single_char = len(required_skill) == 1
        
        # Debug logging for single-character skills
        if is_single_char:
            logger.debug(f"Checking for single-char skill '{required_original}' in candidate skills (total: {len(candidate_normalized)})")
            logger.debug(f"  Candidate skills sample: {candidate_normalized[:10]}")
        
        # CRITICAL: Check single-character FIRST, before exact match
        # This prevents false positives like "R" matching "relational" or "react"
        if is_single_char:
            # For single-character skills, check if it appears as:
            # 1. Exact match: "R" matches "R" or "r"
            # 2. At start of skill name: "R" matches "R Programming", "R Language", etc.
            # This prevents "R" from matching "relational", "react", "angular", etc.
            # Pattern: "R" at start of string followed by space, dash, slash, or end of string
            # OR "R" as a standalone word (word boundary before and after)
            pattern_start = r'^' + re.escape(required_skill) + r'(?:\s|$|[-/\(\.])'  # Start of string, followed by space/end/punctuation
            pattern_word = r'\b' + re.escape(required_skill) + r'\b'  # Word boundary (standalone word)
            
            for candidate_idx, candidate_skill in enumerate(candidate_normalized):
                # Check if it's at the start of the skill name
                if re.match(pattern_start, candidate_skill, re.IGNORECASE):
                    found = True
                    matched_candidate_skill = candidate_original[candidate_idx] if candidate_idx < len(candidate_original) else candidate_skill
                    match_method = "exact (single-char at start)"
                    logger.debug(f"  ✅ Matched '{required_original}' to '{matched_candidate_skill}' using method: {match_method}")
                    break
                # Check if it's a standalone word (but not in the middle of another word)
                elif re.search(pattern_word, candidate_skill, re.IGNORECASE):
                    # Additional check: ensure it's not part of a longer word
                    # If the character before or after is a lowercase letter, it's part of a word
                    match_obj = re.search(pattern_word, candidate_skill, re.IGNORECASE)
                    if match_obj:
                        start_pos = match_obj.start()
                        end_pos = match_obj.end()
                        # Check characters before and after
                        before_ok = start_pos == 0 or not candidate_skill[start_pos - 1].isalpha()
                        after_ok = end_pos >= len(candidate_skill) or not candidate_skill[end_pos].islower()
                        if before_ok and after_ok:
                            found = True
                            matched_candidate_skill = candidate_original[candidate_idx] if candidate_idx < len(candidate_original) else candidate_skill
                            match_method = "exact (single-char standalone)"
                            logger.debug(f"  ✅ Matched '{required_original}' to '{matched_candidate_skill}' using method: {match_method}")
                            break
            if not found:
                match_method = "none (single-char requires exact match)"
                logger.debug(f"Single-char skill '{required_original}' not found in candidate skills: {candidate_normalized[:10]}")
        else:
            # Try exact match for multi-character skills
            if required_skill in candidate_normalized:
                found = True
                matched_candidate_skill = required_skill
                match_method = "exact"
                logger.debug(f"Exact match found: '{required_original}' = '{matched_candidate_skill}'")
            else:
                # Try substring/contains match with word boundaries and minimum length
                # Require at least 3 characters to prevent false positives like "r" matching "relational"
                min_length = 3
                if len(required_skill) >= min_length:
                    for candidate_idx, candidate_skill in enumerate(candidate_normalized):
                        # Use word boundary matching to prevent false positives
                        # Example: "sql" matches "SQL" but "r" doesn't match "relational" (word boundary)
                        pattern = r'\b' + re.escape(required_skill) + r'\b'
                        if re.search(pattern, candidate_skill, re.IGNORECASE):
                            found = True
                            matched_candidate_skill = candidate_original[candidate_idx] if candidate_idx < len(candidate_original) else candidate_skill
                            match_method = "substring"
                            logger.debug(f"Substring match found: '{required_original}' = '{matched_candidate_skill}'")
                            break
                        
                        # Also check if candidate skill is contained in required (for compound skills)
                        # Example: "Power BI" in "Microsoft Power BI"
                        if len(candidate_skill) >= min_length:
                            candidate_pattern = r'\b' + re.escape(candidate_skill) + r'\b'
                            if re.search(candidate_pattern, required_skill, re.IGNORECASE):
                                found = True
                                matched_candidate_skill = candidate_original[candidate_idx] if candidate_idx < len(candidate_original) else candidate_skill
                                match_method = "substring"
                                logger.debug(f"Substring match found: '{required_original}' in '{matched_candidate_skill}'")
                                break
                else:
                    # For 2-character skills, only exact match
                    found = any(required_skill == cand for cand in candidate_normalized)
        
        # If not found and skill is conceptual, try semantic matching
        # CRITICAL: NEVER use semantic matching for single-character skills
        if not found and use_semantic_matching and not is_single_char:
            # Check if skill type is concept or soft
            if skill_type in ["concept", "soft"]:
                semantic_found, semantic_match, similarity = match_skill_semantically(
                    required_original, candidate_original, threshold=0.7
                )
                if semantic_found:
                    found = True
                    matched_candidate_skill = semantic_match
                    match_method = f"semantic (similarity: {similarity:.3f})"
            
            # FALLBACK: If still not found and skill looks conceptual, try semantic matching anyway
            # This handles cases where categorization might have been wrong
            elif not found:
                # Check if required skill contains conceptual keywords
                conceptual_keywords = ["process", "processes", "pipeline", "pipelines", 
                                      "database", "databases", "analysis", "analytics", 
                                      "methodology", "framework", "design", "modeling"]
                if any(keyword in required_original.lower() for keyword in conceptual_keywords):
                    # Try semantic matching with lower threshold for concepts
                    semantic_found, semantic_match, similarity = match_skill_semantically(
                        required_original, candidate_original, threshold=0.65
                    )
                    if semantic_found:
                        found = True
                        matched_candidate_skill = semantic_match
                        match_method = f"semantic_fallback (similarity: {similarity:.3f})"
                        logger.info(f"Semantic fallback match: '{required_original}' ~ '{semantic_match}' (similarity: {similarity:.3f})")
        
        if found:
            found_skills.append(f"{required_original} (matched: {matched_candidate_skill}, method: {match_method})")
            match_methods[required_original] = match_method
            logger.debug(f"✅ Found required skill '{required_original}' → matched to '{matched_candidate_skill}' via {match_method}")
        else:
            missing_skills.append(required_original)
            match_methods[required_original] = "none"
            logger.debug(f"❌ Missing required skill '{required_original}' - no match found in candidate skills")
    
    # Log detailed results
    details = {
        "found_skills": found_skills,
        "missing_skills": missing_skills,
        "match_methods": match_methods
    }
    
    if missing_skills:
        logger.warning(f"❌ Candidate missing required skills: {missing_skills}")
        logger.info(f"   Found skills: {found_skills}")
        return (False, details)
    else:
        logger.info(f"✅ Candidate has all required skills: {found_skills}")
        return (True, details)

def calculate_skill_mismatch_penalty(merged_json: Dict) -> float:
    """
    Calculate penalty for complete skill mismatch (0-30 pts penalty) using semantic similarity
    
    Uses embeddings to match candidate skills to required skills semantically.
    No hardcoded keyword matching - works with any technologies.
    
    If candidate has NONE of the must-have skills, apply significant penalty.
    This helps catch cases where semantic similarity is high but actual skills don't match.
    
    CRITICAL: Checks for framework mismatches FIRST before semantic matching.
    """
    from app.services.semantic import get_embeddings, cosine_similarity
    
    logger.info("=== calculate_skill_mismatch_penalty called ===")
    
    job_desc = merged_json.get("job_description", {})
    must_have_skills = job_desc.get("must_have", [])
    
    logger.info(f"Must-have skills count: {len(must_have_skills) if must_have_skills else 0}")
    if must_have_skills:
        logger.debug(f"First 5 must-have skills: {must_have_skills[:5]}")
    
    if not must_have_skills:
        logger.warning("No must-have skills defined, returning 0.0 penalty")
        return 0.0
    
    candidate = merged_json.get("candidate", {})
    candidate_skills_raw = candidate.get("skills_raw", [])
    candidate_skills_canonical = candidate.get("skills_canonical", [])
    all_candidate_skills = list(set(candidate_skills_raw + candidate_skills_canonical))
    
    logger.info(f"Candidate has {len(all_candidate_skills)} total skills (raw: {len(candidate_skills_raw)}, canonical: {len(candidate_skills_canonical)})")
    if all_candidate_skills:
        logger.debug(f"First 10 candidate skills: {all_candidate_skills[:10]}")
    
    if not all_candidate_skills:
        logger.warning("No candidate skills at all, returning 30.0 penalty")
        return 30.0
    
    # Normalize must-have skills
    must_have_normalized = [s.strip() for s in must_have_skills if s and s.strip()]
    
    logger.info(f"Normalized must-have skills count: {len(must_have_normalized)}")
    
    if not must_have_normalized:
        logger.warning("Must-have skills normalized to empty, returning 0.0 penalty")
        return 0.0
    
    # Filter to only technical skills for mismatch checking
    from app.services.skill_categorizer import filter_technical_skills
    
    # Only check technical skills for technology mismatch
    must_have_technical = filter_technical_skills(must_have_normalized)
    
    if not must_have_technical:
        logger.info("No technical skills in must_have after filtering - skipping technology mismatch penalty")
        return 0.0
    
    logger.info(f"Checking technical skills only: {must_have_technical} (filtered from {len(must_have_normalized)} total)")
    
    # CRITICAL: Check if candidate has required technical skills FIRST
    # Only apply technology mismatch penalty if candidate is MISSING required technical skills
    candidate_has_required_skills, skill_match_details = has_required_skills(
        all_candidate_skills, must_have_technical, use_semantic_matching=True
    )
    
    # Always get mismatch result for use in semantic matching
    mismatch_result = detect_technology_mismatch(job_desc, candidate)
    
    # CRITICAL: Detect contradictions between has_required_skills() and mismatch detector
    if mismatch_result.get("mismatch_detected") and candidate_has_required_skills:
        logger.warning("⚠️ CONTRADICTION DETECTED: Technology mismatch detector says missing, but has_required_skills() says found")
        logger.warning(f"   Mismatch detector result: {mismatch_result}")
        logger.warning(f"   Skill match details: {skill_match_details}")
        logger.warning(f"   Required technologies from mismatch: {mismatch_result.get('required_technologies', [])}")
        logger.warning(f"   Found skills from has_required_skills: {skill_match_details.get('found_skills', [])}")
        
        # Use stricter validation: if has_required_skills says found, trust it (it uses same logic)
        # But log the contradiction for investigation
        logger.warning("   Resolving contradiction: Using has_required_skills() result (candidate has required skills)")
        mismatch_result["mismatch_detected"] = False
        mismatch_result["severity"] = None
    
    if candidate_has_required_skills:
        logger.info(f"✅ Candidate has all required technical skills: {must_have_technical}")
        logger.info(f"   Match details: {skill_match_details.get('found_skills', [])}")
        logger.info("   Skipping technology mismatch penalty - candidate has required technical skills")
        # If mismatch was detected but candidate has required skills, reduce severity
        if mismatch_result.get("mismatch_detected"):
            logger.info(f"   Technology mismatch detected but candidate has required skills - ignoring mismatch")
            # Override to prevent penalty
            mismatch_result["mismatch_detected"] = False
            mismatch_result["severity"] = None
    else:
        logger.warning(f"❌ Candidate is missing some required technical skills: {must_have_technical}")
        logger.warning(f"   Missing: {skill_match_details.get('missing_skills', [])}")
        logger.info(f"   Found: {skill_match_details.get('found_skills', [])}")
        # Check for technology mismatches if candidate is missing required skills
        if mismatch_result.get("mismatch_detected") and mismatch_result.get("severity") == "critical":
            logger.warning(f"🚨 CRITICAL TECHNOLOGY MISMATCH: {mismatch_result.get('mismatch_details', '')}")
            logger.warning(f"   Required: {mismatch_result.get('required_technologies', [])}")
            logger.warning(f"   Candidate has incompatible: {mismatch_result.get('incompatible_technologies', [])}")
            logger.warning(f"   Applying maximum penalty (30 pts)")
            return 30.0  # Maximum penalty for critical technology mismatch
    
    # Get incompatible technologies from mismatch result for use in semantic matching
    incompatible_techs = []
    if mismatch_result.get("mismatch_detected"):
        incompatible_techs = [tech.lower() for tech in mismatch_result.get("incompatible_technologies", [])]
        required_techs = [tech.lower() for tech in mismatch_result.get("required_technologies", [])]
    
    # Use semantic similarity to match skills
    matched_skills = 0
    similarity_threshold = 0.6  # Consider a match if similarity >= 0.6
    
    try:
        # Get embeddings for all candidate skills (batch for efficiency)
        candidate_skills_text = " ".join(all_candidate_skills)
        candidate_embedding = get_embeddings(candidate_skills_text)
        
        # Check each required technical skill (already filtered above)
        for required_skill in must_have_technical:
            skill_found = False
            
            # First try exact/substring match (fast check)
            required_lower = required_skill.lower()
            
            # CRITICAL: Exclude technology mismatches from matching using LLM-detected incompatibilities
            # If there's a mismatch detected, skip semantic matching for incompatible technologies
            if incompatible_techs and required_techs:
                # Check if this required skill is in the required technologies list
                required_tech_match = any(tech in required_lower for tech in required_techs)
                # Check if candidate has incompatible technologies
                candidate_has_incompatible = any(tech in " ".join([s.lower() for s in all_candidate_skills]) for tech in incompatible_techs)
                
                if required_tech_match and candidate_has_incompatible:
                    # Skip semantic matching for required technology if candidate has incompatible technology
                    logger.debug(f"Skipping semantic match for '{required_skill}' - technology mismatch detected")
                    continue
            
            for candidate_skill in all_candidate_skills:
                candidate_lower = candidate_skill.lower()
                # Exact match
                if required_lower == candidate_lower:
                    skill_found = True
                    break
                # Substring match (but exclude technology mismatches)
                if required_lower in candidate_lower or candidate_lower in required_lower:
                    # Check if this would be a technology mismatch
                    if incompatible_techs and required_techs:
                        required_tech_match = any(tech in required_lower for tech in required_techs)
                        candidate_has_incompatible = any(tech in candidate_lower for tech in incompatible_techs)
                        if required_tech_match and candidate_has_incompatible:
                            continue
                    skill_found = True
                    break
                # Handle compound skills like "Flutter & Dart"
                if '&' in required_skill or ' and ' in required_skill.lower():
                    parts = re.split(r'[&\s]+and\s+', required_skill, flags=re.IGNORECASE)
                    parts = [p.strip().lower() for p in parts if p.strip()]
                    for part in parts:
                        if part in candidate_lower or candidate_lower in part:
                            # Check if this would be a technology mismatch
                            if incompatible_techs and required_techs:
                                required_tech_match = any(tech in part for tech in required_techs)
                                candidate_has_incompatible = any(tech in candidate_lower for tech in incompatible_techs)
                                if required_tech_match and candidate_has_incompatible:
                                    continue
                            skill_found = True
                            break
                    if skill_found:
                        break
            
            # If not found by exact match, try semantic similarity
            # BUT: Skip semantic matching for technology mismatches to avoid false matches
            if not skill_found:
                required_lower = required_skill.lower()
                # Don't use semantic similarity for technology mismatches
                is_required_tech = incompatible_techs and required_techs and any(tech in required_lower for tech in required_techs)
                
                if is_required_tech:
                    # For required technologies with detected mismatches, only use exact matching (already done above)
                    # Don't use semantic similarity as it might incorrectly match incompatible technologies
                    logger.debug(f"Skipping semantic matching for framework skill '{required_skill}' to avoid false matches")
                else:
                    # For non-framework skills, use semantic similarity
                    try:
                        required_embedding = get_embeddings(required_skill)
                        similarity = cosine_similarity(required_embedding, candidate_embedding)
                        
                        # Also check individual candidate skills for better matching
                        max_similarity = similarity
                        for candidate_skill in all_candidate_skills[:10]:  # Limit to first 10 for performance
                            candidate_skill_embedding = get_embeddings(candidate_skill)
                            skill_similarity = cosine_similarity(required_embedding, candidate_skill_embedding)
                            max_similarity = max(max_similarity, skill_similarity)
                        
                        if max_similarity >= similarity_threshold:
                            skill_found = True
                            logger.debug(f"Semantic match found: '{required_skill}' ~ '{candidate_skills_text[:50]}' (similarity: {max_similarity:.2f})")
                    except Exception as e:
                        logger.warning(f"Error calculating semantic similarity for skill '{required_skill}': {str(e)}")
                        # Continue without semantic match
            
            if skill_found:
                matched_skills += 1
        
    except Exception as e:
        logger.error(f"Error in semantic skill matching: {str(e)}, falling back to exact matching")
        # Fallback to simple exact matching (use technical skills only)
        must_have_lower = [s.lower() for s in must_have_technical]
        candidate_skills_lower = [s.lower() for s in all_candidate_skills]
        matched_skills = sum(1 for req in must_have_lower 
                           if any(req in cand or cand in req for cand in candidate_skills_lower))
    
    # Calculate match ratio
    match_ratio = matched_skills / len(must_have_technical) if must_have_technical else 0.0
    
    # Apply penalty based on match ratio
    # 0% match = 20 pts penalty
    # 25% match = 15 pts penalty
    # 50% match = 10 pts penalty
    # 75% match = 5 pts penalty
    # 100% match = 0 pts penalty
    if match_ratio == 0.0:
        penalty = 20.0  # Complete mismatch
    elif match_ratio < 0.25:
        penalty = 15.0  # Very poor match
    elif match_ratio < 0.5:
        penalty = 10.0  # Poor match
    elif match_ratio < 0.75:
        penalty = 5.0   # Moderate match
    else:
        penalty = 0.0   # Good match
    
    # Log the match details for debugging
    logger.info(f"Skill mismatch calculation: matched {matched_skills}/{len(must_have_technical)} technical must-have skills, match_ratio={match_ratio:.2f}, base_penalty={penalty:.1f}")
    
    # Clamp to max 30 pts (framework mismatches already return 30.0 early, so this is for other cases)
    penalty = min(30.0, penalty)
    
    logger.info(f"Final skill mismatch penalty: {penalty:.1f} (matched {matched_skills}/{len(must_have_technical)} technical skills, ratio: {match_ratio:.2f})")
    
    return penalty

def calculate_technology_mismatch_penalty(merged_json: Dict) -> float:
    """
    Calculate penalty for technology/framework mismatches (0-15 pts penalty)
    
    Uses LLM-based dynamic detection to identify incompatible technology pairs
    without any hardcoded technology names.
    
    CRITICAL: Only applies penalty if candidate is MISSING required skills.
    If candidate has all required skills, no penalty is applied.
    """
    job_desc = merged_json.get("job_description", {})
    candidate = merged_json.get("candidate", {})
    
    # Check if candidate has required skills FIRST
    must_have_skills = job_desc.get("must_have", [])
    candidate_skills_raw = candidate.get("skills_raw", [])
    candidate_skills_canonical = candidate.get("skills_canonical", [])
    all_candidate_skills = list(set(candidate_skills_raw + candidate_skills_canonical))
    
    if must_have_skills:
        # Filter to only technical skills for mismatch checking
        from app.services.skill_categorizer import filter_technical_skills
        must_have_technical = filter_technical_skills(must_have_skills)
        
        if must_have_technical:
            # Use same has_required_skills() function to ensure consistency
            candidate_has_required_skills, skill_match_details = has_required_skills(
                all_candidate_skills, must_have_technical, use_semantic_matching=True
            )
            if candidate_has_required_skills:
                logger.info(f"✅ Candidate has all required technical skills - skipping technology mismatch penalty")
                logger.info(f"   Match details: {skill_match_details.get('found_skills', [])}")
                return 0.0
            else:
                logger.info(f"❌ Candidate missing some required technical skills - checking for technology mismatch")
                logger.info(f"   Missing: {skill_match_details.get('missing_skills', [])}")
        else:
            logger.info("No technical skills in must_have - skipping technology mismatch penalty")
            return 0.0
    
    # Use LLM-based dynamic technology mismatch detection
    mismatch_result = detect_technology_mismatch(job_desc, candidate)
    
    if not mismatch_result.get("mismatch_detected"):
        return 0.0
    
    severity = mismatch_result.get("severity", "moderate")
    mismatch_details = mismatch_result.get("mismatch_details", "")
    
    # Apply penalty based on severity
    if severity == "critical":
        penalty = 15.0
        logger.warning(f"🚨 CRITICAL technology mismatch: {mismatch_details}")
        logger.warning(f"   Required: {mismatch_result.get('required_technologies', [])}")
        logger.warning(f"   Candidate has incompatible: {mismatch_result.get('incompatible_technologies', [])}")
    elif severity == "moderate":
        penalty = 10.0
        logger.info(f"Moderate technology mismatch: {mismatch_details}")
    else:  # minor
        penalty = 5.0
        logger.info(f"Minor technology mismatch: {mismatch_details}")
    
    return penalty


def calculate_role_match_bonus(merged_json: Dict) -> float:
    """
    Calculate role match bonus based on predicted roles vs job title.
    
    This bonus rewards candidates whose predicted role matches or exceeds
    the job level (e.g., predicted as "Data Scientist" applying for "Data Science Intern").
    
    Args:
        merged_json: Merged JSON containing candidate and job description data
    
    Returns:
        Bonus points (-5 to +5)
    """
    try:
        # Get job title and role predictions
        jd_info = merged_json.get("job_description", {})
        job_title = jd_info.get("title", "")
        
        # Try to get role predictions from merged_json (may not be available yet)
        # Role predictions are typically added after aggregation, so this might return 0
        role_predictions = merged_json.get("role_predictions", [])
        
        if not job_title or not role_predictions:
            # Role predictions might not be available at aggregation time
            # This is expected - role match bonus will be 0
            return 0.0
        
        # Calculate role match using role_matcher utility
        from app.utils.role_matcher import calculate_role_match
        
        role_match = calculate_role_match(job_title, role_predictions)
        bonus = role_match.get("bonus", 0.0)
        
        # Clamp bonus to -5 to +5
        bonus = max(-5.0, min(5.0, bonus))
        
        if bonus != 0.0:
            match_type = role_match.get("match_type", "")
            similarity = role_match.get("similarity", 0.0)
            logger.info(f"Role match bonus: {bonus:.1f} (type: {match_type}, similarity: {similarity:.2f})")
        
        return bonus
        
    except Exception as e:
        logger.error(f"Error calculating role match bonus: {str(e)}")
        return 0.0

