---
name: streamerbot-import
description: Generate Streamer.bot import codes/files (actions, C# sub-actions, commands) that are imported with the Import button. Use when the user asks to "create a file to import into Streamer.bot", for a Streamer.bot export/import string, or to decode a U0JBRR… code.
---

# Streamer.bot import codes

Tested successfully: import of 14 C# actions into Streamer.bot 0.2.x.

## Format

`base64( b"SBAE" + gzip(json_utf8) )`

- The text always starts with `U0JBRR` (which is "SBAE" in base64).
- To import it: **Import** in Streamer.bot, then drag the `.txt` file or paste it into *Import String*.
- The official docs don't document it. It was derived by decoding:
  - examples from docs.streamer.bot (the `"code"` values on the `/examples/*` pages, with `\u002F` in place of `/`);
  - public repositories.

## Root JSON

```json
{ "meta": { "name": "…", "author": "…", "version": "1.0.0", "description": "…",
            "autoRunAction": null, "minimumVersion": null },
  "data": { "actions": [ACTION…], "queues": [], "commands": [COMMAND…],
            "websocketServers": [], "websocketClients": [], "timers": [] },
  "version": 10, "exportedFrom": "0.2.5", "minimumVersion": "0.2.4" }
```

## Action

```json
{ "id": "<uuid4>", "queue": null, "enabled": true, "excludeFromHistory": false,
  "name": "Group · Name", "group": "Group", "alwaysRun": false, "randomAction": false,
  "concurrent": false, "triggers": [], "actions": [SUB_ACTION…],
  "actionGroups": [], "collapsedGroups": [] }
```

Sub-actions go in `"actions"`, not `subActions`. Each one carries these common fields:
- `"id"` (uuid4)
- `"weight": 0.0`
- `"type"`
- `"group": null`
- `"enabled": true`
- `"index"` (order, starting at 0)

## Known sub-action types (`type`)

Derived from decoding ~350 public exports (docs.streamer.bot and GitHub). Names are inferred from the fields and how the exports use them.

**Core**

| type | Sub-action | Own fields |
|---|---|---|
| 99999 | Execute C# Code | `name`, `description`, `references` (.dll paths), `byteCode` (= **base64 of the source code**, not compiled), `precompile`, `delayStart`, `saveResultToVariable`, `saveToVariable`, `keepAlive` |
| 99998 | Execute C# Method | `executeCodeId` (id of a 99999 sub-action), `method`, `runOnUiThread`, `saveResultToVariable`, `saveToVariable` |
| 4 | Run Action | `actionId`, `runImmedately` (sic, misspelled) |
| 1002 | Delay | `value` (ms, string), `random`, `maxValue` |
| 120 | If/Else | `variableName`, `operation`, `value`, `autoType`, `actionId`, `runImmediately`, `afterAction`, `elseActionId`, `elseRunImmediately`, `elseAfterAction` |
| 123 | Set Argument | `variableName`, `value`, `autoType` |
| 121 | Get Global/User Variable | `variableName`, `destinationVariable`, `defaultValue`, `source`, `persisted` |
| 122 | Set Global/User Variable | `variableName`, `value`, `source`, `destination`, `persisted` |
| 1003 | Get Random Number | `randomType`, `min`, `max` |
| 1007 | Fetch URL | `url`, `variableName`, `headers` (object), `parseAsJson` |
| 1009 | Comment | `value`, `color` |
| 1004 | Set Action State | `actionId`, `state` |
| 1011 | Set Action Group State | `groupName`, `state` |
| 1001 | Set Action Queue State | `actionQueueId`, `state`, `clear` |
| 9 | Set Command State | `commandId`, `state` |
| 8 | Set Timer State | `timerId`, `state` |
| 1013 | Get Commands | `variableName`, `groupName`, `includeAll`, `hasPermission`, `ignoreAliases` |
| 3 | Write To File | `file`, `text`, `append` |
| 6 | Run a Program | `command`, `arguments`, `workingDir`, `envVars`, `waitForExit` |
| 1012 | Keypress | `key`, `modifiers` |
| 1 | Play Sound | `soundFile`, `volume` (0.0–1.0), `finishBeforeContinuing`, `device`, `soundName`, `useFileNameAsName` |
| 7 | Play Random Sound (folder) | `folder`, `recursive`, `volume`, `finishBeforeContinuing`, `device`, `soundName`, `useFileNameAsName` |
| 601 | Text to Speech | `alias`, `message`, `badWordFilter` |
| 1023 | User Input Dialog | `title`, `prompt`, `originalText`, `outputVariable`, `autoTypeOutput` |
| 1024 | Show Toast Notification | `title`, `text`, `attribution`, `iconPath`, `toastId` |

**Twitch**

| type | Sub-action | Own fields |
|---|---|---|
| 10 | Send Message | `text`, `preferredAccount`, `useBot`, `fallback` |
| 560 | Reply to Message | `replyId`, `text`, `preferredAccount`, `useBot`, `fallback` |
| 23 | Announcement | `text`, `color`, `preferredAccount`, `useBot`, `fallback` |
| 20 | Timeout User | `userLogin`, `duration`, `reason`, `excludeModerators`, … |
| 29 | Shoutout | `userLogin` |
| 15 | Set Title | `title` |
| 16 | Set Game | `game`, `gameId`, `source` |
| 17 | Create Stream Marker | `description` |
| 200 | Set Reward State | `rewardId`, `state` |
| 202 | Set Reward Cost | `rewardId`, `cost`, `operator` |
| 205 | Set Reward Title | `rewardId`, `title` |
| 206 | Set Reward Prompt | `rewardId`, `prompt` |

**YouTube / Discord**

| type | Sub-action | Own fields |
|---|---|---|
| 4001 | YouTube: Send Message | `text`, `broadcast`, `preferredAccount` |
| 4003 | YouTube: Set Description | `description`, `broadcast` |
| 7001 | Discord: Webhook | `webhookUrl`, `content`, `username`, `avatar`, `image`, `textToSpeech` |

**OBS** (all carry `connectionId`)

| type | Sub-action | Own fields |
|---|---|---|
| 34 | Set Current Scene | `sceneName` |
| 30 | Set Source Visibility | `sceneName`, `sourceName`, `state` |
| 35 | Set Source Filter State | `sceneName`, `sourceName`, `filterName`, `state` |
| 47 | Set Scene Filter State | `sceneName`, `filterName`, `state` |
| 38 | Set Browser Source URL | `sceneName`, `sourceName`, `url` |
| 39 | Set GDI Text | `sceneName`, `sourceName`, `text` |
| 322 | Set Media Source File | `sceneName`, `sourceName`, `fileName` |
| 48 | Take Screenshot | `sceneName`, `sourceName`, `path`, `quality` |
| 33 | Set Streaming State | `state` |
| 45 | Set Recording State | `state` |
| 46 | Raw | `name`, `raw` (JSON `{"requestType":…,"requestData":…}`), `resultsToArgs`, `prefix` |

For `state`, 2 = toggle. The meaning of 0/1 is not confirmed and may differ per type, so check it with an exported example.

**Prefer C# (99999):**
- It is the most reliable type.
- It can do anything Streamer.bot allows through the `CPH.*` methods.

For other types the number is unknown, so never invent it. Instead, either:
- use C#; or
- ask the user to export an example and decode it.

Known command trigger: `{"commandId":"<command uuid>","id":"<uuid>","type":401,"enabled":true,"exclusions":[]}`.

## Generator (Python, no dependencies)

```python
import json, uuid, base64, gzip

def csharp(name, code, index=0):
    return {"name": name, "description": "",
            "references": [r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\mscorlib.dll",
                           r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.dll"],
            "byteCode": base64.b64encode(code.encode()).decode(),
            "precompile": False, "delayStart": False, "saveResultToVariable": False, "saveToVariable": "",
            "id": str(uuid.uuid4()), "weight": 0.0, "type": 99999, "group": None, "enabled": True, "index": index}

def action(name, group, subs, triggers=()):
    return {"id": str(uuid.uuid4()), "queue": None, "enabled": True, "excludeFromHistory": False,
            "name": name, "group": group, "alwaysRun": False, "randomAction": False, "concurrent": False,
            "triggers": list(triggers), "actions": subs, "actionGroups": [], "collapsedGroups": []}

def export(name, author, actions, commands=()):
    doc = {"meta": {"name": name, "author": author, "version": "1.0.0", "description": "",
                    "autoRunAction": None, "minimumVersion": None},
           "data": {"actions": actions, "queues": [], "commands": list(commands),
                    "websocketServers": [], "websocketClients": [], "timers": []},
           "version": 10, "exportedFrom": "0.2.5", "minimumVersion": "0.2.4"}
    s = base64.b64encode(b"SBAE" + gzip.compress(json.dumps(doc, ensure_ascii=False).encode())).decode()
    # self-check
    assert s.startswith("U0JBRR") and json.loads(gzip.decompress(base64.b64decode(s)[4:])) == doc
    return s
```

C# template:

```csharp
using System;

public class CPHInline
{
    public bool Execute()
    {
        // ...
        return true;
    }
}
```

Remember to escape JSON quotes inside C# strings (`\"`).

## Decoding an existing code

```python
s = open("code.txt").read().strip()
j = json.loads(gzip.decompress(base64.b64decode(s + "=" * (-len(s) % 4))[4:]))
```

This is useful for learning the `type` of a sub-action: ask the user to export an action that uses it, then decode it.

## Steps

1. Generate the `.txt` file with `export(...)` in the project folder, with a descriptive name.
2. If it contains C#, show the decoded code of one sub-action so it can be reviewed.
3. Tell the user how to import it:
   - **Import** in Streamer.bot → drag the file → **Import**;
   - accept the C# compilation if prompted.
4. If the import fails, offer the equivalent manual steps.
