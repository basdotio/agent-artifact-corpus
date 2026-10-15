"""Tests for Garage61Client._parse_telemetry_csv (static method — no HTTP needed)."""

import pytest

from garage61.client import Garage61Client
from garage61.exceptions import TelemetryParseError


LAP_LENGTH_M = 5435.0


class TestParseTelemetryCsv:
    def test_returns_dataframe_with_distance_column(self, valid_csv_text: str) -> None:
        df = Garage61Client._parse_telemetry_csv(valid_csv_text, LAP_LENGTH_M)
        assert "distance_m" in df.columns

    def test_distance_m_equals_lap_dist_pct_times_lap_length(
        self, valid_csv_text: str
    ) -> None:
        df = Garage61Client._parse_telemetry_csv(valid_csv_text, LAP_LENGTH_M)
        expected = df["LapDistPct"] * LAP_LENGTH_M
        assert (df["distance_m"] - expected).abs().max() < 1e-9

    def test_filters_to_on_track_rows_only(self, mixed_position_csv_text: str) -> None:
        df = Garage61Client._parse_telemetry_csv(mixed_position_csv_text, LAP_LENGTH_M)
        assert (df["PositionType"] == 3).all()
        assert len(df) == 2  # 2 of 4 rows have PositionType == 3

    def test_non_on_track_rows_are_excluded(self, mixed_position_csv_text: str) -> None:
        df = Garage61Client._parse_telemetry_csv(mixed_position_csv_text, LAP_LENGTH_M)
        assert 1 not in df["PositionType"].values  # pit lane
        assert 4 not in df["PositionType"].values  # off track

    def test_index_is_reset(self, mixed_position_csv_text: str) -> None:
        df = Garage61Client._parse_telemetry_csv(mixed_position_csv_text, LAP_LENGTH_M)
        assert list(df.index) == list(range(len(df)))

    def test_missing_column_raises_telemetry_parse_error(self) -> None:
        bad_csv = "Speed,LapDistPct,PositionType\n50.0,0.1,3\n"
        with pytest.raises(TelemetryParseError):
            Garage61Client._parse_telemetry_csv(bad_csv, LAP_LENGTH_M)

    def test_parse_error_message_includes_present_columns(self) -> None:
        bad_csv = "Speed,LapDistPct,PositionType\n50.0,0.1,3\n"
        with pytest.raises(TelemetryParseError, match="Present columns"):
            Garage61Client._parse_telemetry_csv(bad_csv, LAP_LENGTH_M)

    def test_all_on_track_rows_preserved(self, valid_csv_text: str) -> None:
        df = Garage61Client._parse_telemetry_csv(valid_csv_text, LAP_LENGTH_M)
        assert len(df) == 3  # all 3 rows in valid_csv_text are PositionType == 3

    def test_lap_length_scales_distance(self, valid_csv_text: str) -> None:
        short_lap = 1000.0
        df = Garage61Client._parse_telemetry_csv(valid_csv_text, short_lap)
        # First row has LapDistPct == 0.1
        assert abs(df.iloc[0]["distance_m"] - 0.1 * short_lap) < 1e-9
