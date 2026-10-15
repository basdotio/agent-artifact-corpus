#!/usr/bin/env python3
"""Find the tools needed to build a course APK, and say exactly what is missing.

Usage:  toolchain.py [--json]

Needed (no Gradle, no Android Studio):
  * JDK 17+            javac, keytool        (java for d8/apksigner)
  * Android SDK with
      build-tools 34+  aapt2, d8, zipalign, apksigner
      platforms;android-NN (NN >= 34)  android.jar
  * optional: platform-tools (adb) — only to install straight onto a connected device

Exit code 0 = ready to build, 1 = something is missing (the report says what and where to get it).
Tools are searched in the usual places even when they are not on PATH (JAVA_HOME, ANDROID_HOME, ~/Android/Sdk,
~/.jdks, Android Studio's bundled JBR, /usr/lib/jvm, …) and in the folder setup_toolchain.py installs into.
"""
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys

MIN_JDK = 17
MIN_BUILD_TOOLS = 34
MIN_PLATFORM = 34
WIN = os.name == "nt"
HOME = os.path.expanduser("~")
# setup_toolchain.py installs here; nothing outside this folder (and ~/.android for the debug key) is touched.
OWN_DIR = os.environ.get("COURSE_TO_APK_HOME") or (
    os.path.join(os.environ.get("LOCALAPPDATA", HOME), "course-to-apk") if WIN
    else os.path.join(HOME, ".local", "share", "course-to-apk"))


def exe(name):
    return name + ".exe" if WIN else name


def script(name):
    return name + ".bat" if WIN else name


def _version_key(s):
    return [int(x) for x in re.findall(r"\d+", s)] or [0]


# ---- JDK -----------------------------------------------------------------------------------------
def _jdk_major(java_home):
    rel = os.path.join(java_home, "release")
    if os.path.exists(rel):
        m = re.search(r'JAVA_VERSION="(\d+)(?:\.(\d+))?', open(rel, encoding="utf-8", errors="replace").read())
        if m:
            return 8 if m.group(1) == "1" else int(m.group(1))
    try:
        out = subprocess.run([os.path.join(java_home, "bin", exe("javac")), "-version"],
                             capture_output=True, text=True, timeout=30)
        m = re.search(r"javac (\d+)(?:\.(\d+))?", out.stdout + out.stderr)
        if m:
            return 8 if m.group(1) == "1" else int(m.group(1))
    except (OSError, subprocess.SubprocessError):
        pass
    return 0


def _jdk_candidates():
    seen = []

    def add(p):
        if not p:
            return
        p = os.path.realpath(p)
        if p not in seen and os.path.exists(os.path.join(p, "bin", exe("javac"))):
            seen.append(p)

    add(os.environ.get("JAVA_HOME"))
    for tool in ("javac", "java"):
        w = shutil.which(tool)
        if w:
            add(os.path.dirname(os.path.dirname(os.path.realpath(w))))
    pats = [os.path.join(OWN_DIR, "jdk*"), os.path.join(HOME, ".jdks", "*"),
            os.path.join(HOME, ".sdkman", "candidates", "java", "*"), os.path.join(HOME, ".asdf", "installs", "java", "*"),
            "/usr/lib/jvm/*", "/usr/java/*", "/opt/jdk*", "/opt/java/*",
            # Android Studio ships a full JDK ("JBR")
            "/opt/android-studio/jbr", os.path.join(HOME, "android-studio", "jbr"),
            os.path.join(HOME, ".local", "share", "JetBrains", "Toolbox", "apps", "android-studio*", "jbr"),
            os.path.join(HOME, ".local", "share", "JetBrains", "Toolbox", "apps", "*", "*", "jbr"),
            "/snap/android-studio/current/jbr",
            "/Library/Java/JavaVirtualMachines/*/Contents/Home",
            os.path.join(HOME, "Library", "Java", "JavaVirtualMachines", "*", "Contents", "Home"),
            "/Applications/Android Studio.app/Contents/jbr/Contents/Home",
            "/opt/homebrew/opt/openjdk*/libexec/openjdk.jdk/Contents/Home"]
    if WIN:
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
            pats += [os.path.join(base, v, "*") for v in ("Java", "Eclipse Adoptium", "Microsoft", "Zulu", "Android\\Android Studio")]
            pats.append(os.path.join(base, "Android", "Android Studio", "jbr"))
    for pat in pats:
        for p in sorted(glob.glob(pat)):
            add(p)
    return seen


def find_jdk():
    """Newest JDK >= MIN_JDK with javac and keytool, or (None, [found-but-too-old])."""
    good, old = [], []
    for home in _jdk_candidates():
        major = _jdk_major(home)
        if not os.path.exists(os.path.join(home, "bin", exe("keytool"))):
            continue
        (good if major >= MIN_JDK else old).append((major, home))
    if good:
        major, home = max(good)
        return {"home": home, "major": major}, old
    return None, old


