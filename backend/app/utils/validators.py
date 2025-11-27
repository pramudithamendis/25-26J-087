from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

def validate_file_upload(filename: str, allowed_extensions: List[str] = None) -> Optional[Dict]:
    """
    Validate uploaded file (utility function for additional checks)
    
    Note: Most validation is handled by Pydantic schemas. This function
    is kept for additional file validation checks if needed.
    
    Args:
        filename: Name of uploaded file
        allowed_extensions: List of allowed extensions (default: ['pdf'])
    
    Returns:
        None if valid, dict with errors if invalid
    """
    if allowed_extensions is None:
        allowed_extensions = ['pdf']
    
    errors = []
    
    if not filename:
        errors.append("Filename is required")
    elif '.' not in filename:
        errors.append("File must have an extension")
    else:
        extension = filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            errors.append(f"File extension '{extension}' not allowed. Allowed extensions: {', '.join(allowed_extensions)}")
    
    if errors:
        logger.warning(f"Validation errors for file upload: {errors}")
        return {"errors": errors}
    
    return None

