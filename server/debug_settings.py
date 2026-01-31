import sys
from pathlib import Path

# Add project root to sys.path
file_path = Path(__file__).resolve()
root_path = file_path.parents[1]
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from server.app.config import get_settings

settings = get_settings()
print(f"REPORTS_DIR: {settings.reports_dir}")
print(f"Resolved REPORTS_DIR: {settings.reports_dir.resolve() if settings.reports_dir else 'None'}")
print(f"Exists: {settings.reports_dir.exists() if settings.reports_dir else 'False'}")
