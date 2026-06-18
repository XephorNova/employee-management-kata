from __future__ import annotations
from pathlib import Path
import chromadb

_CHROMA_DIR = Path(__file__).parent.parent.parent / "chroma_data"
_client: chromadb.PersistentClient | None = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _CHROMA_DIR.mkdir(exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    return _client
