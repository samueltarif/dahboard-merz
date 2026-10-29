"""Tipos e utilidades compartilhados pelos repositórios."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass
class SaveResult:
    import_id: int | None
    rows_read: int
    rows_inserted: int
    rows_duplicated: int
