import csv
from io import StringIO
from typing import Iterable


def get_json_as_csv_lines(json_list: Iterable[dict]) -> Iterable[str]:
    json_list = list(json_list)
    if not json_list:
        return []
    fieldnames = list({
        key
        for row in json_list
        for key in row.keys()
    })
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(json_list)
    return buffer.getvalue().splitlines()
