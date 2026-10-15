import os
from azure.ai.vision.face import FaceAdministrationClient
from azure.core.credentials import AzureKeyCredential


def list_large_person_groups():
    """
    List all large person groups in the configured Azure Face resource.

    Returns:
        str: A newline-separated string with Group ID and Name for each large person group,
             or a message indicating none were found.
    """
    endpoint = os.getenv("AZURE_FACE_ENDPOINT")
    key = os.getenv("AZURE_FACE_API_KEY")

    groups_output = []

    with FaceAdministrationClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
        headers={"X-MS-AZSDK-Telemetry": "sample=mcp-face-reco-list-lpgs"},
    ) as client:
        start = None
        while True:
            groups = client.large_person_group.get_large_person_groups(
                start=start, top=1000
            )
            if not groups:
                break
            for g in groups:
                group_id = getattr(g, "large_person_group_id", getattr(g, "id", None))
                name = getattr(g, "name", None)
                groups_output.append(f"Group ID: {group_id}, Name: {name}")
            start = groups[-1].large_person_group_id  # pagination anchor

    return (
        "\n".join(groups_output) if groups_output else "No large person groups found."
    )
