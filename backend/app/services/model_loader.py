import logging
import joblib
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Module-level singletons for lazy-loaded model artefacts
_model = None
_preprocessor = None
_model_dir = None

# --- Model file names ---
PREPROCESSOR_FILENAME = "scaler.pkl"

# Ordered list of candidate model filenames (most preferred first)
MODEL_CANDIDATES = [
    "ensemble_soft_weighted_calibrated.joblib",
    "cat.pkl",
    "xgb.pkl",
    "rf.pkl",
]

# Ordered list of candidate tree-model filenames for SHAP (most preferred first)
SHAP_MODEL_CANDIDATES = [
    ("cat.pkl", "CatBoost"),
    ("xgb.pkl", "XGBoost"),
    ("rf.pkl", "Random Forest"),
]

# Tree-model type name substrings used when unwrapping an ensemble for SHAP
TREE_MODEL_TYPE_SUBSTRINGS = ['Forest', 'XGB', 'CatBoost', 'Gradient']

# Number of parent directories to traverse from this file to reach app/
# __file__ = backend/app/services/model_loader.py
# parents[0] = backend/app/services/
# parents[1] = backend/app/
APP_DIR_DEPTH = 2

# Subdirectory inside backend/app/ where model artefacts are stored
ML_MODELS_SUBDIR = "ml_models"


# ============================================================
# FinalEnsemble (must be defined before unpickling)
# ============================================================

class FinalEnsemble:
    """
    Custom weighted soft-voting ensemble wrapper.

    Must be defined before any joblib.load call that deserialises a
    pickled FinalEnsemble instance.
    """

    def __init__(self, models_dict: Dict, weights: Dict, preprocessor):
        """
        Initialise the ensemble.

        Args:
            models_dict: Mapping of model name to fitted estimator (or pipeline).
            weights: Mapping of model name to its voting weight.
            preprocessor: A fitted transformer whose ``transform`` method
                prepares raw feature DataFrames for the member classifiers.
        """
        self.models = models_dict
        self.weights = weights
        self.preprocessor = preprocessor

    def predict_proba(self, X) -> np.ndarray:
        """
        Predict class probabilities using a weighted average across all members.

        The raw weighted sum is row-normalised so that each row sums to 1.0.

        Args:
            X: Feature matrix as a NumPy array or pandas DataFrame.

        Returns:
            Array of shape (n_samples, n_classes) with normalised probabilities.
        """
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)

        X_proc = self.preprocessor.transform(X)
        probas = []

        for name, model in self.models.items():
            clf = model.named_steps["clf"] if hasattr(model, "named_steps") else model
            p = clf.predict_proba(X_proc)
            probas.append(self.weights[name] * p)

        weighted_proba = np.sum(probas, axis=0)
        # Normalise so that each row sums to 1.0
        row_sums = weighted_proba.sum(axis=1, keepdims=True)
        return weighted_proba / row_sums

    def predict(self, X) -> np.ndarray:
        """
        Predict class labels by taking the argmax of ``predict_proba``.

        Args:
            X: Feature matrix as a NumPy array or pandas DataFrame.

        Returns:
            Integer class label array of shape (n_samples,).
        """
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)


# ============================================================
# Model loading functions
# ============================================================

def get_model_directory() -> Path:
    """
    Resolve and cache the absolute path to the ml_models directory.

    The path is derived relative to this source file:
    ``backend/app/services/model_loader.py → backend/app/ml_models/``

    Returns:
        A ``Path`` pointing to the ml_models directory.
    """
    global _model_dir

    if _model_dir is None:
        current_file = Path(__file__).resolve()
        app_dir = current_file.parents[APP_DIR_DEPTH - 1]
        _model_dir = app_dir / ML_MODELS_SUBDIR
        logger.debug("Model directory resolved to: %s", _model_dir)

    return _model_dir


def load_model():
    """
    Load the trained ensemble model from disk and cache it in ``_model``.

    Iterates through ``MODEL_CANDIDATES`` in order and loads the first
    file that exists. Skips files that fail to deserialise and continues
    to the next candidate.

    Returns:
        The loaded model object.

    Raises:
        FileNotFoundError: If none of the candidate files are found in the
            model directory.
    """
    global _model

    if _model is not None:
        return _model

    model_dir = get_model_directory()
    logger.info("Loading model from directory: %s", model_dir)

    for model_file in MODEL_CANDIDATES:
        model_path = model_dir / model_file
        if model_path.exists():
            try:
                _model = joblib.load(model_path)
                logger.info("Model loaded successfully: %s", model_file)
                return _model
            except Exception as e:
                logger.warning("Failed to load %s: %s", model_file, e)
                continue

    available_files = (
        list(model_dir.glob("*.pkl")) + list(model_dir.glob("*.joblib"))
    )
    raise FileNotFoundError(
        f"No trained model found in {model_dir}\n"
        f"Available files: {[f.name for f in available_files]}\n"
    )


def load_preprocessor():
    """
    Load the feature preprocessor (scaler) from disk and cache it.

    Looks for ``PREPROCESSOR_FILENAME`` inside the ml_models directory. If
    the file is absent or fails to load, returns ``None`` so that callers
    can proceed without preprocessing when features are already scaled.

    Returns:
        The loaded preprocessor object, or ``None`` on failure.
    """
    global _preprocessor

    if _preprocessor is not None:
        return _preprocessor

    model_dir = get_model_directory()
    preprocessor_path = model_dir / PREPROCESSOR_FILENAME

    if not preprocessor_path.exists():
        logger.warning(
            "Preprocessor not found at: %s. "
            "Model will operate without preprocessing if features are already scaled.",
            preprocessor_path,
        )
        return None

    try:
        _preprocessor = joblib.load(preprocessor_path)
        logger.info("Preprocessor loaded successfully from: %s", preprocessor_path)
        return _preprocessor
    except Exception as e:
        logger.error("Failed to load preprocessor: %s", e)
        return None


