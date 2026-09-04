import os
import sys
from pathlib import Path

# Add src to sys.path
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print("\n" + "=" * 60)
    print("  AI-Driven ITI Employability System is running!")
    print(f"  Access Web Application : http://localhost:{port}")
    print(f"  API Documentation      : http://localhost:{port}/docs")
    print("=" * 60 + "\n")

    uvicorn.run("api:app", host=host, port=port)
