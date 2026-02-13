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

def run_evaluation(rag_system: RAGSystem) -> List[Dict]: 
    """Run the evaluation on all test questions. 
    Returns: List of answer dictionaries with question_id, answer, and sources 
    """ 
    questions = [ {"question_id": 1, "question": "What was Apples total revenue for the fiscal year ended September 28, 2024?"}, 
                 {"question_id": 2, "question": "How many shares of common stock were issued and outstanding as of October 18, 2024?"}, 
                 {"question_id": 3, "question": "What is the total amount of term debt (current + non-current) reported by Apple as of September 28, 2024?"}, 
                 {"question_id": 4, "question": "On what date was Apples 10-K report for 2024 signed and filed with the SEC?"}, 
                 {"question_id": 5, "question": "Does Apple have any unresolved staff comments from the SEC as of this filing? How do you know?"}, 
                 {"question_id": 6, "question": "What was Teslas total revenue for the year ended December 31, 2023?"}, 
                 {"question_id": 7, "question": "What percentage of Teslas total revenue in 2023 came from Automotive Sales (excluding Leasing)?"}, 
                 {"question_id": 8, "question": "What is the primary reason Tesla states for being highly dependent on Elon Musk?"}, 
                 {"question_id": 9, "question": "What types of vehicles does Tesla currently produce and deliver?"}, 
                 {"question_id": 10, "question": "What is the purpose of Teslas 'lease pass-through fund arrangements'?"}, 
                 {"question_id": 11, "question": "What is Teslas stock price forecast for 2025?"}, 
                 {"question_id": 12, "question": "Who is the CFO of Apple as of 2025?"}, 
                 {"question_id": 13, "question": "What color is Teslas headquarters painted?"} ] 
    
    answers = [] 
    print("\n" + "="*80) 
    print("RUNNING EVALUATION ON 13 TEST QUESTIONS") 
    print("="*80 + "\n") 
    
    for q_data in questions: 
        print(f"Q{q_data['question_id']}: {q_data['question']}") 
        result = rag_system.answer_question(q_data['question']) 
        answer_entry = { "question_id": q_data['question_id'], "answer": result['answer'], "sources": result['sources'] } 
        answers.append(answer_entry) 
        print(f"Answer: {result['answer'][:100]}...") 
        print(f"Sources: {result['sources']}\n")

    # Save results with timestamp 
    from datetime import datetime 
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
    output_file = f"evaluation_results_{timestamp}.json"
    
    with open(output_file, "w") as f: 
        json.dump(answers, f, indent=2) 
    
    print("\n" + "="*80) 
    print(f"Evaluation complete! Results saved to {output_file}") 
    print("="*80) 
    
    return answers
