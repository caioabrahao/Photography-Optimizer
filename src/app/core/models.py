from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ConversionOptions:
    input_files: list[Path]
    output_dir: Path
    quality: int
    export_name: str | None = None
    api_base_url: str | None = None
    overwrite: bool = True


@dataclass(slots=True)
class BatchResult:
    total: int
    succeeded: int
    failed: int
    gallery_json_path: Path


@dataclass(slots=True)
class ConvertedImageRecord:
    source_file: str
    output_file: str
    api_url: str | None
    metadata: dict[str, Any]
