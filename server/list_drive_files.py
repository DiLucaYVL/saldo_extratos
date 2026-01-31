"""Lista todos os arquivos encontrados via DRIVE_ROOT_ID/banco/mes/dia."""
from datetime import date

from server.app.config import get_settings
from server.app.ingestao.file_locator import StatementLocator
from server.app.ingestao.drive_client import DriveClient

settings = get_settings()
if not settings.drive_root_id or not settings.drive_credentials_path:
    raise SystemExit("Configure DRIVE_ROOT_ID e DRIVE_SA_CREDENTIALS_PATH no .env")

client = DriveClient(settings.drive_root_id, settings.resolved_drive_credentials_path)
locator = StatementLocator(drive_client=client)

inicio = date(2025, 11, 13)
fim = date(2025, 11, 13)

arquivos = locator.locate(inicio, fim)
print(f"Arquivos encontrados entre {inicio} e {fim}: {len(arquivos)}")
for caminho in arquivos:
    print("-", caminho)
locator.cleanup()
