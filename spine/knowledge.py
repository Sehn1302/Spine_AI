"""Local knowledge base — ingest files and retrieve context via RAG."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ollama
from chromadb import Documents, EmbeddingFunction, Embeddings, PersistentClient

SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".yaml", ".yml"}


class OllamaEmbedder(EmbeddingFunction[Documents]):
    def __init__(self, model: str) -> None:
        self.model = model

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: Embeddings = []
        for text in input:
            response = ollama.embed(model=self.model, input=text)
            embeddings.append(response["embeddings"][0])
        return embeddings


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


class KnowledgeBase:
    def __init__(
        self,
        knowledge_dir: str,
        chroma_dir: str,
        embed_model: str,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        top_k: int = 4,
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir = Path(chroma_dir)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.embed_model = embed_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

        self.manifest_path = self.chroma_dir / "manifest.json"
        self.manifest = self._load_manifest()

        self._client = PersistentClient(path=str(self.chroma_dir))
        self._collection = self._client.get_or_create_collection(
            name="spine_knowledge",
            embedding_function=OllamaEmbedder(embed_model),
            metadata={"hnsw:space": "cosine"},
        )

    def _load_manifest(self) -> dict[str, str]:
        if not self.manifest_path.exists():
            return {}
        try:
            with self.manifest_path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_manifest(self) -> None:
        with self.manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(self.manifest, handle, indent=2)

    def _file_hash(self, path: Path) -> str:
        stat = path.stat()
        payload = f"{path.resolve()}|{stat.st_mtime}|{stat.st_size}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def _read_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    def _discover_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.knowledge_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                if path.name.startswith("."):
                    continue
                files.append(path)
        return sorted(files)

    def _chunk_id(self, source: str, index: int) -> str:
        digest = hashlib.sha256(f"{source}:{index}".encode()).hexdigest()[:16]
        return f"{digest}"

    def _remove_source(self, source: str) -> None:
        existing = self._collection.get(where={"source": source})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    def index_all(self) -> dict[str, int]:
        indexed = 0
        skipped = 0

        for path in self._discover_files():
            source = str(path.relative_to(self.knowledge_dir))
            file_hash = self._file_hash(path)
            if self.manifest.get(source) == file_hash:
                skipped += 1
                continue

            text = self._read_file(path)
            chunks = chunk_text(text, self.chunk_size, self.chunk_overlap)
            self._remove_source(source)

            if chunks:
                ids = [self._chunk_id(source, i) for i in range(len(chunks))]
                metadatas = [{"source": source, "chunk": i} for i in range(len(chunks))]
                self._collection.add(ids=ids, documents=chunks, metadatas=metadatas)

            self.manifest[source] = file_hash
            indexed += 1
            logging.info("Indexed knowledge file: %s (%d chunks)", source, len(chunks))

        self._save_manifest()
        return {"indexed": indexed, "skipped": skipped, "total_chunks": self._collection.count()}

    def add_note(self, text: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"note_{timestamp}.md"
        path = self.knowledge_dir / filename
        body = f"# Note — {datetime.now(timezone.utc).isoformat()}\n\n{text.strip()}\n"
        path.write_text(body, encoding="utf-8")

        source = filename
        chunks = chunk_text(body, self.chunk_size, self.chunk_overlap)
        self._remove_source(source)

        if chunks:
            ids = [self._chunk_id(source, i) for i in range(len(chunks))]
            metadatas = [{"source": source, "chunk": i} for i in range(len(chunks))]
            self._collection.add(ids=ids, documents=chunks, metadatas=metadatas)

        self.manifest[source] = self._file_hash(path)
        self._save_manifest()
        logging.info("Saved note to knowledge base: %s", filename)
        return filename

    def search(self, query: str) -> list[dict[str, Any]]:
        if self._collection.count() == 0:
            return []

        results = self._collection.query(query_texts=[query], n_results=self.top_k)
        hits: list[dict[str, Any]] = []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for document, metadata, distance in zip(documents, metadatas, distances):
            hits.append(
                {
                    "text": document,
                    "source": metadata.get("source", "unknown"),
                    "distance": distance,
                }
            )
        return hits

    def format_context(self, hits: list[dict[str, Any]]) -> str:
        if not hits:
            return ""

        sections = []
        for hit in hits:
            sections.append(f"[{hit['source']}]\n{hit['text']}")
        return "\n\n---\n\n".join(sections)

    @property
    def document_count(self) -> int:
        return self._collection.count()
