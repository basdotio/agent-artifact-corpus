# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import logging
import os
import re

import aiohttp
from azure.core.exceptions import ResourceNotFoundError
from semantic_kernel.functions import kernel_function

from data_models.chat_artifact import ChatArtifact, ChatArtifactFilename, ChatArtifactIdentifier
from data_models.chat_context import ChatContext
from data_models.data_access import DataAccess
from data_models.plugin_configuration import PluginConfiguration

logger = logging.getLogger(__name__)


def create_plugin(plugin_config: PluginConfiguration):
    return GraphRagPlugin(
        graph_rag_url=plugin_config.agent_config.get("graph_rag_url"),
        subscription_key=os.environ.get("GRAPH_RAG_SUBSCRIPTION_KEY"),
        index_name=plugin_config.agent_config.get("graph_rag_index_name"),
        chat_ctx=plugin_config.chat_ctx,
        data_access=plugin_config.data_access,
    )


class GraphRagPlugin:
    def __init__(self, graph_rag_url: str, subscription_key: str, index_name: str, chat_ctx: ChatContext, data_access: DataAccess) -> None:
        self.graph_rag_url = graph_rag_url
        self.subscription_key = subscription_key
        self.index_name = index_name
        self.chat_ctx = chat_ctx
        self.data_access = data_access

    @kernel_function()
    async def process_prompt(self, prompt: str) -> tuple[str, dict]:
        """
        Processes a prompt using the Graph RAG API and returns the text and sources in a dictionary.
        The text will contain text with references such as  [Data: Sources (78721, 78722)]. or [Data: Sources (78721, 78722); Entities (178146, 11551)]

        The sources will be a dictionary, with the source ID as the key and a dictionary with the title, authors, and link as the value.
        The text can be used to generate a response with links to the sources.
        """
        headers = {"Ocp-Apim-Subscription-Key": self.subscription_key}
        body = {
            "index_name": self.index_name,
            "query": prompt,
            "community_level": 2
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.graph_rag_url}/query/local", json=body, headers=headers) as resp:
                resp.raise_for_status()
                resp = await resp.json()
                result = resp["result"]
                sources = resp["context_data"].get("sources", [])

            formatted_sources = {}
            for source in sources:
                title_match = re.search(r"title:\s*(.+?)\.", source["text"])
                pmid_match = re.search(r"pmid:\s*(\d+)", source["text"])
                authors_match = re.search(r"authors:\s*(.+?)\.", source["text"])

                title = title_match.group(1) if title_match else None
                pmid = pmid_match.group(1) if pmid_match else None
                authors = authors_match.group(1) if authors_match else None
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
                formatted_link = f"[{title}]({link})"

                # The same link can be used for multiple sources, but we're only going to display one link for each source.
                # We'll replace the source ID in the text with the PMID, and use that at the bottom for generating the reference.
                formatted_sources[pmid] = {
                    "title": title,
                    "authors": authors,
                    "link": formatted_link,
                    "url": link,
                }

                result = result.replace(source["id"], pmid)

        # Save results for Word document
        await self._save_research_papers(formatted_sources)

        return {"text": result, "sources": formatted_sources}

    async def _save_research_papers(self, papers: dict) -> None:
        artifact_id = ChatArtifactIdentifier(
            conversation_id=self.chat_ctx.conversation_id,
            patient_id=self.chat_ctx.patient_id,
            filename=ChatArtifactFilename.RESEARCH_PAPERS,
        )

        try:
            # Merge with existing research papers
            artifact = await self.data_access.chat_artifact_accessor.read(artifact_id)
            artifact_str = artifact.data.decode("utf-8")
            research_papers = json.loads(artifact_str)
            research_papers.update(papers)
        except ResourceNotFoundError:
            research_papers = papers

        await self.data_access.chat_artifact_accessor.write(
            ChatArtifact(artifact_id=artifact_id, data=json.dumps(research_papers).encode("utf-8"))
        )
