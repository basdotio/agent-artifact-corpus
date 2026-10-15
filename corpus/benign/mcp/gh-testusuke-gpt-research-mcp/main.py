import os

from fastmcp import FastMCP

# FastMCP サーバーインスタンス
mcp = FastMCP(
    name="gpt-search-mcp",
    instructions="An AI agent with advanced web search capabilities. Useful for finding the latest information, troubleshooting errors, and discussing ideas or design challenges. Supports natural language queries."
)


def _langfuse_enabled() -> bool:
    """LangFuse環境変数がすべて設定されているか確認"""
    required_vars = [
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_BASE_URL",
    ]
    return all(os.environ.get(var) for var in required_vars)


def _create_openai_client():
    """環境変数に基づいてOpenAIクライアントを作成"""
    if _langfuse_enabled():
        from langfuse.openai import OpenAI
    else:
        from openai import OpenAI
    return OpenAI()


# OpenAI クライアント（LangFuse有効時は自動トレース）
client = _create_openai_client()


@mcp.tool
def research(query: str) -> str:
    """
    Ask questions, search for information, or consult about complex problems in English.
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
