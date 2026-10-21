"""SQL validation: AST parsing, dangerous command detection, EXPLAIN cost check."""

import logging
import sqlparse
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Dangerous keywords that should be blocked by default
_BLOCKED_KEYWORDS = {"drop", "truncate", "alter", "grant", "revoke", "create", "delete", "update"}


class SQLValidator:
    """Validates generated SQL before execution."""

    @staticmethod
    def validate(sql: str, max_cost: float = 100000.0) -> Dict[str, Any]:
        """Run all validation checks. Returns {valid: bool, error: str?, warnings: [str]}."""
        warnings = []

        # 1. Parse check
        parsed = sqlparse.parse(sql)
        if not parsed:
            return {"valid": False, "error": "Could not parse SQL", "warnings": []}

        stmt = parsed[0]
        first_token = stmt.get_type().upper() if stmt.get_type() else "UNKNOWN"

        # 2. Dangerous command check
        tokens_lower = {t.ttype and str(t).lower() or str(t).lower() for t in stmt.flatten()}
        dangerous = _BLOCKED_KEYWORDS & tokens_lower
        if dangerous:
            return {"valid": False, "error": f"Dangerous keywords detected: {dangerous}", "warnings": []}

        # 3. DELETE/UPDATE without WHERE
        if first_token in ("DELETE", "UPDATE"):
            has_where = any(str(t).upper() == "WHERE" for t in stmt.tokens if hasattr(t, "ttype"))
            if not has_where:
                return {"valid": False, "error": f"{first_token} without WHERE clause is not allowed", "warnings": []}

        # 4. SELECT * warning
        if first_token == "SELECT":
            sql_lower = sql.lower()
            if "select *" in sql_lower or "select *" in sql_lower:
                warnings.append("SELECT * detected — consider specifying columns to reduce result size")

        return {"valid": True, "error": None, "warnings": warnings, "statement_type": first_token}

    @staticmethod
    async def check_cost(db, sql: str, max_cost: float = 100000.0) -> Dict[str, Any]:
        """Run EXPLAIN and check estimated cost."""
        try:
            plan = await db.explain_query(sql)
            cost = _extract_cost(plan)
            if cost and cost > max_cost:
                return {"valid": False, "error": f"Query cost ({cost}) exceeds threshold ({max_cost})", "cost": cost}
            return {"valid": True, "error": None, "cost": cost}
        except Exception as e:
            logger.warning("EXPLAIN failed (non-fatal): %s", e)
            return {"valid": True, "error": None, "cost": None}


def _extract_cost(plan: Dict[str, Any]) -> Optional[float]:
    """Best-effort cost extraction from various EXPLAIN formats."""
    # PostgreSQL
    if "Plan" in plan:
        return plan["Plan"].get("Total Cost")
    # MySQL
    if "query_block" in plan:
        return plan["query_block"].get("cost_info", {}).get("query_cost")
    # MSSQL / others
    if "plan_xml" in plan:
        return None  # XML parsing not implemented
    return None
