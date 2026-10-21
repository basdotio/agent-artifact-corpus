# MCP Database Server Usage Examples

This document provides practical examples of how to use the database tools provided by the MCP Database Server with Claude Desktop.

## Example Prompts for Claude

Here are examples of tasks you can ask Claude to perform using the MCP Database Server tools.

### Basic Database Operations

#### Listing Tables

```
What tables are in the database?
```

#### Describing a Table

```
Show me the structure of the Products table.
```

#### Reading Data

```
Show me all records from the Customers table.
```

```
Find all products with a price greater than 50.
```

#### Writing Data

```
Insert a new product with the name "New Widget", price 29.99, and category "Accessories".
```

```
Update the price of all products in the "Electronics" category to increase by 10%.
```

```
Delete all orders that are more than 5 years old.
```

### Schema Management

#### Creating a Table

```
Create a new table called "Feedback" with columns for ID (auto-increment primary key), 
CustomerID (integer), Rating (integer 1-5), and Comment (text).
```

#### Altering a Table

```
Add a "DateCreated" datetime column to the Products table.
```

```
Rename the "Phone" column in the Customers table to "ContactNumber".
```

#### Dropping a Table

```
Delete the temporary_logs table if it exists.
```

### Advanced Queries

#### Complex Joins

```
Show me a list of customers along with their total order amounts,
sorted from highest to lowest total amount.
```

#### Exporting Data

```
Export all customer data as CSV.
```

```
Export the sales summary by month as JSON.
```

## SQL Syntax Examples

### SQLite Examples

```sql
-- Creating a table in SQLite
CREATE TABLE Products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL,
  category TEXT
);

-- Querying with LIMIT and OFFSET
SELECT * FROM Products LIMIT 10 OFFSET 20;

-- Date formatting
SELECT date('now') as today;
SELECT strftime('%Y-%m-%d', date_column) as formatted_date FROM Orders;

-- String concatenation
SELECT first_name || ' ' || last_name as full_name FROM Customers;
```

### SQL Server Examples

```sql
-- Creating a table in SQL Server
CREATE TABLE Products (
  id INT IDENTITY(1,1) PRIMARY KEY,
  name NVARCHAR(100) NOT NULL,
  price DECIMAL(10,2),
  category NVARCHAR(50)
);

-- Querying with OFFSET-FETCH (SQL Server equivalent of LIMIT)
SELECT * FROM Products ORDER BY id OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;

-- Date formatting
SELECT FORMAT(GETDATE(), 'yyyy-MM-dd') as today;
SELECT CONVERT(VARCHAR(10), date_column, 120) as formatted_date FROM Orders;

-- String concatenation
SELECT first_name + ' ' + last_name as full_name FROM Customers;
```

## Working with Claude

### Tips for Using the MCP Database Server

1. **Be specific about database type**: If you have both SQLite and SQL Server configurations, tell Claude which one you want to use.

2. **Security awareness**: Avoid exposing sensitive database credentials in your conversations.

3. **SQL syntax differences**: Remember that SQL syntax might differ between SQLite and SQL Server. 

4. **Error handling**: If Claude encounters an error, it will tell you what went wrong so you can correct your query.

5. **Complex operations**: For complex operations, consider breaking them down into smaller steps.

### Example Claude Conversations

#### Exploring a Database

**User**: "I need to explore my database. What tables do I have?"

**Claude**: *Uses list_tables to show available tables*

**User**: "Tell me about the Customers table structure."

**Claude**: *Uses describe_table to show the schema of the Customers table*

**User**: "Show me the first 5 records from the Customers table."

**Claude**: *Uses read_query to execute a SELECT query*

#### Data Analysis

**User**: "Find customers who haven't placed an order in the last 6 months."

**Claude**: *Uses read_query with a more complex query involving dates and joins*

**User**: "Create a summary of sales by product category."

**Claude**: *Uses read_query with GROUP BY to aggregate sales data*

#### Database Modifications

**User**: "I need to add an 'active' column to the Users table with a default value of true."

**Claude**: *Uses alter_table to modify the schema*

**User**: "Update all products in the 'Discontinued' category to set their 'active' status to false."

**Claude**: *Uses write_query to perform an UPDATE operation* 