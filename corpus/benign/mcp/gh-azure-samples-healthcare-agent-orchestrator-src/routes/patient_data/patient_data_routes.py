# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging
import os

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient
from fastapi import APIRouter, Response

from data_models import mime_type

logger = logging.getLogger(__name__)


def patient_data_routes(blob_service_client: BlobServiceClient):
    router = APIRouter()

    async def get_blob(blob_path: str, container_name: str) -> Response:
        ''' Get a file generated from an Azure AI Agent '''

        filename = os.path.basename(blob_path)
        logger.info(f"blob_path: {blob_path}")

        try:
            container_client = blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_path)

            # Download the blob content
            blob = await blob_client.download_blob()
            blob_data = await blob.readall()

            # Set content type
            headers = {
                'Content-Type': mime_type(filename)
            }

            return Response(media_type=mime_type(filename), content=blob_data, headers=headers)
        except ResourceNotFoundError:
            return Response(status_code=404, content=f"Blob not found: {blob_path}")

    @router.get("/chat_artifacts/{blob_path:path}")
    async def get_chat_artifact(blob_path: str):
        return await get_blob(blob_path, container_name="chat-artifacts")

    @router.get("/patient_data/{blob_path:path}")
    async def get_patient_data(blob_path: str):
        return await get_blob(blob_path, container_name="patient-data")

    return router


def get_chat_artifacts_url(blob_path: str) -> str:
    """Get the URL for a given blob path in chat artifacts."""
    hostname = os.getenv("BACKEND_APP_HOSTNAME")
    return f"https://{hostname}/chat_artifacts/{blob_path}"


def get_patient_data_url(blob_path: str) -> str:
    """Get the URL for a given blob path."""
    hostname = os.getenv("BACKEND_APP_HOSTNAME")
    return f"https://{hostname}/patient_data/{blob_path}"
