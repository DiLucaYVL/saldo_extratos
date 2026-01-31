"""RF004-RF007 - Normalizacao dos dados ingeridos."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from rapidfuzz import fuzz


class NormalizationService:
    """Aplica as regras de normalizacao sobre extratos e SETA."""

    def normalize_statements(self, raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalizados: list[dict[str, Any]] = []
        for row in raw_rows:
            normalizados.append(
                {
                    "banco": row.get("banco"),
                    "data": self._parse_date(row.get("data")),
                    "historico": self._clean_text(row.get("historico")),
                    "documento": self._clean_text(row.get("documento")),
                    "valor": self._parse_decimal(row.get("valor")),
                    "origem": row.get("origem"),
                    "origem_drive": row.get("origem_drive"),  # Preserva caminho Drive
                    "arquivo_drive": row.get("arquivo_drive"),  # Preserva caminho Drive alternativo
                    "origem_arquivo": row.get("origem_arquivo"),  # Preserva origem do arquivo
                    "conta": row.get("conta"),  # Preserva conta
                    "agencia": row.get("agencia"),  # Preserva agência
                }
            )
        return normalizados

    def normalize_seta(self, raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalizados: list[dict[str, Any]] = []
        for row in raw_rows:
            normalizados.append(
                {
                    "codigo": row.get("Codigo") or row.get("codigo"),
                    "conta": row.get("Conta") or row.get("conta"),
                    "descricao": self._clean_text(row.get("Descricao") or row.get("descricao")),
                    "pagamento": self._parse_date(row.get("Pagamento") or row.get("pagamento")),
                    "valor": self._parse_decimal(row.get("Valor") or row.get("valor")),
                    "tipo": row.get("Tipo") or row.get("tipo"),
                }
            )
        return normalizados

    @staticmethod
    def _parse_date(valor: Any) -> date | None:
        if valor in (None, ""):
            return None
        if isinstance(valor, date):
            return valor
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, str):
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(valor, fmt).date()
                except ValueError:
                    continue
        if isinstance(valor, (int, float)):
            base = datetime(1899, 12, 30)
            return (base + timedelta(days=int(valor))).date()
        return None

    @staticmethod
    def _parse_decimal(valor: Any) -> Decimal:
        if isinstance(valor, Decimal):
            return valor
        if isinstance(valor, (int, float)):
            return Decimal(str(valor))
        if isinstance(valor, str):
            cleaned = valor.replace(".", "").replace(",", ".")
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                return Decimal("0")
        return Decimal("0")

    @staticmethod
    def _clean_text(valor: Any) -> str:
        return str(valor or "").strip()

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Auxiliar usado nas fases fuzzy do motor."""
        return float(fuzz.token_sort_ratio(a or "", b or ""))
