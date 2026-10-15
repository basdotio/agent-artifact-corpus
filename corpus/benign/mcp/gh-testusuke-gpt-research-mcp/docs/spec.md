# GPT Research MCP Server 実装仕様書

## 概要

OpenAI GPT-5.1 の Responses API と組み込み Web Search ツールを活用したリサーチ MCP サーバーを実装する。

## 技術スタック

| コンポーネント | 技術 |
|---------------|------|
| パッケージ管理 | uv |
| Python バージョン | 3.12 |
| MCP フレームワーク | FastMCP 2.0 |
| OpenAI クライアント | openai (公式ライブラリ) |
| モデル | gpt-5.1 |

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client                           │
│                 (Claude Desktop等)                      │
└─────────────────────┬───────────────────────────────────┘
                      │ STDIO
┌─────────────────────▼───────────────────────────────────┐
│                  FastMCP Server                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              @mcp.tool                            │  │
│  │         research(query: str)                      │  │
│  └───────────────────┬───────────────────────────────┘  │
└──────────────────────┼──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              OpenAI Responses API                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  model: gpt-5.1                                   │  │
│  │  tools: [web_search]                              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 依存関係

```toml
# pyproject.toml
[project]
name = "gpt-research-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.0.0",
    "openai>=1.0.0",
]
```

## 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `OPENAI_API_KEY` | ✅ | OpenAI API キー |

## MCP ツール仕様

### `research(query: str) -> str`

**説明**: GPT-5.1 の Web Search 機能を使用してクエリを調査し、結果を返す

**パラメータ**:
- `query` (str): 調査したい質問やトピック

**戻り値**:
- `str`: GPT-5.1 が生成したリサーチ結果（引用情報を含む）

**内部処理**:
1. OpenAI クライアントを初期化
2. Responses API を呼び出し（`web_search` ツール付き）
3. レスポンスからテキストと引用を抽出
4. フォーマットして返却

## 実装コード

### main.py

```python
import os
from fastmcp import FastMCP
from openai import OpenAI

# FastMCP サーバーインスタンス
mcp = FastMCP(name="GPT Research Server")

# OpenAI クライアント（環境変数から自動で API キーを読み込み）
client = OpenAI()


@mcp.tool
def research(query: str) -> str:
    """
    GPT-5.1とWeb検索を使用してクエリを調査します。

    Args:
        query: 調査したい質問やトピック

    Returns:
        調査結果（引用情報を含む）
    """
    # Responses API で Web Search を実行
    response = client.responses.create(
        model="gpt-5.1",
        tools=[
            {
                "type": "web_search",
                "search_context_size": "medium",  # low/medium/high
            }
        ],
        input=query,
    )

    # レスポンステキストを取得
    result_text = response.output_text

    # 引用情報を抽出してフォーマット
    citations = []
    for item in response.output:
        if hasattr(item, 'type') and item.type == "message":
            for content in item.content:
                if hasattr(content, 'annotations'):
                    for annotation in content.annotations:
                        citations.append(f"- [{annotation.title}]({annotation.url})")

    # 結果と引用を結合
    if citations:
        result_text += "\n\n## Sources\n" + "\n".join(citations)

    return result_text


if __name__ == "__main__":
    mcp.run()
```

## ディレクトリ構成

```
gpt-research-mcp/
├── .python-version      # Python 3.12
├── pyproject.toml       # プロジェクト設定
├── uv.lock              # 依存関係ロック
├── main.py              # MCPサーバー実装
├── docs/
│   └── spec.md          # この仕様書
└── README.md            # 使用方法
```

## 使用方法

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

```bash
export OPENAI_API_KEY="sk-..."
```

### 3. サーバーの起動

```bash
uv run python main.py
```

### 4. Claude Desktop への登録

`~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gpt-research": {
      "command": "uv",
      "args": ["run", "python", "/path/to/gpt-research-mcp/main.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## OpenAI Responses API リファレンス

### 基本的な Web Search 呼び出し

```python
response = client.responses.create(
    model="gpt-5.1",
    tools=[{"type": "web_search"}],
    input="検索クエリ",
)
```

### 設定オプション

#### search_context_size
Web から収集する情報量を制御:
- `low`: 最速だが情報量少
- `medium`: バランス（デフォルト）
- `high`: 詳細だが遅い・コスト高

#### user_location
地域ベースの結果を最適化:
```python
"user_location": {
    "type": "approximate",
    "country": "JP",
    "city": "Tokyo",
    "timezone": "Asia/Tokyo"
}
```

### レスポンス構造

```python
response.output_text  # 生成されたテキスト
response.output       # 詳細な出力配列（メッセージ、引用等）
```

### 引用の抽出

```python
for item in response.output:
    if item.type == "message":
        for content in item.content:
            if hasattr(content, 'annotations'):
                for annotation in content.annotations:
                    print(f"Title: {annotation.title}")
                    print(f"URL: {annotation.url}")
```

## 参考リンク

- [OpenAI Web Search Tool Guide](https://platform.openai.com/docs/guides/tools-web-search)
- [OpenAI Cookbook: Responses API](https://cookbook.openai.com/examples/responses_api/responses_example)
- [GPT-5.1 Model Documentation](https://platform.openai.com/docs/models/gpt-5.1)
- [FastMCP Documentation](https://gofastmcp.com/tutorials/create-mcp-server)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OpenAI Python Library](https://github.com/openai/openai-python)
