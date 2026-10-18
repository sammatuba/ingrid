"""R0 exact native UTF-8 text segmentation; no semantic or legal inference."""
from .structure import (
    PARSER_REVISION, DateMetadata, Diagnostic, DocumentStructure, Locator,
    Source, Span, StructureError, parse, validate_locator,
)

__all__ = [
    'PARSER_REVISION', 'DateMetadata', 'Diagnostic', 'DocumentStructure',
    'Locator', 'Source', 'Span', 'StructureError', 'parse', 'validate_locator',
]
