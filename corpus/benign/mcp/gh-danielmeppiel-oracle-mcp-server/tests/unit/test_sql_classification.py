import pytest
import sqlparse
from db_context.database import DatabaseConnector

@pytest.mark.parametrize("sql,expected", [
    ("SELECT 1 FROM dual", True),
    ("  SELECT * FROM employees", True),
    ("/*comment*/SELECT col FROM t", True),
    ("WITH x AS (SELECT 1 FROM dual) SELECT * FROM x", True),
    ("EXPLAIN SELECT 1 FROM dual", True),
    ("DESCRIBE employees", True),
    ("SHOW something", True),
    ("", False),
    ("   ", False),
    ("SELECT 1; SELECT 2", False),
    ("INSERT INTO t VALUES (1)", False),
    ("UPDATE t SET a=1", False),
    ("DELETE FROM t", False),
    ("CREATE TABLE x(a int)", False),
    ("DROP TABLE x", False),
])
def test_is_select_query(sql, expected):
    assert DatabaseConnector._is_select_query(sql) is expected

@pytest.mark.parametrize("sql,expected", [
    ("INSERT INTO t VALUES(1)", True),
    ("  update t set a=1", True),
    ("DELETE FROM t", True),
    ("MERGE INTO t USING s ON (t.id=s.id) WHEN MATCHED THEN UPDATE SET t.a=s.a", True),
    ("CREATE TABLE x(a int)", True),
    ("ALTER TABLE x ADD b int", True),
    ("DROP TABLE x", True),
    ("TRUNCATE TABLE x", True),
    ("GRANT SELECT ON t TO u", True),
    ("REVOKE SELECT ON t FROM u", True),
    ("SELECT 1 FROM dual", False),
    ("WITH c AS (SELECT 1 FROM dual) SELECT * FROM c", False),
    ("EXPLAIN SELECT 1 FROM dual", False),
    ("SELECT 1; DELETE FROM t", False),  # multi-statement returns False
])
def test_is_write_operation(sql, expected):
    assert DatabaseConnector._is_write_operation(sql) is expected
