import requests
import os
from pathlib import Path
from tqdm import tqdm

def download_file_from_google_drive(file_id: str, destination: Path):
    """
    Download a file from Google Drive
    
    Args:
        file_id: Google Drive file ID (from shareable link)
        destination: Local path to save the file
    """
    
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768
        
        # Get total file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, "wb") as f:
            if total_size > 0:
                # Show progress bar
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=destination.name) as pbar:
                    for chunk in response.iter_content(CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                # No size info, just download
                print(f"   Downloading {destination.name}...")
                for chunk in response.iter_content(CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

    URL = "https://docs.google.com/uc?export=download"
    
    session = requests.Session()
    response = session.get(URL, params={'id': file_id}, stream=True)
    token = get_confirm_token(response)

    if token:
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


def ensure_model_files():
    """
    Ensure all required model files are present.
    Downloads from Google Drive if missing.
    """
    
    from app.config import settings
    
    model_dir = settings.MODEL_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    
    MODEL_FILES = {
        "ensemble_soft_weighted_calibrated.joblib": {
            "file_id": "1WixQvXwb0Xv-wgKHAkgfLwIuI3BxOLWW",  
            "size_mb": 138,
            "description": "Calibrated Weighted Ensemble Model"
        }
    }
    
    print("\n Checking model files...")
    
    for filename, info in MODEL_FILES.items():
        model_path = model_dir / filename
        
        # Check if file exists and has reasonable size
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            if size_mb > 0.1:  # File exists and is not empty
                print(f"    {filename} already exists ({size_mb:.1f} MB)")
                continue
        
        # File missing or corrupted - download it
        print(f"\n Downloading {filename} from Google Drive...")
        print(f"   Description: {info['description']}")
        print(f"   Expected size: ~{info['size_mb']} MB")
        
        try:
            download_file_from_google_drive(info['file_id'], model_path)
            
            # Verify download
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                print(f"    Download complete: {size_mb:.1f} MB")
            else:
                print(f"    Download failed for {filename}")
                
        except Exception as e:
            print(f"   Error downloading {filename}: {e}")
            print(f"   Please manually download from Google Drive and place in {model_dir}")
    
    print("\n Model file check complete\n")


# Alternative: Simpler version with direct download (if files are public)
def download_from_direct_link(url: str, destination: Path):
    """
    Download from a direct download link (like Dropbox, OneDrive, etc.)
    """
    print(f" Downloading {destination.name}...")
    
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(destination, 'wb') as f:
        if total_size > 0:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=destination.name) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        else:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    
    print(f" Download complete: {destination.name}")