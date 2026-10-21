# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from dataclasses import dataclass


class ChatArtifactFilename:
    PATIENT_DATA_ANSWERS = "patient_data_answers.json"
    PATIENT_TIMELINE = "patient_timeline.json"
    RESEARCH_PAPERS = "research_papers.json"


@dataclass(frozen=True)
class ChatArtifactIdentifier:
    conversation_id: str
    patient_id: str
    filename: str


@dataclass(frozen=True)
class ChatArtifact:
    artifact_id: ChatArtifactIdentifier
    data: bytes
