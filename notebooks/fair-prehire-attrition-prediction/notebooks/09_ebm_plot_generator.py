"""
Generate EBM Feature Shape Function Plots
"""

import joblib
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================
MODELS_DIR = Path("../models")
OUTPUT_DIR = Path("../results/artifacts/ebm_plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EBM_MODEL_FILE = MODELS_DIR / "ebm.pkl"

print("="*60)
print("EBM SHAPE FUNCTION PLOT GENERATOR")
print("="*60)

# ============================================================
# Load EBM Model
# ============================================================
print(f"\n Loading EBM model from: {EBM_MODEL_FILE}")

try:
    ebm_model = joblib.load(EBM_MODEL_FILE)
    print(" EBM model loaded successfully")
except FileNotFoundError:
    print(f" Error: {EBM_MODEL_FILE} not found")
    print("\nAvailable model files:")
    for f in MODELS_DIR.glob("*.pkl"):
        print(f"  • {f.name}")
    exit(1)

# ============================================================
# Generate Global Explanation
# ============================================================
print("\n Generating EBM global explanations...")

try:
    # Get the classifier from pipeline if needed
    if hasattr(ebm_model, 'named_steps'):
        ebm_clf = ebm_model.named_steps['clf']
    else:
        ebm_clf = ebm_model
    
    ebm_global = ebm_clf.explain_global()
    print(" Global explanation generated")
    
    # Save the explanation object
    explanation_path = OUTPUT_DIR / "ebm_global_explanation.joblib"
    joblib.dump(ebm_global, explanation_path)
    print(f" Saved explanation to: {explanation_path}")
    
except Exception as e:
    print(f" Error generating explanation: {e}")
    exit(1)

# ============================================================
# Plot Top 10 Most Important Features
# ============================================================
print("\n Creating feature importance plot...")

fig, ax = plt.subplots(figsize=(10, 8))

# Get feature names and importance scores
feature_names = ebm_global.data()['names']
importance_scores = ebm_global.data()['scores']

# Sort by importance
sorted_indices = sorted(range(len(importance_scores)), 
                       key=lambda i: abs(importance_scores[i]), 
                       reverse=True)

# Top 10 features
top_10_indices = sorted_indices[:10]
top_features = [feature_names[i] for i in top_10_indices]
top_scores = [importance_scores[i] for i in top_10_indices]

# Create bar plot
colors = ['#e74c3c' if score < 0 else '#2ecc71' for score in top_scores]
bars = ax.barh(range(len(top_features)), top_scores, color=colors, edgecolor='black')

ax.set_yticks(range(len(top_features)))
ax.set_yticklabels(top_features)
ax.set_xlabel('Feature Importance', fontsize=12, fontweight='bold')
ax.set_title('EBM Global Feature Importance (Top 10)', fontsize=14, fontweight='bold')
ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
importance_plot_path = OUTPUT_DIR / "ebm_feature_importance.png"
plt.savefig(importance_plot_path, dpi=300, bbox_inches='tight')
print(f"✅ Saved: {importance_plot_path}")
plt.close()

# ============================================================
# Generate Individual Feature Shape Plots
# ============================================================
print("\n Creating individual feature shape plots...")

# Create subplots for top 6 features
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

plots_created = 0
for idx, feature_idx in enumerate(top_10_indices[:6]):
    try:
        ax = axes[idx]
        feature_name = feature_names[feature_idx]
        
        # Get feature data
        feature_data = ebm_global.data(feature_idx)
        
        # Plot shape function
        if 'names' in feature_data and 'scores' in feature_data:
            x_values = feature_data['names']
            y_values = feature_data['scores']
            
            # Ensure x_values and y_values match in length
            if hasattr(x_values, '__len__') and hasattr(y_values, '__len__'):
                # Handle multiclass case (y_values might be 2D: [n_samples, n_classes])
                if len(y_values.shape) > 1 and y_values.shape[1] > 1:
                    # Multiclass - plot each class separately
                    colors = ['#e74c3c', '#f39c12', '#2ecc71']  # High, Medium, Low risk
                    labels = ['High Risk', 'Medium Risk', 'Low Risk']
                    
                    # Match lengths
                    min_len = min(len(x_values), y_values.shape[0])
                    x_values_trimmed = x_values[:min_len]
                    
                    for class_idx in range(min(3, y_values.shape[1])):
                        y_class = y_values[:min_len, class_idx]
                        ax.plot(x_values_trimmed, y_class, linewidth=2, 
                               color=colors[class_idx], label=labels[class_idx], alpha=0.7)
                    
                    ax.legend(loc='best', fontsize=8)
                else:
                    # Binary or single output - match lengths
                    min_len = min(len(x_values), len(y_values))
                    x_values_trimmed = x_values[:min_len]
                    y_values_trimmed = y_values[:min_len]
                    
                    ax.plot(x_values_trimmed, y_values_trimmed, linewidth=2, color='steelblue')
                    ax.fill_between(x_values_trimmed, y_values_trimmed, alpha=0.3, color='steelblue')
                
                ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.3)
                ax.set_xlabel('Feature Value', fontsize=10)
                ax.set_ylabel('Effect on Prediction', fontsize=10)
                ax.set_title(f'{feature_name}', fontsize=11, fontweight='bold')
                ax.grid(alpha=0.3)
                plots_created += 1
        
    except Exception as e:
        print(f"   Skipped feature {feature_name}: {e}")
        continue

