# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import List, Optional, Tuple

from pydantic import BaseModel


class Evidence(BaseModel):
    begin: int
    end: int


def _normalize(input_str: str) -> Tuple[str, List[int]]:
    whitespace = set([" ", "\n", "\t"])
    norm_str = ""
    offset_map = []
    last_is_whitespace = False
    for cidx, c in enumerate(input_str):
        if c in whitespace:
            if last_is_whitespace:
                # skip this character
                continue
            else:
                last_is_whitespace = True
                norm_str += " "
        else:
            last_is_whitespace = False
            norm_str += c
        offset_map.append(cidx)
    # need to add the last offset
    offset_map.append(len(input_str))
    return norm_str, offset_map


def find_evidence(evidence_string: str, doc_text: str) -> Optional[Evidence]:
    """Find the evidence string in the document text.  Raises ValueError if not
    found."""
    begin = doc_text.find(evidence_string)
    if begin > -1:
        end = begin + len(evidence_string)
    else:
        # try again, normalizing whitespace
        norm_text, offset_map = _normalize(doc_text)
        norm_str, _ = _normalize(evidence_string)
        norm_begin = norm_text.lower().find(norm_str.lower())
        if norm_begin == -1:
            # TODO: maybe one more try with edit distance
            return None
        begin = offset_map[norm_begin]
        end = offset_map[norm_begin + len(norm_str)]
    return Evidence(begin=begin, end=end)
