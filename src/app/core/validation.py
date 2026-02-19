from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.models import ConversionOptions


@dataclass(slots=True)
class OutputConflicts:
    gallery_json_exists: bool
    duplicate_files: list[str]

    @property
    def has_conflicts(self) -> bool:
        return self.gallery_json_exists or bool(self.duplicate_files)


def resolve_effective_output_dir(base_output_dir: Path) -> Path:
    return base_output_dir / "exported"


def detect_output_conflicts(options: ConversionOptions, expected_output_names: list[str]) -> OutputConflicts:
    output_dir = options.output_dir
    gallery_json_exists = (output_dir / "gallery-data.json").exists()
    duplicate_files = [name for name in expected_output_names if (output_dir / name).exists()]

    return OutputConflicts(
        gallery_json_exists=gallery_json_exists,
        duplicate_files=duplicate_files,
    )
