"""LLM integration module (Kaggle-compatible, no LangChain, no Ollama)."""

from typing import List, Dict
from rag_system.hf_llm import HFLLM


class RAGPrompt:
    """Manages RAG prompts and response generation."""

    @staticmethod
    def get_system_prompt() -> str:
        return (
            "You are an assistant that answers user questions using ONLY the provided context. "
            "Cite sources clearly. Do NOT hallucinate. "
            "If the answer is not in the context, respond: "
            "'The information is not available in the provided documents.'"
        )

    @staticmethod
    def create_answer_prompt(query: str, context: str) -> str:
        system_prompt = RAGPrompt.get_system_prompt()

        return (
            f"{system_prompt}\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Answer concisely and include citations (e.g., [DocName - Page X])."
        )

    @staticmethod
    def format_context(retrieved_chunks: List[Dict]) -> str:
        """
        Convert list of retrieved chunk dicts into a single context string with citations.
        """
        parts = []

        for chunk in retrieved_chunks:
            text = chunk.get("text", "").strip()
            doc = chunk.get("document") or chunk.get("source") or "UnknownDoc"
            page = chunk.get("page")

            if page is not None:
                citation = f"[{doc} - Page {page}]"
            else:
                citation = f"[{doc}]"

            parts.append(f"{citation}\n{text}")

        return "\n\n---\n\n".join(parts)


class LLMIntegration:
    """Integrates HF LLM with RAG pipeline (no LangChain)."""

    def __init__(
        self,
        model_name: str = "microsoft/Phi-3-mini-4k-instruct",
        temperature: float = 0.3,
    ):
        self.temperature = temperature
        self.llm = HFLLM(model_name)

    def generate_answer(self, query: str, chunks: List[Dict]) -> str:
        """
        Generate answer from retrieved chunks.
        """
        context = RAGPrompt.format_context(chunks)
        prompt = RAGPrompt.create_answer_prompt(query, context)

        try:
            return self.llm.generate(prompt).strip()
        except Exception as e:
            print(f"Error generating answer: {e}")
            return "Unable to generate answer at this time."
