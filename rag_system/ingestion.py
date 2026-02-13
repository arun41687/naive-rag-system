"""
Document ingestion and indexing module for RAG system.
Optimized for Kaggle / Python 3.12 compatibility.
"""

import os
import json
from typing import List, Dict, Tuple
import pdfplumber
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


class DocumentIngestor:
    """Handles PDF parsing and text chunking."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def parse_pdf(self, pdf_path: str, doc_name: str) -> List[Dict]:
        chunks = []

        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            page_mapping = {}

            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                start_pos = len(full_text)
                full_text += page_text + "\n\n"
                end_pos = len(full_text)
                page_mapping[(start_pos, end_pos)] = page_num

        # Overlapping chunking
        step = self.chunk_size - self.overlap
        for i in range(0, len(full_text), step):
            chunk_text = full_text[i:i + self.chunk_size]

            if len(chunk_text.strip()) < 50:
                continue

            # Determine page number
            page_num = 1
            for (start, end), page in page_mapping.items():
                if start <= i < end:
                    page_num = page
                    break

            chunks.append({
                "id": f"{doc_name}_{len(chunks)}",
                "text": chunk_text,
                "document": doc_name,
                "page": page_num,
                "position": i
            })

        return chunks


class VectorStore:
    """Manages embeddings and vector search (cosine similarity)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks = []
        self.embedding_dim = None

    # -------------------------------
    # Add Chunks (Efficient Version)
    # -------------------------------
    def add_chunks(self, chunks: List[Dict]) -> None:
        """
        Add new chunks to the vector store.
        Only embeds new chunks (efficient).
        Uses cosine similarity (FAISS IP + normalization).
        """
        if not chunks:
            return

        new_texts = [chunk["text"] for chunk in chunks]
        new_embeddings = self.model.encode(
            new_texts,
            convert_to_numpy=True,
            normalize_embeddings=True  # important for cosine similarity
        )

        if self.index is None:
            self.embedding_dim = new_embeddings.shape[1]
            self.index = faiss.IndexFlatIP(self.embedding_dim)

        self.index.add(new_embeddings.astype(np.float32))
        self.chunks.extend(chunks)

    # -------------------------------
    # Search
    # -------------------------------
    def search(self, query: str, k: int = 5) -> List[Tuple[Dict, float]]:
        if self.index is None:
            raise ValueError("Vector index not initialized. Add chunks first.")

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        scores, indices = self.index.search(
            query_embedding.astype(np.float32),
            k
        )

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))

        return results

    # -------------------------------
    # Save
    # -------------------------------
    def save(self, save_dir: str) -> None:
        os.makedirs(save_dir, exist_ok=True)

        if self.index is None:
            raise ValueError("Cannot save empty index.")

        faiss.write_index(self.index, os.path.join(save_dir, "index.faiss"))

        with open(os.path.join(save_dir, "chunks.json"), "w") as f:
            json.dump(self.chunks, f)

    # -------------------------------
    # Load
    # -------------------------------
    def load(self, save_dir: str) -> None:
        self.index = faiss.read_index(os.path.join(save_dir, "index.faiss"))

        with open(os.path.join(save_dir, "chunks.json"), "r") as f:
            self.chunks = json.load(f)

        self.embedding_dim = self.index.d
