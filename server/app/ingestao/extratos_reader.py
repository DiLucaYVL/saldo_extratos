"""Leitura consolidada de extratos bancarios (RF001.3 + RF002 + RF004-RF007)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from pathlib import Path
from typing import Any, Iterable
import unicodedata

import pandas as pd
import pdfplumber
from zoneinfo import ZoneInfo

from server.app.ingestao.file_locator import StatementLocator

_ZONE = ZoneInfo("America/Sao_Paulo")
_STRUCTURE_ORDER = [
    "data",
    "valor",
    "historico",
    "descricao",
    "documento_id",
    "banco",
    "agencia",
    "conta",
    "plano_contas_codigo",
    "origem_arquivo",
]
_ORIGEM_PADRAO = "EXTRATO BANCARIO"
_AGENCIA_RE = re.compile(r"ag(?:encia)?\D*(\d{3,5})", re.IGNORECASE)
_CONTA_RE = re.compile(r"conta?\D*(\d{4,12})", re.IGNORECASE)


def carregar_extratos_por_periodo(base: str | Path, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Localiza todos os arquivos elegiveis e devolve um DataFrame normalizado."""
    locator = StatementLocator(Path(base))
    arquivos = locator.locate(data_inicio, data_fim)
    linhas: list[dict[str, Any]] = []
    for arquivo in arquivos:
        nome = arquivo.name.lower()
        if "bradesco" in nome:
            linhas.extend(ler_extrato_bradesco(arquivo))
        elif "santander" in nome:
            linhas.extend(ler_extrato_santander(arquivo))
        elif "caixa" in nome:
            linhas.extend(ler_extrato_caixa_pdf(arquivo))
    return pd.DataFrame(linhas, columns=_STRUCTURE_ORDER)


def ler_extrato_bradesco(caminho: Path | str) -> list[dict[str, Any]]:
    caminho = Path(caminho)
    df = _read_excel_file(caminho)
    df.columns = [_simplificar_nome(col) for col in df.columns]

    data_col = _pick_column(df.columns, ["data", "data_lancamento"])
    hist_col = _pick_column(df.columns, ["historico", "descricao"])
    doc_col = _pick_column(df.columns, ["documento", "n_documento"])
    credito_col = _pick_column(df.columns, ["credito_r", "credito", "valor_credito"])
    debito_col = _pick_column(df.columns, ["debito_r", "debito", "valor_debito"])
    valor_col = _pick_column(df.columns, ["valor"])

    agencia, conta = _extrair_agencia_conta(caminho)
    linhas: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        raw_data = row.get(data_col)
        raw_hist = row.get(hist_col)
        raw_doc = row.get(doc_col)

        if pd.isna(raw_data) or pd.isna(raw_hist):
            continue

        valor = Decimal("0")
        credito = row.get(credito_col) if credito_col else None
        debito = row.get(debito_col) if debito_col else None
        if credito not in (None, "", 0) and not pd.isna(credito):
            valor = _normalizar_valor(credito, positivo=True)
        elif debito not in (None, "", 0) and not pd.isna(debito):
            valor = _normalizar_valor(debito, positivo=False)
        elif valor_col:
            valor = _normalizar_valor(row.get(valor_col))

        linhas.append(
            _build_linha(
                banco="BRADESCO",
                data=raw_data,
                valor=valor,
                historico=raw_hist,
                documento=raw_doc,
                agencia=agencia,
                conta=conta,
                origem=caminho,
            )
        )
    return linhas


def ler_extrato_santander(caminho: Path | str) -> list[dict[str, Any]]:
    caminho = Path(caminho)
    df = _read_excel_file(caminho)
    df.columns = [_simplificar_nome(col) for col in df.columns]

    data_col = _pick_column(df.columns, ["data", "data_movimento"])
    hist_col = _pick_column(df.columns, ["historico", "descricao", "lancamento"])
    doc_col = _pick_column(df.columns, ["documento", "num_documento"])
    valor_col = _pick_column(df.columns, ["valor", "valor_lancamento"])
    tipo_col = _pick_column(df.columns, ["tipo", "debito_credito"])

    agencia, conta = _extrair_agencia_conta(caminho)
    linhas: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        raw_data = row.get(data_col)
        raw_hist = row.get(hist_col)
        raw_doc = row.get(doc_col)
        if pd.isna(raw_data) or pd.isna(raw_hist):
            continue
        valor = row.get(valor_col)
        is_credito = False
        if tipo_col:
            tipo = str(row.get(tipo_col) or "").strip().upper()
            is_credito = tipo.startswith("C")
        linhas.append(
            _build_linha(
                banco="SANTANDER",
                data=raw_data,
                valor=_normalizar_valor(valor, positivo=is_credito),
                historico=raw_hist,
                documento=raw_doc,
                agencia=agencia,
                conta=conta,
                origem=caminho,
            )
        )
    return linhas


