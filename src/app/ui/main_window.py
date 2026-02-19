from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core.converter import BatchConverter, filter_supported_images
from app.core.models import ConversionOptions


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Photography EXIF Manager")
        self.geometry("900x640")
        self.minsize(820, 580)

        self.selected_files: list[Path] = []
        self.output_dir: Path | None = None
        self.converter = BatchConverter()

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        controls = ctk.CTkFrame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        controls.grid_columnconfigure((0, 1), weight=1)

        self.select_files_button = ctk.CTkButton(controls, text="Select Images", command=self._pick_files)
        self.select_files_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.select_output_button = ctk.CTkButton(controls, text="Select Output Folder", command=self._pick_output_dir)
        self.select_output_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        options = ctk.CTkFrame(self)
        options.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        options.grid_columnconfigure((0, 1), weight=1)

        self.files_label = ctk.CTkLabel(options, text="No images selected")
        self.files_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))

        self.output_label = ctk.CTkLabel(options, text="Output: not selected")
        self.output_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        ctk.CTkLabel(options, text="WebP Quality").grid(row=2, column=0, sticky="w", padx=12)
        self.quality_value = ctk.StringVar(value="90")
        self.quality_slider = ctk.CTkSlider(
            options,
            from_=1,
            to=100,
            number_of_steps=99,
            command=self._on_quality_change,
        )
        self.quality_slider.set(90)
        self.quality_slider.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))

        self.quality_label = ctk.CTkLabel(options, textvariable=self.quality_value)
        self.quality_label.grid(row=3, column=1, sticky="w", padx=12)

        ctk.CTkLabel(options, text="Export Base Name (optional)").grid(row=4, column=0, sticky="w", padx=12)
        self.export_name_entry = ctk.CTkEntry(options, placeholder_text="e.g. portfolio")
        self.export_name_entry.grid(row=5, column=0, sticky="ew", padx=12, pady=(4, 12))

        ctk.CTkLabel(options, text="API Base URL (optional)").grid(row=4, column=1, sticky="w", padx=12)
        self.api_url_entry = ctk.CTkEntry(options, placeholder_text="https://cdn.example.com/gallery")
        self.api_url_entry.grid(row=5, column=1, sticky="ew", padx=12, pady=(4, 12))

        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Progress: 0/0")
        self.progress_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        logs_frame = ctk.CTkFrame(self)
        logs_frame.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 10))
        logs_frame.grid_rowconfigure(1, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(logs_frame, text="Logs").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.logs_text = ctk.CTkTextbox(logs_frame)
        self.logs_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        footer = ctk.CTkFrame(self)
        footer.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(footer, text="Start Batch Conversion", command=self._start_conversion)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    def _pick_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )

        if not selected:
            return

        paths = [Path(path) for path in selected]
        filtered = filter_supported_images(paths)

        if not filtered:
            messagebox.showwarning("No supported images", "None of the selected files are supported.")
            return

        self.selected_files = filtered
        self.files_label.configure(text=f"Selected images: {len(filtered)}")
        self._log(f"Selected {len(filtered)} images.")

    def _pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if not selected:
            return

        self.output_dir = Path(selected)
        self.output_label.configure(text=f"Output: {self.output_dir}")
        self._log(f"Output folder set to: {self.output_dir}")

    def _on_quality_change(self, value: float) -> None:
        self.quality_value.set(str(int(value)))

    def _start_conversion(self) -> None:
        if not self.selected_files:
            messagebox.showerror("Missing images", "Please select at least one image.")
            return

        if self.output_dir is None:
            messagebox.showerror("Missing output folder", "Please select an output folder.")
            return

        self._clear_logs()
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Progress: 0/{len(self.selected_files)}")

        options = ConversionOptions(
            input_files=self.selected_files,
            output_dir=self.output_dir,
            quality=int(float(self.quality_slider.get())),
            export_name=self.export_name_entry.get().strip() or None,
            api_base_url=self.api_url_entry.get().strip() or None,
            overwrite=True,
        )

        self.start_button.configure(state="disabled")
        self._log("Starting conversion...")

        worker = threading.Thread(target=self._run_conversion, args=(options,), daemon=True)
        worker.start()

    def _run_conversion(self, options: ConversionOptions) -> None:
        result = self.converter.run(
            options,
            on_progress=self._on_progress,
            on_log=self._log,
        )

        def finish() -> None:
            self.start_button.configure(state="normal")
            summary = (
                f"Done. Converted: {result.succeeded}/{result.total}. "
                f"Failed: {result.failed}. JSON: {result.gallery_json_path.name}"
            )
            self._log(summary)
            messagebox.showinfo("Batch finished", summary)

        self.after(0, finish)

    def _on_progress(self, current: int, total: int) -> None:
        def update() -> None:
            fraction = current / total if total else 0
            self.progress_bar.set(fraction)
            self.progress_label.configure(text=f"Progress: {current}/{total}")

        self.after(0, update)

    def _log(self, message: str) -> None:
        def append() -> None:
            self.logs_text.insert("end", message + "\n")
            self.logs_text.see("end")

        self.after(0, append)

    def _clear_logs(self) -> None:
        self.logs_text.delete("1.0", "end")
