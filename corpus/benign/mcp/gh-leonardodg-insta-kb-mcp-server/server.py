"""Insta Knowledge Base — MCP Server.

Exposes the Instagram-saved-posts pipeline (RabbitMQ queue + ig-worker) and
the knowledge base (Postgres + pgvector + local LLM) as MCP tools, for use
from an MCP client (OpenCode, Claude Desktop, etc.).

Ported from minimax-video-factory's `minimax_mcp/server.py` -- same
decorator/Field/`{"ok": bool, ...}` pattern -- but pared down to only the
tools whose underlying modules have been migrated to this project:
`ig_sync.py`/`queue.py`/`ig_worker.py` (Instagram) and `knowledge.py`/
`vault.py` (knowledge base). The video-generation tools (`submit_scene`,
`generate_video`, ...) stay in minimax-video-factory; they are out of scope
here.

LOCATION NOTE: this package is named `mcp_server`, not `mcp` -- `fastmcp`
itself depends on the `mcp` SDK package, and `src` is on `sys.path` for
this project (editable install), so a local `src/mcp/` package would shadow
the real `import mcp` fastmcp needs and break at import time. `mcp_server`
avoids that collision while still mirroring the existing `src/api/` /
`src/app/` sibling layout.

Run (stdio):
  uv run python src/mcp_server/server.py

Configuration: `core.settings.config.settings` (MCP_TRANSPORT, MCP_HOST,
MCP_PORT, and everything infra.queue/infra.instagram/core.knowledge read).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from core.contracts import (
    AskOk,
    ControlCommandOk,
    ErrResult,
    ExportDocumentsOk,
    ExportSearchOk,
    ListDocumentsOk,
    ProgressOk,
    QueueStatusOk,
    ReindexOk,
    SearchOk,
)
from core.knowledge import knowledge
from core.settings.config import settings
from infra import db
from infra.instagram import ig_sync
from infra.queue import queue as ig_queue
from services import ig_control

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("mcp_server")

mcp = FastMCP("insta-knowledge-base")


# =============================================================================
# Instagram saved posts -> queue -> ig-worker
# =============================================================================


@mcp.tool()
def ig_sync_saved(
    reprocessar: bool = Field(
        default=False,
        description=(
            "Reenfileira TUDO, inclusive o que já está no banco. "
            "O padrão (False) publica só os ig_pk novos."
        ),
    ),
) -> dict[str, Any]:
    """Enfileira os posts salvos do Instagram (via IG_SESSIONID) na fila ig.saved.

    Não processa nada -- o daemon ig-worker consome a fila em background.
    Publica CONFORME enumera, uma coleção por vez, então o worker já começa a
    trabalhar antes de a varredura terminar.
    Retorna {ok, published, skipped_existing, descartados, total}.
    `descartados` são os posts que a listagem não conseguiu converter e pulou;
    o payload cru de cada um fica em `IG_DESCARTADOS_FILE`.
    """
    if not ig_sync.IG_SESSIONID:
        return {"ok": False, "error": ig_sync.SESSIONID_MISSING}
    conn = ig_queue.connect()
    try:
        channel = conn.channel()
        ig_queue.declare(channel)
        session = db.get_session()
        try:
            existing = db.list_ig_pks(session)
        finally:
            session.close()
        client = ig_sync.make_client()

        def progresso(ev: dict[str, Any]) -> None:
            logger.info(
                "ig_sync: %s -> %d na coleção, %d publicados, %d pulados "
                "(acumulado: %d)",
                ev["collection"],
                ev["in_collection"],
                ev["published"],
                ev["skipped"],
                ev["published_total"],
            )

        return ig_sync.sync_saved_posts(
            client,
            existing_pks=existing,
            publish_fn=lambda msg: ig_queue.publish(channel, msg),
            progress_fn=progresso,
            reprocessar=reprocessar,
        )
    except Exception as e:
        return {"ok": False, "error": f"ig_sync_saved failed: {e}"}
    finally:
        ig_queue.close(conn)


@mcp.tool()
def ig_queue_status() -> QueueStatusOk | ErrResult:
    """Mostra o tamanho da fila ig.saved (ready/dead) e quantos consumidores ativos."""
    return ig_control.queue_status()


@mcp.tool()
def ig_worker_start() -> ControlCommandOk | ErrResult:
    """Envia o comando 'start' ao daemon ig-worker (retoma o consumo da fila)."""
    return ig_control.publish_control_command("start")


@mcp.tool()
def ig_worker_stop() -> ControlCommandOk | ErrResult:
    """Envia o comando 'stop' ao daemon ig-worker (pausa o consumo da fila)."""
    return ig_control.publish_control_command("stop")


@mcp.tool()
def ig_get_progress(
    last_n: int = Field(
        default=10, description="Quantos últimos resultados processados mostrar"
    ),
) -> ProgressOk | ErrResult:
    """Mostra os últimos N posts do Instagram processados pelo ig-worker
    (state file)."""
    return ig_control.get_progress(last_n)


# =============================================================================
# Knowledge base
# =============================================================================


@mcp.tool()
def knowledge_ingest_text(
    text: str = Field(description="Texto/transcrição já pronta para processar"),
    source_url: str | None = Field(
        default=None, description="URL de origem, se houver"
    ),
    title: str | None = Field(default=None, description="Título do documento"),
    platform: str = Field(
        default="manual", description="Origem: manual, instagram, youtube, podcast"
    ),
) -> dict[str, Any]:
    """Gera resumo+tutorial via LLM local e salva um texto/transcrição já pronto
    na base de conhecimento."""
    return knowledge.ingest_text(
        text, source_url=source_url, title=title, platform=platform
    )


@mcp.tool()
def knowledge_ingest_markdown(
    path: str = Field(
        description="Arquivo .md ou diretório (ex.: caminho do Obsidian) a importar"
    ),
    recursive: bool = Field(
        default=False, description="Se path for diretório, incluir subdiretórios"
    ),
    doc_type: str = Field(
        default="document",
        description="Tipo do documento na base (ex.: document, tutorial)",
    ),
) -> dict[str, Any]:
    """Importa um ou mais arquivos markdown (ex.: tutoriais do Obsidian) para a
    base de conhecimento. Aproveita YAML frontmatter (title/tags/url) e reutiliza
    `## Summary` se houver; senão gera via LLM."""
    return knowledge.ingest_markdown(path, recursive=recursive, doc_type=doc_type)


@mcp.tool()
def knowledge_ingest_video(
    url: str = Field(description="URL do vídeo (Instagram Reel, YouTube, etc.)"),
    browser: str = Field(default="chrome", description="Navegador para cookies"),
    whisper_model: str = Field(
        default=settings.WHISPER_MODEL, description="Tamanho do modelo Whisper"
    ),
) -> dict[str, Any]:
    """Baixa, transcreve e documenta um vídeo na base de conhecimento (resumo +
    tutorial via LLM)."""
    return knowledge.ingest_video(
        url,
        browser=browser,
        downloads_dir=settings.IG_DOWNLOADS_DIR,
        whisper_model=whisper_model,
        whisper_device=settings.WHISPER_DEVICE,
    )


@mcp.tool()
def knowledge_ingest_audio(
    path_or_url: str = Field(
        description="Caminho local de um áudio/podcast, ou URL para baixar"
    ),
    browser: str = Field(
        default="chrome", description="Navegador para cookies (se for URL)"
    ),
    whisper_model: str = Field(
        default=settings.WHISPER_MODEL, description="Tamanho do modelo Whisper"
    ),
) -> dict[str, Any]:
    """Transcreve e documenta um áudio/podcast na base de conhecimento (resumo +
    tutorial via LLM)."""
    return knowledge.ingest_audio(
        path_or_url,
        browser=browser,
        downloads_dir=settings.IG_DOWNLOADS_DIR,
        whisper_model=whisper_model,
        whisper_device=settings.WHISPER_DEVICE,
    )


@mcp.tool()
def knowledge_search(
    query: str = Field(
        description="Termo ou pergunta para buscar na base de conhecimento"
    ),
    top_k: int = Field(default=5, description="Número máximo de resultados"),
) -> SearchOk | ErrResult:
    """Busca na base de conhecimento (palavra-chave + semântica) e retorna os
    documentos mais relevantes."""
    return knowledge.search(query, top_k=top_k)


@mcp.tool()
def knowledge_ask(
    query: str = Field(
        description="Pergunta em linguagem natural sobre o que já foi salvo"
    ),
    top_k: int = Field(default=3, description="Quantos documentos usar como contexto"),
) -> AskOk | ErrResult:
    """Responde a uma pergunta usando RAG sobre a base de conhecimento (busca + LLM)."""
    return knowledge.ask(query, top_k=top_k)


@mcp.tool()
def knowledge_reindex(
    embedding_model: str | None = Field(
        default=None,
        description="Modelo de embedding a usar (default: EMBEDDING_MODEL)",
    ),
) -> ReindexOk | ErrResult:
    """Recalcula chunks e embeddings de todos os documentos (use após trocar de
    modelo de embedding)."""
    return knowledge.reindex(embedding_model=embedding_model)


@mcp.tool()
def kb_list_documents(
    limit: int = Field(default=20, description="Quantos documentos por página"),
    offset: int = Field(default=0, description="Quantos documentos pular"),
    platform: str | None = Field(
        default=None,
        description="Filtra por origem (ex.: instagram, youtube, manual)",
    ),
    doc_type: str | None = Field(
        default=None, description="Filtra por categoria (video, audio, text, markdown)"
    ),
    tag: str | None = Field(default=None, description="Filtra por uma tag exata"),
) -> ListDocumentsOk | ErrResult:
    """Lista o catálogo completo de documentos (paginado, mais recente
    primeiro), com filtros por categoria/origem/tag -- navegue por tudo que
    já está documentado, sem precisar de uma busca, para decidir o que
    exportar com kb_export."""
    return knowledge.list_documents(
        limit=limit, offset=offset, platform=platform, doc_type=doc_type, tag=tag
    )


@mcp.tool()
def kb_export_search(
    query: str | None = Field(
        default=None,
        description="Texto para buscar em título/resumo/conteúdo (opcional)",
    ),
    ids: list[int] | None = Field(
        default=None, description="IDs diretos dos documentos (opcional)"
    ),
    limit: int = Field(default=20, description="Número máximo de resultados"),
) -> ExportSearchOk | ErrResult:
    """Lista documentos para export -- por IDs, por busca, ou os mais recentes.
    Não grava nada; use a lista para confirmar e depois chamar kb_export."""
    return knowledge.export_search(query=query, ids=ids, limit=limit)


@mcp.tool()
def kb_export(
    ids: list[int] = Field(
        description=(
            "IDs dos documentos a exportar (confirme antes com kb_export_search)"
        )
    ),
    output_dir: str = Field(
        default="output/kb-export/",
        description=(
            "Diretório de destino dos .md (os arquivos caem em <output_dir>/Knowledge/)"
        ),
    ),
) -> ExportDocumentsOk | ErrResult:
    """Exporta os documentos selecionados como arquivos .md legíveis."""
    return knowledge.export_documents(ids=ids, output_dir=output_dir)


# ---------------- entrypoint ----------------
def main() -> None:
    transport = settings.MCP_TRANSPORT
    if transport in ("stdio", "http", "streamable-http", "sse"):
        logger.info(
            "Starting Insta Knowledge Base MCP server (transport=%s)", transport
        )
        if transport == "stdio":
            mcp.run(transport="stdio")
        else:
            kwargs: dict[str, Any] = {
                "host": settings.MCP_HOST,
                "port": settings.MCP_PORT,
            }
            # "http" is accepted above as an alias but FastMCP's actual
            # transport name is "streamable-http" -- both need /mcp, or
            # .mcp.json's http://.../mcp 404s (review finding, 2026-10-07).
            if transport in ("streamable-http", "http"):
                kwargs["path"] = "/mcp"
            mcp.run(transport=transport, **kwargs)
    else:
        sys.exit(
            f"Unknown MCP_TRANSPORT={transport!r} "
            "(use stdio, http, streamable-http or sse)"
        )


if __name__ == "__main__":
    main()
