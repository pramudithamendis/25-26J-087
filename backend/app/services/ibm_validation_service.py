import asyncio
from pathlib import Path
from app.config import settings

async def run_ibm_validation():
    """
    Run IBM validation asynchronously
    Calls IBM validation script
    """
    
    # Path to IBM validation notebook/script
    validation_script = settings.MODEL_DIR.parent / "notebooks" / "08_ibm_validation.py"
    
    if not validation_script.exists():
        raise FileNotFoundError(f"IBM validation script not found: {validation_script}")
    
    # Run script asynchronously
    process = await asyncio.create_subprocess_exec(
        'python', str(validation_script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        raise RuntimeError(f"IBM validation failed: {error_msg}")
    
    # Read results
    results_dir = settings.MODEL_DIR.parent / "results" / "artifacts" / "ibm_validation"
    summary_file = results_dir / "ibm_validation_summary.json"
    
    if summary_file.exists():
        import json
        with open(summary_file, 'r') as f:
            return json.load(f)
    else:
        return {
            "status": "completed",
            "message": "Validation ran but no summary file generated",
            "output": stdout.decode()
        }