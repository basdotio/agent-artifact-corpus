"""Inspect comma-separated text. The first record is the header."""

import csv
import io


def inspect_csv(text: str) -> dict:
    """Report rows, empty cells, and ragged records (record 1 is the header).

    Missing counts include absent trailing cells and whitespace-only cells.
    Entirely blank records are skipped by Python's CSV reader. Header cells that
    are empty or whitespace-only are reported by zero-based position in
    ``empty_header_indices``; the original names are still kept in ``columns``,
    and a blank name is a warning, not an invalid document.
    """
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        return {"valid": False, "error": str(error)}
    if not rows:
        return {"valid": True, "columns": [], "row_count": 0,
                "missing_values": [], "inconsistent_rows": [],
                "empty_header_indices": []}
    header, data = rows[0], rows[1:]
    empty_header_indices = [index for index, name in enumerate(header) if not name.strip()]
    missing = [0] * len(header)
    inconsistent = []
    for record, row in enumerate(data, start=2):
        if len(row) != len(header):
            inconsistent.append({"record": record, "expected": len(header), "actual": len(row)})
        for index in range(len(header)):
            if index >= len(row) or not row[index].strip():
                missing[index] += 1
    return {"valid": True, "columns": header, "row_count": len(data),
            "missing_values": [
                {"column": name, "index": index, "count": missing[index]}
                for index, name in enumerate(header)
            ], "inconsistent_rows": inconsistent,
            "empty_header_indices": empty_header_indices}
