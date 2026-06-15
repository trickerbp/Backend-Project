"""Vendored Core Engine from document-processing-api.

``document_processing_model.py`` is copied byte-for-byte from
document-processing-api/backend/models/. Do not edit it here; regenerate it in
that project's notebook and re-copy. Use ``core_extractor`` (sibling module) for
the backend-facing adapter rather than importing this artifact directly.
"""
from __future__ import annotations

from app.services.matching.core_engine.document_processing_model import (
    DocumentParser,
    ParserConfig,
)


__all__ = ["DocumentParser", "ParserConfig"]
