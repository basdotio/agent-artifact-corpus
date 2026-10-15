# LangFuse Integration Specification

## Overview

GPT Research MCPサーバーにLangFuseトレーシングを統合し、OpenAI API呼び出しの可観測性を実現する。

## Requirements

### 環境変数による条件付き有効化

LangFuseは以下の3つの環境変数が**すべて設定されている場合のみ**有効化される：

```env
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com  # or https://us.cloud.langfuse.com
```

環境変数が不足している場合は、通常のOpenAI SDKを使用する（フォールバック動作）。

## Implementation Design

### 1. パッケージ追加

```bash
uv add langfuse
```

`langfuse` パッケージには OpenAI 統合が含まれている。

### 2. OpenAI クライアント初期化の変更

#### 現在の実装 (main.py:2,8)
```python
from openai import OpenAI
client = OpenAI()
```

#### 新しい実装
```python
import os

def _langfuse_enabled() -> bool:
    """LangFuse環境変数がすべて設定されているか確認"""
    required_vars = [
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_BASE_URL"
    ]
    return all(os.environ.get(var) for var in required_vars)

def _create_openai_client():
    """環境変数に基づいてOpenAIクライアントを作成"""
    if _langfuse_enabled():
        # LangFuse統合を使用
        from langfuse.openai import OpenAI
        return OpenAI()
    else:
        # 通常のOpenAI SDKを使用
        from openai import OpenAI
        return OpenAI()

client = _create_openai_client()
```

### 3. トレース属性の付与（オプション拡張）

LangFuseでは `metadata` パラメータを通じてトレース属性を追加できる：

```python
response = client.responses.create(
    model="gpt-5.1",
    tools=[...],
    input=query,
    # LangFuse用メタデータ（有効時のみ使用される）
    name="research-tool",
    metadata={
        "langfuse_session_id": session_id,  # オプション
        "langfuse_user_id": user_id,        # オプション
        "langfuse_tags": ["research", "web-search"],
    }
)
```

### 4. フラッシュ処理

短期実行アプリケーションでは、終了前にLangFuseキューをフラッシュする必要がある：

```python
if _langfuse_enabled():
    from langfuse import get_client
    get_client().flush()
```

MCPサーバーは長期実行のため、通常は自動バッチ処理で十分。

## File Changes

### main.py

```python
import os
from fastmcp import FastMCP

# FastMCP サーバーインスタンス
mcp = FastMCP(name="GPT Research Server")


def _langfuse_enabled() -> bool:
    """LangFuse環境変数がすべて設定されているか確認"""
    required_vars = [
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_BASE_URL"
    ]
    return all(os.environ.get(var) for var in required_vars)


def _create_openai_client():
    """環境変数に基づいてOpenAIクライアントを作成"""
    if _langfuse_enabled():
        from langfuse.openai import OpenAI
        return OpenAI()
    else:
        from openai import OpenAI
        return OpenAI()


# OpenAI クライアント（LangFuse有効時は自動トレース）
client = _create_openai_client()


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
                "search_context_size": "medium",
            }
        ],
        input=query,
        # LangFuse用（有効時のみ使用される、無効時は無視される）
        name="research",
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

### pyproject.toml

```toml
[project]
name = "gpt-research-mcp"
version = "0.1.0"
description = "GPT-5.1 Web Search を使用したリサーチ MCP サーバー"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.0.0",
    "openai>=1.0.0",
    "langfuse>=2.0.0",
]
```

## Testing

### LangFuse有効時のテスト

```bash
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_BASE_URL="https://cloud.langfuse.com"
uv run python main.py
```

### LangFuse無効時のテスト（フォールバック確認）

```bash
unset LANGFUSE_SECRET_KEY
unset LANGFUSE_PUBLIC_KEY
unset LANGFUSE_BASE_URL
uv run python main.py
```

## Verification

LangFuse有効時、以下がLangFuseダッシュボードで確認可能：

- プロンプト/コンプリーション
- レイテンシ
- APIエラー
- トークン使用量とコスト (USD)

## Notes

1. **後方互換性**: LangFuse環境変数が未設定の場合、既存動作を維持
2. **パフォーマンス**: LangFuseはバックグラウンドでキューイング/バッチ処理を行うため、APIレスポンスへの影響は最小限
3. **OpenAI Responses API**: LangFuseのドキュメントは `chat.completions` APIを例示しているが、drop-in replacementのため `responses` APIでも動作する想定（要検証）
4. **サンプリング**: 本番環境でトレース量を制御したい場合は `LANGFUSE_SAMPLE_RATE` 環境変数で調整可能
