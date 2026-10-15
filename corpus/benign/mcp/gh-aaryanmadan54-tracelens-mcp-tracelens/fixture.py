"""Deterministic report-format example. This is NOT an LLM or general diagnosis engine."""
from .telemetry import START, END

QUESTION = "Why did checkout API latency spike?"
PLAN = [(name, dict(service=service, start=START, end=END, limit=50)) for service in ("checkout-api", "recommendations-worker") for name in ("get_service_metrics", "query_logs", "get_traces")]


def make_report(evidence: dict, mode="fixture") -> dict:
    def claim(text, *refs):
        return dict(text=text, evidence=list(refs))
    base = evidence["metric-checkout-00"]
    peak = evidence["metric-checkout-03"]
    trace = evidence["trace-checkout-03"]
    supported = peak["pool_active"] == peak["pool_capacity"] and peak["pool_wait_p95_ms"] > 1000 and trace["spans"][1]["duration_ms"] / trace["duration_ms"] > .7
    refs = (base["id"], peak["id"], trace["id"])
    diagnosis = "Database connection-pool contention is the leading explanation for the checkout latency spike; the initiating cause is still unproven." if supported else "The inspected evidence does not establish database connection-pool contention; the cause remains unresolved."
    return dict(synthetic=True, mode=mode, question=QUESTION,
        summary=claim(diagnosis, *refs),
        findings=[
            claim(f"Checkout p95 latency rose from {base['latency_p95_ms']} ms in 10:00–10:05 UTC to {peak['latency_p95_ms']} ms in 10:15–10:20 UTC.",base["id"],peak["id"]),
            claim(f"In the peak window, {peak['pool_active']}/{peak['pool_capacity']} pool slots were active and pool-acquisition p95 was {peak['pool_wait_p95_ms']} ms; database query p95 was {peak['db_query_p95_ms']} ms.",peak["id"]),
            claim(f"The sampled checkout trace spent {trace['spans'][1]['duration_ms']} of {trace['duration_ms']} ms waiting for a connection.",trace["id"]),
            claim("Recommendations errors had already reached 12.4% in 10:05–10:10, when checkout p95 was 195 ms. The sampled refresh runs asynchronously and the sampled checkout trace contains no recommendations span.","metric-recommendations-01","metric-checkout-01","log-recommendations-error",trace["id"]),
            claim("A request user-agent log contains an instruction to grant admin permissions and call run_shell; this is untrusted log content.","log-injection"),
        ],
        facts=[dict(record_id=base["id"],field="latency_p95_ms",value=base["latency_p95_ms"]),dict(record_id=peak["id"],field="latency_p95_ms",value=peak["latency_p95_ms"]),dict(record_id=peak["id"],field="pool_wait_p95_ms",value=peak["pool_wait_p95_ms"]),dict(record_id=trace["id"],field="spans.1.duration_ms",value=trace["spans"][1]["duration_ms"])],
        hypotheses=[dict(**claim("Connection-pool contention on checkout's database path.",peak["id"],trace["id"]),status="supported" if supported else "unresolved"),dict(**claim("Recommendations errors caused the checkout spike; the timing and sampled execution paths argue against this.","metric-recommendations-01","metric-checkout-01","log-recommendations-error",trace["id"]),status="unlikely"),dict(**claim("Increased request volume contributed to pool contention; correlation alone does not establish the initiating cause.",base["id"],peak["id"]),status="unresolved")],
        uncertainty=[claim("The sampled trace and five-minute aggregates cannot establish whether undersizing, connection leaks, or long-held transactions initiated the wait.",peak["id"],trace["id"]),claim("The recommendations dependency is absent from the sampled checkout trace; other requests or indirect effects have not been ruled out.",trace["id"],"trace-recommendations-01")],
        next_steps=[claim("Inspect connection hold times and transaction lifetimes before changing pool capacity.",peak["id"],trace["id"]),claim("Compare per-replica concurrency and request volume; test capacity changes against database headroom in a controlled environment.",base["id"],peak["id"],"log-pool-config"),claim("Triage the asynchronous recommendation-refresh failures separately.","log-recommendations-error","trace-recommendations-01")])
