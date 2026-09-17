---
name: storage-state
description: Playwright の storage_state.json を生成・管理してログイン情報を固定する実装を行う際に使用。「ログイン状態を保存したい」「storage_state.json を作りたい・再生成したい」「Cookie が切れた」「セッションが切れた」「認証を自動化したい」という依頼で起動。生成スクリプト実装 → ユーティリティー実装 → 自動化スクリプトへ組み込み の流れで進める。
---

# storage-state スキル

Playwright の `storage_state.json`（Cookie + localStorage の保存形式）を使って
ログイン状態を固定し、自動化スクリプトで再利用する実装パターンを提供します。
特定のプロジェクトに依存せず、Playwright を使う任意のプロジェクトに適用できます。

## いつ使うか

- ログインが必要なサイトの自動化で、毎回ログイン処理を実行したくない
- `storage_state.json` が存在しない / 古くなった（目安: 7日以上）
- ログイン失敗・セッション切れが発生した
- 新規プロジェクトで認証保持の仕組みを実装する

## 実装構成

```
your_package/
├── generate_storage_state.py   # headful 起動 → 手動ログイン → JSON保存
└── utils/
    └── storage_state.py        # パス取得・ディレクトリー作成・鮮度チェック
```

---

## Step 1: ユーティリティーを実装する

`utils/storage_state.py` に以下のパターンを実装します。

```python
"""Playwright storage state ユーティリティー。"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def get_storage_state_path() -> Path:
    """環境変数 STORAGE_STATE_PATH からパスを返す。未設定時は KeyError。"""
    v = os.environ.get("STORAGE_STATE_PATH")
    if not v:
        raise KeyError("STORAGE_STATE_PATH is required (set env or .env)")
    return Path(v)


def ensure_storage_state_dir(path: Path) -> None:
    """保存先の親ディレクトリーを作成する。"""
    path.parent.mkdir(parents=True, exist_ok=True)


def is_storage_state_stale(path: Path, *, days: int) -> bool:
    """ファイルが days 日より古い（または存在しない）場合 True を返す。"""
    if not path.exists():
        return True
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return True
    return datetime.now() - mtime > timedelta(days=days)


def warn_if_storage_state_stale(path: Path) -> None:
    """古い場合に WARNING ログを出力する（起動時に呼び出す）。

    環境変数:
      STORAGE_STATE_WARN_ENABLED: true（デフォルト）で有効
      STORAGE_STATE_WARN_DAYS: 警告閾値の日数（デフォルト 7）
    """
    enabled = os.environ.get("STORAGE_STATE_WARN_ENABLED", "true").lower() in {
        "1", "true", "yes", "on"
    }
    if not enabled:
        return
    try:
        days = int(os.environ.get("STORAGE_STATE_WARN_DAYS", "7"))
    except Exception:
        days = 7
    if is_storage_state_stale(path, days=days):
        logger.warning(
            "storage_state:stale_or_missing",
            path=str(path),
            warn_after_days=days,
        )
```

---

## Step 2: 生成スクリプトを実装する

`generate_storage_state.py` に以下のパターンを実装します。
headful ブラウザを起動し、手動ログイン後に Enter を押すと JSON を保存します。

