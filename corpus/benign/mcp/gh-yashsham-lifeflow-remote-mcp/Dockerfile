FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx pydantic uvicorn

COPY servers/ ./servers/

EXPOSE 8001

# Run the Unified LifeFlowCloudIntelligence Server
CMD ["python", "-m", "servers.remote_hub"]
