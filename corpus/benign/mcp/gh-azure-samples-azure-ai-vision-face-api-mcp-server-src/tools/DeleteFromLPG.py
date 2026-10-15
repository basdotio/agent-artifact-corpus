import os
from typing import Annotated

from azure.ai.vision.face import FaceAdministrationClient
from azure.core.credentials import AzureKeyCredential
from pydantic import Field

from .utils._enums import DeletePersonFromLPGConfig, DeleteFaceFromLPGConfig

# Keep pending confirmations here
_PENDING_DELETES: dict[str, bool] = {}

# Word the user must type to confirm
_CONFIRM_WORD = "YES_DELETE"


def delete_person_from_group(
    person_id: Annotated[str, Field(DeletePersonFromLPGConfig.ARGS_PERSON_ID)],
    group_uuid: Annotated[
        str, Field(description=DeletePersonFromLPGConfig.ARGS_GROUP_UUID)
    ],
    confirm_text: Annotated[
        str, Field(description=f"Type exactly '{_CONFIRM_WORD}' to confirm deletion")
    ] = "",
):
    key = f"{group_uuid}:{person_id}"

    # First call: warn and require explicit confirm word
    if _PENDING_DELETES.get(key) is None:
        _PENDING_DELETES[key] = True
        return {
            "status": "needs_confirmation",
            "message": DeletePersonFromLPGConfig.DOUBLE_CONFIRM_WARNING.format(
                person_id=person_id, group_uuid=group_uuid
            )
            + f" To proceed, call again with confirm_text='{_CONFIRM_WORD}'.",
        }

    # Second call: must match confirm word
    if confirm_text != _CONFIRM_WORD:
        return {
            "status": "confirmation_required",
            "message": f"You must type confirm_text='{_CONFIRM_WORD}' to delete person {person_id} from group {group_uuid}.",
        }

    # Passed confirmation → perform deletion
    _PENDING_DELETES.pop(key, None)

    ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
    KEY = os.getenv("AZURE_FACE_API_KEY")
    output_list = []

    with FaceAdministrationClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        headers={"X-MS-AZSDK-Telemetry": "sample=mcp-face-reco-delete"},
    ) as face_admin_client:
        try:
            face_admin_client.large_person_group.delete_person(
                large_person_group_id=group_uuid, person_id=person_id
            )
            output_list.append(
                f"Deleted person with ID: {person_id} from group: {group_uuid}"
            )
        except Exception as e:
            output_list.append(
                f"Failed to delete person with ID: {person_id} from group: {group_uuid}. Error: {str(e)}"
            )
    return "\n".join(output_list)


def delete_face_from_group(
    face_id: Annotated[str, Field(DeleteFaceFromLPGConfig.ARGS_FACE_ID)],
    person_id: Annotated[str, Field(DeleteFaceFromLPGConfig.ARGS_PERSON_ID)],
    group_uuid: Annotated[
        str, Field(description=DeleteFaceFromLPGConfig.ARGS_GROUP_UUID)
    ],
    confirm_text: Annotated[
        str, Field(description=f"Type exactly '{_CONFIRM_WORD}' to confirm deletion")
    ] = "",
):
    key = f"{group_uuid}:{person_id}:{face_id}"

    # First call: warn and require explicit confirm word
    if _PENDING_DELETES.get(key) is None:
        _PENDING_DELETES[key] = True
        return {
            "status": "needs_confirmation",
            "message": DeleteFaceFromLPGConfig.DOUBLE_CONFIRM_WARNING.format(
                face_id=face_id, person_id=person_id, group_uuid=group_uuid
            )
            + f" To proceed, call again with confirm_text='{_CONFIRM_WORD}'.",
        }

    # Second call: must match confirm word
    if confirm_text != _CONFIRM_WORD:
        return {
            "status": "confirmation_required",
            "message": f"You must type confirm_text='{_CONFIRM_WORD}' to delete face {face_id} of person {person_id} in group {group_uuid}.",
        }

    # Passed confirmation → perform deletion
    _PENDING_DELETES.pop(key, None)

    ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
    KEY = os.getenv("AZURE_FACE_API_KEY")
    output_list = []

    with FaceAdministrationClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        headers={"X-MS-AZSDK-Telemetry": "sample=mcp-face-reco-delete"},
    ) as face_admin_client:
        try:
            face_admin_client.large_person_group.delete_face(
                large_person_group_id=group_uuid,
                person_id=person_id,
                persisted_face_id=face_id,
            )
            output_list.append(
                f"Deleted face with ID: {face_id} from person ID: {person_id} in group: {group_uuid}"
            )
        except Exception as e:
            output_list.append(
                f"Failed to delete face with ID: {face_id} from person ID: {person_id} in group: {group_uuid}. Error: {str(e)}"
            )
    return "\n".join(output_list)
