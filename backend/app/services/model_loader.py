# backend/app/services/model_loader.py
import joblib
import os
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd

# Global variables to store loaded models
_model = None
_preprocessor = None
_model_dir = None

# ============================================================
# Define FinalEnsemble class BEFORE loading
# ============================================================
class FinalEnsemble:
    """Custom ensemble wrapper - must be defined before unpickling"""
    def __init__(self, models_dict, weights, preprocessor):
        self.models = models_dict
        self.weights = weights
        self.preprocessor = preprocessor
    
    def predict_proba(self, X):
        """Predict probabilities using weighted ensemble"""
        # Convert to DataFrame if needed
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        
        X_proc = self.preprocessor.transform(X)
        probas = []
        
        for name, model in self.models.items():
            clf = model.named_steps["clf"] if hasattr(model, "named_steps") else model
            p = clf.predict_proba(X_proc)
            probas.append(self.weights[name] * p)
        
        weighted_proba = np.sum(probas, axis=0)
        # Normalize to ensure probabilities sum to 1.0
        row_sums = weighted_proba.sum(axis=1, keepdims=True)
        normalized_proba = weighted_proba / row_sums
        return normalized_proba
    
    def predict(self, X):
        """Predict class labels"""
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

# ============================================================
# Model Loading Functions
# ============================================================

def get_model_directory() -> Path:
    """Get the directory where models are stored"""
    global _model_dir
    
    if _model_dir is None:
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parent.parent.parent  # Go to backend/
        project_root = backend_dir.parent  # Go to 25-26J-087/
        _model_dir = project_root / "notebooks" / "fair-prehire-attrition-prediction" / "models"
    
    return _model_dir

def load_model():
    """Load the trained ensemble model"""
    global _model
    
    if _model is not None:
        return _model
    
    model_dir = get_model_directory()
    
    # Try loading models in order of preference
    model_candidates = [
        "final_ensemble.pkl",
        "ensemble_soft_weighted_calibrated.joblib",
        "ensemble_soft_weighted.joblib",
        "cat.pkl",
        "xgb.pkl",
        "rf.pkl",
    ]
    
    print(f"📦 Looking for models in: {model_dir}")
    
    for model_file in model_candidates:
        model_path = model_dir / model_file
        if model_path.exists():
            try:
                print(f"   Loading model: {model_file}")
                _model = joblib.load(model_path)
                print(f"✅ Model loaded successfully: {model_file}")
                return _model
            except Exception as e:
                print(f"⚠️  Failed to load {model_file}: {e}")
                continue
    
    # If no model found, raise error
    available_files = list(model_dir.glob("*.pkl")) + list(model_dir.glob("*.joblib"))
    raise FileNotFoundError(
        f"No trained model found in {model_dir}\n"
        f"Available files: {[f.name for f in available_files]}\n"
        f"Please run the training notebook (04_model_training.py)"
    )

def load_preprocessor():
    """Load the feature preprocessor (scaler)"""
    global _preprocessor
    
    if _preprocessor is not None:
        return _preprocessor
    
    model_dir = get_model_directory()
    preprocessor_path = model_dir / "scaler.pkl"
    
    if not preprocessor_path.exists():
        print(f"⚠️  Preprocessor not found at: {preprocessor_path}")
        print("   Model will work without preprocessing if features are already scaled")
        return None
    
    try:
        print(f"📦 Loading preprocessor: scaler.pkl")
        _preprocessor = joblib.load(preprocessor_path)
        print(f"✅ Preprocessor loaded successfully")
        return _preprocessor
    except Exception as e:
        print(f"⚠️  Failed to load preprocessor: {e}")
        return None

def get_model():
    """Get the loaded model (load if not already loaded)"""
    if _model is None:
        load_model()
    return _model

def get_preprocessor():
    """Get the loaded preprocessor (load if not already loaded)"""
    if _preprocessor is None:
        load_preprocessor()
    return _preprocessor

def predict_with_model(features: Dict[str, float]) -> tuple:
    """
    Make prediction using the loaded model
    
    Args:
        features: Dictionary of feature names to values
        
    Returns:
        Tuple of (predicted_class, probabilities)
    """
    model = get_model()
    
    # Convert features dict to DataFrame (preserve feature order)
    feature_df = pd.DataFrame([features])
    
    # Make prediction
    try:
        prediction = model.predict(feature_df)[0]
        
        try:
            probabilities = model.predict_proba(feature_df)[0]
        except:
            # If predict_proba not available, create dummy probabilities
            probabilities = np.zeros(3)
            probabilities[int(prediction)] = 1.0
        
        return int(prediction), probabilities
        
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        print(f"   Model type: {type(model)}")
        print(f"   Features shape: {feature_df.shape}")
        raise

def model_health_check() -> Dict[str, Any]:
    """
    Check if models are loaded and ready
    Returns status information
    """
    status = {
        "model_loaded": _model is not None,
        "preprocessor_loaded": _preprocessor is not None,
        "model_directory": str(get_model_directory()),
        "model_directory_exists": get_model_directory().exists(),
    }
    
    if _model is not None:
        status["model_type"] = type(_model).__name__
    
    if get_model_directory().exists():
        model_files = list(get_model_directory().glob("*.pkl")) + \
                     list(get_model_directory().glob("*.joblib"))
        status["available_model_files"] = [f.name for f in model_files]
    
    return status