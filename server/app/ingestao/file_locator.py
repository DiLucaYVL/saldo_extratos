"""
RF001.3 - Dynamic statement locator.
Maps requested periods to physical files in the filesystem or Google Drive.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import tempfile
import logging

import re
from .drive_client import DriveClient

logger = logging.getLogger(__name__)


class StatementLocator:
    """Responsavel por mapear o periodo solicitado para arquivos fisicos."""

    # Adicionado "Caixa" e "BB" na lista de suportados
    SUPPORTED_BANKS = ("Santander", "Caixa", "BB", "Bradesco")
    ALLOWED_EXTENSIONS = (".pdf",)

    # Configuracao especifica para buscar apenas .pdf na pasta da Caixa e BB
    BANK_EXTENSIONS = {
        "Santander": (".pdf",),
        "Bradesco": (".pdf",),
        "Caixa": (".pdf",),
        "BB": (".pdf",),
    }

    def __init__(
        self,
        root_dir: Path | None = None,
        bancos: tuple[str, ...] | None = None,
        drive_client: DriveClient | None = None,
    ) -> None:
        self.root_dir = Path(root_dir) if root_dir else Path("dados") / "extratos"
        self.bancos = bancos or self.SUPPORTED_BANKS
        self.drive_client = drive_client
        self._temp_files: list[Path] = []
        self._drive_map: dict[Path, str] = {}

    def locate(self, data_inicio: date, data_fim: date, existing_accounts: set[tuple[str, str]] | None = None) -> list[Path]:
        """Percorre a estrutura do Google Drive local e encontra os arquivos validos."""
        # Se houver cliente do Drive configurado, usa a busca no Drive
        if self.drive_client is not None:
            return self._locate_drive(data_inicio, data_fim, existing_accounts)

        # Busca no sistema de arquivos local
        if not self.root_dir.exists():
            return []

        arquivos: list[Path] = []
        dia = data_inicio

        # Itera dia a dia para montar o caminho Banco/MM-AAAA/DD-MM
        while dia <= data_fim:
            mes_dir = dia.strftime("%m-%Y")  # MM-AAAA
            dia_dir = dia.strftime("%d-%m")  # DD-MM

            for banco in self.bancos:
                # Monta o caminho: root/Caixa/11-2025/14-11
                candidatos = self._coletar_arquivos(
                    self.root_dir / banco / mes_dir / dia_dir,
                    banco,
                )
                
                # Filter local files if needed (though user emphasized Drive download skipping)
                if existing_accounts:
                    filtered_candidates = []
                    for f in candidatos:
                         account = self._extract_account_from_filename(f.name)
                         if (banco, account) in existing_accounts:
                             logger.debug(f"Skipping local file {f.name} (Account {account} already processed)")
                             continue
                         filtered_candidates.append(f)
                    candidatos = filtered_candidates
                    
                arquivos.extend(candidatos)
            dia += timedelta(days=1)

        # Remove duplicidades preservando ordem
        vistos: set[str] = set()
        resultado: list[Path] = []
        for caminho in arquivos:
            chave = str(caminho.resolve())
            if chave in vistos:
                continue
            vistos.add(chave)
            resultado.append(caminho)
        return sorted(resultado)

    def _coletar_arquivos(self, pasta: Path, banco: str) -> list[Path]:
        """Coleta arquivos suportados dentro da pasta informada."""
        if not pasta.exists() or not pasta.is_dir():
            return []

        # Obtem extensoes validas para o banco (ex: Caixa -> .pdf)
        extensoes = self.BANK_EXTENSIONS.get(banco, self.ALLOWED_EXTENSIONS)

        arquivos: list[Path] = []
        for arquivo in pasta.iterdir():
            if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
                arquivos.append(arquivo)
        return arquivos

    def _locate_drive(self, data_inicio: date, data_fim: date, existing_accounts: set[tuple[str, str]] | None = None) -> list[Path]:
        if not self.drive_client:
            return []
        arquivos: list[Path] = []
        dia = data_inicio
        while dia <= data_fim:
            mes_dir = dia.strftime("%m-%Y")
            dia_dir = dia.strftime("%d-%m")
            for banco in self.bancos:
                # Busca pasta analoga no Drive
                folder_id = self.drive_client.get_nested_folder([banco, mes_dir, dia_dir])
                if not folder_id:
                    continue
                for arquivo in self.drive_client.list_files(folder_id):
                    nome = arquivo["name"]
                    if not self._arquivo_aceitavel(nome, banco):
                        continue
                    
                    # Check if account already processed
                    if existing_accounts:
                        account = self._extract_account_from_filename(nome)
                        if (banco, account) in existing_accounts:
                            logger.info(f"Skipping download of {nome} (Account {account} already processed for this date)")
                            continue
                    
                    drive_path = Path(banco) / mes_dir / dia_dir / nome
                    destino = self._criar_destino_temp(drive_path, arquivo["id"])
                    self.drive_client.download_file(arquivo["id"], destino)
                    self._temp_files.append(destino)
                    resolved = destino.resolve()
                    self._drive_map[resolved] = drive_path.as_posix()
                    arquivos.append(destino)
            dia += timedelta(days=1)
        return arquivos

    def _extract_account_from_filename(self, filename: str) -> str:
        """Extract account digits from filename."""
        # Simple extraction based on typical pattern: ..._12345-X.pdf
        # Remove extension
        stem = Path(filename).stem
        match = re.search(r"_([A-Za-z0-9-]+)$", stem)
        if match:
             return match.group(1)
        return stem.split("_")[-1]

    def cleanup(self) -> None:
        """Remove arquivos temporarios baixados do Drive."""
        for caminho in self._temp_files:
            try:
                caminho.unlink(missing_ok=True)
                parent = caminho.parent
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                continue
        self._temp_files.clear()
        self._drive_map.clear()

    def _arquivo_aceitavel(self, nome: str, banco: str) -> bool:
        extensoes = self.BANK_EXTENSIONS.get(banco, self.ALLOWED_EXTENSIONS)
        return any(nome.lower().endswith(ext) for ext in extensoes)

    @staticmethod
    def _criar_destino_temp(relative_path: str | Path | None, file_id: str) -> Path:
        base = Path(tempfile.mkdtemp(prefix="drive_extrato_"))
        rel = Path(relative_path) if relative_path else Path(file_id)
        destino = base / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        return destino

    def resolve_drive_path(self, local_path: str | Path | None) -> str | None:
        if not local_path:
            return None
        caminho = Path(local_path)
        resolved = caminho.resolve()
        return self._drive_map.get(resolved) or self._drive_map.get(caminho)