def ler_extrato_caixa_pdf(caminho: Path | str) -> list[dict[str, Any]]:
    caminho = Path(caminho)
    agencia, conta = _extrair_agencia_conta(caminho)
    linhas: list[dict[str, Any]] = []

    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            tabela = page.extract_table()
            if not tabela or len(tabela) < 2:
                continue
            header = [_simplificar_nome(col) for col in tabela[0]]
            data_idx = _index_column(header, ["data"])
            hist_idx = _index_column(header, ["historico", "descricao"])
            doc_idx = _index_column(header, ["documento"])
            valor_idx = _index_column(header, ["valor"])

            for raw in tabela[1:]:
                if not raw or data_idx is None or valor_idx is None:
                    continue
                raw_data = raw[data_idx]
                raw_hist = raw[hist_idx] if hist_idx is not None else ""
                raw_doc = raw[doc_idx] if doc_idx is not None else ""
                raw_valor = raw[valor_idx]
                if not raw_data or not raw_valor:
                    continue
                linhas.append(
                    _build_linha(
                        banco="CAIXA",
                        data=raw_data,
                        valor=_normalizar_valor(raw_valor),
                        historico=raw_hist,
                        documento=raw_doc,
                        agencia=agencia,
                        conta=conta,
                        origem=caminho,
                    )
                )
    return linhas


def _build_linha(
    *,
    banco: str,
    data: Any,
    valor: Decimal,
    historico: Any,
    documento: Any,
    agencia: str | None,
    conta: str | None,
    origem: Path,
) -> dict[str, Any]:
    return {
        "data": _normalizar_data(data),
        "valor": valor,
        "historico": _normalizar_texto(historico),
        "descricao": None,
        "documento_id": _normalizar_texto(documento),
        "banco": banco,
        "agencia": agencia,
        "conta": conta,
        "plano_contas_codigo": None,
        "origem_arquivo": str(origem),
    }


def _normalizar_data(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, date):
        dt = datetime.combine(valor, datetime.min.time())
    elif isinstance(valor, (int, float)):
        # Excel serial
        base = datetime(1899, 12, 30)
        dt = base + pd.to_timedelta(valor, unit="D")
        dt = datetime.combine(dt.date(), datetime.min.time())
    else:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(valor), fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_ZONE)
    else:
        dt = dt.astimezone(_ZONE)
    return dt.date().isoformat()


def _normalizar_valor(valor: Any, *, positivo: bool | None = None) -> Decimal:
    decimal_val = _coagir_decimal(valor)
    if positivo is True:
        decimal_val = abs(decimal_val)
    elif positivo is False:
        decimal_val = -abs(decimal_val)
    return decimal_val.quantize(Decimal("0.01"))


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
    if pd.isna(valor):
        return Decimal("0")
    return Decimal(str(valor))


def _normalizar_texto(valor: Any) -> str | None:
    if valor in (None, "") or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = " ".join(texto.split())
    texto = texto.upper()
    return texto or None


def _simplificar_nome(nome: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_")
    return texto.lower()


def _pick_column(columns: Iterable[str], candidatos: list[str]) -> str | None:
    columns = list(columns)
    for candidato in candidatos:
        if candidato in columns:
            return candidato
    for candidato in candidatos:
        for col in columns:
            if candidato in col:
                return col
    return None


def _index_column(header: list[str], candidatos: list[str]) -> int | None:
    candidato = _pick_column(header, candidatos)
    if candidato and candidato in header:
        return header.index(candidato)
    return None


def _extrair_agencia_conta(path: Path | str) -> tuple[str | None, str | None]:
    texto = str(path)
    agencia = _buscar_regex(_AGENCIA_RE, texto)
    conta = _buscar_regex(_CONTA_RE, texto)
    if not conta:
        conta = _extrair_conta_por_nome(Path(texto).name)
    return agencia, conta


def _extrair_conta_por_nome(nome_arquivo: str) -> str | None:
    """Extrai conta a partir do trecho final do nome do arquivo conforme regra definida."""
    if not nome_arquivo:
        return None
    parte_final = Path(nome_arquivo).stem.rsplit("_", 1)[-1]
    digitos = re.sub(r"\D", "", parte_final)
    return digitos or None


def _buscar_regex(pattern: re.Pattern[str], texto: str) -> str | None:
    match = pattern.search(texto)
    return match.group(1) if match else None


def _read_excel_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    engine = "openpyxl"
    if suffix == ".xls":
        engine = "xlrd"
    return pd.read_excel(path, engine=engine)


__all__ = [
    "carregar_extratos_por_periodo",
    "ler_extrato_bradesco",
    "ler_extrato_santander",
    "ler_extrato_caixa_pdf",
]
