"""
Main script to run the RAG system (Kaggle Compatible).
Uses HuggingFace Phi-3-mini-4k-instruct.
No LangChain.
"""

import os
from pathlib import Path
from rag_system import RAGSystem, run_evaluation


# ==============================
# CONFIGURATION (EDIT HERE)
# ==============================

MODE = "evaluate"   # "index" | "query" | "evaluate"
QUERY = "What was Apple's revenue in 2024?"

MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

INDEX_DIR = "./rag_index"


# ==============================
# MAIN EXECUTION
# ==============================

def main():

    print("Initializing RAG system (HF Phi-3)...")

    rag = RAGSystem(
        model_name=MODEL_NAME,
        embedding_model=EMBEDDING_MODEL,
        use_reranker=False   # safer for Kaggle
    )

    # Documents (ensure PDFs are uploaded to Kaggle)
    documents = [
        {
            "path": "10-Q4-2024-As-Filed.pdf",
            "name": "Apple 10-K"
        },
        {
            "path": "tsla-20231231-gen.pdf",
            "name": "Tesla 10-K"
        }
    ]

    for doc in documents:
        if not os.path.exists(doc["path"]):
            print(f"Warning: {doc['path']} not found")

    # ==============================
    # INDEX MODE
    # ==============================

    if MODE == "index":
        print("\nMode: Index and save")

        rag.ingest_documents(documents)
        rag.save_index(INDEX_DIR)

        print(f"Index saved to {INDEX_DIR}")

    # ==============================
    # QUERY MODE
    # ==============================

    elif MODE == "query":
        print("\nMode: Query")

        if os.path.exists(INDEX_DIR):
            rag.load_index(INDEX_DIR)
        else:
            print("Index not found. Creating index...")
            rag.ingest_documents(documents)
            rag.save_index(INDEX_DIR)

        result = rag.answer_question(QUERY)

        print(f"\nQuestion: {QUERY}")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nSources:\n{result['sources']}")

    # ==============================
    # EVALUATION MODE
    # ==============================

    elif MODE == "evaluate":
        print("\nMode: Evaluate (All test questions)")

        if os.path.exists(INDEX_DIR):
            print(f"Loading index from {INDEX_DIR}...")
            rag.load_index(INDEX_DIR)
        else:
            print("Index not found. Creating index...")
            rag.ingest_documents(documents)
            rag.save_index(INDEX_DIR)

        results = run_evaluation(rag)

        return results


if __name__ == "__main__":
    main()
