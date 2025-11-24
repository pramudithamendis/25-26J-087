"""
============================================================
Explainability (SHAP + Feature Importance)
============================================================
Purpose:
- Generate SHAP explanations for tree models
- Create global feature importance plots
- Generate local explanations (waterfall plots)
- Export ensemble probability breakdowns
- Save all artifacts for documentation
============================================================
"""

import os
import joblib
import json
import shap
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

print("="*60)
print("EXPLAINABILITY (SHAP)")
print("="*60)

# ============================================================
# CRITICAL: Define FinalEnsemble class BEFORE loading
# ============================================================

class FinalEnsemble:
    """Custom ensemble wrapper - must be defined before unpickling"""
    def __init__(self, models_dict, weights, preprocessor):
        self.models = models_dict
        self.weights = weights
        self.preprocessor = preprocessor
    
    def predict_proba(self, X):
        X_proc = self.preprocessor.transform(X)
        probas = []
        for name, model in self.models.items():
            clf = model.named_steps["clf"]
            p = clf.predict_proba(X_proc)
            probas.append(self.weights[name] * p)
        
        weighted_proba = np.sum(probas, axis=0)
        # Normalize to ensure probabilities sum to 1.0
        row_sums = weighted_proba.sum(axis=1, keepdims=True)
        normalized_proba = weighted_proba / row_sums
        return normalized_proba
    
    def predict(self, X):
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

# ============================================================
# Auto-Detecting Paths
# ============================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

MODEL_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"
ARTIFACT_DIR = RESULTS_DIR / "artifacts" / "shap"

