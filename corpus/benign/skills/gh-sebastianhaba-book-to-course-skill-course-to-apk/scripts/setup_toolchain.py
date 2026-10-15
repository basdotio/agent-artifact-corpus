#!/usr/bin/env python3
"""Download whatever toolchain.py reports as missing — without sudo, into one folder of the user's home.

Usage:
  setup_toolchain.py --dry-run                 # print what would be downloaded, from where, how big — download nothing
  setup_toolchain.py --show-license            # print the Android SDK licence text (show it to the user)
  setup_toolchain.py --accept-licenses         # download + install (only the missing parts)

Installs into ~/.local/share/course-to-apk (%LOCALAPPDATA%\\course-to-apk on Windows); set COURSE_TO_APK_HOME to change it
(toolchain.py and build_apk.py read the same variable, so they find what was installed).

Sources (official only, checksums verified):
  JDK 21      Eclipse Temurin via https://api.adoptium.net  (~200 MB download)
  build-tools https://dl.google.com/android/repository/  (~62 MB)   — newest stable, listed in repository2-3.xml
  platform    https://dl.google.com/android/repository/  (~65 MB)   — newest stable android-NN

--accept-licenses means the USER agreed to the Android SDK License Agreement
(https://developer.android.com/studio/terms). Only pass it after they said yes.
Standard library only.
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolchain  # noqa: E402

REPO = "https://dl.google.com/android/repository/"
REPO_XML = REPO + "repository2-3.xml"
JDK_FEATURE = 21
UA = {"User-Agent": "course-to-apk/1.0"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def host_os():
    return "windows" if os.name == "nt" else "macosx" if sys.platform == "darwin" else "linux"


def host_arch():
    m = toolchain.platform.machine().lower()
    return "aarch64" if m in ("arm64", "aarch64") else "x64"


# ---- plan ----------------------------------------------------------------------------------------
def plan_jdk():
    os_name = {"windows": "windows", "macosx": "mac", "linux": "linux"}[host_os()]
    url = ("https://api.adoptium.net/v3/assets/latest/%d/hotspot?os=%s&architecture=%s&image_type=jdk&vendor=eclipse"
           % (JDK_FEATURE, os_name, host_arch()))
    data = json.loads(fetch(url))
    if not data:
        raise SystemExit("Adoptium has no JDK %d build for %s/%s — install a JDK by hand." % (JDK_FEATURE, os_name, host_arch()))
    pkg = data[0]["binary"]["package"]
    return {"what": "JDK %s (Eclipse Temurin)" % data[0]["version"]["semver"], "kind": "jdk", "url": pkg["link"],
            "size": pkg["size"], "hash": ("sha256", pkg["checksum"]), "name": pkg["name"]}


def _stable(path):
    return not any(x in path for x in ("-rc", "beta", "-ext", "preview"))


def plan_sdk(need_bt, need_pl):
    root = ET.fromstring(fetch(REPO_XML))
    licenses = {l.get("id"): (l.text or "") for l in root.findall("license")}
    best_bt = best_pl = None
    for p in root.findall("remotePackage"):
        path = p.get("path")
        if p.find("channelRef") is not None and p.find("channelRef").get("ref") != "channel-0":
            continue
        if not _stable(path):
            continue
        if path.startswith("build-tools;"):
            ver = path.split(";", 1)[1]
            key = toolchain._version_key(ver)
            if key[0] < toolchain.MIN_BUILD_TOOLS:
                continue
            arc = next((a for a in p.findall("archives/archive") if a.findtext("host-os") == host_os()), None)
            if arc is not None and (best_bt is None or key > best_bt[0]):
                best_bt = (key, path, ver, arc, p)
        elif path.startswith("platforms;android-") and path.split("-", 1)[1].isdigit():
            api = int(path.split("-", 1)[1])
            arcs = p.findall("archives/archive")
            if api >= toolchain.MIN_PLATFORM and arcs and (best_pl is None or api > best_pl[0]):
                best_pl = (api, path, "android-%d" % api, arcs[0], p)
    items = []
    for need, best, kind in ((need_bt, best_bt, "build-tools"), (need_pl, best_pl, "platform")):
        if not need:
            continue
        if not best:
            raise SystemExit("No suitable %s found in %s" % (kind, REPO_XML))
        _, path, folder, arc, pkg = best
        cs = arc.find("complete/checksum")
        lic = pkg.find("uses-license").get("ref")
        items.append({"what": path, "kind": kind, "folder": folder, "url": REPO + arc.findtext("complete/url"),
                      "size": int(arc.findtext("complete/size")),
                      "hash": ((cs.get("type") or "sha1").replace("-", ""), cs.text.strip()),
                      "license_id": lic, "license_text": licenses.get(lic, "")})
    return items


def make_plan(info):
    items = []
    if "jdk" in info["missing"]:
        items.append(plan_jdk())
    if "build-tools" in info["missing"] or "platform" in info["missing"]:
        items += plan_sdk("build-tools" in info["missing"], "platform" in info["missing"])
    return items


# ---- install -------------------------------------------------------------------------------------
def download(item, tmp):
    dest = os.path.join(tmp, item["url"].rsplit("/", 1)[-1].split("?")[0] or "download")
    algo, want = item["hash"]
    h = hashlib.new(algo)
    req = urllib.request.Request(item["url"], headers=UA)
    done, last = 0, -1
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            pct = done * 100 // max(item["size"], 1)
            if pct // 10 != last:
                last = pct // 10
                print("  %s  %d%%  (%d / %d MB)" % (item["what"], pct, done >> 20, item["size"] >> 20), flush=True)
    if h.hexdigest().lower() != want.lower():
        raise SystemExit("Checksum mismatch for %s — download corrupted or tampered with; nothing installed." % item["url"])
    return dest


def _single_top(names):
    tops = {n.split("/", 1)[0] for n in names if n.strip("/")}
    return tops.pop() if len(tops) == 1 else None


def extract_zip(path, target):
    """Extract stripping the archive's single top folder; keep exec bits and symlinks (zipfile drops both)."""
    with zipfile.ZipFile(path) as z:
        top = _single_top(z.namelist())
        for info in z.infolist():
            rel = info.filename[len(top) + 1:] if top else info.filename
            if not rel or rel.endswith("/"):
                continue
            out = os.path.normpath(os.path.join(target, rel))
            if not out.startswith(os.path.normpath(target) + os.sep):
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) and os.name != "nt":
                if os.path.lexists(out):
                    os.remove(out)
                os.symlink(z.read(info).decode(), out)
                continue
            with z.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            if mode & 0o111:
                os.chmod(out, 0o755)


