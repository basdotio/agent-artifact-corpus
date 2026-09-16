#!/usr/bin/env python3
"""
Generate evaluation Q&A dataset from documents.

Usage:
    python generate_qa_dataset.py --documents-dir ./data --output eval_dataset.json
"""

import argparse
import json
import sys
from pathlib import Path


def generate_qa_pairs(documents_dir: str, num_questions_per_chunk: int = 2, output_file: str = "eval_dataset.json"):
    """
    Generate Q&A pairs from documents.

    This is a placeholder that shows the structure. In actual use, you would:
    1. Load documents using SimpleDirectoryReader
    2. Use generate_question_context_pairs from LlamaIndex
    3. Filter invalid entries
    4. Save to JSON
    """
    try:
        # In actual implementation, uncomment and use:
        # from llama_index.core import SimpleDirectoryReader
        # from llama_index.core.evaluation import generate_question_context_pairs
        # from llama_index.llms.openai import OpenAI

        print(f"Loading documents from {documents_dir}...")

        # Example structure (replace with actual implementation):
        # documents = SimpleDirectoryReader(documents_dir).load_data()
        # llm = OpenAI(model="gpt-4o-mini")
        # qa_dataset = generate_question_context_pairs(
        #     nodes,
        #     llm=llm,
        #     num_questions_per_chunk=num_questions_per_chunk
        # )

        # For demonstration, create sample structure
        sample_dataset = {
            "queries": {
                "q1": "What is the main topic of this document?",
                "q2": "What are the key findings?",
                "q3": "Who are the primary stakeholders mentioned?"
            },
            "corpus": {
                "doc1": "Sample document content...",
                "doc2": "Another document content...",
            },
            "relevant_docs": {
                "q1": ["doc1"],
                "q2": ["doc1", "doc2"],
                "q3": ["doc2"]
            }
        }

        # Save dataset
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_dataset, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Generated dataset with {len(sample_dataset['queries'])} questions")
        print(f"✓ Saved to {output_file}")

        print("\nTo use actual generation, uncomment the LlamaIndex code in this script and run:")
        print(f"  python {__file__} --documents-dir {documents_dir} --output {output_file}")

        return 0

    except Exception as e:
        print(f"Error generating dataset: {e}", file=sys.stderr)
        return 1


def filter_invalid_entries(qa_dataset: dict) -> dict:
    """
    Filter out invalid Q&A pairs.

    Common issues:
    - Questions containing "Here are 2 questions"
    - Auto-generated artifacts
    """
    queries_to_remove = set()

    for query_id, query_text in qa_dataset["queries"].items():
        # Remove queries with common artifacts
        if any(phrase in query_text.lower() for phrase in [
            "here are",
            "here's",
            "the questions are",
            "question 1",
            "question 2"
        ]):
            queries_to_remove.add(query_id)

    # Filter queries and relevant docs
    filtered_queries = {
        k: v for k, v in qa_dataset["queries"].items()
        if k not in queries_to_remove
    }

    filtered_relevant_docs = {
        k: v for k, v in qa_dataset["relevant_docs"].items()
        if k not in queries_to_remove
    }

    return {
        "queries": filtered_queries,
        "corpus": qa_dataset["corpus"],
        "relevant_docs": filtered_relevant_docs
    }


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation Q&A dataset from documents")
    parser.add_argument("--documents-dir", type=str, required=True, help="Directory containing documents")
    parser.add_argument("--output", type=str, default="eval_dataset.json", help="Output JSON file")
    parser.add_argument("--num-questions-per-chunk", type=int, default=2, help="Questions to generate per chunk")

    args = parser.parse_args()

    print("=" * 60)
    print("Q&A Dataset Generation")
    print("=" * 60)
    print()

    result = generate_qa_pairs(
        args.documents_dir,
        args.num_questions_per_chunk,
        args.output
    )

    print("\n" + "=" * 60)
    if result == 0:
        print("✓ Dataset generation completed")
        print("\nNext steps:")
        print("1. Review the generated questions for quality")
        print("2. Manually add or edit questions as needed")
        print("3. Use this dataset for retriever evaluation:")
        print(f"   python compare_retrievers.py --dataset {args.output}")
    else:
        print("✗ Dataset generation failed")
    print("=" * 60)

    return result


if __name__ == "__main__":
    sys.exit(main())
