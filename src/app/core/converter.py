from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image

from app.core.exif import extract_exif_data
from app.core.gallery_data import build_api_url, write_gallery_data
from app.core.models import BatchResult, ConversionOptions, ConvertedImageRecord

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

ProgressCallback = Callable[[int, int], None]
LogCallback = Callable[[str], None]


class BatchConverter:
    def run(
        self,
        options: ConversionOptions,
        on_progress: ProgressCallback | None = None,
        on_log: LogCallback | None = None,
    ) -> BatchResult:
        options.output_dir.mkdir(parents=True, exist_ok=True)

        total = len(options.input_files)
        succeeded = 0
        failed = 0
        input_total_bytes = 0
        output_total_bytes = 0
        records: list[ConvertedImageRecord] = []

        for index, source_path in enumerate(options.input_files, start=1):
            if on_log:
                on_log(f"[{index}/{total}] Processing: {source_path.name}")

            try:
                output_name = self._build_output_name(source_path, options, index)
                output_path = options.output_dir / output_name

                with Image.open(source_path) as image:
                    metadata = extract_exif_data(image)
                    image_to_save = self._resize_if_enabled(image, options)
                    image_to_save.save(
                        output_path,
                        format="WEBP",
                        quality=options.quality,
                        method=6,
                    )

                input_total_bytes += source_path.stat().st_size
                output_total_bytes += output_path.stat().st_size

                records.append(
                    ConvertedImageRecord(
                        source_file=source_path.name,
                        output_file=output_name,
                        api_url=build_api_url(options.api_base_url, output_name),
                        metadata=metadata,
                    )
                )

                succeeded += 1
                if on_log:
                    on_log(f"Saved: {output_name}")
            except Exception as error:
                failed += 1
                if on_log:
                    on_log(f"Failed: {source_path.name} ({error})")
            finally:
                if on_progress:
                    on_progress(index, total)

        gallery_json_path = write_gallery_data(options.output_dir, records)
        if on_log:
            on_log(f"Metadata file created: {gallery_json_path.name}")

        return BatchResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            gallery_json_path=gallery_json_path,
            input_total_bytes=input_total_bytes,
            output_total_bytes=output_total_bytes,
        )

    def _build_output_name(self, source_path: Path, options: ConversionOptions, index: int) -> str:
        if options.export_name and options.export_name.strip():
            base_name = options.export_name.strip()
            return f"{base_name}-{index}.webp"
        return f"{source_path.stem}.webp"

    def get_expected_output_names(self, options: ConversionOptions) -> list[str]:
        names: list[str] = []
        for index, source_path in enumerate(options.input_files, start=1):
            names.append(self._build_output_name(source_path, options, index))
        return names

    def _resize_if_enabled(self, image: Image.Image, options: ConversionOptions) -> Image.Image:
        if not options.resize_enabled:
            return image

        target_width = options.resize_width
        target_height = options.resize_height

        if target_width is None and target_height is None:
            return image

        if options.preserve_aspect_ratio:
            resized = image.copy()
            width = target_width if target_width is not None else image.width
            height = target_height if target_height is not None else image.height
            resized.thumbnail((max(1, width), max(1, height)), Image.Resampling.LANCZOS)
            return resized

        width = target_width if target_width is not None else image.width
        height = target_height if target_height is not None else image.height
        return image.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)

def filter_supported_images(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.suffix.lower() in SUPPORTED_EXTENSIONS]
