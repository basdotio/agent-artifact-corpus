import os
import subprocess
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)

ver = data.get("project", {}).get("version", "1.0.0")
tag = f"v{ver}"

# Comprobar si el tag ya existe local o remotamente
result = subprocess.run(["git", "tag", "-l", tag], capture_output=True, text=True)
tag_exists = result.stdout.strip() == tag

print(f"Versión detectada: {ver} -> Tag: {tag} (Existe: {tag_exists})")

github_env = os.environ.get("GITHUB_ENV")
if github_env:
    with open(github_env, "a", encoding="utf-8") as env:
        env.write(f"RELEASE_TAG={tag}\n")
        env.write(f"PACKAGE_VERSION={ver}\n")
        env.write(f"GENERATE_NOTES={'false' if tag_exists else 'true'}\n")
