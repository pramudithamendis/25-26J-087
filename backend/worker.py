"""
RQ Worker Script for processing background evaluation tasks

Run this script to start the Redis Queue worker that processes evaluation jobs.

Usage:
    python worker.py

This worker uses a custom polling loop that continuously processes jobs without exiting.
It handles errors gracefully and automatically recovers from transient failures.
"""
import sys
import os
import time
import signal
import traceback
from typing import Optional

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rq import Queue
from rq.job import Job
from app.services.queue_service import get_redis_connection, get_evaluation_queue
from app.services.tasks.evaluation_task import process_evaluation
from app.config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    if sys.platform != 'win32':
        # Unix/Linux signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    else:
        # Windows only supports SIGINT
        signal.signal(signal.SIGINT, signal_handler)


def reconnect_redis(max_retries: int = 5, base_delay: float = 1.0) -> Optional[Queue]:
    """
    Attempt to reconnect to Redis with exponential backoff
    
    Args:
        max_retries: Maximum number of reconnection attempts
        base_delay: Base delay in seconds for exponential backoff
    
    Returns:
        Queue object if successful, None otherwise
    """
    for attempt in range(max_retries):
        try:
            redis_conn = get_redis_connection()
            queue = get_evaluation_queue()
            # Test connection
            redis_conn.ping()
            logger.info(f"Successfully reconnected to Redis (attempt {attempt + 1}/{max_retries})")
            return queue
        except Exception as e:
            delay = base_delay * (2 ** attempt)
            if attempt < max_retries - 1:
                logger.warning(f"Redis reconnection attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to reconnect to Redis after {max_retries} attempts: {str(e)}")
                return None
    return None


def process_job(job: Job, queue: Queue) -> bool:
    """
    Process a single job using RQ's job execution mechanism
    
    Args:
        job: RQ Job object
        queue: RQ Queue object
    
    Returns:
        True if job was processed successfully, False otherwise
    """
    job_id = job.id
    logger.info(f"Processing job {job_id}...")
    
    try:
        # Use RQ's perform method to execute the job properly
        # This handles job status updates, result storage, and error tracking
        try:
            job.perform()
        except AttributeError as attr_error:
            # Fallback if job.perform() fails (e.g., function not deserializable)
            # Call the function directly using job's args
            logger.warning(f"job.perform() failed for {job_id}, using direct function call: {str(attr_error)}")
            if hasattr(job, 'func') and job.func:
                result = job.func(*job.args, **job.kwargs)
                job._result = result
                job._status = 'finished'
            else:
                # Last resort: call process_evaluation directly if we can extract args
                if job.args and len(job.args) >= 3:
                    result = process_evaluation(job.args[0], job.args[1], job.args[2])
                    job._result = result
                    job._status = 'finished'
                else:
                    raise ValueError(f"Cannot execute job {job_id}: missing function or invalid args")
        
        # Check if job completed successfully
        if job.is_finished and not job.is_failed:
            logger.info(f"Job {job_id} completed successfully. Result: {job.result}")
            return True
        elif job.is_failed:
            error_info = job.exc_info if hasattr(job, 'exc_info') else "Unknown error"
            logger.error(f"Job {job_id} failed: {error_info}")
            return False
        else:
            logger.warning(f"Job {job_id} status unclear: {job.get_status()}")
            return False
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.error(f"Error processing job {job_id}: {error_msg}")
        logger.debug(f"Traceback for job {job_id}:\n{error_trace}")
        
        # Mark job as failed in RQ if not already marked
        try:
            if not job.is_failed:
                job.set_status('failed')
                if hasattr(job, 'exc_info'):
                    job.exc_info = error_trace
        except Exception as mark_error:
            logger.warning(f"Failed to mark job {job_id} as failed: {str(mark_error)}")
        
        return False


