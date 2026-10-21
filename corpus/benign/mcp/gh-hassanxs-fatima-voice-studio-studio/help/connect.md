# Connect: API and AI agents

Fatima Voice Studio can be used from other programs as well as from its own pages:

- **Apps** that can use OpenAI's text-to-speech can use your PC instead, through the **OpenAI-compatible API**.
- **AI agents** (Claude Code, Codex, Antigravity, Hermes and others) can make voiceovers for you through **MCP**.

Everything you need to copy is on the **Connect** page, already filled in with your address and key. The app must
be running for either to work.

## The API key

Other programs prove they're allowed with the **API key**, a long password made when the app first started.
Copy it from the Connect page or from the tray menu (**Copy API key**). Requests without it are refused.

The API and MCP only listen on your own PC (`127.0.0.1`): other computers on your network can't reach them. If the
key was shared by mistake, change it in **Settings → App**, then update your apps and agents.

## OpenAI-compatible API

Base URL: `http://127.0.0.1:9830/v1` (copy it from the tray menu: **Copy API URL**). Send the key in the header
`Authorization: Bearer <API key>`.

| Endpoint | What it does |
|---|---|
| `POST /v1/audio/speech` | Text to speech. `voice` is a name from your library. Formats: mp3, wav, flac, pcm. Extras: `language`, `seed`. Any length: long text is split and joined. |
| `POST /v1/audio/transcriptions` | Speech to text with Whisper. Formats: json, text, srt, vtt, verbose_json. |
| `GET /v1/audio/voices` | Your voice library. |
| `GET /v1/models` | The installed models. |

Example in Python, with OpenAI's own library:

```python
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:9830/v1", api_key="<API key>")
client.audio.speech.create(model="qwen3-tts", voice="Narrator", input="Hello!").write_to_file("hello.mp3")
```

`model` is `qwen3-tts` (or `qwen3-tts-q4`), `omnivoice` / `omnivoice-q4` for OmniVoice, `chatterbox`, `voxcpm2`,
`cosyvoice3`, `kokoro`, `moss-tts-nano`, or `s2-pro` / `s2-pro-q6` for Fish Audio S2 Pro, once they're downloaded. Kokoro takes only its own
voices (the ones marked Kokoro).
S2 Pro is non-commercial, so AI agents only use it if you allow non-commercial models on this page.

API requests go ahead of batches, so an app doesn't wait for the queue. The full, interactive list of endpoints is
at `http://127.0.0.1:9830/docs`.

## AI agents (MCP)

[MCP](https://modelcontextprotocol.io) lets an AI agent use the studio's tools: list your voices, start a batch,
wait for it, fix parts and export the result. On the Connect page, pick your agent's tab and copy the setup:

- **Claude Code** — one command to paste in a terminal.
- **Codex**, **Antigravity**, **Hermes** — a few lines for the agent's settings file (the file's path is in the
  first line).
- **Other (stdio)** — for agents that can only start a local program.

For Claude Code, the command looks like this (with your own key):

```
claude mcp add --scope user --transport http fatima-voice-studio http://127.0.0.1:9830/mcp --header "Authorization: Bearer <API key>"
```

Then ask the agent in plain words, for example: *"Make a voiceover of script.txt on my Desktop with the Narrator
voice, wait for it, and export it as a ZIP."*

### What agents can do

| Tools | What they do |
|---|---|
| `list_voices`, `list_models`, `get_settings`, `list_presets` | See what's available. |
| `speak` | One piece of text right away, ahead of batches. |
| `create_batch` | Start a batch: scripts as text or `.txt` files, each with its own voice and language if wanted. Takes a preset by name. |
| `list_batches`, `get_batch`, `wait_for_batch` | Follow batches, get file paths, find parts worth a listen. |
| `regenerate_part`, `edit_part`, `edit_script`, `retry_failed` | Fix parts and scripts. |
| `control_batch`, `rename_batch`, `move_in_queue` | Pause, resume, cancel, rename, reorder. |
| `export_batch` | Copy a batch, or a ZIP of it, to the Exports folder. |
| `add_voice` | Add a voice from a clip; the agent must confirm the speaker's permission. |
| `transcribe` | Text and subtitles of an audio or video file. |
| `list_pronunciations`, `add_pronunciation`, `preview_reading` | Use and add to your pronunciation list. |

### Guard rails

You stay in charge of what agents can touch:

- Agents **can't download** models or **delete** anything.
- They only **write** to the Exports folder.
- They only **read** files (voice clips, scripts) from the folders listed on the Connect page, plus Batches and
  Exports. By default: Music, Downloads, Desktop and Documents. Edit the list and click **Save guard rails**.
- They can't use a **non-commercial** model unless you tick *Let agents use non-commercial models*. None is
  installed today.

## The port

The address uses port **9830**. If another program already uses it, change it in **Settings → App → Port** and
restart the app; then update the address in your apps and agents (the Connect page shows the new one).
