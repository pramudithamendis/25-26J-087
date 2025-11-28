from fastapi import APIRouter, HTTPException
from app.services.ibm_validation_service import run_ibm_validation
import os

router = APIRouter(prefix="/validation", tags=["Model Validation"])

@router.post("/ibm-dataset")
async def validate_with_ibm():
    """
    Run IBM HR dataset validation
    
    This endpoint:
    1. Loads IBM HR Attrition dataset
    2. Maps features to match our model
    3. Trains baseline model on IBM data
    4. Tests our trained model on IBM data (transfer learning)
    5. Compares performance and generalization
    
    Note: This is a long-running operation (2-5 minutes)
    """
    
    try:
        # Check if IBM dataset exists
        from pathlib import Path
        from app.config import settings
        
        data_dir = settings.MODEL_DIR.parent / "data"
        ibm_path = data_dir / "ibm_hr.csv"
        
        if not ibm_path.exists():
            return {
                "status": "dataset_missing",
                "message": "IBM HR dataset not found",
                "instructions": [
                    "Download from: https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset",
                    f"Place at: {ibm_path}"
                ]
            }
        
        # Run validation
        results = await run_ibm_validation()
        
        return {
            "status": "success",
            "validation_results": results
        }
        
    except Exception as e:
        raise HTTPException(500, f"IBM validation failed: {str(e)}")

@router.get("/results")
async def get_validation_results():
    """Retrieve latest IBM validation results"""
    from pathlib import Path
    from app.config import settings
    import json
    
    results_dir = settings.MODEL_DIR.parent / "results" / "artifacts" / "ibm_validation"
    summary_file = results_dir / "ibm_validation_summary.json"
    
    if not summary_file.exists():
        raise HTTPException(404, "No validation results found. Run /validation/ibm-dataset first.")
    
    with open(summary_file, 'r') as f:
        results = json.load(f)
    
    return {
        "status": "success",
        "results": results,
        "artifacts": {
            "summary": str(summary_file),
            "confusion_matrices": [
                "ibm_baseline_cm.png",
                "trained_model_ibm_cm.png",
                "ibm_comparison.png"
            ]
        }
    }