```python
"""Playwright storage_state.json 生成スクリプト（headful）。

使い方:
    uv run python -m your_package.generate_storage_state

環境変数:
    STORAGE_STATE_PATH  : 保存先パス（必須）
    LOGIN_URL           : ブラウザで開く URL（必須）
    BROWSER_CHANNEL     : chrome | msedge（デフォルト: chrome）
    BROWSER_LOCALE      : ブラウザのロケール（デフォルト: ja-JP）
    PATCH_WEBDRIVER     : 自動化検出の緩和（デフォルト: true）
"""
from __future__ import annotations

import os
from contextlib import suppress

import structlog
from playwright.sync_api import sync_playwright

from .utils.storage_state import ensure_storage_state_dir, get_storage_state_path

logger = structlog.get_logger(__name__)


def main() -> None:
    storage_path = get_storage_state_path()
    ensure_storage_state_dir(storage_path)

    login_url = os.environ.get("LOGIN_URL")
    if not login_url:
        raise KeyError("LOGIN_URL is required")

    channel = os.environ.get("BROWSER_CHANNEL", "chrome")
    locale = os.environ.get("BROWSER_LOCALE", "ja-JP")

    logger.info("storage_state:generate:start", path=str(storage_path), channel=channel)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel=channel,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        ctx = browser.new_context(locale=locale)

        # navigator.webdriver を undefined 化して自動化検出を緩和
        if os.environ.get("PATCH_WEBDRIVER", "true").lower() in {"1", "true", "yes", "on"}:
            ctx.add_init_script("""
                () => {
                    try {
                        const proto = window.navigator.__proto__;
                        delete proto.webdriver;
                    } catch (e) {}
                }
            """)

        page = ctx.new_page()
        page.goto(login_url, wait_until="load")

        logger.info(
            "please_login_then_press_enter",
            url=login_url,
            message="ログイン完了後にターミナルへ戻り Enter を押してください",
        )
        try:
            input("[待機] ログイン完了後に Enter を押してください...")
        except KeyboardInterrupt:
            logger.warning("storage_state:generate:interrupted")
            # ユーザーが中断した場合は storage_state.json を保存せずに終了する
            with suppress(Exception):
                ctx.close()
            with suppress(Exception):
                browser.close()
            return

        ctx.storage_state(path=str(storage_path))
        logger.info("storage_state:generate:done", path=str(storage_path))

        with suppress(Exception):
            ctx.close()


if __name__ == "__main__":
    main()
```

---

## Step 3: 自動化スクリプトへ組み込む

生成した `storage_state.json` を `browser.new_context()` の `storage_state` 引数に渡します。

```python
from playwright.sync_api import sync_playwright
from .utils.storage_state import get_storage_state_path, warn_if_storage_state_stale

def run_automation() -> None:
    storage_path = get_storage_state_path()
    warn_if_storage_state_stale(storage_path)   # 古い場合に WARNING

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=str(storage_path))
        page = ctx.new_page()
        # ... 自動化処理 ...
        ctx.close()
```

---

## Step 4: 環境変数を設定する

`.env` ファイルに以下を追加します（`.env.sample` としてサンプルを同梱推奨）。

```dotenv
# 必須
STORAGE_STATE_PATH=storage_state/storage_state.json
LOGIN_URL=https://example.com/login

# 任意
BROWSER_CHANNEL=chrome
BROWSER_LOCALE=ja-JP
PATCH_WEBDRIVER=true
STORAGE_STATE_WARN_ENABLED=true
STORAGE_STATE_WARN_DAYS=7
```

生成を実行する場合:

```powershell
# PowerShell
$env:STORAGE_STATE_PATH = "storage_state/storage_state.json"
$env:LOGIN_URL = "https://example.com/login"
uv run python -m your_package.generate_storage_state
```

---

## セキュリティー注意事項

- `storage_state.json` には **認証 Cookie / トークンが含まれます**
- `.gitignore` に必ず追加し、リポジトリにコミットしないこと
- ファイルパーミッションを制限する（所有者のみ読み取り可）
- CI/CD で使用する場合はシークレット管理サービス（GitHub Secrets / Secret Manager 等）経由で注入すること

```gitignore
# .gitignore に必ず追加
**/storage_state/*.json
storage_state.json
```

---

## テストパターン

鮮度チェック関数はファイルシステムに依存するため、`tmp_path` フィクスチャーで単体テストできます。

```python
from pathlib import Path
from your_package.utils.storage_state import is_storage_state_stale

def test_正常系_存在するファイルは古くない(tmp_path: Path) -> None:
    f = tmp_path / "storage_state.json"
    f.write_text("{}")
    assert is_storage_state_stale(f, days=7) is False

def test_正常系_存在しないファイルはstale(tmp_path: Path) -> None:
    f = tmp_path / "storage_state.json"
    assert is_storage_state_stale(f, days=7) is True
```

---

## トラブルシューティング

### ブラウザが起動しない

- `uv run playwright install chromium` でブラウザをインストール
- `BROWSER_CHANNEL` に指定したブラウザがローカルにインストール済みか確認

### Enter を押してもセッションが保存されない

- ログイン後のホーム画面が完全に表示されてから Enter を押す
- 2段階認証が途中の場合は認証を完了させてから Enter を押す

### 自動化スクリプト実行時にログインを求められる

- `STORAGE_STATE_PATH` の値が生成時と実行時で一致しているか確認
- `storage_state.json` のタイムスタンプを確認し、古ければ再生成する
- サイト側で IP や UA が変わると Cookie が無効になる場合がある
