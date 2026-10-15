import os
from typing import Annotated

from azure.ai.vision.face import FaceAdministrationClient
from azure.core.credentials import AzureKeyCredential
from pydantic import Field

from .utils._enums import DeleteLPGConfig

# In-memory map to track if a group needs confirmation
_PENDING_DELETES = {}

# Word the user must type to confirm
_CONFIRM_WORD = "YES_DELETE"


def delete_large_person_group(
    group_uuid: Annotated[str, Field(description=DeleteLPGConfig.ARGS_GROUP_UUID)],
    confirm_text: Annotated[
        str, Field(description=f"Type exactly '{_CONFIRM_WORD}' to confirm deletion")
    ] = "",
):
    # First call: warn and require explicit confirm word
    if _PENDING_DELETES.get(group_uuid) is None:
        _PENDING_DELETES[group_uuid] = True
        return {
            "status": "needs_confirmation",
            "message": DeleteLPGConfig.DOUBLE_CONFIRM_WARNING.format(
                group_uuid=group_uuid
            )
            + f" To proceed, call again with confirm_text='{_CONFIRM_WORD}'.",
        }

    # Second call: must match confirm word exactly
    if confirm_text != _CONFIRM_WORD:
        return {
            "status": "confirmation_required",
            "message": f"You must type confirm_text='{_CONFIRM_WORD}' to delete group {group_uuid}.",
        }

    # Passed confirmation → perform deletion
    _PENDING_DELETES.pop(group_uuid, None)

    ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
    KEY = os.getenv("AZURE_FACE_API_KEY")

    with FaceAdministrationClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        headers={"X-MS-AZSDK-Telemetry": "sample=mcp-face-reco-delete-lpg"},
    ) as face_admin_client:
        try:
            face_admin_client.large_person_group.delete(
                large_person_group_id=group_uuid
            )
            return f"Deleted large person group with UUID: {group_uuid} successfully."
        except Exception as e:
            if "ResourceNotFound" in str(e) or "not found" in str(e).lower():
                return f"Large person group with UUID: {group_uuid} does not exist."
            else:
                raise