# ---- Android SDK ---------------------------------------------------------------------------------
def _sdk_candidates():
    c = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"), os.path.join(OWN_DIR, "sdk")]
    if WIN:
        c.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk"))
    elif sys.platform == "darwin":
        c.append(os.path.join(HOME, "Library", "Android", "sdk"))
    else:
        c += [os.path.join(HOME, "Android", "Sdk"), "/opt/android-sdk", "/usr/lib/android-sdk", "/opt/android-sdk-linux"]
    for tool in ("adb", "sdkmanager", "aapt2"):
        w = shutil.which(tool)
        if w:  # <sdk>/platform-tools/adb, <sdk>/cmdline-tools/latest/bin/sdkmanager, <sdk>/build-tools/X/aapt2
            p = os.path.realpath(w)
            for up in (2, 3, 4):
                c.append(os.path.abspath(os.path.join(p, *[".."] * up)))
    out = []
    for p in c:
        if p and os.path.isdir(p) and os.path.realpath(p) not in out and (
                os.path.isdir(os.path.join(p, "build-tools")) or os.path.isdir(os.path.join(p, "platforms"))
                or os.path.isdir(os.path.join(p, "platform-tools")) or os.path.isdir(os.path.join(p, "cmdline-tools"))):
            out.append(os.path.realpath(p))
    return out


def _build_tools(sdk):
    need = [exe("aapt2"), script("d8"), exe("zipalign"), script("apksigner")]
    best = None
    for d in glob.glob(os.path.join(sdk, "build-tools", "*")):
        v = os.path.basename(d)
        if _version_key(v)[0] < MIN_BUILD_TOOLS or not all(os.path.exists(os.path.join(d, n)) for n in need):
            continue
        if best is None or _version_key(v) > _version_key(best[0]):
            best = (v, d)
    return best


def _api_level(platform_dir):
    props = os.path.join(platform_dir, "source.properties")
    if os.path.exists(props):
        m = re.search(r"AndroidVersion\.ApiLevel=(\d+)", open(props, encoding="utf-8", errors="replace").read())
        if m:
            return int(m.group(1))
    m = re.match(r"android-(\d+)", os.path.basename(platform_dir))
    return int(m.group(1)) if m else 0


def _platform(sdk):
    best = None
    for d in glob.glob(os.path.join(sdk, "platforms", "android-*")):
        if not os.path.exists(os.path.join(d, "android.jar")):
            continue
        api = _api_level(d)
        key = (api, _version_key(os.path.basename(d)))
        if api >= MIN_PLATFORM and (best is None or key > best[0]):
            best = (key, d)
    return {"api": best[0][0], "dir": best[1], "jar": os.path.join(best[1], "android.jar")} if best else None


def find_sdk():
    """Best SDK = the one that has both usable build-tools and a platform; otherwise the most complete one."""
    found = []
    for sdk in _sdk_candidates():
        bt, pl = _build_tools(sdk), _platform(sdk)
        adb = os.path.join(sdk, "platform-tools", exe("adb"))
        sdkm = None
        for cand in (os.path.join(sdk, "cmdline-tools", "latest", "bin", script("sdkmanager")),
                     *sorted(glob.glob(os.path.join(sdk, "cmdline-tools", "*", "bin", script("sdkmanager"))), reverse=True),
                     os.path.join(sdk, "tools", "bin", script("sdkmanager"))):
            if os.path.exists(cand):
                sdkm = cand
                break
        found.append({"root": sdk,
                      "build_tools": {"version": bt[0], "dir": bt[1]} if bt else None,
                      "platform": pl,
                      "adb": adb if os.path.exists(adb) else shutil.which("adb"),
                      "sdkmanager": sdkm})
    found.sort(key=lambda s: (bool(s["build_tools"]) and bool(s["platform"]), bool(s["build_tools"]),
                              bool(s["platform"]), bool(s["sdkmanager"])), reverse=True)
    return found[0] if found else None


# ---- report --------------------------------------------------------------------------------------
def detect():
    jdk, old_jdks = find_jdk()
    sdk = find_sdk()
    missing = []
    if not jdk:
        missing.append("jdk")
    if not sdk or not sdk["build_tools"]:
        missing.append("build-tools")
    if not sdk or not sdk["platform"]:
        missing.append("platform")
    return {"ready": not missing, "missing": missing, "jdk": jdk,
            "old_jdks": [{"major": m, "home": h} for m, h in old_jdks], "sdk": sdk,
            "os": sys.platform, "arch": platform.machine(), "install_dir": OWN_DIR}


