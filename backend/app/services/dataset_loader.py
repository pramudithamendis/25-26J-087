"""
Dataset loader for ground truth evaluation dataset.

Loads and manages the 592-pair ground truth dataset for validation and calibration.
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import pickle
import hashlib
from app.config import settings
from app.services.semantic import get_embeddings, cosine_similarity

logger = logging.getLogger(__name__)

# Global dataset cache
_dataset_cache: Optional[pd.DataFrame] = None
_candidates_cache: Optional[pd.DataFrame] = None
_jobs_cache: Optional[pd.DataFrame] = None
_dataset_embeddings_cache: Optional[Dict[str, np.ndarray]] = None


def load_dataset(dataset_path: str = None) -> pd.DataFrame:
    """
    Load evaluations dataset from CSV.
    
    Args:
        dataset_path: Path to dataset directory (defaults to settings.DATASET_PATH)
    
    Returns:
        DataFrame with evaluation pairs
    """
    global _dataset_cache
    
    if _dataset_cache is not None:
        return _dataset_cache
    
    try:
        dataset_path_str = dataset_path or settings.DATASET_PATH
        # Handle both relative and absolute paths
        if Path(dataset_path_str).is_absolute():
            dataset_dir = Path(dataset_path_str)
        else:
            # Relative to project root (go up from backend/app/services)
            project_root = Path(__file__).parent.parent.parent.parent
            dataset_dir = project_root / dataset_path_str
        
        evaluations_file = dataset_dir / "evaluations.csv"
        
        logger.info(f"Looking for dataset at: {evaluations_file}")
        logger.info(f"Dataset directory exists: {dataset_dir.exists()}")
        
        if not evaluations_file.exists():
            logger.warning(f"Dataset file not found: {evaluations_file}")
            logger.warning(f"Current working directory: {Path.cwd()}")
            logger.warning(f"Project root calculated as: {Path(__file__).parent.parent.parent.parent}")
            return pd.DataFrame()
        
        df = pd.read_csv(evaluations_file)
        logger.info(f"Loaded dataset with {len(df)} evaluation pairs")
        _dataset_cache = df
        return df
    except Exception as e:
        logger.error(f"Failed to load dataset: {str(e)}")
        return pd.DataFrame()


def load_candidates(dataset_path: str = None) -> pd.DataFrame:
    """
    Load candidates dataset from CSV.
    
    Args:
        dataset_path: Path to dataset directory
    
    Returns:
        DataFrame with candidate profiles
    """
    global _candidates_cache
    
    if _candidates_cache is not None:
        return _candidates_cache
    
    try:
        dataset_path_str = dataset_path or settings.DATASET_PATH
        # Handle both relative and absolute paths
        if Path(dataset_path_str).is_absolute():
            dataset_dir = Path(dataset_path_str)
        else:
            # Relative to project root (go up from backend/app/services)
            project_root = Path(__file__).parent.parent.parent.parent
            dataset_dir = project_root / dataset_path_str
        
        candidates_file = dataset_dir / "candidates.csv"
        
        if not candidates_file.exists():
            logger.warning(f"Candidates file not found: {candidates_file}")
            return pd.DataFrame()
        
        df = pd.read_csv(candidates_file)
        logger.info(f"Loaded {len(df)} candidates")
        _candidates_cache = df
        return df
    except Exception as e:
        logger.error(f"Failed to load candidates: {str(e)}")
        return pd.DataFrame()


def load_jobs(dataset_path: str = None) -> pd.DataFrame:
    """
    Load jobs dataset from CSV.
    
    Args:
        dataset_path: Path to dataset directory
    
    Returns:
        DataFrame with job descriptions
    """
    global _jobs_cache
    
    if _jobs_cache is not None:
        return _jobs_cache
    
    try:
        dataset_path_str = dataset_path or settings.DATASET_PATH
        # Handle both relative and absolute paths
        if Path(dataset_path_str).is_absolute():
            dataset_dir = Path(dataset_path_str)
        else:
            # Relative to project root (go up from backend/app/services)
            project_root = Path(__file__).parent.parent.parent.parent
            dataset_dir = project_root / dataset_path_str
        
        jobs_file = dataset_dir / "jobs.csv"
        
        if not jobs_file.exists():
            logger.warning(f"Jobs file not found: {jobs_file}")
            return pd.DataFrame()
        
        df = pd.read_csv(jobs_file)
        logger.info(f"Loaded {len(df)} jobs")
        _jobs_cache = df
        return df
    except Exception as e:
        logger.error(f"Failed to load jobs: {str(e)}")
        return pd.DataFrame()


def get_dataset_statistics(dataset_path: str = None) -> Dict:
    """
    Get dataset statistics including score distributions and decision patterns.
    
    Args:
        dataset_path: Path to dataset directory
    
    Returns:
        Dictionary with statistics
    """
    try:
        df = load_dataset(dataset_path)
        
        if df.empty:
            return {}
        
        # Score statistics
        scores = df['total_score'].values if 'total_score' in df.columns else []
        score_stats = {
            "min": int(scores.min()) if len(scores) > 0 else 0,
            "max": int(scores.max()) if len(scores) > 0 else 100,
            "mean": float(scores.mean()) if len(scores) > 0 else 0.0,
            "median": float(np.median(scores)) if len(scores) > 0 else 0.0
        }
        
        # Decision distribution
        decision_dist = {}
        if 'decision' in df.columns:
            decision_counts = df['decision'].value_counts().to_dict()
            decision_dist = {str(k): int(v) for k, v in decision_counts.items()}
        
        return {
            "total_pairs": len(df),
            "score_statistics": score_stats,
            "decision_distribution": decision_dist
        }
    except Exception as e:
        logger.error(f"Failed to get dataset statistics: {str(e)}")
        return {}


def _build_profile_text(candidate_row: pd.Series, job_row: pd.Series) -> str:
    """
    Build a text representation of candidate-job pair for embedding.
    
    Args:
        candidate_row: Candidate row from DataFrame
        job_row: Job row from DataFrame
    
    Returns:
        Combined text representation
    """
    parts = []
    
    # Candidate info
    if 'name' in candidate_row and pd.notna(candidate_row['name']):
        parts.append(f"Candidate: {candidate_row['name']}")
    if 'skills' in candidate_row and pd.notna(candidate_row['skills']):
        parts.append(f"Skills: {candidate_row['skills']}")
    if 'num_experience' in candidate_row and pd.notna(candidate_row['num_experience']):
        parts.append(f"Experience: {candidate_row['num_experience']} years")
    
    # Job info
    if 'title' in job_row and pd.notna(job_row['title']):
        parts.append(f"Job: {job_row['title']}")
    if 'must_have_skills' in job_row and pd.notna(job_row['must_have_skills']):
        parts.append(f"Required Skills: {job_row['must_have_skills']}")
    if 'min_years' in job_row and pd.notna(job_row['min_years']):
        parts.append(f"Min Experience: {job_row['min_years']} years")
    
    return " ".join(parts)


def _get_embeddings_cache_path(dataset_path: str = None) -> Path:
    """
    Get the path to the embeddings cache file.
    
    Args:
        dataset_path: Path to dataset directory
    
    Returns:
        Path to cache file
    """
    dataset_path_str = dataset_path or settings.DATASET_PATH
    if Path(dataset_path_str).is_absolute():
        dataset_dir = Path(dataset_path_str)
    else:
        project_root = Path(__file__).parent.parent.parent.parent
        dataset_dir = project_root / dataset_path_str
    
    # Create cache directory if it doesn't exist
    cache_dir = dataset_dir / ".cache"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create cache directory {cache_dir}: {str(e)}")
        raise
    
    cache_file_path = cache_dir / "dataset_embeddings.pkl"
    logger.debug(f"Cache directory: {cache_dir}")
    logger.debug(f"Cache file path: {cache_file_path}")
    
    return cache_file_path


def _precompute_dataset_embeddings(dataset_path: str = None) -> Dict[str, np.ndarray]:
    """
    Pre-compute embeddings for all candidate-job pairs in the dataset.
    This is done once and cached to disk for performance.
    
    Args:
        dataset_path: Path to dataset directory
    
    Returns:
        Dictionary mapping cache keys to embeddings
    """
    global _dataset_embeddings_cache
    
    if _dataset_embeddings_cache is not None:
        logger.info(f"Using in-memory cache with {len(_dataset_embeddings_cache)} embeddings")
        return _dataset_embeddings_cache
    
    # Try to load from disk cache first
    cache_path = _get_embeddings_cache_path(dataset_path)
    logger.info(f"Checking for embeddings cache at: {cache_path}")
    logger.info(f"Cache file exists: {cache_path.exists()}")
    logger.info(f"Cache directory exists: {cache_path.parent.exists()}")
    
    if cache_path.exists():
        try:
            logger.info(f"Loading embeddings from cache: {cache_path}")
            with open(cache_path, 'rb') as f:
                _dataset_embeddings_cache = pickle.load(f)
            
            # Validate loaded cache data
            if not isinstance(_dataset_embeddings_cache, dict):
                logger.error(f"Cache file contains invalid data type: {type(_dataset_embeddings_cache)}")
                _dataset_embeddings_cache = None
            elif len(_dataset_embeddings_cache) == 0:
                logger.warning("Cache file exists but is empty, will recompute")
                _dataset_embeddings_cache = None
            else:
                # Validate embeddings are numpy arrays
                sample_key = next(iter(_dataset_embeddings_cache.keys()))
                if not isinstance(_dataset_embeddings_cache[sample_key], np.ndarray):
                    logger.error("Cache contains invalid embedding format")
                    _dataset_embeddings_cache = None
                else:
                    logger.info(f"Successfully loaded {len(_dataset_embeddings_cache)} embeddings from cache")
                    return _dataset_embeddings_cache
        except Exception as e:
            logger.error(f"Failed to load embeddings cache: {str(e)}, will recompute", exc_info=True)
            _dataset_embeddings_cache = None
    
    logger.info("Pre-computing embeddings for all dataset pairs (this may take a minute on first call)...")
    evaluations_df = load_dataset(dataset_path)
    candidates_df = load_candidates(dataset_path)
    jobs_df = load_jobs(dataset_path)
    
    if evaluations_df.empty or candidates_df.empty or jobs_df.empty:
        logger.warning("Dataset files are empty, cannot pre-compute embeddings")
        return {}
    
    embeddings_dict = {}
    total_pairs = len(evaluations_df)
    
    for idx, eval_row in evaluations_df.iterrows():
        try:
            candidate_name = eval_row.get('candidate_name', '')
            job_title = eval_row.get('job_title', '')
            
            # Create cache key
            cache_key = f"{candidate_name}|||{job_title}"
            
            # Find matching rows
            candidate_matches = candidates_df[candidates_df['name'] == candidate_name] if 'name' in candidates_df.columns else pd.DataFrame()
            job_matches = jobs_df[jobs_df['title'] == job_title] if 'title' in jobs_df.columns else pd.DataFrame()
            
            if candidate_matches.empty or job_matches.empty:
                continue
            
            candidate_row = candidate_matches.iloc[0]
            job_row = job_matches.iloc[0]
            
            # Build profile text
            profile_text = _build_profile_text(candidate_row, job_row)
            
            # Get embedding
            embedding = get_embeddings(profile_text)
            embeddings_dict[cache_key] = embedding
            
            # Log progress every 50 pairs
            if (idx + 1) % 50 == 0:
                logger.info(f"Pre-computed embeddings: {idx + 1}/{total_pairs} pairs")
            
        except Exception as e:
            logger.debug(f"Error pre-computing embedding for row {idx}: {str(e)}")
            continue
    
    # Save to disk cache
    try:
        logger.info(f"Saving {len(embeddings_dict)} embeddings to cache: {cache_path}")
        # Ensure parent directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file first, then rename
        temp_path = cache_path.with_suffix('.tmp')
        with open(temp_path, 'wb') as f:
            pickle.dump(embeddings_dict, f)
        
        # Atomic rename
        temp_path.replace(cache_path)
        
        # Verify file was saved
        if cache_path.exists():
            file_size = cache_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"Embeddings cache saved successfully ({file_size:.2f} MB)")
        else:
            logger.error("Cache file was not created after save")
    except Exception as e:
        logger.error(f"Failed to save embeddings cache: {str(e)}", exc_info=True)
        # Clean up temp file if it exists
        temp_path = cache_path.with_suffix('.tmp')
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
    
    _dataset_embeddings_cache = embeddings_dict
    logger.info(f"Pre-computed {len(embeddings_dict)} embeddings for dataset pairs (cached for future use)")
    return embeddings_dict


def find_similar_pairs(
    candidate_profile: Dict,
    job_desc: Dict,
    top_k: int = 5,
    dataset_path: str = None
) -> List[Dict]:
    """
    Find similar candidate-job pairs from dataset using embeddings.
    
    Args:
        candidate_profile: Candidate profile dictionary
        job_desc: Job description dictionary
        top_k: Number of similar pairs to return
        dataset_path: Path to dataset directory
    
    Returns:
        List of similar pairs with similarity scores and ground truth labels
    """
    try:
        evaluations_df = load_dataset(dataset_path)
        candidates_df = load_candidates(dataset_path)
        jobs_df = load_jobs(dataset_path)
        
        if evaluations_df.empty or candidates_df.empty or jobs_df.empty:
            logger.warning("Dataset files are empty, cannot find similar pairs")
            return []
        
        # Build query text
        query_parts = []
        
        # Candidate info - try multiple name fields
        candidate_name = (
            candidate_profile.get('name') or 
            candidate_profile.get('candidate_name') or
            candidate_profile.get('cv_data', {}).get('name', '')
        )
        if candidate_name:
            query_parts.append(f"Candidate: {candidate_name}")
        
        if 'skills_raw' in candidate_profile:
            skills = candidate_profile['skills_raw']
            if isinstance(skills, list):
                query_parts.append(f"Skills: {', '.join(skills[:20])}")  # Limit to first 20 skills
        elif 'skills_canonical' in candidate_profile:
            skills = candidate_profile['skills_canonical']
            if isinstance(skills, list):
                query_parts.append(f"Skills: {', '.join(skills[:20])}")
        
        if 'experience' in candidate_profile:
            exp = candidate_profile['experience']
            if isinstance(exp, list) and len(exp) > 0:
                query_parts.append(f"Experience: {len(exp)} positions")
                # Add experience details
                for e in exp[:2]:  # First 2 experiences
                    if isinstance(e, dict):
                        title = e.get('title', '')
                        if title:
                            query_parts.append(f"{title}")
        
        # Job info
        if 'title' in job_desc:
            query_parts.append(f"Job: {job_desc['title']}")
        if 'must_have' in job_desc:
            must_have = job_desc['must_have']
            if isinstance(must_have, list):
                query_parts.append(f"Required Skills: {', '.join(must_have[:15])}")  # Limit skills
        if 'min_years' in job_desc:
            query_parts.append(f"Min Experience: {job_desc['min_years']} years")
        
        query_text = " ".join(query_parts)
        
        # Get query embedding (ONCE per evaluation)
        query_embedding = get_embeddings(query_text)
        
        # Pre-compute dataset embeddings (cached after first call)
        # Check if cache exists before calling to avoid expensive computation
        cache_path = _get_embeddings_cache_path(dataset_path)
        if not cache_path.exists():
            logger.warning(
                f"Dataset embeddings cache not found at {cache_path}. "
                "Skipping dataset validation. Please pre-compute embeddings first."
            )
            return []
        
        dataset_embeddings = _precompute_dataset_embeddings(dataset_path)
        
        if not dataset_embeddings:
            logger.warning("No dataset embeddings available, cannot find similar pairs")
            return []
        
        # Calculate similarities using cached embeddings
        similarities = []
        
        for idx, eval_row in evaluations_df.iterrows():
            try:
                # Get candidate and job info
                candidate_name = eval_row.get('candidate_name', '')
                job_title = eval_row.get('job_title', '')
                
                # Create cache key
                cache_key = f"{candidate_name}|||{job_title}"
                
                # Get cached embedding (skip if not found)
                if cache_key not in dataset_embeddings:
                    continue
                
                profile_embedding = dataset_embeddings[cache_key]
                
                # Calculate similarity
                similarity = cosine_similarity(query_embedding, profile_embedding)
                
                # Get ground truth
                ground_truth_score = eval_row.get('total_score', 0)
                ground_truth_decision = eval_row.get('decision', 'Review')
                
                similarities.append({
                    "candidate_name": candidate_name,
                    "job_title": job_title,
                    "ground_truth_score": int(ground_truth_score) if pd.notna(ground_truth_score) else 0,
                    "ground_truth_decision": str(ground_truth_decision),
                    "similarity": float(similarity),
                    "skill_match": eval_row.get('skill_match', 0),
                    "experience_match": eval_row.get('experience_match', 0),
                    "overall_fit": eval_row.get('overall_fit', 0),
                    "reasoning": eval_row.get('reasoning', '')
                })
            except Exception as e:
                logger.debug(f"Error processing row {idx}: {str(e)}")
                continue
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Filter by similarity threshold
        threshold = settings.DATASET_SIMILARITY_THRESHOLD
        filtered = [s for s in similarities if s['similarity'] >= threshold]
        
        return filtered[:top_k]
        
    except Exception as e:
        logger.error(f"Failed to find similar pairs: {str(e)}")
        return []


def clear_cache(clear_disk_cache: bool = False):
    """
    Clear dataset cache (useful for testing or reloading)
    
    Args:
        clear_disk_cache: If True, also delete the disk cache file
    """
    global _dataset_cache, _candidates_cache, _jobs_cache, _dataset_embeddings_cache
    _dataset_cache = None
    _candidates_cache = None
    _jobs_cache = None
    _dataset_embeddings_cache = None
    
    if clear_disk_cache:
        cache_path = _get_embeddings_cache_path()
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.info(f"Deleted disk cache: {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to delete disk cache: {str(e)}")
    
    logger.info("Dataset cache cleared")

