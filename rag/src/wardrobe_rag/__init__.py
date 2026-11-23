"""Standalone wardrobe retrieval package for the AI Lookbook project."""

from .config import RAGConfig
from .constraints import assemble_outfit, validate_selection
from .retrieval import RetrievalEngine
from .schemas import (
    Candidate, QueryContext, RetrievalRequest, RetrievalResult, SelectionValidation, SlotSearchRequest, SlotSearchResult,
    SyncResult, VectorHit, WardrobeItem, WeatherAttributes,
)
from .service import RAGService

__all__ = [
    "Candidate", "QueryContext", "RAGConfig", "RAGService", "RetrievalEngine",
    "RetrievalRequest", "RetrievalResult", "SelectionValidation", "SyncResult",
    "SlotSearchRequest", "SlotSearchResult",
    "VectorHit", "WardrobeItem", "WeatherAttributes", "assemble_outfit", "validate_selection",
]
