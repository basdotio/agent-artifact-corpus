import os
import json
from typing import Annotated
from pydantic import Field
from azure.ai.vision.face import FaceAdministrationClient
from azure.core.credentials import AzureKeyCredential

from .utils._enums import ListPersonsInLPGConfig


def list_persons_in_group(
    group_uuid: Annotated[
        str, Field(description=ListPersonsInLPGConfig.ARGS_GROUP_UUID)
    ],
):
    ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
    KEY = os.getenv("AZURE_FACE_API_KEY")
    output_list = []
    with FaceAdministrationClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        headers={"X-MS-AZSDK-Telemetry": "sample=mcp-face-reco-list-persons"},
    ) as face_admin_client:
        persons = face_admin_client.large_person_group.get_persons(
            large_person_group_id=group_uuid
        )
        if not persons:
            return f"No persons found in the group with UUID: {group_uuid}"
        for person in persons:
            face_ids = person.persisted_face_ids or []
            output_list.append(
                f"Person ID: {person.person_id}, "
                f"Name: {person.name}, "
                f"Number of faces: {len(face_ids)}"
            )
            for pfid in face_ids:
                face = face_admin_client.large_person_group.get_face(
                    large_person_group_id=group_uuid,
                    person_id=person.person_id,
                    persisted_face_id=pfid,
                )
                file_path = None
                if face.user_data:
                    # user_data is a string; try to parse JSON, fall back to raw
                    try:
                        ud = json.loads(face.user_data)
                        file_path = (
                            ud.get("file_path") if isinstance(ud, dict) else None
                        )
                        # If file_path is a URL, append token as query parameter
                        if file_path and file_path.startswith("http"):
                            token = os.getenv("AZURE_STORAGE_SAS_TOKEN")
                            if token:
                                sep = "&" if "?" in file_path else "?"
                                file_path = f"{file_path}{sep}{token}"
                    except Exception:
                        file_path = face.user_data

                if file_path:
                    output_list.append(f"  - Face ID: {pfid}, file_path: {file_path}")
                else:
                    output_list.append(
                        f"  - Face ID: {pfid}, user_data: {face.user_data or ''}"
                    )
    return "\n".join(output_list)
