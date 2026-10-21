# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import logging
from io import BytesIO
from time import time

from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger(__name__)


class ImageAccessor:
    def __init__(
        self, blob_service_client: BlobServiceClient,
        container_name: str = "patient-data",
        folder_name: str = "images"
    ):
        self.blob_service_client = blob_service_client
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(container_name)
        self.folder_name = folder_name

    def get_blob_path(self, patient_id: str, filename: str) -> str:
        """Get the blob path for a given patient ID and filename."""
        return f"{patient_id}/{self.folder_name}/{filename}"

    async def get_metadata_list(self, patient_id: str) -> list[dict[str, str]]:
        """Get the metadata for the images of a given patient ID."""
        start = time()
        try:
            blob_path = self.get_blob_path(patient_id, "metadata.json")
            blob_client = self.container_client.get_blob_client(blob_path)
            blob = await blob_client.download_blob()
            blob_str = await blob.readall()
            decoded_str = blob_str.decode("utf-8")
            metadatas = json.loads(decoded_str)
            for metadata in metadatas:
                filename = metadata["filename"]
                metadata["url"] = self.get_url(patient_id, filename)
            return metadatas
        finally:
            logger.info(f"Get image metadata for {patient_id}. Duration: {time() - start}s")

    def get_url(self, patient_id: str, filename: str) -> str:
        """Get the URL for the image of a given patient ID and filename."""
        blob_path = self.get_blob_path(patient_id, filename)
        blob_client = self.container_client.get_blob_client(blob_path)
        return blob_client.url

    async def read(self, patient_id: str, filename: str) -> BytesIO:
        """Read the image for a given patient ID and filename."""
        start = time()
        try:
            blob_path = self.get_blob_path(patient_id, filename)
            blob_client = self.container_client.get_blob_client(blob_path)

            # Download the blob content as a stream
            stream = BytesIO()
            blob = await blob_client.download_blob()
            bytes_read = await blob.readinto(stream)

            # Seek to the beginning of the stream
            stream.seek(0)

            return stream
        finally:
            logger.info(f"Read image for {blob_path}. Duration: {time() - start}s")
