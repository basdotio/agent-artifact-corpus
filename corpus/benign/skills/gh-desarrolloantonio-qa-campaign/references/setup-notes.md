# Setup notes

The detail behind steps 5 and 6 of `SKILL.md` §2.1. Read it when you reach them: the rules are there,
the reasons and the traps are here.

## Devices

### The allow-list is the harness's, not adb's

Once `devices` lists anything the scripts refuse every other device — but that guard is theirs alone:
an `adb install`, an `adb reverse`, a `settings put` or a Gradle task typed straight into the shell
goes wherever adb decides. Carry the device on each of them —
`ANDROID_SERIAL="$(ui.py serial qa)" adb install app.apk`, same prefix for `installDebug` and
`connectedAndroidTest`, which honour it too. Per command: a shell variable doesn't survive between
calls. 
### Name an emulator by its AVD, not by its serial

List it as
`"qa": "avd:Resizable_Experimental"` — not by its serial: `emulator-5554` is only *whichever
emulator booted first*, so the same serial can name another campaign's emulator tomorrow
(measured). Start emulators with `-port <even number>` so their serial can be found from the
process list. A project-side script that talks to the device (a store reader, an injector) gets
the serial from `ui.py serial <alias>` — `avd:…` is not a serial.

### More than one app in the repo

The devices question asks **which one** first: the module,
the flavor and the build type, and the `applicationId` read from that module's build file. A
monorepo with dozens of application modules has dozens of ids, and `android.package` holds exactly
one — picked wrong, every command drives another app that looks just like it (audit). Record the
answer next to the device in `CAMPAIGN.md`; `installed --apk` then ties the device to that build.

## Credentials

### Say what the file is for in the same message

"The agent never types a password" next to "put the password in this file" reads as a contradiction —
measured twice, in two projects. One sentence settles it: *the scripts read it to
sign in through the API, check the server and inject the session into the app; I never see the
password and never type it into the login screen — the one typed login is yours.*


### The project already keeps test credentials somewhere

`e2e.properties`, `.env.test`, a copied CI secrets file. When the
project's own scripts — an adapter, an injection test — already read it, **use it as it is** and
name it as the source in `CAMPAIGN.md`: a second copy that nothing reads is one more place for the
passwords to leak from (measured). Only for scripts written now, and never by asking the human to
copy them: generate `qa.credentials.json` from that file with a short script that writes
the values without printing them and reports only the keys it filled. Leave the original where it
is — whatever reads it still does — and record it as the source in `CAMPAIGN.md`, so a changed
password is regenerated rather than debugged.


### No credentials anywhere

Create the file for the human to fill in: add it to `.gitignore`
first (step 7), then write it with mode `600` and **empty values**, in the shape this server signs
in with, for the accounts agreed in step 3 — `{"accounts": {"A": {"username": "", "password":
""}}}`. Give its path and say what goes in each field. When the human says it is filled in, check
that no value is empty, naming keys only.