def get_model():
    """
    Return the cached model, loading it from disk on first access.

    Returns:
        The loaded model object.
    """
    if _model is None:
        load_model()
    return _model


def get_preprocessor():
    """
    Return the cached preprocessor, loading it from disk on first access.

    Returns:
        The loaded preprocessor object, or ``None`` if unavailable.
    """
    if _preprocessor is None:
        load_preprocessor()
    return _preprocessor


def get_model_for_shap():
    """
    Return a tree-based model suitable for SHAP explanations.

    Resolution order:
        1. Individual tree model files listed in ``SHAP_MODEL_CANDIDATES``.
        2. A tree estimator unwrapped from the main ensemble (handles
           pipelines, ``CalibratedClassifierCV``, and ``VotingClassifier``).
        3. The main model as a last resort.

    Returns:
        A fitted estimator (or pipeline) compatible with SHAP tree explainers.
    """
    model_dir = get_model_directory()

    # 1. Try individual tree model files
    for model_file, model_name in SHAP_MODEL_CANDIDATES:
        model_path = model_dir / model_file
        if model_path.exists():
            try:
                model = joblib.load(model_path)
                logger.info(
                    "Loaded %s (%s) for SHAP explanations.", model_name, model_file
                )
                return model
            except Exception as e:
                logger.warning("Failed to load %s for SHAP: %s", model_file, e)
                continue

    # 2. Attempt to unwrap a tree model from the main ensemble
    logger.warning(
        "No individual tree model found; attempting to extract from ensemble."
    )
    main_model = get_model()

    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import VotingClassifier

    clf = main_model

    # Unwrap pipeline
    if hasattr(clf, 'named_steps'):
        clf = clf.named_steps.get('clf', clf)

    # Unwrap calibration wrapper
    if isinstance(clf, CalibratedClassifierCV):
        if hasattr(clf, 'calibrated_classifiers_') and len(clf.calibrated_classifiers_) > 0:
            clf = clf.calibrated_classifiers_[0].estimator
        elif hasattr(clf, 'base_estimator'):
            clf = clf.base_estimator

    # Search inside a voting ensemble for the first tree-based member
    if isinstance(clf, VotingClassifier):
        for name, estimator in clf.estimators_:
            est = estimator
            if hasattr(est, 'named_steps'):
                est = est.named_steps.get('clf', est)

            model_type = type(est).__name__
            if any(substring in model_type for substring in TREE_MODEL_TYPE_SUBSTRINGS):
                logger.info(
                    "Extracted %s from ensemble for SHAP explanations.", model_type
                )
                return estimator  # Return the full pipeline (with preprocessor)

    # 3. Last resort: return the main model unchanged
    logger.warning(
        "Could not find a tree-based model; falling back to the main model for SHAP."
    )
    return main_model


def predict_with_model(features: Dict[str, float]) -> Tuple[int, np.ndarray]:
    """
    Run inference with the loaded model for a single feature set.

    Args:
        features: Mapping of feature names to their numeric values for one
            candidate record.

    Returns:
        A tuple of ``(predicted_class, probabilities)`` where
        ``predicted_class`` is an integer class index and ``probabilities``
        is a 1-D array of per-class probabilities. If ``predict_proba`` is
        unavailable, a one-hot probability array is returned instead.

    Raises:
        Exception: Re-raises any exception thrown by the model after logging
            diagnostic information.
    """
    model = get_model()
    feature_df = pd.DataFrame([features])

    try:
        prediction = model.predict(feature_df)[0]

        try:
            probabilities = model.predict_proba(feature_df)[0]
        except Exception:
            logger.warning(
                "predict_proba unavailable for %s; using one-hot fallback.",
                type(model).__name__,
            )
            probabilities = np.zeros(3)
            probabilities[int(prediction)] = 1.0

        return int(prediction), probabilities

    except Exception as e:
        logger.error(
            "Prediction error: %s | Model type: %s | Features shape: %s",
            e, type(model).__name__, feature_df.shape,
        )
        raise


def model_health_check() -> Dict[str, Any]:
    """
    Gather diagnostic information about the current model loading state.

    Returns:
        A dictionary with the following keys:
        - ``model_loaded`` (bool): Whether the main model is in memory.
        - ``preprocessor_loaded`` (bool): Whether the preprocessor is in memory.
        - ``model_directory`` (str): Resolved path to the model directory.
        - ``model_directory_exists`` (bool): Whether that directory exists on disk.
        - ``model_type`` (str): Class name of the loaded model (if loaded).
        - ``available_model_files`` (list[str]): Names of ``.pkl`` / ``.joblib``
          files present in the model directory (if the directory exists).
    """
    model_dir = get_model_directory()

    status: Dict[str, Any] = {
        "model_loaded": _model is not None,
        "preprocessor_loaded": _preprocessor is not None,
        "model_directory": str(model_dir),
        "model_directory_exists": model_dir.exists(),
    }

    if _model is not None:
        status["model_type"] = type(_model).__name__

    if model_dir.exists():
        model_files = list(model_dir.glob("*.pkl")) + list(model_dir.glob("*.joblib"))
        status["available_model_files"] = [f.name for f in model_files]

    logger.debug("Health check status: %s", status)
    return status