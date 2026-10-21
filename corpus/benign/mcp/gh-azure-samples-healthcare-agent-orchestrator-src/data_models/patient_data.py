# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from pydantic import BaseModel


class PatientDataSource(BaseModel):
    note_id: str
    sentences: list[str]


class PatientDataAnswer(BaseModel):
    text: str
    sources: list[PatientDataSource]


class PatientTimelineEntry(BaseModel):
    date: str
    title: str
    description: str
    sources: list[PatientDataSource]


class PatientTimeline(BaseModel):
    patient_id: str
    entries: list[PatientTimelineEntry]
