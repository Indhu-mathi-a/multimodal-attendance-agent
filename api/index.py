import os
import sys
from pathlib import Path

# Add project root to sys.path so app and relative imports work on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app

# Vercel looks for the WSGI/ASGI 'app' object
if __name__ == "__main__":
    app.run()
