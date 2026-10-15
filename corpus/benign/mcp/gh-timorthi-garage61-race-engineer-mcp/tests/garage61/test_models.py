"""Tests for garage61.models — TelemetrySample.from_api and exceptions."""

import pytest

from garage61.exceptions import (
    APIError,
    LapNotFoundError,
    NoLapsFoundError,
    TelemetryParseError,
    TelemetryUnavailableError,
)
from garage61.models import TelemetrySample


class TestTelemetrySampleFromApi:
    def test_happy_path_all_fields(self, sample_row_dict: dict) -> None:
        sample = TelemetrySample.from_api(sample_row_dict)

        assert sample.speed_mps == 50.0
        assert sample.lap_dist_pct == 0.1
        assert sample.lat == 52.0
        assert sample.lon == 4.0
        assert sample.brake == 0.0
        assert sample.throttle == 0.8
        assert sample.rpm == 4000.0
        assert sample.steering_wheel_angle == 0.05
        assert sample.gear == 3
        assert sample.clutch == 0.0
        assert sample.abs_active is False
        assert sample.drs_active is False
        assert sample.lat_accel == 0.1
        assert sample.long_accel == -0.2
        assert sample.vert_accel == 9.8
        assert sample.yaw == 0.01
        assert sample.yaw_rate == 0.02
        assert sample.position_type == 3

    def test_abs_active_string_true_normalises_to_bool(
        self, sample_row_dict: dict
    ) -> None:
        sample_row_dict["ABSActive"] = "true"
        assert TelemetrySample.from_api(sample_row_dict).abs_active is True

    def test_abs_active_string_false_normalises_to_bool(
        self, sample_row_dict: dict
    ) -> None:
        sample_row_dict["ABSActive"] = "false"
        assert TelemetrySample.from_api(sample_row_dict).abs_active is False

    def test_drs_active_string_true_normalises_to_bool(
        self, sample_row_dict: dict
    ) -> None:
        sample_row_dict["DRSActive"] = "true"
        assert TelemetrySample.from_api(sample_row_dict).drs_active is True

    def test_drs_active_case_insensitive(self, sample_row_dict: dict) -> None:
        sample_row_dict["ABSActive"] = "True"
        sample_row_dict["DRSActive"] = "FALSE"
        sample = TelemetrySample.from_api(sample_row_dict)
        assert sample.abs_active is True
        assert sample.drs_active is False

    def test_gear_is_int(self, sample_row_dict: dict) -> None:
        sample_row_dict["Gear"] = "4"
        assert isinstance(TelemetrySample.from_api(sample_row_dict).gear, int)
        assert TelemetrySample.from_api(sample_row_dict).gear == 4

    def test_speed_is_float(self, sample_row_dict: dict) -> None:
        sample_row_dict["Speed"] = "123"
        assert isinstance(TelemetrySample.from_api(sample_row_dict).speed_mps, float)

    def test_missing_column_raises_key_error(self, sample_row_dict: dict) -> None:
        del sample_row_dict["Speed"]
        with pytest.raises(KeyError):
            TelemetrySample.from_api(sample_row_dict)

    def test_missing_boolean_column_raises_key_error(
        self, sample_row_dict: dict
    ) -> None:
        del sample_row_dict["ABSActive"]
        with pytest.raises(KeyError):
            TelemetrySample.from_api(sample_row_dict)


class TestExceptionToModel:
    @pytest.mark.parametrize(
        "exc_class, expected_code, expected_recoverable",
        [
            (LapNotFoundError, "lap_not_found", False),
            (TelemetryUnavailableError, "telemetry_unavailable", False),
            (TelemetryParseError, "telemetry_parse_error", False),
            (APIError, "api_error", False),
            (NoLapsFoundError, "no_laps_found", True),
        ],
    )
    def test_to_model_error_code_and_recoverable(
        self,
        exc_class: type,
        expected_code: str,
        expected_recoverable: bool,
    ) -> None:
        exc = exc_class("test message")
        model = exc.to_model()

        assert model.error == expected_code
        assert model.recoverable is expected_recoverable

    def test_to_model_message_matches_exception_text(self) -> None:
        exc = LapNotFoundError("Lap ID 'abc' not found")
        model = exc.to_model()
        assert model.message == "Lap ID 'abc' not found"
