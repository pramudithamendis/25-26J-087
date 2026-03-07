"""
Verify dataset embeddings cache integrity and performance.

This script checks if the cache file exists, can be loaded, and contains
the expected number of embeddings. It also tests cache loading performance.

Usage:
    python -m scripts.verify_cache
"""

import sys
import time
import logging
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.dataset_loader import (
    load_dataset,
    _get_embeddings_cache_path,
    _precompute_dataset_embeddings
)
from app.config import settings
import pickle
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def verify_cache(dataset_path: str = None):
    """
    Verify cache file integrity and performance.
    
    Args:
        dataset_path: Path to dataset directory (defaults to settings.DATASET_PATH)
    
    Returns:
        Dictionary with verification results
    """
    results = {
        "cache_exists": False,
        "cache_readable": False,
        "cache_valid": False,
        "embedding_count": 0,
        "expected_count": 0,
        "file_size_mb": 0.0,
        "load_time_seconds": 0.0,
        "errors": []
    }
    
    logger.info("=" * 60)
    logger.info("Verifying dataset embeddings cache")
    logger.info("=" * 60)
    
    # Get cache path
    cache_path = _get_embeddings_cache_path(dataset_path)
    logger.info(f"Cache file path: {cache_path}")
    
    # Check if cache exists
    results["cache_exists"] = cache_path.exists()
    if not results["cache_exists"]:
        logger.error("Cache file does not exist")
        results["errors"].append("Cache file not found")
        return results
    
    logger.info("✓ Cache file exists")
    
    # Get file size
    try:
        file_size_bytes = cache_path.stat().st_size
        results["file_size_mb"] = file_size_bytes / (1024 * 1024)
        logger.info(f"Cache file size: {results['file_size_mb']:.2f} MB")
    except Exception as e:
        logger.error(f"Failed to get file size: {str(e)}")
        results["errors"].append(f"Failed to get file size: {str(e)}")
    
    # Get expected count from dataset
    try:
        evaluations_df = load_dataset(dataset_path)
        results["expected_count"] = len(evaluations_df)
        logger.info(f"Expected embeddings: {results['expected_count']}")
    except Exception as e:
        logger.warning(f"Failed to load dataset to get expected count: {str(e)}")
    
    # Test cache loading
    logger.info("Testing cache loading...")
    start_time = time.time()
    
    try:
        with open(cache_path, 'rb') as f:
            cached_data = pickle.load(f)
        
        results["load_time_seconds"] = time.time() - start_time
        logger.info(f"✓ Cache file is readable (loaded in {results['load_time_seconds']:.3f} seconds)")
        results["cache_readable"] = True
        
        # Validate data structure
        if not isinstance(cached_data, dict):
            logger.error(f"Cache contains invalid data type: {type(cached_data)}")
            results["errors"].append(f"Invalid data type: {type(cached_data)}")
            return results
        
        results["embedding_count"] = len(cached_data)
        logger.info(f"✓ Cache contains {results['embedding_count']} embeddings")
        
        # Validate embeddings format
        if results["embedding_count"] > 0:
            sample_key = next(iter(cached_data.keys()))
            sample_embedding = cached_data[sample_key]
            
            if not isinstance(sample_embedding, np.ndarray):
                logger.error(f"Cache contains invalid embedding format: {type(sample_embedding)}")
                results["errors"].append(f"Invalid embedding format: {type(sample_embedding)}")
                return results
            
            embedding_dim = len(sample_embedding)
            logger.info(f"✓ Embedding dimension: {embedding_dim}")
            
            # Check a few more embeddings
            validation_count = min(10, results["embedding_count"])
            valid_count = 0
            for i, (key, embedding) in enumerate(cached_data.items()):
                if i >= validation_count:
                    break
                if isinstance(embedding, np.ndarray) and len(embedding) == embedding_dim:
                    valid_count += 1
            
            if valid_count == validation_count:
                logger.info(f"✓ Validated {valid_count} sample embeddings")
                results["cache_valid"] = True
            else:
                logger.warning(f"Only {valid_count}/{validation_count} sample embeddings are valid")
                results["errors"].append(f"Validation failed: {valid_count}/{validation_count} valid")
        else:
            logger.warning("Cache is empty")
            results["errors"].append("Cache is empty")
    
    except Exception as e:
        logger.error(f"Failed to load cache: {str(e)}", exc_info=True)
        results["errors"].append(f"Failed to load cache: {str(e)}")
        return results
    
    # Test using the actual function
    logger.info("Testing cache loading via _precompute_dataset_embeddings()...")
    start_time = time.time()
    try:
        embeddings = _precompute_dataset_embeddings(dataset_path)
        load_time = time.time() - start_time
        logger.info(f"✓ Function loaded {len(embeddings)} embeddings in {load_time:.3f} seconds")
        
        if len(embeddings) != results["embedding_count"]:
            logger.warning(f"Mismatch: direct load={results['embedding_count']}, function={len(embeddings)}")
    except Exception as e:
        logger.error(f"Failed to load via function: {str(e)}")
        results["errors"].append(f"Function load failed: {str(e)}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Verification Summary:")
    logger.info(f"  Cache exists: {results['cache_exists']}")
    logger.info(f"  Cache readable: {results['cache_readable']}")
    logger.info(f"  Cache valid: {results['cache_valid']}")
    logger.info(f"  Embedding count: {results['embedding_count']}")
    logger.info(f"  Expected count: {results['expected_count']}")
    logger.info(f"  File size: {results['file_size_mb']:.2f} MB")
    logger.info(f"  Load time: {results['load_time_seconds']:.3f} seconds")
    
    if results["errors"]:
        logger.warning(f"  Errors: {len(results['errors'])}")
        for error in results["errors"]:
            logger.warning(f"    - {error}")
    else:
        logger.info("  ✓ No errors found")
    
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    try:
        results = verify_cache()
        
        if results["cache_valid"] and len(results["errors"]) == 0:
            logger.info("Cache verification PASSED")
            sys.exit(0)
        else:
            logger.error("Cache verification FAILED")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)
