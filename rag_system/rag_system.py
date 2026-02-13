"""Main RAG system orchestrator (Kaggle + HF compatible)."""

import os
import json
from typing import Dict, List
from rag_system.ingestion import DocumentIngestor, VectorStore
from rag_system.retriever import RetrieverWithReranker
from rag_system.llm_integration import LLMIntegration, RAGPrompt


class RAGSystem:
    """Complete RAG system for answering questions about SEC filings."""

    def __init__(
        self,
        model_name: str = "microsoft/Phi-3-mini-4k-instruct",
        embedding_model: str = "all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        use_reranker: bool = True
    ):

        print("Initializing RAG System...")

        self.use_reranker = use_reranker

        # ------------------------------
        # Document ingestion
        # ------------------------------
        self.ingestor = DocumentIngestor(
            chunk_size=chunk_size,
            overlap=chunk_overlap
        )

        # ------------------------------
        # Vector store (FAISS)
        # ------------------------------
        self.vector_store = VectorStore(model_name=embedding_model)

        # ------------------------------
        # Retriever WITH reranker
        # ------------------------------
        self.retriever = RetrieverWithReranker(
            self.vector_store,
            use_reranker=self.use_reranker
        )

        if self.use_reranker:
            print("Reranker ENABLED")
        else:
            print("Reranker DISABLED")

        # ------------------------------
        # HF LLM
        # ------------------------------
        self.llm = LLMIntegration(model_name=model_name)

        self.indexed = False

    # ------------------------------------------------------------
    # INGESTION
    # ------------------------------------------------------------

    def ingest_documents(self, documents: List[Dict[str, str]]) -> None:

        print("Starting document ingestion...")
        all_chunks = []

        for doc in documents:
            print(f"Processing {doc['name']} from {doc['path']}...")
            chunks = self.ingestor.parse_pdf(doc['path'], doc['name'])
            all_chunks.extend(chunks)
            print(f"  Created {len(chunks)} chunks")

        print(f"Total chunks created: {len(all_chunks)}")

        print("Creating embeddings and indexing...")
        self.vector_store.add_chunks(all_chunks)

        self.indexed = True
        print("Indexing complete!")

    # ------------------------------------------------------------
    # QUESTION ANSWERING
    # ------------------------------------------------------------

    def answer_question(self, query: str) -> Dict:

        if not self.indexed:
            return {
                "answer": "Error: System not yet indexed. Please ingest documents first.",
                "sources": []
            }

        if self._is_out_of_scope(query):
            return {
                "answer": "This question cannot be answered based on the provided documents.",
                "sources": []
            }

        # ------------------------------------------------
        # STEP 1: Vector Retrieval (Top 10 initial)
        # ------------------------------------------------
        retrieved_chunks = self.retriever.retrieve(
            query=query,
            top_k=10,                 # retrieve more initially
            rerank=self.use_reranker  # force reranker usage
        )

        if not retrieved_chunks:
            return {
                "answer": "Not specified in the document.",
                "sources": []
            }

        # ------------------------------------------------
        # STEP 2: Keep top 5 after reranking
        # ------------------------------------------------
        retrieved_chunks = retrieved_chunks[:5]

        # ------------------------------------------------
        # STEP 3: Format context
        # ------------------------------------------------
        context = RAGPrompt.format_context(retrieved_chunks)

        # ------------------------------------------------
        # STEP 4: Generate answer (HF Phi-3)
        # ------------------------------------------------
        answer = self.llm.generate_answer(query, context)

        # ------------------------------------------------
        # STEP 5: Extract sources
        # ------------------------------------------------
        sources = self.retriever.format_sources(retrieved_chunks)

        return {
            "answer": answer,
            "sources": sources
        }

    # ------------------------------------------------------------
    # OUT OF SCOPE FILTER
    # ------------------------------------------------------------

    @staticmethod
    def _is_out_of_scope(query: str) -> bool:

        out_of_scope_keywords = [
            "stock price forecast",
            "future price",
            "predict",
            "2025",
            "next quarter",
            "next year",
            "color",
            "painted",
            "weather",
            "climate change",
            "political",
            "stock recommendation"
        ]

        query_lower = query.lower()

        return any(keyword in query_lower for keyword in out_of_scope_keywords)

    # ------------------------------------------------------------
    # SAVE / LOAD INDEX
    # ------------------------------------------------------------

    def save_index(self, save_dir: str) -> None:
        os.makedirs(save_dir, exist_ok=True)
        self.vector_store.save(save_dir)
        print(f"Index saved to {save_dir}")

    def load_index(self, save_dir: str) -> None:
        self.vector_store.load(save_dir)
        self.indexed = True
        print(f"Index loaded from {save_dir}")
