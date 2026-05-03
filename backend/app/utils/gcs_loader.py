"""
GCS model loader — downloads ML model files from Google Cloud Storage to a
local temp directory on container startup.

Usage (called once at the top of main_ml.py lifespan before load_model()):
    from app.utils.gcs_loader import download_models_if_gcs
    download_models_if_gcs()

Environment variables:
    GCS_BUCKET_NAME    — GCS bucket name. If empty, this function is a no-op
                         (local dev: models are already on disk).
    GCS_MODEL_PREFIX   — Path prefix inside the bucket (default: "models/").
    ML_MODELS_DIR      — Set automatically by this function after download.
                         Read by model_loader.py and skill_ner_loader.py.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

LOCAL_MODEL_DIR = Path("/tmp/ml_models")


def download_models_if_gcs() -> None:
    """
    Download ML models from GCS to LOCAL_MODEL_DIR and set ML_MODELS_DIR.

    No-op if GCS_BUCKET_NAME is not set (local development).
    Skips files that already exist on disk (safe to call on container restart).
    """
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "").strip()
    if not bucket_name:
        logger.info("GCS_BUCKET_NAME not set — using local disk models")
        return

    prefix = os.environ.get("GCS_MODEL_PREFIX", "models/")
    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading ML models from gs://%s/%s → %s", bucket_name, prefix, LOCAL_MODEL_DIR)

    try:
        from google.cloud import storage  # type: ignore
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        blobs = list(bucket.list_blobs(prefix=prefix))
        if not blobs:
            logger.warning("No blobs found at gs://%s/%s", bucket_name, prefix)
            return

        for blob in blobs:
            # Strip the bucket prefix to get the relative file path
            relative_path = blob.name[len(prefix):]
            if not relative_path:
                continue  # skip the directory entry itself

            local_path = LOCAL_MODEL_DIR / relative_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if local_path.exists():
                logger.debug("Skipping already-downloaded file: %s", local_path)
                continue

            logger.info("Downloading %s → %s", blob.name, local_path)
            blob.download_to_filename(str(local_path))

        # Point model loaders at the downloaded directory
        os.environ["ML_MODELS_DIR"] = str(LOCAL_MODEL_DIR)
        logger.info("ML_MODELS_DIR set to %s", LOCAL_MODEL_DIR)

    except Exception as exc:
        logger.error("Failed to download models from GCS: %s", exc, exc_info=True)
        raise RuntimeError(
            f"Could not download ML models from gs://{bucket_name}/{prefix}. "
            "Set GCS_BUCKET_NAME='' to use local disk models."
        ) from exc