def install_jdk(item, archive, dest):
    tmp = tempfile.mkdtemp(dir=dest)
    if archive.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive) as t:
            t.extractall(tmp, filter="tar") if hasattr(tarfile, "data_filter") else t.extractall(tmp)
    else:
        with zipfile.ZipFile(archive) as z:
            z.extractall(tmp)
    top = os.path.join(tmp, os.listdir(tmp)[0])
    final = os.path.join(dest, "jdk-%d" % JDK_FEATURE)
    if os.path.exists(final):
        shutil.rmtree(final)
    os.rename(top, final)
    shutil.rmtree(tmp, ignore_errors=True)
    if os.path.isdir(os.path.join(final, "Contents", "Home")):  # macOS bundle layout
        return os.path.join(final, "Contents", "Home")
    if os.name != "nt":
        for b in os.listdir(os.path.join(final, "bin")):
            os.chmod(os.path.join(final, "bin", b), 0o755)
    return final


def install_sdk_pkg(item, archive, sdk):
    sub = "build-tools" if item["kind"] == "build-tools" else "platforms"
    target = os.path.join(sdk, sub, item["folder"])
    if os.path.exists(target):
        shutil.rmtree(target)
    os.makedirs(target)
    extract_zip(archive, target)
    # same marker sdkmanager writes, so Android Studio / sdkmanager also treat the licence as accepted
    lic_dir = os.path.join(sdk, "licenses")
    os.makedirs(lic_dir, exist_ok=True)
    lic_file = os.path.join(lic_dir, item["license_id"])
    digest = hashlib.sha1(item["license_text"].encode("utf-8")).hexdigest()
    existing = open(lic_file).read().split() if os.path.exists(lic_file) else []
    if digest not in existing:
        with open(lic_file, "a") as f:
            f.write("\n" + digest)
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-license", action="store_true")
    ap.add_argument("--accept-licenses", action="store_true")
    a = ap.parse_args()

    info = toolchain.detect()
    if info["ready"] and not a.show_license:
        print(toolchain.describe(info))
        print("\nNothing to install.")
        return
    if a.show_license:
        root = ET.fromstring(fetch(REPO_XML))
        print(next(l.text for l in root.findall("license") if l.get("id") == "android-sdk-license"))
        return

    dest = toolchain.OWN_DIR
    plan = make_plan(info)
    total = sum(i["size"] for i in plan)
    print("Missing: %s.  Will download (%d MB total) into %s:" % (", ".join(info["missing"]), total >> 20, dest))
    for i in plan:
        print("  - %-34s %4d MB  %s" % (i["what"], i["size"] >> 20, i["url"]))
    if a.dry_run:
        if any(i["kind"] != "jdk" for i in plan):
            print("\nAndroid SDK packages require accepting the Android SDK License Agreement: https://developer.android.com/studio/terms")
        return
    if any(i["kind"] != "jdk" for i in plan) and not a.accept_licenses:
        raise SystemExit("\nRefusing to download Android SDK packages without --accept-licenses "
                         "(ask the user to accept https://developer.android.com/studio/terms first).")

    os.makedirs(dest, exist_ok=True)
    sdk = os.path.join(dest, "sdk")
    with tempfile.TemporaryDirectory(dir=dest) as tmp:
        for item in plan:
            archive = download(item, tmp)
            if item["kind"] == "jdk":
                print("  installed JDK → " + install_jdk(item, archive, dest))
            else:
                print("  installed %s → %s" % (item["what"], install_sdk_pkg(item, archive, sdk)))
            os.remove(archive)

    print()
    after = toolchain.detect()
    print(toolchain.describe(after))
    sys.exit(0 if after["ready"] else 1)


if __name__ == "__main__":
    main()
