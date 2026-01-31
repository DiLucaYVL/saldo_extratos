import os
import uvicorn
import sys
from pathlib import Path

# Add project root to sys.path
file_path = Path(__file__).resolve()
root_path = file_path.parents[1]
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

os.environ["API_PORT"] = "55001"
# We need to make sure we use the same database settings etc, which are loaded from .env
# Uvicorn will load .env if we don't override everything.
# But we want to override port.

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=55001,
        reload=False,
    )
