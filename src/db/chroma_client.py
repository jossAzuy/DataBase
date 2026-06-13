import chromadb
from chromadb.api.models.Collection import Collection

from src.config import settings


chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_chroma_collection() -> Collection:
    return chroma_client.get_or_create_collection(name=settings.chroma_collection)
