"""Carrega e normaliza o relatório SETA diretamente do PostgreSQL (RF001.2 + RF004-RF007)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
import unicodedata
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from zoneinfo import ZoneInfo

from server.app.db import get_session

# Select utilizado feito no banco de dados do SETA para ingestão de dados para conciliar com os extratos.

SETA_QUERY = """
SELECT 
    b.banco,
    vc.auxiliar,
    vc.codigo,
    b.conta,
    vc.data,
    vc.descricao,
    b.descricao AS descricao1,
    vc.documento,
    vc.empresa,
    vc.item,
    vc.itemx,
    vc.parcela,
    vc.lote,
    vc.pessoa,
    vc.pessoax,
    vc.rp,
    vc.valor
FROM vContas vc
INNER JOIN financeiro_contas b ON vc.conta = b.codigo
WHERE vc.data BETWEEN :data_inicio AND :data_fim
  AND (b.conta IS NOT NULL AND TRIM(b.conta) <> '')
  AND b.banco <> '116'
ORDER BY vc.data;
"""

_ZONE = ZoneInfo("America/Sao_Paulo")
_STRUCTURE_ORDER = [
    "banco",
    "auxiliar",
    "codigo",
    "conta",
    "data",
    "descricao",
    "descricao1",
    "documento",
    "empresa",
    "item",
    "itemx",
    "parcela",
    "lote",
    "pessoa",
    "pessoax",
    "rp",
    "valor",
    "origem_arquivo",
]
_ORIGEM_ARQUIVO = "SETA (BANCO DE DADOS)"


def buscar_despesas_seta(data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Executa a query SETA, aplica as regras RF004‑RF007 e retorna um DataFrame normalizado.
    O filtro de contas foi removido, trazendo todas as contas com dados bancários válidos (não nulos/vazios).
    """
    if data_fim < data_inicio:
        raise ValueError("data_fim deve ser maior ou igual a data_inicio")

    # Executa a query
    with get_session() as session:
        params = {"data_inicio": data_inicio, "data_fim": data_fim}
        resultado = session.execute(text(SETA_QUERY), params)
        colunas = resultado.keys()
        registros = [dict(zip(colunas, linha)) for linha in resultado.fetchall()]

    linhas_normalizadas = [_normalizar_linha(registro) for registro in registros]
    return pd.DataFrame(linhas_normalizadas, columns=_STRUCTURE_ORDER)

import time
from sqlalchemy.exc import OperationalError
from loguru import logger

def _executar_query(data_inicio: date, data_fim: date) -> list[dict[str, Any]]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with get_session() as session:
                resultado = session.execute(
                    text(SETA_QUERY),
                    {"data_inicio": data_inicio, "data_fim": data_fim},
                )
                colunas = resultado.keys()
                return [dict(zip(colunas, linha)) for linha in resultado.fetchall()]
        except OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = 1 * (attempt + 1)
                logger.warning(f"Erro de conexão com banco de dados (tentativa {attempt + 1}/{max_retries}). Retentando em {wait_time}s... Erro: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Falha na conexão com banco de dados após {max_retries} tentativas.")
                raise e
    return []


def _normalizar_linha(row: dict[str, Any]) -> dict[str, Any]:
    # Mantém a lógica de sanitização de conta para consistência
    raw_conta = _get(row, "conta")
    # Fix específico para conta vindo cortada do banco
    if str(raw_conta).strip() == "577864104-":
        raw_conta = "577864104-0"
    elif str(raw_conta).strip() == "110105-6":
        raw_conta = "110105-5"
        
    # conta_bancaria = _sanitizar_conta(raw_conta) # REMOVIDO: Usar valor original tratada acima
    
    return {
        "banco": _normalizar_texto(_get(row, "banco")),
        "auxiliar": _normalizar_texto(_get(row, "auxiliar")),
        "codigo": _get(row, "codigo"), # Manter original ou texto? Conciliação xlsx parece ter numeros/texto misto.
        "conta": raw_conta, # Manter original (com correção se aplicado)
        "data": _normalizar_data(_get(row, "data")),
        "descricao": _normalizar_texto(_get(row, "descricao")),
        "descricao1": _normalizar_texto(_get(row, "descricao1")),
        "documento": _normalizar_texto(_get(row, "documento")),
        "empresa": _normalizar_texto(_get(row, "empresa")),
        "item": _normalizar_texto(_get(row, "item")),
        "itemx": _normalizar_texto(_get(row, "itemx")),
        "parcela": _get(row, "parcela"),
        "lote": _get(row, "lote"),
        "pessoa": _normalizar_texto(_get(row, "pessoa")),
        "pessoax": _normalizar_texto(_get(row, "pessoax")),
        "rp": _normalizar_texto(_get(row, "rp")),
        "valor": _normalizar_valor(_get(row, "valor")),
        "origem_arquivo": _ORIGEM_ARQUIVO,
    }


def _normalizar_data(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, date):
        dt = datetime.combine(valor, datetime.min.time())
    elif isinstance(valor, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(valor, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_ZONE)
    else:
        dt = dt.astimezone(_ZONE)
    return dt.date().isoformat()


def _normalizar_valor(valor: Any) -> Decimal:
    quantidade = _coagir_decimal(valor)
    return quantidade.quantize(Decimal("0.01"))


def _coagir_decimal(valor: Any) -> Decimal:
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    if isinstance(valor, str):
        bruto = valor.replace(".", "").replace(",", ".")
        try:
            return Decimal(bruto)
        except InvalidOperation:
            return Decimal("0")
    return Decimal("0")


def _normalizar_texto(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    texto = str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = " ".join(texto.split())
    return texto.upper()


def _sanitizar_conta(valor: Any) -> str | None:
    texto = _normalizar_texto(valor)
    if not texto:
        return None
    digits = re.sub(r"\D", "", texto)
    return digits or None


def _get(row: dict[str, Any], chave: str) -> Any:
    """Obtém um valor independentemente de caixa."""
    if chave in row:
        return row[chave]
    chave_lower = chave.lower()
    for key, value in row.items():
        if key.lower() == chave_lower:
            return value
    return None


__all__ = ["buscar_despesas_seta"]