# Create folders
for folder in [MODEL_DIR, RESULTS_DIR, ARTIFACT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print(f"\n Project root: {PROJECT_ROOT}")
print(f" Models folder: {MODEL_DIR}")
print(f" Artifacts folder: {ARTIFACT_DIR}")

# ============================================================
# Load Test Data
# ============================================================

print("\n Loading test data...")
try:
    X_test = joblib.load(MODEL_DIR / "X_test.pkl")
    y_test = joblib.load(MODEL_DIR / "y_test.pkl")
    print(f" Loaded test data: {X_test.shape}")
except FileNotFoundError as e:
    print(f" Error: Test data not found. Run 04_model_training.py first.")
    print(f"Missing file: {e.filename}")
    exit()

# ============================================================
# Load Models
# ============================================================

print("\n Loading trained models...")

model_files = {
    "logreg": "logreg.pkl",
    "rf": "rf.pkl",
    "xgb": "xgb.pkl",
    "cat": "cat.pkl",
    "ebm": "ebm.pkl"
}

models = {}
for name, filename in model_files.items():
    filepath = MODEL_DIR / filename
    if filepath.exists():
        try:
            models[name] = joblib.load(filepath)
            print(f" Loaded {name}")
        except Exception as e:
            print(f"  Could not load {name}: {e}")
    else:
        print(f"  {name} not found, skipping")

if not models:
    print(" No models loaded. Cannot proceed.")
    exit()

# Load ensemble models (try multiple versions)
print("\n Loading ensemble model...")

ensemble_files = [
    ("ensemble_soft_weighted_calibrated.joblib", "Calibrated Ensemble"),
    ("ensemble_soft_weighted.joblib", "Weighted Ensemble"),
    ("final_ensemble.pkl", "Custom Ensemble")
]

final_model = None
ensemble_name = None

for filename, name in ensemble_files:
    filepath = MODEL_DIR / filename
    if filepath.exists():
        try:
            final_model = joblib.load(filepath)
            ensemble_name = name
            print(f" Loaded {name} ({filename})")
            break
        except Exception as e:
            print(f"  Failed to load {filename}: {e}")
            continue

if final_model is None:
    print("  No ensemble model found, will skip ensemble explanations")

# ============================================================
# PART 1: SHAP for Tree Models
# ============================================================

print("\n" + "="*60)
print(" GENERATING SHAP EXPLANATIONS FOR TREE MODELS")
print("="*60)

# Initialize SHAP JavaScript for interactive plots
shap.initjs()

tree_models = ["rf", "xgb", "cat"]

for model_name in tree_models:
    if model_name not in models:
        print(f"\n  Skipping {model_name} - not loaded")
        continue
    
    print(f"\n→ Explaining {model_name.upper()}...")
    try:
        model = models[model_name]
        
        # Get the actual classifier from pipeline
        if hasattr(model, 'named_steps'):
            clf = model.named_steps['clf']
            X_test_transformed = model.named_steps['pre'].transform(X_test)
        else:
            clf = model
            X_test_transformed = X_test
        
        # Create SHAP explainer
        print(f"  Creating TreeExplainer...")
        explainer = shap.TreeExplainer(clf)
        
        # Calculate SHAP values (use subset for speed)
        print(f"  Calculating SHAP values...")
        shap_values = explainer.shap_values(X_test_transformed[:500])  # Use 500 samples for speed
        
        # Handle multi-class SHAP values
        if isinstance(shap_values, list):
            # For multi-class, create summary for each class
            class_names = ["High Risk (0-6mo)", "Medium Risk (6-12mo)", "Low Risk (>12mo)"]
            
            for class_idx, class_name in enumerate(class_names):
                plt.figure(figsize=(12, 8))
                shap.summary_plot(
                    shap_values[class_idx], 
                    X_test_transformed[:500], 
                    feature_names=X_test.columns.tolist(),
                    show=False,
                    max_display=15
                )
                plt.title(f"SHAP Summary - {model_name.upper()} - {class_name}", fontsize=14, fontweight='bold')
                plt.tight_layout()
                
                output_path = ARTIFACT_DIR / f"{model_name}_shap_summary_class{class_idx}.png"
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                print(f"   Saved: {output_path.name}")
        else:
            # Binary or single output
            plt.figure(figsize=(12, 8))
            shap.summary_plot(
                shap_values, 
                X_test_transformed[:500],
                feature_names=X_test.columns.tolist(),
                show=False,
                max_display=15
            )
            plt.title(f"SHAP Summary - {model_name.upper()}", fontsize=14, fontweight='bold')
            plt.tight_layout()
            
            output_path = ARTIFACT_DIR / f"{model_name}_shap_summary.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"   Saved: {output_path.name}")
        
        print(f" Completed SHAP analysis for {model_name.upper()}")
        
    except Exception as e:
        print(f" Error generating SHAP for {model_name}: {e}")
        import traceback
        traceback.print_exc()

# ============================================================
# PART 2: Local Explainability (Bar Plots)
# ============================================================

print("\n" + "="*60)
print(" GENERATING LOCAL EXPLANATIONS (BAR PLOTS)")
print("="*60)

if "cat" in models:
    try:
        print("\n→ Creating local explanation plots for sample predictions...")
        model = models["cat"]
        
        if hasattr(model, 'named_steps'):
            clf = model.named_steps['clf']
            X_test_transformed = model.named_steps['pre'].transform(X_test)
        else:
            clf = model
            X_test_transformed = X_test
        
        explainer = shap.TreeExplainer(clf)
        
        print("  Selecting sample candidates...")
        y_pred_all = model.predict(X_test)
        sample_indices = []
        
        for class_idx in range(3):
            class_samples = np.where(y_pred_all == class_idx)[0]
            if len(class_samples) > 0:
                sample_indices.append(class_samples[0])
        
        if len(sample_indices) == 0:
            sample_indices = [5, 100, 200]
        
        class_names = ["High Risk (0-6mo)", "Medium Risk (6-12mo)", "Low Risk (>12mo)"]
        
        for i, sample_idx in enumerate(sample_indices):
            print(f"\n  Processing sample {i+1}/{len(sample_indices)} (index: {sample_idx})...")
            
            shap_values_sample = explainer.shap_values(X_test_transformed[sample_idx:sample_idx+1])
            
            # Convert to Python ints
            y_pred_sample = int(y_pred_all[sample_idx])
            y_true_sample = int(y_test.iloc[sample_idx])
            
            # Handle 3D array format: (1, 22, 3)
            if len(shap_values_sample.shape) == 3:
                shap_vals = shap_values_sample[0, :, y_pred_sample]
                expected_values = explainer.expected_value
                base_value = float(expected_values[y_pred_sample]) if isinstance(expected_values, (list, np.ndarray)) else float(expected_values)
            elif isinstance(shap_values_sample, list):
                shap_vals = shap_values_sample[y_pred_sample][0]
                expected_values = explainer.expected_value
                base_value = float(expected_values[y_pred_sample]) if isinstance(expected_values, (list, np.ndarray)) else float(expected_values)
            else:
                print(f"      Unexpected format, skipping")
                continue
            
            # Get feature values
            feature_vals = X_test.iloc[sample_idx].values
            feature_names = X_test.columns.tolist()
            
            # Create plotting DataFrame
            shap_df = pd.DataFrame({
                'feature': feature_names,
                'shap_value': shap_vals,
                'feature_value': feature_vals
            })
            
            shap_df['abs_shap'] = np.abs(shap_df['shap_value'])
            shap_df = shap_df.sort_values('abs_shap', ascending=True).tail(15)
            
            # Create plot
            fig, ax = plt.subplots(figsize=(10, 8))
            
            colors = ['#e74c3c' if x < 0 else '#2ecc71' for x in shap_df['shap_value']]
            
            ax.barh(range(len(shap_df)), shap_df['shap_value'], color=colors, edgecolor='black')
            ax.set_yticks(range(len(shap_df)))
            ax.set_yticklabels([f"{feat} = {val:.2f}" for feat, val in 
                               zip(shap_df['feature'], shap_df['feature_value'])], fontsize=9)
            ax.set_xlabel('SHAP Value (Impact on Prediction)', fontsize=11, fontweight='bold')
            ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
            ax.grid(axis='x', alpha=0.3)
            
            correct = " CORRECT" if y_pred_sample == y_true_sample else " INCORRECT"
            ax.set_title(
                f"Local Explanation - Sample #{sample_idx}\n"
                f"Predicted: {class_names[y_pred_sample]} | Actual: {class_names[y_true_sample]}\n"
                f"{correct}\n"
                f"Base Value: {base_value:.3f}",
                fontsize=12, fontweight='bold', pad=15
            )
            
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#2ecc71', label='Increases Risk'),
                Patch(facecolor='#e74c3c', label='Decreases Risk')
            ]
            ax.legend(handles=legend_elements, loc='lower right')
            
            plt.tight_layout()
            
            bar_path = ARTIFACT_DIR / f"local_explanation_sample_{sample_idx}_class{y_pred_sample}.png"
            plt.savefig(bar_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"     Saved: {bar_path.name}")
        
        print("\n Local explanation plots generated successfully")
        
    except Exception as e:
        print(f" Error generating local explanations: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  CatBoost not available, skipping local explanations")


