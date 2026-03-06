"""
Pre-compute embeddings for all dataset pairs.

This script pre-computes embeddings for all candidate-job pairs in the dataset
and saves them to cache. This should be run once before using dataset validation
to avoid expensive computation on first request.

Usage:
    python -m scripts.precompute_embeddings
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import pickle

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.dataset_loader import (
    load_dataset,
    load_candidates,
    load_jobs,
    _build_profile_text,
    _get_embeddings_cache_path,
    _precompute_dataset_embeddings
)
from app.services.semantic import get_embeddings
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def precompute_embeddings(dataset_path: str = None):
    """
    Pre-compute embeddings for all dataset pairs.
    
    Args:
        dataset_path: Path to dataset directory (defaults to settings.DATASET_PATH)
    """
    logger.info("=" * 60)
    logger.info("Starting embeddings pre-computation")
    logger.info("=" * 60)
    
    # Load datasets
    logger.info("Loading dataset files...")
    evaluations_df = load_dataset(dataset_path)
    candidates_df = load_candidates(dataset_path)
    jobs_df = load_jobs(dataset_path)
    
    if evaluations_df.empty or candidates_df.empty or jobs_df.empty:
        logger.error("Dataset files are empty, cannot pre-compute embeddings")
        return False
    
    logger.info(f"Loaded {len(evaluations_df)} evaluation pairs")
    logger.info(f"Loaded {len(candidates_df)} candidates")
    logger.info(f"Loaded {len(jobs_df)} jobs")
    
    # Check if cache already exists
    cache_path = _get_embeddings_cache_path(dataset_path)
    if cache_path.exists():
        logger.warning(f"Cache file already exists at {cache_path}")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            logger.info("Aborting pre-computation")
            return False
    
    # Compute embeddings
    logger.info("Computing embeddings for all pairs (this may take several minutes)...")
    embeddings_dict = {}
    total_pairs = len(evaluations_df)
    successful = 0
    failed = 0
    
    for idx, eval_row in evaluations_df.iterrows():
        try:
            candidate_name = eval_row.get('candidate_name', '')
            job_title = eval_row.get('job_title', '')
            
            # Create cache key
            cache_key = f"{candidate_name}|||{job_title}"
            
            # Skip if already computed
            if cache_key in embeddings_dict:
                continue
            
            # Find matching rows
            candidate_matches = candidates_df[candidates_df['name'] == candidate_name] if 'name' in candidates_df.columns else pd.DataFrame()
            job_matches = jobs_df[jobs_df['title'] == job_title] if 'title' in jobs_df.columns else pd.DataFrame()
            
            if candidate_matches.empty or job_matches.empty:
                logger.debug(f"Skipping pair {idx}: candidate or job not found")
                failed += 1
                continue
            
            candidate_row = candidate_matches.iloc[0]
            job_row = job_matches.iloc[0]
            
            # Build profile text
            profile_text = _build_profile_text(candidate_row, job_row)
            
            # Get embedding
            embedding = get_embeddings(profile_text)
            embeddings_dict[cache_key] = embedding
            successful += 1
            
            # Log progress every 50 pairs
            if (idx + 1) % 50 == 0:
                logger.info(f"Progress: {idx + 1}/{total_pairs} pairs ({successful} successful, {failed} failed)")
        
        except Exception as e:
            logger.error(f"Error pre-computing embedding for row {idx}: {str(e)}")
            failed += 1
            continue
    
    logger.info(f"Computed {successful} embeddings successfully, {failed} failed")
    
    # Save to cache
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
            logger.info(f"Cache location: {cache_path}")
            return True
        else:
            logger.error("Cache file was not created after save")
            return False
    except Exception as e:
        logger.error(f"Failed to save embeddings cache: {str(e)}", exc_info=True)
        # Clean up temp file if it exists
        temp_path = cache_path.with_suffix('.tmp')
        if temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass
        return False


if __name__ == "__main__":
    try:
        success = precompute_embeddings()
        if success:
            logger.info("=" * 60)
            logger.info("Pre-computation completed successfully!")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.error("Pre-computation failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\nPre-computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)
