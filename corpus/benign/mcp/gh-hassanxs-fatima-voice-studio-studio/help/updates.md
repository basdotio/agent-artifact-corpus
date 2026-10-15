# Updates and uninstalling

## How you hear about a new version

The installed app checks GitHub for a new version when it starts and every 6 hours. When there is one:

- a dot appears on the menu button at the top right (and on **About** inside it),
- a short message says which version is out,
- Windows shows a notification once for each new version, and
- the footer at the bottom of every page says *update available*.

Open **About** (in the menu at the top right) and look at the **Updates** card. It lists what's new in plain words, with a link to the
release page on GitHub.

## Quick update or Full update

| | What it does | Takes |
|---|---|---|
| **Quick update** | Replaces only the app's own files. A few MB. | a few seconds |
| **Full update** | Downloads the new installer and runs it. About 35 MB. | about a minute |

Use **Quick update** when it's offered. It isn't offered when the new version also changes the parts the app runs
on (its bundled Python, for example); then only **Full update** is shown.

Both check the download before installing it, close the app, update it and start it again by itself. Your voices,
models, settings, pronunciation list, presets and audio are kept.

If an update was skipped, the Updates card lists what's new in every version since yours.

**Check now** checks straight away. Untick **Check automatically** to stop the checks; you can still check by hand.

You can also install a new version over the old one by running its installer from the
[releases page](https://github.com/hassanxs/fatima-voice-studio/releases). Your data is kept.

## Uninstall

Uninstall from **Windows Settings → Apps → Installed apps → Fatima Voice Studio → Uninstall**.

It asks whether to also delete the downloaded models, engine and settings. Answering **Yes** also deletes your
pronunciation list, channel presets and transcripts (they're kept with the settings), so
[export the pronunciation list](pronunciation.md#import-and-export) first if you want it. **Your voice library and
your audio are always kept**: delete `Music\Fatima Voice Studio` and `%LOCALAPPDATA%\Fatima Voice Studio\voices` yourself if you
want them gone. See [Files and folders](files-and-folders.md).
