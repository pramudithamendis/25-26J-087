from typing import Dict
import numpy as np
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize embedding providers
_openai_client = None
_sentence_model = None

def get_openai_client():
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    return _openai_client

def get_sentence_model():
    """Get or create sentence-transformers model"""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformers model...")
            _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence-transformers model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {str(e)}")
    return _sentence_model

def get_embeddings_openai(text: str) -> np.ndarray:
    """Get embeddings using OpenAI API"""
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, falling back to sentence-transformers")
        return get_embeddings_sentence_transformers(text)
    
    try:
        client = get_openai_client()
        if not client:
            return get_embeddings_sentence_transformers(text)
        
        response = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text[:8000]  # Limit text length for API
        )
        embedding = np.array(response.data[0].embedding)
        logger.debug(f"Generated OpenAI embedding of dimension {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"OpenAI embedding error: {str(e)}, falling back to sentence-transformers")
        return get_embeddings_sentence_transformers(text)

def get_embeddings_sentence_transformers(text: str) -> np.ndarray:
    """Get embeddings using sentence-transformers (free, local)"""
    try:
        model = get_sentence_model()
        if not model:
            logger.error("Sentence-transformers model not available")
            return np.zeros(384)  # all-MiniLM-L6-v2 dimension
        
        embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        logger.debug(f"Generated sentence-transformers embedding of dimension {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Sentence-transformers error: {str(e)}")
        return np.zeros(384)  # all-MiniLM-L6-v2 dimension

def get_embeddings(text: str) -> np.ndarray:
    """Get embeddings based on configured provider"""
    if settings.EMBEDDING_PROVIDER == "openai":
        return get_embeddings_openai(text)
    else:
        return get_embeddings_sentence_transformers(text)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors"""
    try:
        # Handle zero vectors
        if np.all(a == 0) or np.all(b == 0):
            return 0.0
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        similarity = float(dot_product / (norm_a * norm_b))
        return similarity
    except Exception as e:
        logger.error(f"Cosine similarity error: {str(e)}")
        return 0.0

def build_semantic_features(candidate_block: str, jd_block: str, github_summary: str = "") -> Dict:
    """
    Build semantic similarity features using real embeddings
    
    Uses OpenAI embeddings by default, falls back to sentence-transformers if OpenAI is not configured.
    
    Args:
        candidate_block: Combined text from CV + LinkedIn
        jd_block: Job description text
        github_summary: Summary of GitHub activity (optional)
    
    Returns:
        Dictionary with similarity scores
    """
    try:
        # Validate inputs
        if not candidate_block or not candidate_block.strip():
            logger.warning("Candidate block is empty, cannot compute semantic similarity")
            return {
                "sim_profile_to_jd": 0.0,
                "sim_github_to_jd": 0.0
            }
        
        if not jd_block or not jd_block.strip():
            logger.warning("Job description block is empty, cannot compute semantic similarity")
            return {
                "sim_profile_to_jd": 0.0,
                "sim_github_to_jd": 0.0
            }
        
        # Truncate text if too long (for API limits)
        max_length = 8000
        candidate_block = candidate_block[:max_length] if len(candidate_block) > max_length else candidate_block
        jd_block = jd_block[:max_length] if len(jd_block) > max_length else jd_block
        
        logger.info(f"Computing semantic similarity: candidate_block length={len(candidate_block)}, jd_block length={len(jd_block)}")
        
        # Generate embeddings
        logger.info("Generating embeddings for candidate profile and job description...")
        candidate_embedding = get_embeddings(candidate_block)
        jd_embedding = get_embeddings(jd_block)
        
        # Check if embeddings are zero vectors
        if np.all(candidate_embedding == 0):
            logger.warning("Candidate embedding is zero vector")
        if np.all(jd_embedding == 0):
            logger.warning("JD embedding is zero vector")
        
        # Compute cosine similarity
        sim_profile_to_jd = cosine_similarity(candidate_embedding, jd_embedding)
        
        # GitHub similarity (if provided)
        sim_github_to_jd = 0.0
        if github_summary and github_summary.strip():
            github_summary = github_summary[:max_length] if len(github_summary) > max_length else github_summary
            github_embedding = get_embeddings(github_summary)
            sim_github_to_jd = cosine_similarity(github_embedding, jd_embedding)
        
        # Clamp to [0, 1]
        sim_profile_to_jd = max(0.0, min(1.0, sim_profile_to_jd))
        sim_github_to_jd = max(0.0, min(1.0, sim_github_to_jd))
        
        logger.info(f"Semantic similarities computed: profile_to_jd={sim_profile_to_jd:.3f}, github_to_jd={sim_github_to_jd:.3f}")
        
        return {
            "sim_profile_to_jd": round(sim_profile_to_jd, 3),
            "sim_github_to_jd": round(sim_github_to_jd, 3)
        }
    
    except Exception as e:
        logger.error(f"Error building semantic features: {str(e)}", exc_info=True)
        # Return zero instead of placeholder to avoid false positives
        return {
            "sim_profile_to_jd": 0.0,
            "sim_github_to_jd": 0.0
        }

