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
    resize_enabled: bool = False
    resize_width: int | None = None
    resize_height: int | None = None
    preserve_aspect_ratio: bool = True


@dataclass(slots=True)
class BatchResult:
    total: int
    succeeded: int
    failed: int
    gallery_json_path: Path
    input_total_bytes: int
    output_total_bytes: int

    @property
    def bytes_saved(self) -> int:
        return self.input_total_bytes - self.output_total_bytes

    @property
    def compression_rate_percent(self) -> float:
        if self.input_total_bytes <= 0:
            return 0.0
        return (self.bytes_saved / self.input_total_bytes) * 100


@dataclass(slots=True)
class ConvertedImageRecord:
    source_file: str
    output_file: str
    api_url: str | None
    metadata: dict[str, Any]
