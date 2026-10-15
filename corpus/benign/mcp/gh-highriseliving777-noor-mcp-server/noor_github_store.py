#!/usr/bin/env python3
"""
noor_github_store.py — GitHub-backed certificate storage.

Commits certificates to the public noor-governance-protocol repo so they
survive Render restarts and are publicly verifiable forever.

Environment variables (required on Render):
  GITHUB_TOKEN — Personal Access Token with "repo" scope
  GITHUB_REPO  — "highriseliving777/noor-governance-protocol"

Falls back gracefully if not configured (local dev without GitHub).
"""

import os
import json
import base64
import requests
from typing import Optional

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "highriseliving777/noor-governance-protocol")
GITHUB_BRANCH = "main"
CERT_PATH = "certificates"

def is_enabled() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_REPO)

def _headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

def push_certificate(cert: dict) -> dict:
    """Push a certificate to the public GitHub repo.

    Returns:
        {"ok": True, "url": "..."} on success
        {"ok": False, "error": "..."} on failure
    """
    if not is_enabled():
        return {"ok": False, "error": "GitHub store not configured"}

    cert_id = cert.get("certificate_id")
    if not cert_id:
        return {"ok": False, "error": "certificate_id missing"}

    path = f"{CERT_PATH}/{cert_id}.json"
    content = json.dumps(cert, indent=2, sort_keys=True)
    content_b64 = base64.b64encode(content.encode()).decode()

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"

    # Check if file already exists — need SHA for update
    existing_sha = None
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code == 200:
            existing_sha = r.json().get("sha")
    except Exception:
        pass

    payload = {
        "message": f"certificate: {cert_id}",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    try:
        r = requests.put(url, headers=_headers(), json=payload, timeout=15)
        if r.status_code in (200, 201):
            html_url = r.json().get("content", {}).get("html_url", "")
            return {"ok": True, "url": html_url}
        return {"ok": False, "error": f"{r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def fetch_certificate(cert_id: str) -> Optional[dict]:
    """Fetch a certificate from the public repo. Returns None if not found."""
    if not is_enabled():
        return None

    path = f"{CERT_PATH}/{cert_id}.json"
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"

    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        content_b64 = data.get("content", "")
        if not content_b64:
            return None
        content = base64.b64decode(content_b64).decode()
        return json.loads(content)
    except Exception:
        return None

def list_certificates_from_github() -> list:
    """List all certificate IDs in the public repo."""
    if not is_enabled():
        return []

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{CERT_PATH}"
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return []
        items = r.json()
        return sorted([item["name"].replace(".json", "") for item in items if item["name"].endswith(".json")])
    except Exception:
        return []

def status() -> dict:
    return {
        "enabled": is_enabled(),
        "repo": GITHUB_REPO,
        "branch": GITHUB_BRANCH,
        "cert_path": CERT_PATH,
    }


# --- Attestation storage ---
ATTESTATION_PATH = "attestations"

def push_attestation(attestation: dict) -> dict:
    """Push an attestation to the public GitHub repo.

    Returns:
        {"ok": True, "url": "..."} on success
        {"ok": False, "error": "..."} on failure
    """
    if not is_enabled():
        return {"ok": False, "error": "GitHub store not configured"}

    chain_index = attestation.get("chain_index")
    if chain_index is None:
        return {"ok": False, "error": "chain_index missing"}

    path = f"{ATTESTATION_PATH}/attestation-{chain_index:06d}.json"
    content = json.dumps(attestation, indent=2, sort_keys=True)
    content_b64 = base64.b64encode(content.encode()).decode()

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"

    existing_sha = None
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code == 200:
            existing_sha = r.json().get("sha")
    except Exception:
        pass

    payload = {
        "message": f"attestation: chain_index={chain_index}",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    try:
        r = requests.put(url, headers=_headers(), json=payload, timeout=15)
        if r.status_code in (200, 201):
            return {"ok": True, "url": r.json().get("content", {}).get("html_url", "")}
        return {"ok": False, "error": f"{r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def fetch_all_attestations() -> list:
    """Fetch all attestations from GitHub, sorted by chain_index."""
    if not is_enabled():
        return []

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{ATTESTATION_PATH}"
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return []
        items = r.json()
        attestations = []
        for item in items:
            if not item["name"].endswith(".json"):
                continue
            file_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{item['path']}"
            fr = requests.get(file_url, headers=_headers(), timeout=10)
            if fr.status_code == 200:
                content_b64 = fr.json().get("content", "")
                if content_b64:
                    try:
                        att = json.loads(base64.b64decode(content_b64).decode())
                        attestations.append(att)
                    except Exception:
                        continue
        attestations.sort(key=lambda x: x.get("chain_index", 0))
        return attestations
    except Exception:
        return []


if __name__ == "__main__":
    print("GitHub Store Status:")
    print(json.dumps(status(), indent=2))
    if is_enabled():
        certs = list_certificates_from_github()
        print(f"\nCertificates in repo: {len(certs)}")
        for c in certs[:10]:
            print(f"  {c}")
    else:
        print("\n⚠️  GITHUB_TOKEN not set — local-only mode")
