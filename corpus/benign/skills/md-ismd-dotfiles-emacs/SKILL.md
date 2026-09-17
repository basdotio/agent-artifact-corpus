---
name: emacs
description: Assist with Emacs configuration in dotfiles
user-invocable: true
---

# Emacs Configuration Skill

Help with editing and maintaining the Emacs configuration in this dotfiles repository.

## Trigger

Use this skill when asked to modify, add, or troubleshoot Emacs configuration including packages, keybindings, modules, and custom functions.

## Configuration Structure

The Emacs config uses **literate programming** with org-babel. All code is in `.org` files:

```
dot_config/emacs/
├── config.org              # Main entry point (loads modules, fonts, daemon)
├── early-init.el           # Pre-initialization
├── init.el                 # Bootstrap (loads config.org)
├── lisp/                   # Elisp utilities
└── modules/
    ├── core.org            # Defaults, utilities, basic editing
    ├── ui.org              # Dashboard, modeline, icons, visual
    ├── completion.org      # Vertico, Corfu, Consult, Orderless
    ├── keybindings.org     # General.el keybinding system
    ├── ai.org              # Claude, Copilot, GPTel
    ├── files.org           # Dired, Dirvish, Treemacs, project.el
    ├── languages.org       # LSP (Eglot), tree-sitter, language modes
    ├── notes.org           # Org mode, Denote notes
    ├── shells.org          # Vterm, Eshell, Eat terminals
    ├── vcs.org             # Magit, git-gutter, git-timemachine
    ├── themes.org          # Theme packages
    └── archive.org         # Legacy configs
```

## Package Manager: Elpaca

Uses **Elpaca** (modern, fast, git-based) instead of package.el/straight.el:
```elisp
(use-package some-package
  :ensure (:host github :repo "user/repo")
  :config ...)
```

Key Elpaca keywords:
- `:ensure t` - install from MELPA
- `:ensure (:host github :repo "...")` - install from GitHub
- `:wait t` - block until installed (for dependencies)

## Module Overview

| Module | Purpose | Key Packages |
|--------|---------|--------------|
| **core.org** | Defaults, auto-save, backups, editing | envrc, super-save, expand-region, multiple-cursors, mwim |
| **ui.org** | Visual enhancements | doom-modeline, dashboard, nerd-icons, which-key, winum, perspective |
| **completion.org** | Completion system | vertico, corfu, consult, orderless, marginalia, embark |
| **keybindings.org** | Keybinding system | general.el (all bindings defined here) |
| **ai.org** | AI assistants | claude-code, claude-code-ide, gptel, copilot, copilot-chat |
| **files.org** | File management | dirvish, treemacs, project.el, rg |
| **languages.org** | Programming support | eglot, treesit-auto, dart-mode, go-mode, elpy, terraform-mode |
| **org-config.org** | Notes & Org mode | denote, org-bullets, org-appear, ox-gfm |
| **shells.org** | Terminals | vterm, vterm-toggle, eshell, eat |
| **vcs.org** | Git integration | magit, git-gutter, git-timemachine |
| **themes.org** | Themes | ef-themes (default: ef-owl), doom-themes, modus-themes |

## Keybinding System

Uses **general.el** with organized prefixes:

| Prefix | Domain |
|--------|--------|
| `C-c a` | AI |
| `C-c b` | Buffers |
| `C-c d` | Dired |
| `C-c e` | Errors |
| `C-c f` | Files |
| `C-c h` | Help |
| `C-c l` | LSP |
| `C-c m` | Multiple Cursors |
| `C-c n` | Notes |
| `C-c o` | Org |
| `C-c p` | Project |
| `C-c s` | Search |
| `C-c t` | Toggle |
| `C-c v` | VCS |
| `C-c w` | Workspaces |

**Global shortcuts:**
- `M-1` to `M-9` - Window switching (winum)
- `M-s` - Jump to char (avy)
- `C-s` - Search in buffer (consult-line)
- `C-a/C-e` - Smart line navigation (mwim)
- `C-k` - Delete to EOL

All keybindings go in `modules/keybindings.org`:

```elisp
(ismd/leader-keys-C-c
  "x" '(:ignore t :wk "prefix-name")
  "x a" '(command-name :wk "description"))
```

## Custom Functions (ismd/ prefix)

| Function | Purpose |
|----------|---------|
| `ismd/reload-buffer` | Revert without confirmation |
| `ismd/delete-word`, `ismd/delete-word-backward` | Word deletion |
| `ismd/delete-line` | Delete to EOL |
| `ismd/delete-this-file` | Delete file and buffer |
| `ismd/fold-toggle`, `ismd/fold-close-all`, `ismd/fold-open-all` | Smart folding (treesit or kirigami) |
| `ismd/dirvish-dual-pane` | Side-by-side file browser |
| `ismd/open-emacs-config` | Edit config.org |
| `ismd/window-split-toggle` | Toggle H/V split |

## File Locations

| Path | Purpose |
|------|---------|
| `~/Nextcloud/Notes/` | Org agenda & Denote notes |
| `~/.config/emacs/custom.el` | Custom variables (API keys loaded here) |
| `~/.config/emacs/.perspectives` | Saved workspace state |
| `~/.local/share/Trash/files` | Backup files |

## Key Technical Constraints

- Package manager: **Elpaca** (not package.el/straight.el)
- LSP: **Eglot** (not lsp-mode)
- Completion: **Vertico+Corfu** (not Ivy/Helm/Company)
- Diagnostics: **Flymake** (not flycheck)
- Keybindings: **general.el**
- Fonts: FiraCode Nerd Font (mono: 130, variable: 140), Noto Color Emoji
- Tree-sitter: Auto-installed via treesit-auto
- Daemon: Auto-starts in config.org

## Instructions

### Before making changes

1. Read the relevant module file(s) to understand existing structure
2. Check `keybindings.org` if adding keybindings
3. Maintain org-babel code block format with proper headers

### Adding a new package

Place in the appropriate module with this pattern:

```org
** Package Name
Description of what this package does.

#+begin_src emacs-lisp
(use-package package-name
  :ensure t  ; or :ensure (:host github :repo "user/repo")
  :hook (mode-name . package-mode)
  :custom
  (setting-name value)
  :config
  (setup-code))
#+end_src
```

### Adding hooks

Use `:hook` with a **named function** (not a lambda) to avoid duplicate entries on re-evaluation. Define the function in `:preface` — it runs before the package loads and before other keywords, so it's always available even with deferred loading:

```elisp
(use-package some-package
  :ensure t
  :preface
  (defun ismd/my-hook-function ()
    "Docstring."
    (do-something))
  :hook (some-mode . ismd/my-hook-function))
```

Avoid `(add-hook ... (lambda ...))` — each re-evaluation adds a new lambda object since Emacs compares lambdas by identity, not equality.

### Adding a new module

1. Create `modules/new-module.org` with org-babel code blocks
2. Add `(ismd/load-module "new-module")` to `config.org`
3. Place in correct loading order (dependencies first)

### Modifying AI integrations

- Claude Code: `modules/ai.org` → `claude-code` and `claude-code-ide` sections
- GPTel: `modules/ai.org` → `gptel` section (Anthropic backend configured)
- Copilot: `modules/ai.org` → `copilot` and `copilot-chat` sections

### Theme customization

- Default theme: `ef-owl` (ef-themes)
- Override: Create `~/.config/emacs/theme.el` with `(load-theme 'theme-name t)`
- Available: ef-themes, doom-themes, modus-themes, nord-theme