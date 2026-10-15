"""Ollama transport: provider token counts are preserved, never estimated as zero."""
import json
import urllib.request
import urllib.error
import time
import hashlib
import http.client


class Ollama:
    fixture = False

    def __init__(self, model, base_url="http://127.0.0.1:11434", context=4096,
                 output_tokens=384, timeout=180, seed=42, temperature=0):
        if not model or context < 1024 or output_tokens < 1 or output_tokens >= context or timeout <= 0:
            raise ValueError("invalid model/context/output/timeout configuration")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.config = {"context": context, "output_tokens": output_tokens, "timeout": timeout,
                       "seed": seed, "temperature": temperature, "num_thread": 4, "think": False}
        self.last_timing = {}
        # A local inference server must not inherit an unrelated corporate proxy.
        self.transport = urllib.request.build_opener(urllib.request.ProxyHandler({})) if self.base_url.startswith(("http://127.0.0.1:", "http://localhost:")) else urllib.request.build_opener()

    def request(self, path, body):
        request = urllib.request.Request(self.base_url + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with self.transport.open(request, timeout=self.config["timeout"]) as response:
            return json.load(response)

    def _metadata(self, path, deadline, body=None):
        """Retry only the three read-only metadata operations, never inference/writes.

        Each socket wait uses the selected provider timeout (capped at 120s).
        Metadata reads/retries share a 180s budget, or the shorter provider
        budget, checked between body reads. Socket waits are individually
        bounded; this is not a separate hard process deadline.
        Invalid JSON, identity errors, authentication and other HTTP errors fail
        immediately. A read-only /api/show POST is safe to repeat after a timeout.
        """
        if (path, body is None) not in {
            ("/api/tags", True), ("/api/version", True), ("/api/show", False)
        }:
            raise ValueError("only model metadata reads may be retried")
        request = urllib.request.Request(
            self.base_url + path,
            None if body is None else json.dumps(body).encode(),
            {} if body is None else {"Content-Type": "application/json"},
        )
        for attempt in range(3):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("model metadata read budget exhausted")
            try:
                with self.transport.open(request, timeout=min(120, remaining)) as response:
                    payload = bytearray()
                    while True:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("model metadata read budget exhausted")
                        chunk = response.read1(65536)
                        if time.monotonic() >= deadline:
                            raise TimeoutError("model metadata read budget exhausted")
                        if not chunk:
                            break
                        payload.extend(chunk)
                        if len(payload) > 4 * 1024 * 1024:
                            raise ValueError("model metadata response exceeds 4 MiB")
                    return json.loads(payload)
            except urllib.error.HTTPError as exc:
                transient = exc.code in {429, 500, 502, 503, 504}
                exc.close()
                if not transient:
                    raise
                failure = exc
            except (TimeoutError, ConnectionError, http.client.IncompleteRead) as exc:
                failure = exc
            except urllib.error.URLError as exc:
                if not isinstance(exc.reason, (TimeoutError, ConnectionError)):
                    raise
                failure = exc
            # No retry happens outside this explicitly read-only operation.
            if attempt == 2:
                raise failure
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("model metadata read budget exhausted")
            time.sleep(min(0.1 * (attempt + 1), remaining))

    def describe(self):
        deadline = time.monotonic() + min(self.config["timeout"], 180)
        models = self._metadata("/api/tags", deadline)["models"]
        if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
            raise ValueError("invalid installed model metadata")
        name = self.model if ":" in self.model else self.model + ":latest"
        entries = [m for m in models if m.get("name") == name]
        if not entries:
            raise ValueError("model is not installed")
        if len(entries) != 1:
            raise ValueError("ambiguous installed model identity")
        entry = entries[0]
        digest = entry.get("digest")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid installed model digest")
        details = self._metadata("/api/show", deadline, {"model": self.model})
        template = details.get("template", "")
        if "{{ .Function }}" in template:
            raise ValueError("model template serializes tool schemas incorrectly; use a tested instruct model or prepare a JSON template variant")
        thinking = details.get("model_info", {}).get("general.thinking_values")
        if isinstance(thinking, list) and False not in thinking:
            raise ValueError("model does not support think=false; choose a non-thinking instruct model")
        return {"name": entry["name"], "digest": entry["digest"], "details": entry.get("details"),
                "capabilities": details.get("capabilities", []), "template_sha256": hashlib.sha256(template.encode()).hexdigest(),
                "ollama": self._metadata("/api/version", deadline), "generation_config": dict(self.config)}

    def embed(self, texts):
        return self.request("/api/embed", {"model": self.model, "input": texts})["embeddings"]

    def complete(self, messages, tools):
        started = time.monotonic()
        response = self.request("/api/chat", {"model": self.model, "messages": messages, "stream": False,
                                "tools": [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}} for t in tools],
                                "think": False,
                                "options": {"temperature": self.config["temperature"], "seed": self.config["seed"],
                                            "num_predict": self.config["output_tokens"], "num_ctx": self.config["context"],
                                            "num_thread": self.config["num_thread"]}})
        message = response["message"]
        if message.get("role") != "assistant" or not isinstance(message.get("content", ""), str):
            raise ValueError("invalid assistant response")
        calls = []
        for call in message.get("tool_calls", []):
            function = call["function"]
            arguments = function["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            calls.append({"name": function["name"], "arguments": arguments})
        usage = {"input": response.get("prompt_eval_count"), "output": response.get("eval_count")}
        self.last_timing = {k: response.get(k) for k in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration", "prompt_eval_cached_count")}
        self.last_timing["wall_seconds"] = time.monotonic() - started
        return {"answer": message.get("content", ""), "calls": calls, "usage": usage, "message": message,
                "timing": self.last_timing, "finish_reason": response.get("done_reason")}


class Scripted:
    """Engineering fixture, explicitly excluded from model-performance claims."""
    fixture = True

    def __init__(self, decisions):
        self.decisions = decisions

    def complete(self, messages, tools):
        index = sum(m["role"] == "assistant" for m in messages)
        if index >= len(self.decisions):
            raise ValueError("fixture exhausted")
        result = dict(self.decisions[index])
        result.setdefault("calls", [])
        result.setdefault("answer", "")
        result["usage"] = {"input": None, "output": None}
        result["message"] = {"role": "assistant", "content": result["answer"]}
        if result["calls"]:
            result["message"]["tool_calls"] = [{"function": c} for c in result["calls"]]
        return result


def prepare_template_variant(source, target, base_url="http://127.0.0.1:11434"):
    """Fix legacy Go-template tool JSON in a new tag; weights are not trained."""
    if source == target:
        raise ValueError("target must differ from source")
    provider = Ollama(source, base_url)
    details = provider.request("/api/show", {"model": source})
    template = details.get("template", "")
    if template.count("{{ .Function }}") != 1:
        raise ValueError("expected exactly one legacy Go-template schema expression")
    repaired = template.replace("{{ .Function }}", "{{ json .Function }}").replace("{{ .Function.Arguments }}", "{{ json .Function.Arguments }}")
    exclusive = "{{ if .Content }}{{ .Content }}\n{{- else if .ToolCalls }}"
    repaired = repaired.replace(exclusive, "{{ if .Content }}{{ .Content }}{{ end }}\n{{- if .ToolCalls }}")
    created = provider.request("/api/create", {"model": target, "from": source, "template": repaired, "stream": False})
    if created.get("status") != "success":
        raise ValueError("model variant creation did not succeed")
    return {"source": source, "target": target, "weights_trained": False,
            "original_template_sha256": hashlib.sha256(template.encode()).hexdigest(),
            "repaired_template_sha256": hashlib.sha256(repaired.encode()).hexdigest(),
            "model_revision": Ollama(target, base_url).describe()}
