#!/usr/bin/env python3
"""Build a signed Android APK (a light WebView wrapper) from a course made by book-to-course.

Usage:  build_apk.py COURSE_DIR [--out DIR] [--package ID] [--label NAME] [--version-name X]
                     [--keystore FILE --ks-pass P --key-alias A [--key-pass P]] [--install]

  COURSE_DIR      the course folder (has index.html, assets/, course/data.js)
  --out           where the Android build lives (default: <COURSE_DIR>-android, next to the course)
  --package       application id, e.g. pl.example.gocourse (default: derived from the course id; remembered in <out>/apk.json)
  --label         name under the launcher icon (default: course title)
  --keystore ...  sign with your own key instead of the Android debug key (~/.android/debug.keystore, created if missing)
  --install       also install on the single device connected over adb (adb install -r)

No Gradle: aapt2 → javac → d8 → zipalign → apksigner, straight from the SDK (see toolchain.py for what is needed).
Every build bumps versionCode in <out>/apk.json, so a new APK installs over the old one and keeps the learner's progress
— as long as the package id and the signing key stay the same.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolchain  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(HERE), "assets", "android")
MIN_SDK = 24  # Android 7.0
# player files the app needs; everything the course page uses is compiled into course/data.js
SKIP_TOP = {"content", "exercises", "progress", ".build", ".git", "serve.py", "start.sh", "start.bat", "README.md",
            "__pycache__", "node_modules", "android"}
ICON_COLORS = ["#1E6FD9", "#0F8B8D", "#2E7D32", "#6A4FB6", "#C2185B", "#D84315", "#5D4037", "#37474F", "#00838F", "#AD1457"]
JAVA_KEYWORDS = set("""abstract assert boolean break byte case catch char class const continue default do double else enum
extends final finally float for goto if implements import instanceof int interface long native new package private protected
public return short static strictfp super switch synchronized this throw throws transient try void volatile while true false
null var record yield""".split())
DEBUG_KS = os.path.join(os.path.expanduser("~"), ".android", "debug.keystore")


def die(msg):
    sys.exit("ERROR: " + msg)


def run(cmd, env, what):
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        die("%s failed (exit %d):\n  %s\n%s%s" % (what, r.returncode, " ".join(cmd), r.stdout[-3000:], r.stderr[-3000:]))
    return r.stdout


def ascii_slug(s):
    s = s.replace("ł", "l").replace("Ł", "L")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def default_package(course_id):
    seg = ascii_slug(course_id)[:40].strip("_") or "course"
    if seg[0].isdigit() or seg in JAVA_KEYWORDS:
        seg = "c_" + seg
    return "net.booktocourse." + seg


def valid_package(p):
    parts = p.split(".")
    return len(parts) >= 2 and all(re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", x) and x not in JAVA_KEYWORDS for x in parts)


def course_meta(course):
    meta = {}
    cj = os.path.join(course, "content", "course.json")
    if os.path.exists(cj):
        try:
            meta = json.load(open(cj, encoding="utf-8"))
        except ValueError:
            pass
    if not meta.get("title"):  # learner package without content/ — read it from data.js
        try:
            txt = open(os.path.join(course, "course", "data.js"), encoding="utf-8").read(200000)
            m = re.search(r'"meta"\s*:\s*\{.*?"id"\s*:\s*"([^"]+)".*?"title"\s*:\s*"([^"]+)"', txt, re.S)
            if m:
                meta.setdefault("id", m.group(1))
                meta["title"] = json.loads('"%s"' % m.group(2))
        except (OSError, ValueError):
            pass
    name = os.path.basename(course.rstrip(os.sep))
    meta.setdefault("id", ascii_slug(name) or "course")
    meta.setdefault("title", name)
    return meta


def stage_course(course, out, dst):
    n = size = 0
    out_real = os.path.realpath(out)
    for entry in sorted(os.listdir(course)):
        src = os.path.join(course, entry)
        if entry in SKIP_TOP or entry.startswith(".") or entry.endswith(".zip") or os.path.realpath(src) == out_real:
            continue
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dst, entry),
                            ignore=shutil.ignore_patterns("__pycache__", ".*", "*.pyc", "*.tmp"))
        else:
            shutil.copy2(src, os.path.join(dst, entry))
    for base, _, files in os.walk(dst):
        for f in files:
            n += 1
            size += os.path.getsize(os.path.join(base, f))
    return n, size


def ensure_debug_keystore(env, jdk):
    if os.path.exists(DEBUG_KS):
        return
    os.makedirs(os.path.dirname(DEBUG_KS), exist_ok=True)
    keytool = os.path.join(jdk["home"], "bin", toolchain.exe("keytool"))
    run([keytool, "-genkeypair", "-keystore", DEBUG_KS, "-storepass", "android", "-alias", "androiddebugkey",
         "-keypass", "android", "-keyalg", "RSA", "-keysize", "2048", "-validity", "10950",
         "-dname", "CN=Android Debug,O=Android,C=US"], env, "keytool (creating ~/.android/debug.keystore)")
    print("Created the Android debug key: " + DEBUG_KS)


def adb_install(adb, apk, env):
    if not adb:
        die("--install needs adb (Android SDK platform-tools) — or copy the APK to the device by hand.")
    out = run([adb, "devices"], env, "adb devices")
    devs = [l.split()[0] for l in out.splitlines()[1:] if l.strip().endswith("device")]
    if len(devs) != 1:
        die("--install needs exactly one connected device with USB debugging on (adb sees %d). APK is ready: %s" % (len(devs), apk))
    r = subprocess.run([adb, "-s", devs[0], "install", "-r", apk], env=env, capture_output=True, text=True)
    text = r.stdout + r.stderr
    if "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in text:
        die("the device has this app signed with a different key. Uninstall it first (this deletes the learner's "
            "progress on that device), then install again:\n  %s uninstall <package>" % adb)
    if r.returncode != 0 or "Success" not in text:
        die("adb install failed:\n" + text)
    print("Installed on device " + devs[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course_dir")
    ap.add_argument("--out")
    ap.add_argument("--package")
    ap.add_argument("--label")
    ap.add_argument("--version-name")
    ap.add_argument("--keystore")
    ap.add_argument("--ks-pass")
    ap.add_argument("--key-alias")
    ap.add_argument("--key-pass")
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()

    course = os.path.abspath(a.course_dir).rstrip(os.sep)
    for need in ("index.html", os.path.join("course", "data.js"), os.path.join("assets", "app.js")):
        if not os.path.exists(os.path.join(course, need)):
            die("%s has no %s — is this a book-to-course course? (run build_course.py first if data.js is missing)" % (course, need))

    info = toolchain.detect()
    if not info["ready"]:
        print(toolchain.describe(info))
        sys.exit(1)
    env = toolchain.tool_env(info)
    jdk, sdk = info["jdk"], info["sdk"]
    bt = sdk["build_tools"]["dir"]
    android_jar, api = sdk["platform"]["jar"], sdk["platform"]["api"]

    out = os.path.abspath(a.out or course + "-android")
    os.makedirs(out, exist_ok=True)
    meta = course_meta(course)

    # ---- apk.json: identity that must stay stable between builds ------------------------------
    cfg_path = os.path.join(out, "apk.json")
    cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}
    if a.package and cfg.get("package") and a.package != cfg["package"]:
        print("NOTE: package changes %s → %s. Android treats this as a different app: progress in the old one is not carried over."
              % (cfg["package"], a.package))
    cfg["package"] = a.package or cfg.get("package") or default_package(meta["id"])
    if not valid_package(cfg["package"]):
        die("invalid package id %r — use something like pl.example.gocourse (letters/digits/_, at least two parts)" % cfg["package"])
    cfg["label"] = a.label or cfg.get("label") or meta["title"]
    cfg["version_code"] = int(cfg.get("version_code", 0)) + 1
    cfg["version_name"] = a.version_name or "1.0.%d" % cfg["version_code"]
    cfg.setdefault("icon_color", ICON_COLORS[int(hashlib.sha1(meta["id"].encode()).hexdigest(), 16) % len(ICON_COLORS)])
    if a.keystore:
        cfg["keystore"] = os.path.abspath(a.keystore)
    ks = cfg.get("keystore") or DEBUG_KS

    # ---- stage --------------------------------------------------------------------------------
    build = os.path.join(out, "build")
    shutil.rmtree(build, ignore_errors=True)
    os.makedirs(build)
    shutil.copytree(os.path.join(TEMPLATE, "res"), os.path.join(build, "res"))
    with open(os.path.join(build, "res", "values", "icon.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="icon_bg">%s</color>\n</resources>\n'
                % cfg["icon_color"])
    manifest = open(os.path.join(TEMPLATE, "AndroidManifest.xml"), encoding="utf-8").read()
    # aapt2 reads @ and ? at the start of a label as references
    label = escape(cfg["label"], {'"': "&quot;"})
    if label[:1] in "@?":
        label = "\\" + label
    manifest = manifest.replace("{{PACKAGE}}", cfg["package"]).replace("{{LABEL}}", label)
    with open(os.path.join(build, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest)
    assets_dir = os.path.join(build, "assets")
    nfiles, nbytes = stage_course(course, out, os.path.join(assets_dir, "course"))

    # ---- resources + manifest + assets → unsigned apk -----------------------------------------
    aapt2 = os.path.join(bt, toolchain.exe("aapt2"))
    res_zip = os.path.join(build, "res.zip")
    run([aapt2, "compile", "--dir", os.path.join(build, "res"), "-o", res_zip], env, "aapt2 compile")
    unsigned = os.path.join(build, "unsigned.apk")
    run([aapt2, "link", "-o", unsigned, "-I", android_jar, "--manifest", os.path.join(build, "AndroidManifest.xml"),
         "-A", assets_dir, "--min-sdk-version", str(MIN_SDK), "--target-sdk-version", str(api),
         "--version-code", str(cfg["version_code"]), "--version-name", cfg["version_name"], res_zip], env, "aapt2 link")

    # ---- java → dex ---------------------------------------------------------------------------
    classes = os.path.join(build, "classes")
    sources = glob.glob(os.path.join(TEMPLATE, "src", "**", "*.java"), recursive=True)
    javac = os.path.join(jdk["home"], "bin", toolchain.exe("javac"))
    run([javac, "--release", "11", "-classpath", android_jar, "-encoding", "UTF-8", "-nowarn", "-d", classes] + sources,
        env, "javac")
    dex_dir = os.path.join(build, "dex")
    os.makedirs(dex_dir)
    class_files = glob.glob(os.path.join(classes, "**", "*.class"), recursive=True)
    run([os.path.join(bt, toolchain.script("d8")), "--release", "--min-api", str(MIN_SDK), "--lib", android_jar,
         "--output", dex_dir] + class_files, env, "d8")
    with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(dex_dir, "classes.dex"), "classes.dex")

    # ---- align + sign -------------------------------------------------------------------------
    aligned = os.path.join(build, "aligned.apk")
    run([os.path.join(bt, toolchain.exe("zipalign")), "-f", "-p", "4", unsigned, aligned], env, "zipalign")
    if ks == DEBUG_KS:
        ensure_debug_keystore(env, jdk)
        ks_pass, alias, key_pass = "android", "androiddebugkey", "android"
    else:
        ks_pass = a.ks_pass or os.environ.get("APK_KS_PASS")
        alias = a.key_alias or cfg.get("key_alias")
        key_pass = a.key_pass or os.environ.get("APK_KEY_PASS") or ks_pass
        if not (ks_pass and alias):
            die("own keystore needs --ks-pass (or APK_KS_PASS) and --key-alias")
        cfg["key_alias"] = alias
    apk = os.path.join(out, (ascii_slug(meta["id"]).replace("_", "-") or "course") + ".apk")
    apksigner = os.path.join(bt, toolchain.script("apksigner"))
    run([apksigner, "sign", "--ks", ks, "--ks-pass", "pass:" + ks_pass, "--ks-key-alias", alias,
         "--key-pass", "pass:" + key_pass, "--out", apk, aligned], env, "apksigner sign")
    certs = run([apksigner, "verify", "--print-certs", apk], env, "apksigner verify")
    if os.path.exists(apk + ".idsig"):
        os.remove(apk + ".idsig")

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    shutil.rmtree(build, ignore_errors=True)

    digest = re.search(r"SHA-256 digest: (\w+)", certs)
    subject = re.search(r"certificate DN: (.+)", certs)
    print("APK:       %s  (%d KB)" % (apk, os.path.getsize(apk) // 1024))
    print("App:       %s  ·  %s  ·  version %s (code %d)" % (cfg["label"], cfg["package"], cfg["version_name"], cfg["version_code"]))
    print("Android:   %s+ (minSdk %d), targetSdk %d" % ("7.0", MIN_SDK, api))
    print("Course:    %d files, %d KB" % (nfiles, nbytes // 1024))
    print("Signed:    %s  [%s]  cert SHA-256 %s" % (ks, subject.group(1).strip() if subject else "?",
                                                    digest.group(1)[:16] + "…" if digest else "?"))
    if os.path.isdir(os.path.join(course, "exercises")) and os.listdir(os.path.join(course, "exercises")):
        print("Note:      the course has code exercises — their 'Run tests' button needs a computer (start.sh); "
              "on the phone the page shows the test command instead.")
    if a.install:
        adb_install(sdk["adb"], apk, env)


if __name__ == "__main__":
    main()
