FROM python:3.11-slim

WORKDIR /mcp-finance/server

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8001

ENTRYPOINT ["sh", "-c"]
CMD ["fastmcp run main.py --transport streamable-http --host 0.0.0.0 --port 8001"]
