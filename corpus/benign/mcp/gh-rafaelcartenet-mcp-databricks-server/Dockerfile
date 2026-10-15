FROM python:3.10-slim

WORKDIR /app

# Set environment variables (users should provide these at runtime)
ENV DATABRICKS_HOST="your-databricks-instance.cloud.databricks.com"
ENV DATABRICKS_TOKEN="your-databricks-access-token"
ENV DATABRICKS_SQL_WAREHOUSE_ID="your-sql-warehouse-id"

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"] 