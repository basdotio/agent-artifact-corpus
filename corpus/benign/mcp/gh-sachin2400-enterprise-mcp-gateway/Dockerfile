FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV USER_ROLE=analyst
EXPOSE 8000
CMD ["uvicorn", "orchestrator:app", "--host", "0.0.0.0", "--port", "8000"]
