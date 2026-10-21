"""Publish only selected fields from a fresh CUA observation in this request."""
import argparse
from pathlib import Path
from typing import Literal
from pydantic import Field
from .read_protocol import (BrowserResponse, SelectedObservation, ReadRequest,
    atomic_json, read_private_json, request_directory, validate_response, timestamp)


def publish(run_dir: Path, request_id: str) -> None:
    directory = request_directory(run_dir, request_id)
    request = ReadRequest.model_validate(read_private_json(directory / "request.json"))
    if request.request_id != request_id:
        raise ValueError("request_id_mismatch")
    selected = SelectedObservation.model_validate(read_private_json(directory / "selected-observation.json"))
    if selected.name is None and not selected.steps:
        raise ValueError("empty_observation")
    response = BrowserResponse(request_id=request_id, workout_id=request.workout_id, **selected.model_dump())
    validate_response(response.model_dump(), request)
    atomic_json(directory / "response.json", response.model_dump())


class ParentBrowserObservation(BrowserResponse):
    """A trusted parent's report, not independent browser attestation."""
    observation_method: Literal["parent_browser_tool"]
    observed_url: str = Field(max_length=256)
    refreshed_at: str


def record_parent_read(run_dir: Path, request_id: str, observation_file: Path) -> None:
    """Validate a host-neutral report before publishing it to the waiting MCP."""
    directory = request_directory(run_dir, request_id)
    request = ReadRequest.model_validate(read_private_json(directory / "request.json"))
    if request.request_id != request_id:
        raise ValueError("request_id_mismatch")
    report = ParentBrowserObservation.model_validate(read_private_json(observation_file))
    if report.observed_url != "https://connect.garmin.com/app/workout/" + str(request.workout_id):
        raise ValueError("observed_url_mismatch")
    if not timestamp(request.created_at) <= timestamp(report.refreshed_at) <= timestamp(report.observed_at):
        raise ValueError("page_not_refreshed_for_request")
    selected = report.model_dump(exclude={"observed_url", "refreshed_at"})
    validate_response(selected, request)
    # Retain the original before publishing. A local interruption may resume only
    # the identical validated report while its original request is still valid.
    # Neither step overwrites evidence or creates a fresh observation timestamp.
    for path, value in ((directory / "parent-observation.json", report.model_dump()),
                        (directory / "response.json", selected)):
        try:
            atomic_json(path, value)
        except FileExistsError:
            if read_private_json(path) != value:
                raise FileExistsError("different_retained_observation")
