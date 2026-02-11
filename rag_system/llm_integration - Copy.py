"""LLM integration module."""

from typing import List, Dict
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class RAGPrompt:
    """Manages RAG prompts and response generation."""
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt for the RAG system."""
        return """You are a helpful financial analyst assistant specialized in analyzing SEC filings.

Your responsibilities:
1. Answer questions accurately based ONLY on the provided context from SEC 10-K filings
2. Always cite your sources in the format: [Document Name, Item/Section, Page Number]
3. If the answer is not found in the provided documents, respond with: "Not specified in the document."
4. For questions outside the scope of the documents, respond with: "This question cannot be answered based on the provided documents."
5. Be concise and factual in your responses
6. Do not make assumptions or provide information not explicitly stated in the documents"""
    
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
        prompt = f"""{RAGPrompt.get_system_prompt()}

Context from the documents:
{context}

Question: {query}

Answer:"""
        return prompt


class LLMIntegration:
    """Integrates LLM with RAG pipeline."""
    
    def __init__(self, model_name: str = "mistral", temperature: float = 0.3):
        """
        Initialize LLM integration.
        
        Args:
            model_name: Name of the Ollama model to use
            temperature: Temperature for generation (0-1)
        """
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize Ollama LLM
        self.llm = Ollama(
            model=model_name,
            temperature=temperature,
            top_p=0.9,
            top_k=40
        )
    
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
            response = self.llm(prompt)
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
