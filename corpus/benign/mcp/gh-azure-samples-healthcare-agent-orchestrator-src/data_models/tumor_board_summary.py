# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from dataclasses import dataclass


@dataclass(frozen=True)
class ClinicalSummary:
    entries: list[str]


@dataclass(frozen=True)
class ClinicalTrial:
    title: str
    summary: str
    url: str
