"""
RQ Worker Script for processing background evaluation tasks

Run this script to start the Redis Queue worker that processes evaluation jobs.

Usage:
    python worker.py

Or using rq command (Unix only, uses fork):
    python -m rq worker evaluations --with-scheduler

On Windows, this script uses SimpleWorker (no fork); on Unix it uses the default Worker.
"""
import sys
import os

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rq import Worker, Queue
from app.services.queue_service import get_redis_connection, get_evaluation_queue
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleWorker(Worker):
    """
    Worker that runs jobs in the same process (no fork).
    Use on Windows where os.fork() is not available.
    """

    def fork_work_horse(self, job, queue):
        """Run job in the current process instead of forking (Windows-compatible)."""
        self.main_work_horse(job, queue)


def get_worker_class():
    """Use SimpleWorker on Windows (no os.fork); default Worker on Unix."""
    if sys.platform == "win32":
        logger.info("Using SimpleWorker (no fork) for Windows compatibility")
        return SimpleWorker
    return Worker


if __name__ == '__main__':
    try:
        # Get Redis connection and queue
        redis_conn = get_redis_connection()
        queue = get_evaluation_queue()
        
        logger.info(f"Starting RQ worker for queue: {settings.EVALUATION_QUEUE_NAME}")
        logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        
        worker_name = f'evaluation_worker_{os.getpid()}'
        worker_class = get_worker_class()
        worker = worker_class([queue], connection=redis_conn, name=worker_name)
        worker.work()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        sys.exit(1)


