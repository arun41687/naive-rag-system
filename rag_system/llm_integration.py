"""LLM integration module."""

from typing import List, Dict
from rag_system.hf_llm import HFLLM  # import a custom HF LLM wrapper
# from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain

class RAGPrompt:
    """Manages RAG prompts and response generation."""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt for the RAG system."""
        return (
            "You are an assistant that answers user questions using only the provided context. "
            "Cite sources and avoid hallucination. If the answer is not in the context, respond "
            "that the information is not available in the provided documents."
        )
    
    @staticmethod
    def create_answer_prompt(query: str, context: str) -> str:
        """
        Create a prompt for answering a question with context.
        
        Args:
            query: The user's question
            context: Retrieved context from documents
            
        Returns:
            Formatted prompt string
        """
        return (
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            "Answer concisely and include citations (e.g., [DocName - Page X])."
        )
    
    @staticmethod
    def format_context(retrieved_chunks: List[Dict]) -> str:
        """
        Convert list of retrieved chunk dicts into a single context string with simple citations.
        Expects each chunk to have at least 'text' and optional 'document'/'page' metadata.
        """
        parts = []
        for i, c in enumerate(retrieved_chunks, start=1):
            text = c.get("text", c.get("content", "")).strip()
            doc = c.get("document") or c.get("source") or c.get("doc_name") or "UnknownDoc"
            page = c.get("page")
            citation = f"[{doc}" + (f" - Page {page}]" if page is not None else "]")
            parts.append(f"{citation}\n{text}")
        return "\n\n---\n\n".join(parts)


class LLMIntegration:
    """Integrates LLM with RAG pipeline."""
    
    def __init__(self, model_name: str = "phi3", temperature: float = 0.3):
        """
        Initialize LLM integration.
        
        Args:
            model_name: Name of the Ollama model to use
            temperature: Temperature for generation (0-1)
        """
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize LLM
        self.llm = HFLLM(model_name)  # HF model interface
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate an answer using the LLM.
        
        Args:
            query: User's question
            context: Retrieved context
            
        Returns:
            Generated answer
        """
        prompt = RAGPrompt.create_answer_prompt(query, context)
        
        try:            
            response = self.llm.generate(prompt)
            return response.strip()
        except Exception as e:
            print(f"Error generating answer: {e}")
            return "Unable to generate answer at this time."
    
    @staticmethod
    def format_context(chunks: List[Dict]) -> str:
        """
        Format retrieved chunks into context string.
        
        Args:
            chunks: List of retrieved chunks
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}: {chunk['document']}, Page {chunk['page']}]\n"
                f"{chunk['text']}\n"
            )
        
        return "\n".join(context_parts)