def tool_env(info):
    """Environment for running d8/apksigner (they are scripts that need java on PATH / JAVA_HOME)."""
    env = dict(os.environ)
    if info.get("jdk"):
        env["JAVA_HOME"] = info["jdk"]["home"]
        env["PATH"] = os.path.join(info["jdk"]["home"], "bin") + os.pathsep + env.get("PATH", "")
    if info.get("sdk"):
        env["ANDROID_HOME"] = info["sdk"]["root"]
    return env


def install_help(info):
    """Human instructions: what to download and where from, for whatever is missing."""
    lines = []
    osname = info["os"]
    if "jdk" in info["missing"]:
        lines.append("JDK %d or newer (javac + keytool):" % MIN_JDK)
        if info["old_jdks"]:
            lines.append("  found only older: " + ", ".join("JDK %d at %s" % (j["major"], j["home"]) for j in info["old_jdks"]))
        lines.append("  download: https://adoptium.net/temurin/releases/?version=21  (Eclipse Temurin 21 LTS, .tar.gz/.zip/.msi/.pkg)")
        if osname.startswith("linux"):
            lines.append("  or package manager: Arch/CachyOS `sudo pacman -S jdk21-openjdk` · Debian/Ubuntu `sudo apt install openjdk-21-jdk-headless`"
                         " · Fedora `sudo dnf install java-21-openjdk-devel`")
        elif osname == "darwin":
            lines.append("  or Homebrew: `brew install --cask temurin@21`")
        elif osname.startswith("win"):
            lines.append("  or: `winget install EclipseAdoptium.Temurin.21.JDK`")
        lines.append("  (Android Studio users already have one in <Android Studio>/jbr — set JAVA_HOME to it)")
    if "build-tools" in info["missing"] or "platform" in info["missing"]:
        sdk = info["sdk"]
        lines.append("Android SDK packages: build-tools;%d.0.0 (or newer) and platforms;android-35 (or newer):" % 35)
        if sdk and sdk["sdkmanager"]:
            lines.append("  you already have sdkmanager — run:")
            lines.append('    "%s" --sdk_root="%s" "build-tools;35.0.0" "platforms;android-35"' % (sdk["sdkmanager"], sdk["root"]))
        else:
            lines.append("  1) 'Command line tools only' from https://developer.android.com/studio#command-line-tools-only")
            lines.append("     unzip so that the path is <SDK>/cmdline-tools/latest/bin/sdkmanager  (suggested <SDK>: %s)"
                         % (sdk["root"] if sdk else ("%%LOCALAPPDATA%%\\Android\\Sdk" if osname.startswith("win") else
                                                     "~/Library/Android/sdk" if osname == "darwin" else "~/Android/Sdk")))
            lines.append('  2) <SDK>/cmdline-tools/latest/bin/sdkmanager --sdk_root=<SDK> "build-tools;35.0.0" "platforms;android-35" "platform-tools"')
            lines.append("     (accept the Android SDK licence when asked; needs the JDK above)")
            lines.append("  or install Android Studio (https://developer.android.com/studio) — its SDK Manager installs the same packages.")
        lines.append("  then, if the SDK is not in a standard place, set ANDROID_HOME to it.")
    return lines


def describe(info):
    lines = []
    j = info["jdk"]
    lines.append("JDK:          " + ("OK  JDK %d  %s" % (j["major"], j["home"]) if j else "MISSING"))
    s = info["sdk"]
    lines.append("Android SDK:  " + (s["root"] if s else "MISSING"))
    if s:
        bt, pl = s["build_tools"], s["platform"]
        lines.append("  build-tools " + ("OK  %s" % bt["version"] if bt else "MISSING (need %d+ with aapt2, d8, zipalign, apksigner)" % MIN_BUILD_TOOLS))
        lines.append("  platform    " + ("OK  API %d  %s" % (pl["api"], os.path.basename(pl["dir"])) if pl else "MISSING (need android-%d+)" % MIN_PLATFORM))
        lines.append("  adb         " + ("OK  %s" % s["adb"] if s["adb"] else "not installed (optional — only for installing over USB)"))
    lines.append("")
    if info["ready"]:
        lines.append("READY — build_apk.py can build the APK.")
    else:
        lines.append("NOT READY — missing: " + ", ".join(info["missing"]))
        lines.append("")
        lines += install_help(info)
        lines.append("")
        lines.append("Automatic alternative (no sudo, installs only into %s; downloads ~%s):" % (
            info["install_dir"], "350 MB" if "jdk" in info["missing"] else "150 MB"))
        lines.append("  python3 setup_toolchain.py --accept-licenses")
    return "\n".join(lines)


def main():
    info = detect()
    if "--json" in sys.argv[1:]:
        info["help"] = install_help(info) if not info["ready"] else []
        print(json.dumps(info, indent=2))
    else:
        print(describe(info))
    sys.exit(0 if info["ready"] else 1)


if __name__ == "__main__":
    main()
