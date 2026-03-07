"""
Redis Queue Service for background job processing
"""
import logging
from typing import Optional

import redis
from rq import Queue
from rq.job import Retry

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_conn = None
evaluation_queue = None


def get_redis_connection():
    """Get or create Redis connection"""
    global redis_conn
    if redis_conn is None:
        try:
            redis_conn = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=False  # RQ needs bytes
            )
            # Test connection
            redis_conn.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    return redis_conn


def get_evaluation_queue():
    """Get or create evaluation queue"""
    global evaluation_queue
    if evaluation_queue is None:
        conn = get_redis_connection()
        evaluation_queue = Queue(settings.EVALUATION_QUEUE_NAME, connection=conn)
        logger.info(f"Initialized evaluation queue: {settings.EVALUATION_QUEUE_NAME}")
    return evaluation_queue


def enqueue_evaluation_task(user_id: str, job_id: str, application_id: str) -> Optional[str]:
    """
    Enqueue an evaluation task
    
    Args:
        user_id: User MongoDB ID
        job_id: Job MongoDB ID
        application_id: Application MongoDB ID
    
    Returns:
        RQ job ID if successful, None otherwise
    """
    try:
        queue = get_evaluation_queue()
        from app.services.tasks.evaluation_task import process_evaluation
        
        # RQ expects retry to be a Retry instance (max + interval in seconds), not an int
        retry = Retry(max=3, interval=[60, 120, 300])  # 1m, 2m, 5m between retries (worker needs --with-scheduler for intervals)
        job = queue.enqueue(
            process_evaluation,
            user_id,
            job_id,
            application_id,
            job_timeout='10m',
            result_ttl=86400,
            failure_ttl=86400,
            retry=retry,
        )
        logger.info(f"Enqueued evaluation task: job_id={job.id}, application_id={application_id}")
        return job.id
    except Exception as e:
        logger.error(f"Failed to enqueue evaluation task: {str(e)}")
        return None


def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get RQ job status
    
    Args:
        job_id: RQ job ID
    
    Returns:
        Dictionary with job status information or None if not found
    """
    try:
        from rq.job import Job
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)
        
        return {
            "id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": str(job.result) if job.result else None,
            "exc_info": job.exc_info if hasattr(job, 'exc_info') else None
        }
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        return None


def get_job_result(job_id: str) -> Optional[dict]:
    """
    Get RQ job result
    
    Args:
        job_id: RQ job ID
    
    Returns:
        Job result dictionary or None if not found/failed
    """
    try:
        from rq.job import Job
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)
        
        if job.is_finished:
            return {
                "success": job.is_finished and not job.is_failed,
                "result": job.result,
                "error": job.exc_info if job.is_failed else None
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get job result: {str(e)}")
        return None

