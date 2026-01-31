import sys
from pathlib import Path

# Add project root to sys.path
file_path = Path(__file__).resolve()
root_path = file_path.parents[1]
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from server.app.config import get_settings
from server.app.utils.gerador_arquivos import localizar_arquivo
from fastapi import HTTPException

settings = get_settings()
print(f"REPORTS_DIR: {settings.reports_dir}")
print(f"Absolute REPORTS_DIR: {settings.reports_dir.resolve()}")

filename = "dados_conciliaçao_04-12-2025_08-31/conciliacao_pacote.zip"
print(f"Testing filename: {filename}")

try:
    path = localizar_arquivo(filename)
    print(f"Resolved path: {path}")
    print(f"Exists: {path.exists()}")
except HTTPException as e:
    print(f"HTTPException: {e.detail}")
except Exception as e:
    print(f"Error: {e}")
