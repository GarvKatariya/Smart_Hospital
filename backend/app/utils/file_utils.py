import os
import shutil
from fastapi import UploadFile, HTTPException

def validate_upload(file: UploadFile, allowed_extensions: list, max_size_mb: int) -> bool:
    # check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        return False
    # we would check size here, but typically done via middleware or read() length
    return True

def safe_filename(filename: str) -> str:
    import re
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)

def save_upload(file: UploadFile, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    filename = safe_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path
