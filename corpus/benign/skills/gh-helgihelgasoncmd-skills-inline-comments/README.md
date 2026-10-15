# inline-comments

**Leave instructions for Claude as comments in your code, then review each change before it lands.**

This is the "comment to change" half of the Copilot experience, built for Claude Code.
Write `@claude <what you want>` where you want it. Tell Claude "do my comments". Each
instruction becomes its own small edit, which you accept or reject in the IDE.

<p align="center">
  <img src="../../docs/inline-comments/walkthrough.gif" width="720" alt="Walkthrough: @claude comments in a file, each turned into a change with Accept and Reject buttons, then a summary of what was done, answered and skipped">
</p>

| 1. Leave a comment | 2. Accept or reject each change | 3. Get a summary |
|---|---|---|
| `@claude` asks for an edit, `@claude?` asks a question. | One small edit per comment, comment removed in the same edit. | Questions answered in chat; unclear comments skipped, never guessed. |

## Example

Before: [`examples/inline-comments/demo.py`](../../examples/inline-comments/demo.py)

```python
def fetch_user(user_id):
    # @claude add a 5 second timeout and raise a clear error on HTTP failure
    with urllib.request.urlopen(f"https://api.example.com/users/{user_id}") as r:
        return json.load(r)


def full_name(user):
    return user["first"] + " " + user["last"]  # @claude handle a missing "last" key


def greeting(user):
    # @claude? why would this break for users with no name at all
    return "Hello, " + full_name(user)
```

> **You:** do my comments in examples/inline-comments/demo.py

Claude makes two edits and leaves the question alone:

```diff
 def fetch_user(user_id):
-    # @claude add a 5 second timeout and raise a clear error on HTTP failure
-    with urllib.request.urlopen(f"https://api.example.com/users/{user_id}") as r:
-        return json.load(r)
+    url = f"https://api.example.com/users/{user_id}"
+    try:
+        with urllib.request.urlopen(url, timeout=5) as r:
+            return json.load(r)
+    except urllib.error.HTTPError as e:
+        raise RuntimeError(f"fetching user {user_id} failed: HTTP {e.code}") from e
```

```diff
 def full_name(user):
-    return user["first"] + " " + user["last"]  # @claude handle a missing "last" key
+    return " ".join(p for p in (user["first"], user.get("last")) if p)
```

```
demo.py:8   done      — 5s timeout, HTTPError re-raised with the user id
demo.py:14  done      — missing "last" now yields just the first name
demo.py:18  answered  — full_name() still indexes user["first"], so a user with
                        no name raises KeyError before greeting() builds the string
```

The exact code Claude writes will vary. What stays the same: one edit per marker, each
marker removed in the edit that handles it, and `@claude?` questions answered in chat
without touching the file.

## Markers

| Comment | Meaning |
|---|---|
| `// @claude make this async` | Do it, then remove the comment |
| `x = load()  # @claude cache this` | Do it; only the comment is removed, the code stays |
| `/* @claude split this into` <br> `   two functions */` | Instructions can span lines in a block comment |
| ` * @claude handle overflow` inside a `/** … */` | Only that line of the doc comment is removed |
| `# @claude? is this thread safe` | Question only: answered in chat, the file isn't changed |

Comments in C-family, JS/TS, Go, Rust, Python, shell, YAML, TOML, Terraform, PHP, SQL,
Lua, CSS and HTML are supported. The scanner deliberately ignores strings, template
literals and Markdown. See [the limits](references/limits.md) for details.

## Reviewing each change (VS Code)

The review step comes from the Claude Code VS Code extension, not from this skill:

1. Install the **Claude Code** extension, version **2.1.275 or later**. That version
   added per-change review.
2. Set the permission mode to **Manual**, using the mode indicator in the prompt box.
   You can also make it the default with `"claudeCode.initialPermissionMode": "default"`
   in your settings. In this mode Claude asks before every file edit instead of applying
   it.
3. When an edit is proposed, the diff opens with **Accept this change** /
   **Reject this change** buttons under each change. You can also edit the proposed code
   directly before accepting, and Claude sees what you changed.

The skill makes a separate edit for each marker, which gives the diff view the best
chance of showing one reviewable change per comment. How changes are grouped is up to
the IDE, though, and diffs with more than 100 changes fall back to whole-file
accept/reject. Docs: https://code.claude.com/docs/en/vs-code

There is no ghost-text tab completion. Claude Code doesn't offer it, and a skill can't
add it.

## Install

As a plugin (Claude Code 2.1.275 or later):

```
/plugin install helgi-skills --marketplace HelgiHelgasonCMD/skills
```

On older versions, in two steps:

```
/plugin marketplace add HelgiHelgasonCMD/skills
/plugin install helgi-skills@helgi-skills
```

Without the plugin system, copy the skill folder:

```bash
git clone https://github.com/HelgiHelgasonCMD/skills
cp -r skills/skills/inline-comments ~/.claude/skills/
```

Then, in any project, write a marker, ask Claude to *"do my comments"*, and review the
diffs.
