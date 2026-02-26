from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

@dataclass
class Chunk:
    doc_name: str
    text: str

class SimpleRAG:
    def __init__(self, kb_dir: str = "data/kb_docs", model_name: str = "all-MiniLM-L6-v2"):
        self.kb_dir = Path(kb_dir)
        self.embedder = SentenceTransformer(model_name)
        self.chunks: List[Chunk] = []
        self.index = None
        self._build()

    def _build(self):
        texts = []
        for p in sorted(self.kb_dir.glob("*.txt")):
            content = p.read_text(encoding="utf-8").strip()
            # Simple chunking: split by lines/paragraphs
            parts = [x.strip() for x in content.split("\n") if x.strip()]
            for part in parts:
                self.chunks.append(Chunk(doc_name=p.name, text=part))
                texts.append(part)

        if not texts:
            raise RuntimeError(f"No KB docs found in {self.kb_dir.resolve()}")

        emb = self.embedder.encode(texts, normalize_embeddings=True)
        emb = np.asarray(emb, dtype="float32")

        self.index = faiss.IndexFlatIP(emb.shape[1])  # cosine via normalized + inner product
        self.index.add(emb)

    def retrieve(self, query: str, k: int = 4) -> List[Tuple[Chunk, float]]:
        q = self.embedder.encode([query], normalize_embeddings=True)
        q = np.asarray(q, dtype="float32")
        scores, idxs = self.index.search(q, k)
        out = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            out.append((self.chunks[idx], float(score)))
        return out