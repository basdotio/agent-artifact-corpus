"""FastMCP 服务：把书籍知识检索暴露为 MCP 工具。

设计要点（见 docs/plans/book-rag-mvp-impl-brief.md 文件清单 10）：
- 全局配置由 ``get_config()`` 从环境变量惰性初始化，便于测试替换；
- ``create_mcp`` 在创建服务时调用一次 ``refresh_all_indexes`` 做增量同步，
  保证服务启动后索引与书籍库一致；
- 对外暴露三个工具：search_book_knowledge / list_indexed_books / refresh_book_index。

工具的检索 / 列举 / 刷新逻辑以模块级函数实现并显式接受 ``config``，
FastMCP 注册的只是薄封装——测试无需启动服务即可覆盖全部行为。
"""

from __future__ import annotations

from fastmcp import FastMCP

from book_rag.config import BookRagConfig
from book_rag.rag.index import RefreshResult, refresh_all_indexes
from book_rag.rag.retriever import (
    SearchResult,
    _list_indexed_metas,
    search_books,
)

# 模块级全局配置，由 get_config() 惰性初始化
_CONFIG: BookRagConfig | None = None


def get_config() -> BookRagConfig:
    """返回全局配置；首次调用时从环境变量构建。"""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = BookRagConfig.from_env()
    return _CONFIG


def format_search_results(results: list[SearchResult], query: str = "") -> str:
    """把检索结果格式化为 Markdown 文本（含书名、章节、相关度、原文片段）。"""
    if not results:
        return f"未找到与查询「{query}」相关的内容。" if query else "未找到相关内容。"

    lines = [f"找到 {len(results)} 条相关片段：", ""]
    for i, r in enumerate(results, start=1):
        lines.append(f"### {i}. {r.book} · {r.section}（相关度 {r.score:.4f}）")
        lines.append("")
        lines.extend(f"> {line}" for line in r.content.splitlines())
        lines.append("")
    return "\n".join(lines).rstrip()


def format_refresh_result(result: RefreshResult) -> str:
    """把增量同步统计格式化为文本。"""
    parts = [
        (
            f"索引同步完成：新建/重建 {len(result.built)} 本，"
            f"跳过 {len(result.skipped)} 本，删除 {len(result.deleted)} 本。"
        )
    ]
    if result.built:
        parts.append("新建/重建：" + "、".join(result.built))
    if result.skipped:
        parts.append("跳过：" + "、".join(result.skipped))
    if result.deleted:
        parts.append("删除：" + "、".join(result.deleted))
    return "\n".join(parts)


def search_book_knowledge(
    query: str,
    *,
    config: BookRagConfig,
    top_k: int = 5,
    book: str | None = None,
    search_all_languages: bool = False,
) -> str:
    """检索书籍知识并返回 Markdown 格式的原文片段。

    Args:
        query: 查询文本。
        config: 全局配置。
        top_k: 最多返回的结果条数。
        book: 可选书籍过滤，支持书名 / 路径的部分匹配。
        search_all_languages: 为 True 时跨语言搜索全部书籍。
    """
    results = search_books(
        query,
        config=config,
        top_k=top_k,
        book=book,
        search_all_languages=search_all_languages,
    )
    return format_search_results(results, query=query)


def list_indexed_books(*, config: BookRagConfig) -> list[str]:
    """列出已索引书籍，每项形如 ``"书名 (语言: zh, 块数: 123)"``。"""
    metas = _list_indexed_metas(config.index_dir)
    return [
        f"{meta.book_path} (语言: {meta.language}, 块数: {meta.chunk_count})"
        for meta in metas
    ]


def refresh_book_index(*, config: BookRagConfig) -> str:
    """执行一次增量同步并返回统计文本。"""
    return format_refresh_result(refresh_all_indexes(config))


# 工具封装（create_mcp 内的同名 def）会遮蔽模块级实现，提前捕获引用
_search_impl = search_book_knowledge
_list_books_impl = list_indexed_books
_refresh_impl = refresh_book_index


def create_mcp(config: BookRagConfig | None = None) -> FastMCP:
    """创建并配置 FastMCP 服务实例。

    创建时先执行一次增量同步（服务启动即与书籍库保持一致），再注册三个工具。
    """
    config = config if config is not None else get_config()
    refresh_all_indexes(config)

    mcp = FastMCP("book-rag")

    @mcp.tool
    def search_book_knowledge(
        query: str,
        top_k: int = 5,
        book: str | None = None,
        search_all_languages: bool = False,
    ) -> str:
        """按内容检索书籍知识，返回书中相关原文片段（Markdown 格式）。

        Args:
            query: 查询文本。
            top_k: 最多返回的结果条数。
            book: 可选书籍过滤，支持书名 / 路径的部分匹配。
            search_all_languages: 为 True 时跨语言搜索全部书籍，
                默认只搜索与查询同语言的书籍。
        """
        return _search_impl(
            query,
            config=config,
            top_k=top_k,
            book=book,
            search_all_languages=search_all_languages,
        )

    @mcp.tool
    def list_indexed_books() -> list[str]:
        """列出所有已建立索引的书籍及其语言与块数。"""
        return _list_books_impl(config=config)

    @mcp.tool
    def refresh_book_index() -> str:
        """增量同步书籍库索引：新书建索引、变更重建、已删除的清理。"""
        return _refresh_impl(config=config)

    return mcp
