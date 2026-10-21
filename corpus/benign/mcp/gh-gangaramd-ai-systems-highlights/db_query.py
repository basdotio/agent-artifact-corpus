"""Aurora PostgreSQL query tools, served via the RDS Data API.

This Lambda is the Gateway target for Episode 1. It exposes THREE tools so an
agent can explore and query a real database:

    list_tables()             -> table names in the public schema
    describe_table(table)     -> columns + types for one table
    run_select(sql)           -> run a read-only SELECT and return rows

We use the RDS Data API (boto3 'rds-data') so there's no VPC and no Postgres
driver to package — the Lambda just makes HTTPS calls. Credentials come from the
RDS-managed Secrets Manager secret; this Lambda only ever sees the secret ARN.

This is a MULTI-tool Lambda, so it has the small tool-name router (the only glue
added for the Gateway — see ../../00-concepts/terraform/lambda_src/order_tools.py
for the explanation, and single_tool_lambda.py for the no-glue contrast).
"""

import os

import boto3

CLUSTER_ARN = os.environ["CLUSTER_ARN"]
SECRET_ARN = os.environ["SECRET_ARN"]
DB_NAME = os.environ["DB_NAME"]

rds = boto3.client("rds-data")


# --- Data API helpers ------------------------------------------------------
def _execute(sql: str, params=None):
    return rds.execute_statement(
        resourceArn=CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DB_NAME,
        sql=sql,
        includeResultMetadata=True,
        parameters=params or [],
    )


def _scalar(field):
    # A Data API field is a one-key dict, e.g. {"stringValue": "x"} / {"isNull": True}.
    if field.get("isNull"):
        return None
    for v in field.values():
        return v
    return None


def _rows(resp):
    cols = [c["name"] for c in resp.get("columnMetadata", [])]
    return [dict(zip(cols, [_scalar(f) for f in record])) for record in resp.get("records", [])]


# --- tools -----------------------------------------------------------------
def list_tables(_args):
    try:
        sql = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        return {"tables": [r["table_name"] for r in _rows(_execute(sql))]}
    except Exception as e:
        return {"error": str(e)}


def describe_table(args):
    a = args or {}
    table = (
        a.get("table") or a.get("table_name") or
        a.get("tableName") or a.get("name")
    )
    if not table:
        return {"error": 'table is required. Call as: {"table": "orders"}'}
    try:
        sql = (
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name = :t ORDER BY ordinal_position"
        )
        resp = _execute(sql, [{"name": "t", "value": {"stringValue": str(table)}}])
        rows = _rows(resp)
        if not rows:
            return {"error": f"Table '{table}' not found. Use list_tables to see available tables."}
        return {"table": table, "columns": rows}
    except Exception as e:
        return {"error": str(e)}


def run_select(args):
    a = args or {}
    sql = (a.get("sql") or a.get("query") or a.get("statement") or "").strip().rstrip(";")
    if not sql:
        return {"error": 'sql is required. Call as: {"sql": "SELECT * FROM orders LIMIT 5"}'}
    if not sql.lower().startswith("select"):
        return {"error": "Only read-only SELECT statements are allowed."}
    if ";" in sql:
        return {"error": "Only a single statement is allowed."}
    if " limit " not in sql.lower():
        sql += " LIMIT 100"
    try:
        return {"rows": _rows(_execute(sql))}
    except Exception as e:
        return {"error": f"SQL execution failed: {e}. Check column names with describe_table."}


HANDLERS = {"list_tables": list_tables, "describe_table": describe_table, "run_select": run_select}


def _tool_name(context) -> str:
    return context.client_context.custom["bedrockAgentCoreToolName"].split("___")[-1]


def lambda_handler(event, context):
    handler = HANDLERS.get(_tool_name(context))
    if handler is None:
        return {"error": "unknown tool", "available": list(HANDLERS)}
    return handler(event or {})
