"""Cliente simples para acessar arquivos no Google Drive."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class DriveClient:
    """Wrapper mínimo sobre a API do Drive para listar e baixar extratos."""

    def __init__(self, root_id: str, credentials_path: Path) -> None:
        self.root_id = root_id
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
        )
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def get_nested_folder(self, names: Iterable[str]) -> str | None:
        """Retorna o ID da pasta navegando pela hierarquia fornecida."""
        current_id = self.root_id
        for name in names:
            folder_id = self._child_folder_id(current_id, name)
            if not folder_id:
                return None
            current_id = folder_id
        return current_id

    def list_files(self, folder_id: str) -> list[dict[str, str]]:
        """Lista arquivos (não pastas) dentro da pasta informada."""
        query = (
            f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' "
            "and trashed = false"
        )
        try:
            response = (
                self.service.files()
                .list(q=query, fields="files(id,name,mimeType)", pageSize=200)
                .execute()
            )
        except HttpError as exc:  # pragma: no cover - erros da API
            raise RuntimeError(f"Erro ao listar arquivos do Drive: {exc}") from exc
        return response.get("files", [])

    def download_file(self, file_id: str, destination: Path) -> Path:
        """Baixa o arquivo indicado para o caminho de destino."""
        request = self.service.files().get_media(fileId=file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return destination

    def _child_folder_id(self, parent_id: str, name: str) -> str | None:
        safe_name = name.replace("'", r"\'")
        query = (
            f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{safe_name}' and trashed = false"
        )
        response = (
            self.service.files()
            .list(q=query, fields="files(id,name)", pageSize=10)
            .execute()
        )
        files = response.get("files", [])
        return files[0]["id"] if files else None


__all__ = ["DriveClient"]
