"""Document ingestion services."""

from .loader import SUPPORTED_EXTENSIONS, load_document

__all__ = ["SUPPORTED_EXTENSIONS", "load_document"]