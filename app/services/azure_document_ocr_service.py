from __future__ import annotations

from pathlib import Path

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

from app.core.config import get_settings


def _client() -> DocumentIntelligenceClient:
    settings = get_settings()
    if not settings.azure_document_intelligence_endpoint:
        raise RuntimeError("Missing AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    if not settings.azure_document_intelligence_key:
        raise RuntimeError("Missing AZURE_DOCUMENT_INTELLIGENCE_KEY")
    return DocumentIntelligenceClient(
        endpoint=settings.azure_document_intelligence_endpoint,
        credential=AzureKeyCredential(settings.azure_document_intelligence_key),
    )


def extract_text(file_path: str) -> str:
    """OCR one local document using Azure Document Intelligence Read.

    Intended as a fallback for scanned/image-heavy files when the local parser
    extracts too little text. Returns page text with line order preserved.
    """
    path = Path(file_path)
    poller = _client().begin_analyze_document(
        "prebuilt-read",
        AnalyzeDocumentRequest(bytes_source=path.read_bytes()),
    )
    result = poller.result()

    pages: list[str] = []
    for page in result.pages or []:
        lines = [line.content for line in page.lines or [] if line.content]
        if lines:
            pages.append("\n".join(lines))
    return "\n\n".join(pages).strip()
