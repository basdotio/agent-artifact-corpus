# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import json
import logging
import os

from azure.core.exceptions import ResourceNotFoundError
from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse

from data_models.chat_artifact import ChatArtifactFilename, ChatArtifactIdentifier
from data_models.data_access import DataAccess
from data_models.patient_data import PatientTimeline
from routes.views.grounded_clinical_note import render_grounded_clinical_note

logger = logging.getLogger(__name__)


def patient_timeline_entry_source_routes(data_access: DataAccess):
    """
    Create routes for viewing patient timeline entry sources.

    This code is not meant to be used in production. It is for demonstration purposes only.
    """
    router = APIRouter()

    @router.get("/view/{conversation_id}/{patient_id}/patient_timeline/entry/{entry_index}/source/{source_index}.html")
    async def get_source(conversation_id: str, patient_id: str, entry_index: str, source_index: str):
        ''' Get a specific source from a patient timeline entry and render it as an HTML page. '''
        try:
            # Get the patient timeline
            artifact_id = ChatArtifactIdentifier(
                conversation_id=conversation_id,
                patient_id=patient_id,
                filename=ChatArtifactFilename.PATIENT_TIMELINE
            )
            artifact = await data_access.chat_artifact_accessor.read(artifact_id)
            artifact_json = artifact.data.decode("utf-8")
            timeline = PatientTimeline.model_validate_json(artifact_json)
            timeline_entry = timeline.entries[int(entry_index)]
            source = timeline_entry.sources[int(source_index)]

            # Get the clinical note
            note_id = source.note_id
            note = await data_access.clinical_note_accessor.read(patient_id, note_id)
            note_dict = json.loads(note)

            body = render_grounded_clinical_note(patient_id, note_dict, source)
            return HTMLResponse(content=body)
        except ResourceNotFoundError:
            return Response(status_code=404, content=f"Patient timeline entry not found. patient_id: {patient_id}, entry_index: {entry_index}")

    return router


def get_patient_timeline_entry_source_url(
    conversation_id: str, patient_id: str, entry_index: str, source_index
) -> str:
    """Get the URL for a patient clinical note."""
    hostname = os.getenv("BACKEND_APP_HOSTNAME")
    return f"https://{hostname}/view/{conversation_id}/{patient_id}/patient_timeline/entry/{entry_index}/source/{source_index}.html"
