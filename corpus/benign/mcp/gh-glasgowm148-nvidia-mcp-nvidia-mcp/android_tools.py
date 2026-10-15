"""APK metadata and signature verification using official Android SDK Build Tools."""

import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import ShieldError

MAX_APK = 600_000_000
PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+")


def sha256_file(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


def run_tool(command):
    try:
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            result = subprocess.run(
                command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=60, check=False
            )
            if result.returncode:
                raise ShieldError(
                    "Android SDK tool rejected the APK; check its signature/manifest and Java installation"
                )
            out.seek(0)
            data = out.read(500_001)
            if len(data) > 500_000:
                raise ShieldError("Android SDK output exceeds the inspection limit")
            return data.decode("utf-8", "replace")
    except FileNotFoundError:
        raise ShieldError(
            "APK tools need official Android SDK Build Tools: configure AAPT2_PATH, APKSIGNER_PATH and Java",
            "missing_dependency",
        ) from None
    except PermissionError:
        raise ShieldError(
            "Android SDK tool could not start: check AAPT2_PATH/APKSIGNER_PATH/JAVA_PATH point to "
            "executables and allow them in OS permissions",
            "permission_denied",
        ) from None
    except OSError:
        raise ShieldError(
            "Android SDK tool could not start: use official Build Tools and Java for this "
            "computer's OS and architecture",
            "missing_dependency",
        ) from None
    except subprocess.TimeoutExpired:
        raise ShieldError("Android SDK APK inspection timed out", "timeout") from None


def signer_command(config):
    path = shutil.which(config.apksigner_path) or config.apksigner_path
    if path.lower().endswith(".jar"):
        return [config.java_path, "-jar", path]
    if path.lower().endswith((".bat", ".cmd")):
        raise ShieldError(
            "Use APKSIGNER_PATH pointing to lib/apksigner.jar on Windows; batch wrappers are unsupported"
        )
    return [path]


def parse_badging(text):
    line = next((s for s in text.splitlines() if s.startswith("package:")), "")
    fields = dict(re.findall(r"([A-Za-z][A-Za-z0-9]*)='([^']*)'", line))
    package, code = fields.get("name", ""), fields.get("versionCode", "")
    if len(package) > 255 or not PACKAGE.fullmatch(package) or not code.isdigit() or len(code) > 19:
        raise ShieldError("APK has an invalid package or versionCode")
    sdk = re.search(r"^(?:sdkVersion|minSdkVersion):'(\d+)'", text, re.M)
    if not sdk:
        raise ShieldError("APK minimum Android SDK is unknown")
    native = re.search(r"^native-code:(.*)$", text, re.M)
    return {
        "package": package,
        "version_code": int(code),
        "version_name": fields.get("versionName", "")[:160],
        "split": fields.get("split", ""),
        "min_sdk": int(sdk[1]),
        "abis": re.findall(r"'([^']+)'", native[1]) if native else [],
    }


def inspect_apk(path, config):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".apk":
        raise ShieldError("Choose a regular local .apk file, not a symlink or bundle archive")
    if not 0 < path.stat().st_size <= MAX_APK:
        raise ShieldError("APK must be between 1 byte and 600 MB")
    path = path.resolve()
    before = sha256_file(path)
    metadata = parse_badging(run_tool([config.aapt2_path, "dump", "badging", str(path)]))
    certs = run_tool([*signer_command(config), "verify", "--print-certs", str(path)])
    signers = sorted(
        set(
            m.lower()
            for m in re.findall(
                r"^Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F]{64})\s*$", certs, re.M
            )
        )
    )
    if not signers:
        raise ShieldError("APK has no verified signing certificate")
    if sha256_file(path) != before:
        raise ShieldError("APK changed during inspection")
    return {**metadata, "signers": signers, "sha256": before, "bytes": path.stat().st_size}


def inspect_set(paths, config):
    if not 1 <= len(paths) <= 20 or len(set(paths)) != len(paths):
        raise ShieldError("Choose 1–20 distinct APK files: base APK and any required splits")
    items = [inspect_apk(path, config) for path in paths]
    base = [item for item in items if not item["split"]]
    if len(base) != 1 or len({item["split"] for item in items}) != len(items):
        raise ShieldError("APK set needs exactly one base and uniquely named splits")
    for item in items:
        if any(item[key] != base[0][key] for key in ("package", "version_code", "signers")):
            raise ShieldError("APK splits must share package, versionCode and all verified signers")
    if sum(item["bytes"] for item in items) > 1_000_000_000:
        raise ShieldError("APK set exceeds 1 GB")
    return base[0], items
