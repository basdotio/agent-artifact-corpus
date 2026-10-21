# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import base64
import logging
from datetime import datetime, timezone
from time import time

from azure.storage.blob.aio import BlobServiceClient

from data_models.chat_artifact import ChatArtifact, ChatArtifactIdentifier

logger = logging.getLogger(__name__)


class ChatArtifactAccessor:
    """Accessor for reading and writing chat artifacts to Azure Blob Storage."""

    def __init__(self, blob_service_client: BlobServiceClient, container_name: str = "chat-artifacts"):
        self.blob_service_client = blob_service_client
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self.container_name = container_name

    async def archive(self, conversation_id: str) -> str:
        start = time()
        try:
            base64_conv_id = base64.urlsafe_b64encode(conversation_id.encode("utf-8")).decode("utf-8")

            # Archive all chat artifacts for the conversation
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            async for blob_name in self.container_client.list_blob_names(name_starts_with=base64_conv_id):
                new_blob_name = f"{timestamp}_{blob_name}"
                blob_client = self.container_client.get_blob_client(blob_name)
                new_blob_client = self.container_client.get_blob_client(new_blob_name)
                await new_blob_client.start_copy_from_url(blob_client.url, requires_sync=True)
                await blob_client.delete_blob()
        finally:
            logger.info(f"Archive ran for {conversation_id}. Duration: {time() - start}s")

    def get_blob_path(self, artifact_id: ChatArtifactIdentifier) -> str:
        """Get the blob path for a ChatArtifact object."""
        # Ensure conversation_id is URL-safe by encoding it in base64. This is required for SAS token.
        base64_conv_id = base64.urlsafe_b64encode(artifact_id.conversation_id.encode("utf-8")).decode("utf-8")
        return f"{base64_conv_id}/{artifact_id.patient_id}/{artifact_id.filename}"

    def get_url(self, artifact_id: ChatArtifactIdentifier) -> str:
        """Get the URL for the chat artifact blob."""
        blob_path = self.get_blob_path(artifact_id)
        blob_client = self.container_client.get_blob_client(blob_path)
        return blob_client.url

    async def read(self, artifact_id: ChatArtifactIdentifier) -> ChatArtifact:
        """Read the chat artifact for a given query."""
        start = time()
        try:
            blob_path = self.get_blob_path(artifact_id)
            blob_client = self.container_client.get_blob_client(blob_path)

            # Download the blob content as a stream
            blob = await blob_client.download_blob()
            blob_data = await blob.readall()  # Read all bytes from the blob

            return ChatArtifact(artifact_id=artifact_id, data=blob_data)
        finally:
            logger.info(f"Read artifact for {blob_path}. Duration: {time() - start}s")

    async def write(self, artifact: ChatArtifact) -> None:
        """Write the WordDocument object to blob storage."""
        start = time()
        try:
            blob_path = self.get_blob_path(artifact.artifact_id)
            blob_client = self.container_client.get_blob_client(blob_path)
            await blob_client.upload_blob(artifact.data, overwrite=True)
        finally:
            logger.info(f"Wrote artifact for {blob_path}. Duration: {time() - start}s")
