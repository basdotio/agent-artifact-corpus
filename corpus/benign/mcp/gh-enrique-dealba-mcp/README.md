# mcp

Testing MCP

To build Docker image:
```sh
docker build -t gpu-env .
```

To run Docker container:
```sh
docker run -d --gpus all -p 8889:8888 -v /home/edealba/Testing/MCP_Testing/client.ipynb:/root/notebooks --name llm gpu-env:latest
```
OR
```sh
docker run -d --gpus all -p 8889:8888 -v ~/.cache/huggingface:/root/.cache/huggingface --name llm gpu-env:latest
```
