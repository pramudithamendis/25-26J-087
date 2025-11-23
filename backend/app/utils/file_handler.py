import os
import re
from typing import Optional
from fastapi import UploadFile

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename(filename: str) -> str:
    """
    Simple secure filename function (replacement for werkzeug's secure_filename)
    Removes or replaces unsafe characters from filename
    """
    # Remove path separators and other unsafe characters
    filename = re.sub(r'[^\w\s-]', '', filename)
    # Replace spaces with underscores
    filename = re.sub(r'[-\s]+', '-', filename)
    # Remove leading/trailing dashes and dots
    filename = filename.strip('.-_')
    return filename

async def save_uploaded_file(
    file: UploadFile, 
    upload_folder: str, 
    candidate_id: str, 
    file_type: str = 'cv'
) -> Optional[str]:
    """
    Save uploaded file to specified folder (FastAPI version)
    
    Args:
        file: FastAPI UploadFile object
        upload_folder: Target upload folder path
        candidate_id: Candidate ID for filename prefix
        file_type: Type of file ('cv' or 'linkedin')
    
    Returns:
        str: Relative file path if successful, None otherwise
    """
    if file.filename and allowed_file(file.filename):
        # Create secure filename with candidate_id prefix
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'pdf'
        new_filename = f"{candidate_id}_{file_type}.{file_extension}"
        
        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_folder, new_filename)
        
        # Read and write file content
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Reset file pointer for potential reuse
        await file.seek(0)
        
        # Return relative path
        return file_path
    
    return None

