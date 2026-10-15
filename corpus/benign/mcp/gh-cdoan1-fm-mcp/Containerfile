FROM registry.redhat.io/ubi9/python-311

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy application code
COPY main.py ./

# Expose the port the app runs on
EXPOSE 8000

# Run the application using uv
CMD ["uv", "run", "python", "main.py"]