# ============================================================
# PART 3: Feature Importance (Global)
# ============================================================

print("\n" + "="*60)
print(" EXPORTING GLOBAL FEATURE IMPORTANCES")
print("="*60)

feature_importances = {}

for name, model in models.items():
    if name == "logreg":  # Skip logistic regression
        continue
        
    try:
        if hasattr(model, 'named_steps'):
            clf = model.named_steps['clf']
        else:
            clf = model
        
        if hasattr(clf, 'feature_importances_'):
            feature_importances[name] = clf.feature_importances_
            print(f" Extracted importances for {name}")
        elif hasattr(clf, 'get_feature_importance'):
            feature_importances[name] = clf.get_feature_importance()
            print(f" Extracted importances for {name}")
    except Exception as e:
        print(f"  Could not extract importances for {name}: {e}")

# Create DataFrame with all importances
if feature_importances:
    fi_dict = {"feature": X_test.columns.tolist()}
    
    for name, importances in feature_importances.items():
        # Ensure length matches
        n_features = len(X_test.columns)
        if len(importances) >= n_features:
            fi_dict[f"{name}_importance"] = importances[:n_features]
        else:
            # Pad with zeros if needed
            padded = np.zeros(n_features)
            padded[:len(importances)] = importances
            fi_dict[f"{name}_importance"] = padded
    
    fi_df = pd.DataFrame(fi_dict)
    fi_path = ARTIFACT_DIR / "global_feature_importance.csv"
    fi_df.to_csv(fi_path, index=False)
    print(f"\n Saved: {fi_path}")
    
    # Plot top features comparison across models
    print("\n→ Creating feature importance comparison plot...")
    
    # Calculate average importance across models
    importance_cols = [col for col in fi_df.columns if 'importance' in col]
    fi_df['avg_importance'] = fi_df[importance_cols].mean(axis=1)
    fi_df_sorted = fi_df.sort_values('avg_importance', ascending=False).head(15)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    x = np.arange(len(fi_df_sorted))
    width = 0.8 / len(importance_cols)
    
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
    
    for i, col in enumerate(importance_cols):
        model_name = col.replace('_importance', '').upper()
        ax.barh(x + i * width, fi_df_sorted[col], width, 
               label=model_name, color=colors[i % len(colors)])
    
    ax.set_yticks(x + width * (len(importance_cols) - 1) / 2)
    ax.set_yticklabels(fi_df_sorted['feature'])
    ax.set_xlabel('Feature Importance', fontsize=12, fontweight='bold')
    ax.set_title('Top 15 Features - Model Comparison', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plot_path = ARTIFACT_DIR / "feature_importance_comparison.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f" Saved: {plot_path}")
    
    # Individual model plot (CatBoost if available)
    if "cat" in feature_importances:
        print("\n→ Creating CatBoost feature importance plot...")
        
        plt.figure(figsize=(10, 8))
        sorted_idx = np.argsort(feature_importances["cat"])[::-1][:15]
        
        colors_cat = ['#e74c3c' if i < 5 else '#3498db' for i in range(len(sorted_idx))]
        
        plt.barh(range(len(sorted_idx)), feature_importances["cat"][sorted_idx], color=colors_cat, edgecolor='black')
        plt.yticks(range(len(sorted_idx)), X_test.columns[sorted_idx])
        plt.xlabel("Feature Importance", fontsize=12, fontweight='bold')
        plt.title("Top 15 Features - CatBoost Model", fontsize=14, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        plot_path = ARTIFACT_DIR / "cat_feature_importance.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f" Saved: {plot_path}")

# ============================================================
# PART 4: Ensemble Explanation (Probability Breakdown)
# ============================================================

print("\n" + "="*60)
print(" GENERATING ENSEMBLE PROBABILITY BREAKDOWN")
print("="*60)

try:
    # Load weights
    weights_path = MODEL_DIR / "final_weights.json"
    if weights_path.exists():
        with open(weights_path, "r") as f:
            weights = json.load(f)
        print(" Loaded ensemble weights")
    else:
        weights = {}
        print("  Weights file not found")
    
    # Get predictions from each model (first 10 samples)
    probabilities = {}
    sample_size = min(10, len(X_test))
    
    for name, model in models.items():
        try:
            probs = model.predict_proba(X_test[:sample_size])
            probabilities[name] = probs.tolist()
            print(f"   Got probabilities from {name}")
        except Exception as e:
            print(f"   Could not get probabilities for {name}: {e}")
    
    # Get final ensemble predictions
    if final_model:
        try:
            final_probs = final_model.predict_proba(X_test[:sample_size])
            final_preds = final_model.predict(X_test[:sample_size])
            print(f"   Got ensemble predictions")
        except Exception as e:
            print(f"   Could not get ensemble predictions: {e}")
            final_probs = None
            final_preds = None
    else:
        final_probs = None
        final_preds = None
    
    # Create breakdown
    breakdown = {
        "weights": weights,
        "n_samples": sample_size,
        "sample_predictions": {
            "base_models": probabilities,
            "ensemble": final_probs.tolist() if final_probs is not None else None,
            "ensemble_classes": final_preds.tolist() if final_preds is not None else None
        },
        "class_mapping": {
            "0": "High Risk (0-6 months)",
            "1": "Medium Risk (6-12 months)",
            "2": "Low Risk (>12 months)"
        },
        "note": "Probabilities for first 10 test samples, ordered as [class_0, class_1, class_2]"
    }
    
    breakdown_path = ARTIFACT_DIR / "ensemble_probability_breakdown.json"
    with open(breakdown_path, "w") as f:
        json.dump(breakdown, f, indent=2)
    print(f"\n Saved: {breakdown_path}")
    
except Exception as e:
    print(f" Error creating ensemble breakdown: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# Summary
# ============================================================

print("\n" + "="*60)
print(" EXPLAINABILITY ARTIFACTS GENERATED")
print("="*60)
print(f"\n Generated artifacts in: {ARTIFACT_DIR}")

print("\n Files created:")
artifact_files = list(ARTIFACT_DIR.glob("*"))
if artifact_files:
    for file in sorted(artifact_files):
        print(f"  • {file.name}")
else:
    print("    No files found")

print("\n Artifact Types:")
print("   SHAP summary plots (global explanations per class)")
print("   Waterfall plots (local explanations for sample predictions)")
print("   Feature importance CSV (all models)")
print("   Feature importance visualizations")
print("   Ensemble probability breakdown (JSON)")

print("\n" + "="*60)
print("Explainability Analysis Completed")
print("="*60)