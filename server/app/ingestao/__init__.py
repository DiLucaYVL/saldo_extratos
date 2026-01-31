"""Modulos da fase 2 (ingestao de extratos)."""
from .file_locator import StatementLocator
from .file_parsers import StatementParserRegistry
from .normalizer import NormalizationService

__all__ = [
    "StatementLocator",
    "StatementParserRegistry",
    "NormalizationService",
]
