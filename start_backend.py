#!/usr/bin/env python3
"""
Quick start script for the backend server
Adds the venv packages to path and starts uvicorn
"""
import sys
import os

# Add the venv site-packages to the path
venv_packages = '/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system/backend/venv/lib/python3.14/site-packages'
backend_dir = '/Users/garvkatariya/.gemini/antigravity/scratch/smart-hospital-management-system/backend'

sys.path.insert(0, venv_packages)
sys.path.insert(0, backend_dir)

# Change to backend directory
os.chdir(backend_dir)

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
