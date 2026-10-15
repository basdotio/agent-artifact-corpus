import os
import uuid

from azure.ai.vision.face import FaceAdministrationClient
from azure.ai.vision.face.models import FaceRecognitionModel
from azure.core.credentials import AzureKeyCredential


def create_large_person_group(group_id=None):
    ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
    KEY = os.getenv("AZURE_FACE_API_KEY")
    group_uuid = group_id if group_id else str(uuid.uuid4())

    with FaceAdministrationClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        headers={"X-MS-AZSDK-Telemetry": "sample=mcp-face-reco-create-lpg"},
    ) as face_admin_client:
        # Check if the group already exists
        try:
            face_admin_client.large_person_group.get(large_person_group_id=group_uuid)
            return f"Large person group with UUID: {group_uuid} already exists."
        except Exception as e:
            # If not found, create it
            if "ResourceNotFound" in str(e) or "not found" in str(e).lower():
                face_admin_client.large_person_group.create(
                    large_person_group_id=group_uuid,
                    name=group_uuid,
                    recognition_model=FaceRecognitionModel.RECOGNITION04,
                )
                return f"Created a large person group with UUID: {group_uuid} successfully."
            else:
                raise
