FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (ODBC packages added)
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copy Poetry files and install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# Copy rest of the code
COPY . .

CMD ["poetry", "run", "--quiet", "fastmcp", "run", "main.py:mcp", "--transport", "stdio"]
