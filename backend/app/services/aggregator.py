from typing import Dict, List
from datetime import datetime, timedelta
from app.services.technology_mismatch_detector import detect_technology_mismatch
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
    scores_list = judge_scores.get("judge_scores", [])
    if scores_list:
        avg_score = sum(score["score"] for score in scores_list) / len(scores_list)
        role_competency = (avg_score / 5.0) * 30  # Scale from 0-5 to 0-30
    else:
        role_competency = 0
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
    
    # Calculate total score
    total_score = semantic_fit + role_competency + experience_recency + github_evidence + bonus_malus - skill_mismatch_penalty - technology_mismatch_penalty
    
    # Clamp to 0-100
    total_score = max(0, min(100, round(total_score)))
    
    return {
        "total_score": total_score,
        "breakdown": {
            "semantic_fit": semantic_fit,
            "role_competency": role_competency,
            "experience_recency": experience_recency,
            "github_evidence": github_evidence,
            "bonus_malus": bonus_malus,
            "skill_mismatch_penalty": round(skill_mismatch_penalty, 1),
            "technology_mismatch_penalty": round(technology_mismatch_penalty, 1)
        }
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
    
    # CRITICAL: Check for technology mismatches FIRST, before semantic matching
    # Use LLM-based dynamic detection to identify incompatible technology pairs
    mismatch_result = detect_technology_mismatch(job_desc, candidate)
    
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
        
        # Check each required skill
        for required_skill in must_have_normalized:
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
        # Fallback to simple exact matching
        must_have_lower = [s.lower() for s in must_have_normalized]
        candidate_skills_lower = [s.lower() for s in all_candidate_skills]
        matched_skills = sum(1 for req in must_have_lower 
                           if any(req in cand or cand in req for cand in candidate_skills_lower))
    
    # Calculate match ratio
    match_ratio = matched_skills / len(must_have_normalized) if must_have_normalized else 0.0
    
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
    logger.info(f"Skill mismatch calculation: matched {matched_skills}/{len(must_have_normalized)} must-have skills, match_ratio={match_ratio:.2f}, base_penalty={penalty:.1f}")
    
    # Clamp to max 30 pts (framework mismatches already return 30.0 early, so this is for other cases)
    penalty = min(30.0, penalty)
    
    logger.info(f"Final skill mismatch penalty: {penalty:.1f} (matched {matched_skills}/{len(must_have_normalized)} skills, ratio: {match_ratio:.2f})")
    
    return penalty

def calculate_technology_mismatch_penalty(merged_json: Dict) -> float:
    """
    Calculate penalty for technology/framework mismatches (0-15 pts penalty)
    
    Uses LLM-based dynamic detection to identify incompatible technology pairs
    without any hardcoded technology names.
    """
    job_desc = merged_json.get("job_description", {})
    candidate = merged_json.get("candidate", {})
    
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

