# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import asyncio
import logging
from time import time

from azure.storage.blob.aio import BlobServiceClient

logger = logging.getLogger(__name__)


class ClinicalNoteAccessor:
    def __init__(
        self, blob_service_client: BlobServiceClient,
        container_name: str = "patient-data",
        folder_name: str = "clinical_notes"
    ):
        self.blob_service_client = blob_service_client
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(self.container_name)
        self.folder_name = folder_name

    async def get_patients(self) -> list[str]:
        """Get the list of patients."""
        start = time()
        try:
            blob_names = [name async for name in self.container_client.list_blob_names()]
            patients = {name.split("/")[0] for name in blob_names}
            return list(patients)
        finally:
            logger.info(f"Get patients. Duration: {time() - start}s")

    async def get_metadata_list(self, patient_id: str) -> list[dict[str, str]]:
        """Get the clinical note URLs for a given patient ID."""
        start = time()
        try:
            blob_path = f"{patient_id}/{self.folder_name}/"
            blob_names = [name async for name in self.container_client.list_blob_names(name_starts_with=blob_path)]

            return [
                {
                    "id": self._parse_note_id(blob_name),
                    "type": "clinical note",
                } for blob_name in blob_names
            ]
        finally:
            logger.info(f"Get clinical note IDs for {patient_id}. Duration: {time() - start}s")

    async def read(self, patient_id: str, note_id: str) -> str:
        """Read the clinical note for a given patient ID and note ID."""
        start = time()
        try:
            blob_path = f"{patient_id}/{self.folder_name}/{note_id}.json"
            return await self._read_blob(blob_path)
        finally:
            logger.info(f"Read clinical note {note_id} for {patient_id}. Duration: {time() - start}s")

    async def read_all(self, patient_id: str) -> list[str]:
        """Read the clinical note for a given patient ID and note ID."""
        start = time()
        try:
            blob_path = f"{patient_id}/{self.folder_name}/"
            blob_names = [name async for name in self.container_client.list_blob_names(name_starts_with=blob_path)]
            batch_size = 10

            # Read blobs in batches
            notes = []
            for i in range(0, len(blob_names), batch_size):
                batch_input = blob_names[i:i + batch_size]
                batch = [self._read_blob(note_id) for note_id in batch_input]
                batch_results = await asyncio.gather(*batch)
                notes.extend(batch_results)

            return notes
        finally:
            logger.info(f"Read all clinical notes for {patient_id}. Duration: {time() - start}s")

    async def _read_blob(self, blob_name: str) -> str:
        blob = await self.container_client.download_blob(blob_name)
        blob_str = await blob.readall()
        return blob_str.decode("utf-8")

    @staticmethod
    def _parse_note_id(blob_name: str) -> str:
        return blob_name.split("/")[-1].split(".")[0]
