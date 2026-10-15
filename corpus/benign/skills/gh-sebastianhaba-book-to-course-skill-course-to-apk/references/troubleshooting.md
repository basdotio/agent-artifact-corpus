# Troubleshooting course-to-apk

## Toolchain
- **JDK installed but reported missing** — it may be a JRE (no `javac`/`keytool`) or older than 17 (the report lists
  too-old ones). Point `JAVA_HOME` at a JDK 17+ folder (the one containing `bin/javac`).
- **SDK in an unusual place** — set `ANDROID_HOME` to the folder that contains `build-tools/` and `platforms/`.
- **Only old build-tools / platform** — need build-tools 34+ and a platform android-34+; `toolchain.py` prints the
  `sdkmanager` command when sdkmanager exists, otherwise `setup_toolchain.py` can fetch them.
- **`setup_toolchain.py` checksum mismatch** — the download was interrupted or altered; run it again. Nothing is
  installed from a file that fails the check.
- **Behind a proxy** — Python's urllib honours `HTTPS_PROXY`; set it before running `setup_toolchain.py`.
- **Windows** — the scripts run with `py scripts\...`; tool names `.bat`/`.exe` are handled. `setup_toolchain.py`
  installs into `%LOCALAPPDATA%\course-to-apk`.

## Build
- **`aapt2 link` error about the label** — unusual characters in the course title; pass a simpler `--label`.
- **`javac` error** — usually a JDK older than 17 picked up via `JAVA_HOME`; check the JDK line of `toolchain.py`.
- **APK very large** — the course folder contains big media next to `index.html`. Everything except `content/`,
  `exercises/`, `progress/`, `.build/`, start scripts, README and zips is packed; move unrelated files out.

## Install on the device
- **"App not installed" / `INSTALL_FAILED_UPDATE_INCOMPATIBLE`** — an older build was signed with a different key
  (e.g. built on another computer, whose `~/.android/debug.keystore` differs). Uninstall the old app first (its
  progress is lost), or rebuild with the original key: copy that computer's `debug.keystore`, or use `--keystore`.
  To build the same app from several computers, use one shared keystore.
- **"Install blocked" / Play Protect** — sideloaded debug-signed apps trigger a warning; choose "Install anyway".
  Allow "install unknown apps" for the file manager / browser that opens the APK.
- **`INSTALL_FAILED_OLDER_SDK`** — the device runs Android older than 7.0; not supported.
- **`adb` sees no device** — USB debugging off, cable charge-only, or the authorization prompt on the phone not
  accepted. `adb devices` must show `device`, not `unauthorized`.

## Running
- **Blank page** — `course/data.js` missing in the course folder when the APK was built; rebuild the course
  (`build_course.py`) and then the APK.
- **Progress gone after reinstall** — uninstalling deletes app data; updating (install over) keeps it. Same package id + same key = update.
- **Progress from the computer is not on the phone** — they are separate stores (`progress/progress.json` vs the app's
  local storage); there is no sync.