def main_worker_loop():
    """Main worker loop that continuously polls for and processes jobs"""
    global shutdown_requested
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Initialize connection
    queue = None
    poll_timeout = 5  # Seconds to wait for a job
    empty_queue_backoff = 1.0  # Initial backoff when no jobs found
    max_backoff = 30.0  # Maximum backoff time
    consecutive_empty_polls = 0
    last_health_check = time.time()
    health_check_interval = 60  # Log health status every 60 seconds
    
    logger.info("=" * 60)
    logger.info("Starting Evaluation Worker")
    logger.info(f"Queue: {settings.EVALUATION_QUEUE_NAME}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"Worker PID: {os.getpid()}")
    logger.info("=" * 60)
    
    # Initial connection
    try:
        redis_conn = get_redis_connection()
        queue = get_evaluation_queue()
        logger.info("Successfully connected to Redis and initialized queue")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        logger.info("Attempting to reconnect...")
        queue = reconnect_redis()
        if queue is None:
            logger.error("Could not establish initial Redis connection. Exiting.")
            sys.exit(1)
    
    # Main polling loop
    while not shutdown_requested:
        try:
            # Health check logging
            current_time = time.time()
            if current_time - last_health_check >= health_check_interval:
                logger.info(f"Worker health check: Running, PID={os.getpid()}, Queue={settings.EVALUATION_QUEUE_NAME}")
                last_health_check = current_time
                
                # Test Redis connection
                try:
                    redis_conn = get_redis_connection()
                    redis_conn.ping()
                except Exception as conn_error:
                    logger.warning(f"Redis connection check failed: {str(conn_error)}")
            
            # Try to dequeue a job
            try:
                # Check if queue has jobs - use RQ's job_ids property
                try:
                    job_ids = queue.job_ids
                    has_jobs = job_ids and len(job_ids) > 0
                except Exception as e:
                    logger.debug(f"Error checking job_ids: {str(e)}")
                    has_jobs = False
                
                if not has_jobs:
                    # No job available
                    consecutive_empty_polls += 1
                    # Exponential backoff, but cap at max_backoff
                    sleep_time = min(empty_queue_backoff * (1.5 ** min(consecutive_empty_polls, 10)), max_backoff)
                    
                    if consecutive_empty_polls % 10 == 0:  # Log every 10th empty poll
                        logger.debug(f"No jobs available. Waiting {sleep_time:.1f}s before next poll (empty polls: {consecutive_empty_polls})")
                    
                    time.sleep(sleep_time)
                    continue
                
                # Reset backoff counter when job is found
                consecutive_empty_polls = 0
                empty_queue_backoff = 1.0
                
                # Get the first job from the queue
                # RQ's Queue doesn't have dequeue_job(), so we use Redis directly
                # to pop from the queue list, then fetch the job object
                redis_conn = get_redis_connection()
                queue_key = queue.key
                
                # Pop job ID from the queue (non-blocking, atomic operation)
                job_id_bytes = redis_conn.lpop(queue_key)
                
                if job_id_bytes is None:
                    # Race condition - job was taken by another worker between check and pop
                    time.sleep(0.1)
                    continue
                
                # Decode job ID
                job_id = job_id_bytes.decode('utf-8') if isinstance(job_id_bytes, bytes) else job_id_bytes
                
                # Fetch the job object from RQ
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                except Exception as fetch_error:
                    logger.warning(f"Could not fetch job {job_id}: {str(fetch_error)}")
                    continue
                
                if job is None:
                    logger.warning("Could not get job from queue, retrying...")
                    time.sleep(0.5)
                    continue
                
                # Process the job
                job_start_time = time.time()
                success = process_job(job, queue)
                job_duration = time.time() - job_start_time
                
                if success:
                    logger.info(f"Job {job.id} processed in {job_duration:.2f} seconds")
                else:
                    logger.warning(f"Job {job.id} failed after {job_duration:.2f} seconds")
                
            except Exception as dequeue_error:
                # Error during dequeue (could be Redis connection issue)
                error_msg = str(dequeue_error)
                logger.error(f"Error dequeuing job: {error_msg}")
                
                # Try to reconnect
                logger.info("Attempting to reconnect to Redis...")
                queue = reconnect_redis()
                
                if queue is None:
                    # Reconnection failed, wait before retrying
                    logger.error("Reconnection failed. Waiting 10 seconds before retry...")
                    time.sleep(10)
                else:
                    logger.info("Reconnection successful, resuming job processing")
                    consecutive_empty_polls = 0
                
        except KeyboardInterrupt:
            # Handle Ctrl+C explicitly
            logger.info("Received KeyboardInterrupt, initiating shutdown...")
            shutdown_requested = True
            break
            
        except Exception as e:
            # Catch-all for any unexpected errors
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"Unexpected error in worker loop: {error_msg}")
            logger.debug(f"Traceback:\n{error_trace}")
            
            # Don't exit, just wait and continue
            logger.info("Waiting 5 seconds before continuing...")
            time.sleep(5)
    
    # Cleanup on shutdown
    logger.info("Worker shutdown complete. Goodbye!")


if __name__ == '__main__':
    try:
        main_worker_loop()
    except Exception as e:
        logger.error(f"Fatal error in worker: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
