#!/usr/bin/env python3
"""
Compare multiple retrieval strategies.

Usage:
    python compare_retrievers.py --dataset eval_dataset.json --strategies vector,bm25,hybrid
"""

import argparse
import json
import sys
from pathlib import Path


def compare_strategies(dataset_file: str, strategies: list, output_file: str = None):
    """
    Compare retrieval strategies on evaluation dataset.

    This is a placeholder showing structure. In actual use:
    1. Load evaluation dataset
    2. For each strategy, create retriever and evaluate
    3. Calculate hit rate, MRR for each
    4. Generate comparison report
    """
    print(f"Loading dataset from {dataset_file}...")

    try:
        with open(dataset_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)

        num_queries = len(dataset.get("queries", {}))
        print(f"✓ Loaded {num_queries} queries")

    except FileNotFoundError:
        print(f"Error: Dataset file not found: {dataset_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in dataset file: {e}", file=sys.stderr)
        return 1

    print(f"\nComparing strategies: {', '.join(strategies)}")
    print()

    # Simulated results (replace with actual evaluation)
    # In actual implementation:
    # from llama_index.core.evaluation import RetrieverEvaluator
    # for strategy_name in strategies:
    #     retriever = create_retriever(strategy_name)
    #     evaluator = RetrieverEvaluator.from_metric_names(
    #         ["mrr", "hit_rate"],
    #         retriever=retriever
    #     )
    #     results[strategy_name] = await evaluator.aevaluate_dataset(dataset)

    results = {
        "vector": {"hit_rate": 0.850, "mrr": 0.780},
        "bm25": {"hit_rate": 0.820, "mrr": 0.750},
        "hybrid": {"hit_rate": 0.890, "mrr": 0.830},
        "metadata": {"hit_rate": 0.870, "mrr": 0.810},
    }

    # Filter to requested strategies
    filtered_results = {k: v for k, v in results.items() if k in strategies}

    # Print comparison table
    print("=" * 60)
    print("Strategy Comparison Results")
    print("=" * 60)
    print(f"{'Strategy':<15} {'Hit Rate':<12} {'MRR':<12} {'Rank'}")
    print("-" * 60)

    # Sort by hit rate
    sorted_strategies = sorted(
        filtered_results.items(),
        key=lambda x: x[1]['hit_rate'],
        reverse=True
    )

    for rank, (strategy, metrics) in enumerate(sorted_strategies, 1):
        hit_rate = metrics['hit_rate']
        mrr = metrics['mrr']

        # Add indicators
        if hit_rate >= 0.90:
            indicator = "✓✓"
        elif hit_rate >= 0.80:
            indicator = "✓"
        else:
            indicator = "⚠️"

        print(f"{strategy:<15} {hit_rate:<12.3f} {mrr:<12.3f} {rank} {indicator}")

    print("=" * 60)

    # Recommendations
    best_strategy = sorted_strategies[0][0]
    best_hit_rate = sorted_strategies[0][1]['hit_rate']

    print("\nRecommendations:")
    print(f"  Best overall: {best_strategy} (hit rate: {best_hit_rate:.3f})")

    if "hybrid" in filtered_results and filtered_results["hybrid"]["hit_rate"] > 0.85:
        print("  ✓ Hybrid search recommended for production (combines vector + keyword)")

    if any(metrics["hit_rate"] < 0.80 for metrics in filtered_results.values()):
        print("  ⚠️  Some strategies have hit rate < 0.80 - consider optimization")
        print("     - Add reranking")
        print("     - Adjust chunk size")
        print("     - Try different embedding model")

    # Save results
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "dataset": dataset_file,
            "strategies": strategies,
            "results": filtered_results,
            "best_strategy": best_strategy,
            "num_queries": num_queries
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Detailed results saved to {output_file}")

    print()
    print("Note: These are simulated results for demonstration.")
    print("Uncomment LlamaIndex evaluation code in this script for actual comparison.")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Compare retrieval strategies")
    parser.add_argument("--dataset", type=str, required=True, help="Path to evaluation dataset JSON")
    parser.add_argument("--strategies", type=str, required=True, help="Comma-separated list of strategies (e.g., vector,bm25,hybrid)")
    parser.add_argument("--output", type=str, help="Output file for detailed results (optional)")

    args = parser.parse_args()

    strategies_list = [s.strip() for s in args.strategies.split(',')]

    print("=" * 60)
    print("Retrieval Strategy Comparison")
    print("=" * 60)
    print()

    result = compare_strategies(args.dataset, strategies_list, args.output)

    return result


if __name__ == "__main__":
    sys.exit(main())
