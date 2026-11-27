"""Stable JSON writer: one line per record, so git diffs stay readable.

A plain json.dumps(indent=2) explodes every nested object across many lines, which
turns a one-field change into a 300-line diff. This writer keeps flat objects
(stats, talents, equipment rows, catalog rows) on a single line and only breaks
where structure actually nests.
"""
from __future__ import annotations

import json


def _flat(value) -> bool:
    return isinstance(value, dict) and all(
        not isinstance(v, (dict, list)) for v in value.values()
    )


def _compact(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def dumps(value, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        if _flat(value) and len(_compact(value)) + indent <= 118:
            return _compact(value)
        parts = []
        for k, v in value.items():
            parts.append(" " * (indent + 2) + json.dumps(k, ensure_ascii=False) + ": "
                         + dumps(v, indent + 2))
        return "{\n" + ",\n".join(parts) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        simple = all(not isinstance(v, (dict, list)) or _flat(v) for v in value) and all(
            len(_compact(v)) + indent <= 118 for v in value)
        parts = [" " * (indent + 2) + _compact(v) for v in value]
        if not simple:
            parts = [" " * (indent + 2) + dumps(v, indent + 2) for v in value]
        return "[\n" + ",\n".join(parts) + "\n" + pad + "]"
    return _compact(value)


def dump(value) -> str:
    return dumps(value) + "\n"
