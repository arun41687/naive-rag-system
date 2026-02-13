"""LLM integration module (Kaggle-compatible, no LangChain, no Ollama)."""

from typing import List, Dict

from celery import chunks
from rag_system.hf_llm import HFLLM


class RAGPrompt:
    """Manages RAG prompts and response generation."""
    
    @staticmethod
    def get_system_prompt() -> str:
        return (
            "You are an assistant that answers user questions using ONLY the provided context. "
            "Cite sources clearly using the format [DocName - Page X]. "
            "Do NOT hallucinate or add information not in the context. "
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
            f"Answer:"
        )
    
    @staticmethod
    def format_context(retrieved_chunks: List[Dict], max_length: int = 2000) -> str:
        """Convert retrieved chunks into context string with length limits."""
        if not retrieved_chunks:
            return "No relevant context available."
        
        parts = []
        current_length = 0
        
        for chunk in retrieved_chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue
                
            doc = chunk.get("document") or chunk.get("source") or "UnknownDoc"
            page = chunk.get("page")
            
            citation = f"[{doc} - Page {page}]" if page is not None else f"[{doc}]"
            chunk_text = f"{citation}\n{text}"
            
            if current_length + len(chunk_text) > max_length and parts:
                break
                
            parts.append(chunk_text)
            current_length += len(chunk_text)
        
        return "\n\n---\n\n".join(parts)

class LLMIntegration:
    """Integrates HF LLM with RAG pipeline."""
    
    def __init__(
        self,
        model_name: str = "microsoft/Phi-3-mini-4k-instruct",
        temperature: float = 0.3,
        max_tokens: int = 300
    ):
        self.temperature = temperature
        self.max_tokens = max_tokens
        try:
            self.llm = HFLLM(model_name)
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def generate_answer(self, query: str, chunks: List[Dict]) -> str:
        """Generate answer from retrieved chunks."""
        try:
            # Input validation
            if not query.strip():
                return "Please provide a valid question."
            
            if not chunks:
                return "No relevant information found in the documents."
            
            # Format context and create prompt
            context = RAGPrompt.format_context(chunks)
            prompt = RAGPrompt.create_answer_prompt(query, context)
            
            # Generate response
            response = self.llm.generate(
                prompt, 
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.strip() if response else "Unable to generate a response."
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            return "Unable to generate answer at this time."
    
    def generate_with_sources(self, query: str, chunks: List[Dict]) -> Dict[str, any]:
        """Generate answer with source information."""
        answer = self.generate_answer(query, chunks)
        
        sources = []
        for chunk in chunks:
            doc = chunk.get("document", "UnknownDoc")
            page = chunk.get("page")
            source = f"{doc}, p. {page}" if page else doc
            if source not in sources:
                sources.append(source)
        
        return {
            "answer": answer,
            "sources": sources,
            "num_chunks_used": len(chunks)
        }
