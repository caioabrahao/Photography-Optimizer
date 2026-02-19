# Photography EXIF Manager

Desktop GUI tool to batch-convert images to WebP and export EXIF metadata into a `gallery-data.json` file.

## Features (foundation)
- Modern desktop GUI built with CustomTkinter.
- Batch convert images (`jpg`, `jpeg`, `png`, `tiff`, `bmp`, `webp`) to WebP.
- Adjustable WebP quality slider.
- Optional custom output naming (`name-1.webp`, `name-2.webp`, ...).
- EXIF extraction for key photography fields (ISO, shutter speed, aperture, camera, lens, focal length, etc.).
- `gallery-data.json` generated for each batch with per-image metadata.
- Optional API base URL field to generate per-image links in JSON.
- Progress bar + live text logs.

## Project structure
- `src/main.py` — app entrypoint.
- `src/app/ui/` — GUI-only code.
- `src/app/core/` — conversion and metadata logic.

## Quick start
1. Create and activate a Python environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python src/main.py
   ```

## Notes
This is the initial architecture foundation. The project is intentionally modular so we can iterate with more features safely.
