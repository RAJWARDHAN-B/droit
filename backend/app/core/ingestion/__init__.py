"""Document ingestion services."""

from .loader import SUPPORTED_EXTENSIONS, load_document
from .metadata_extractor import extract_document_metadata

__all__ = ["SUPPORTED_EXTENSIONS", "extract_document_metadata", "load_document"]