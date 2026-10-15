FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY calendar_server.py .
USER 1000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "calendar_server.py"]