# Hide unused subplots
for idx in range(plots_created, 6):
    axes[idx].set_visible(False)

plt.tight_layout()
shapes_plot_path = OUTPUT_DIR / "ebm_shape_functions_top6.png"
plt.savefig(shapes_plot_path, dpi=300, bbox_inches='tight')
print(f" Saved: {shapes_plot_path} ({plots_created} features plotted)")
plt.close()

# ============================================================
# Generate All Individual Plots
# ============================================================
print("\n Creating individual plots for all features...")

INDIVIDUAL_PLOTS_DIR = OUTPUT_DIR / "individual_features"
INDIVIDUAL_PLOTS_DIR.mkdir(exist_ok=True)

plots_saved = 0
for feature_idx in range(len(feature_names)):
    feature_name = feature_names[feature_idx]
    
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        
        feature_data = ebm_global.data(feature_idx)
        
        if 'names' in feature_data and 'scores' in feature_data:
            x_values = feature_data['names']
            y_values = feature_data['scores']
            
            # Ensure lengths match
            if hasattr(x_values, '__len__') and hasattr(y_values, '__len__'):
                # Handle multiclass
                if len(y_values.shape) > 1 and y_values.shape[1] > 1:
                    colors = ['#e74c3c', '#f39c12', '#2ecc71']
                    labels = ['High Risk', 'Medium Risk', 'Low Risk']
                    
                    # Match lengths
                    min_len = min(len(x_values), y_values.shape[0])
                    x_values_trimmed = x_values[:min_len]
                    
                    for class_idx in range(min(3, y_values.shape[1])):
                        y_class = y_values[:min_len, class_idx]
                        ax.plot(x_values_trimmed, y_class, linewidth=2,
                               color=colors[class_idx], label=labels[class_idx],
                               marker='o', markersize=3, alpha=0.7)
                    
                    ax.legend(loc='best')
                else:
                    # Binary - match lengths
                    min_len = min(len(x_values), len(y_values))
                    x_values_trimmed = x_values[:min_len]
                    y_values_trimmed = y_values[:min_len]
                    
                    ax.plot(x_values_trimmed, y_values_trimmed, linewidth=2, 
                           color='steelblue', marker='o', markersize=4)
                    ax.fill_between(x_values_trimmed, y_values_trimmed, alpha=0.3, color='steelblue')
                
                ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.3)
                ax.set_xlabel('Feature Value', fontsize=11, fontweight='bold')
                ax.set_ylabel('Effect on Prediction', fontsize=11, fontweight='bold')
                ax.set_title(f'Shape Function: {feature_name}', fontsize=12, fontweight='bold')
                ax.grid(alpha=0.3)
                
                plt.tight_layout()
                
                safe_name = feature_name.replace('/', '_').replace(' ', '_')
                plot_path = INDIVIDUAL_PLOTS_DIR / f"{safe_name}.png"
                plt.savefig(plot_path, dpi=200, bbox_inches='tight')
                plt.close()
                plots_saved += 1
    
    except Exception as e:
        print(f"   Skipped {feature_name}: {str(e)[:50]}")
        plt.close()
        continue

print(f" Saved {plots_saved} individual plots to: {INDIVIDUAL_PLOTS_DIR}")

# ============================================================
# Summary
# ============================================================
print("\n" + "="*60)
print(" EBM PLOT GENERATION COMPLETED")
print("="*60)
print(f"\n All plots saved to: {OUTPUT_DIR}")