from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.core.models import ConvertedImageRecord


GALLERY_FILENAME = "gallery-data.json"


def build_api_url(base_url: str | None, output_name: str) -> str | None:
    if not base_url:
        return None
    normalized = base_url.rstrip("/")
    return f"{normalized}/{output_name}"


def write_gallery_data(output_dir: Path, items: Iterable[ConvertedImageRecord]) -> Path:
    gallery_path = output_dir / GALLERY_FILENAME
    payload = [
        {
            "source_file": item.source_file,
            "output_file": item.output_file,
            "api_url": item.api_url,
            "metadata": item.metadata,
        }
        for item in items
    ]

    with gallery_path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)

    return gallery_path
