from fastmcp import FastMCP
import os 
import sqlite3

mcp=FastMCP(name='Expense Tracker')

db_path=os.path.join(os.path.dirname(__file__),"espenses.db")

def init_db():
    with sqlite3.connect(db_path) as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT DEFAULT '',
            note TEXT DEFAULT '')"""
        )
init_db()

@mcp.tool
def add_expense(date,amount,category,subcategory='',note=''):
    """this tool use to add expenses in db"""
    with sqlite3.connect(db_path) as c:
        curr=c.execute("INSERT INTO expenses(date,amount,category,subcategory,note) VALUES(?,?,?,?,?)",(date,amount,category,subcategory,note))
        return {'status':'OK','id':curr.lastrowid}
    
@mcp.tool
def list_expenses():
    """this tool use to list all expenses in db"""
    with sqlite3.connect(db_path) as c:
        curr=c.execute("SELECT * FROM expenses ORDER BY id ASC")
        return curr.fetchall()

@mcp.tool
def summary_expenses():
    """this tool use to summary all expenses in db"""
    with sqlite3.connect(db_path) as c:
        curr=c.execute("SELECT category,SUM(amount) FROM expenses GROUP BY category")
        return curr.fetchall()

@mcp.tool
def delete_expense(expense_id):
    """this tool use to delete expenses in db"""
    with sqlite3.connect(db_path) as c:
        curr=c.execute("DELETE FROM expenses WHERE id=?",(expense_id,))
        return {'status':'OK','deleted':curr.rowcount}

if __name__=="__main__":
    mcp.run(transport="streamable-http",host="127.0.0.1",port=8000)