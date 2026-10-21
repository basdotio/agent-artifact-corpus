#!/usr/bin/env python3
"""Explicitly download pinned, public ONNX data files; never send corpus text."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

MODELS = {
    "embedding": {
        "repository": "Xenova/multilingual-e5-small",
        "revision": "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
        "files": {
            "model.onnx": ("onnx/model_quantized.onnx", "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193"),
            "tokenizer.json": ("tokenizer.json", "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"),
        },
    },
    "reranker": {
        "repository": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        "revision": "1427fd652930e4ba29e8149678df786c240d8825",
        "files": {
            "model.onnx": ("onnx/model_qint8_arm64.onnx", "1825907d6c1a9001ff78124780bbde20a614a8c3df3b63409cf3c72c6fe5c8b4"),
            "tokenizer.json": ("tokenizer.json", "62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626"),
        },
    },
}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", required=True, type=Path)
    parser.add_argument("--model", choices=["embedding", "reranker", "all"], default="all")
    args = parser.parse_args()
    for kind, spec in MODELS.items():
        if args.model not in (kind, "all"):
            continue
        dest = args.models_dir / kind
        dest.mkdir(parents=True, exist_ok=True)
        for name, (remote, expected) in spec["files"].items():
            target = dest / name
            if target.exists() and sha256(target) == expected:
                print(f"Verified cached {kind}/{name}", flush=True)
                continue
            url = f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{remote}"
            temporary = target.with_suffix(target.suffix + ".download")
            print(f"Downloading {kind}/{name}", flush=True)
            with urllib.request.urlopen(url, timeout=90) as response, temporary.open("wb") as out:
                while block := response.read(1024 * 1024):
                    out.write(block)
            if sha256(temporary) != expected:
                raise ValueError(f"SHA256 mismatch for {kind}/{name}; existing file unchanged")
            temporary.replace(target)
        (dest / "manifest.json").write_text(json.dumps(spec, indent=2) + "\n")
    print("Models ready for local inference. No corpus data was transmitted.")


if __name__ == "__main__":
    main()
