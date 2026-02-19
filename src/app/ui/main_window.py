from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.core.converter import BatchConverter, filter_supported_images
from app.core.models import ConversionOptions
from app.core.validation import detect_output_conflicts, resolve_effective_output_dir


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Photography EXIF Manager")
        self.geometry("980x760")
        self.minsize(900, 680)

        self.selected_files: list[Path] = []
        self.output_dir: Path | None = None
        self.converter = BatchConverter()
        self.resize_section_visible = False
        self.numeric_validation = (self.register(self._validate_numeric_input), "%P")

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

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

        self.resize_toggle_button = ctk.CTkButton(
            options,
            text="Resize Options ▸",
            command=self._toggle_resize_section,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.resize_toggle_button.grid(row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))

        self.resize_frame = ctk.CTkFrame(options)
        self.resize_frame.grid_columnconfigure((0, 1), weight=1)

        self.resize_enabled_var = ctk.BooleanVar(value=False)
        self.resize_enabled_checkbox = ctk.CTkCheckBox(
            self.resize_frame,
            text="Enable resize",
            variable=self.resize_enabled_var,
            command=self._update_resize_field_state,
        )
        self.resize_enabled_checkbox.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 8))

        self.preserve_aspect_var = ctk.BooleanVar(value=True)
        self.preserve_aspect_checkbox = ctk.CTkCheckBox(
            self.resize_frame,
            text="Preserve aspect ratio",
            variable=self.preserve_aspect_var,
            command=self._update_resize_field_state,
        )
        self.preserve_aspect_checkbox.grid(row=0, column=1, sticky="w", padx=12, pady=(10, 8))

        ctk.CTkLabel(self.resize_frame, text="Resize Width (px)").grid(row=1, column=0, sticky="w", padx=12)
        self.resize_width_entry = ctk.CTkEntry(
            self.resize_frame,
            placeholder_text="e.g. 1920",
            validate="key",
            validatecommand=self.numeric_validation,
        )
        self.resize_width_entry.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        self.resize_width_entry.bind("<KeyRelease>", self._on_resize_input_change)

        ctk.CTkLabel(self.resize_frame, text="Resize Height (px)").grid(row=1, column=1, sticky="w", padx=12)
        self.resize_height_entry = ctk.CTkEntry(
            self.resize_frame,
            placeholder_text="e.g. 1080",
            validate="key",
            validatecommand=self.numeric_validation,
        )
        self.resize_height_entry.grid(row=2, column=1, sticky="ew", padx=12, pady=(4, 12))
        self.resize_height_entry.bind("<KeyRelease>", self._on_resize_input_change)

        self._update_resize_field_state()

        selected_frame = ctk.CTkFrame(self)
        selected_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 10))
        selected_frame.grid_columnconfigure(0, weight=1)
        selected_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(selected_frame, text="Selected images").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.selected_images_text = ctk.CTkTextbox(selected_frame, height=120)
        self.selected_images_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.selected_images_text.configure(state="disabled")

        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Progress: 0/0")
        self.progress_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        logs_frame = ctk.CTkFrame(self)
        logs_frame.grid(row=4, column=0, sticky="nsew", padx=18, pady=(0, 10))
        logs_frame.grid_rowconfigure(1, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(logs_frame, text="Logs").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.logs_text = ctk.CTkTextbox(logs_frame)
        self.logs_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        footer = ctk.CTkFrame(self)
        footer.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(footer, text="Start Batch Conversion", command=self._start_conversion)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.credit_label = ctk.CTkLabel(footer, text="Made by Caio Abrahão")
        self.credit_label.grid(row=1, column=0, sticky="e", padx=10, pady=(0, 8))

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
        self._refresh_selected_images_list()
        self._log(f"Selected {len(filtered)} images.")

    def _pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if not selected:
            return

        self.output_dir = Path(selected)
        self._refresh_output_label()
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

        try:
            resize_width, resize_height = self._parse_resize_values()
        except ValueError as error:
            messagebox.showerror("Invalid resize values", str(error))
            return

        effective_output_dir = resolve_effective_output_dir(self.output_dir)

        self._clear_logs()
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Progress: 0/{len(self.selected_files)}")

        options = ConversionOptions(
            input_files=self.selected_files,
            output_dir=effective_output_dir,
            quality=int(float(self.quality_slider.get())),
            export_name=self.export_name_entry.get().strip() or None,
            api_base_url=self.api_url_entry.get().strip() or None,
            resize_enabled=self.resize_enabled_var.get(),
            resize_width=resize_width,
            resize_height=resize_height,
            preserve_aspect_ratio=self.preserve_aspect_var.get(),
        )

        conflicts = detect_output_conflicts(options, self.converter.get_expected_output_names(options))
        if conflicts.has_conflicts:
            messages: list[str] = []
            if conflicts.gallery_json_exists:
                messages.append("- gallery-data.json already exists")
            if conflicts.duplicate_files:
                preview = ", ".join(conflicts.duplicate_files[:5])
                if len(conflicts.duplicate_files) > 5:
                    preview += ", ..."
                messages.append(f"- Duplicate output images found: {preview}")

            proceed = messagebox.askyesno(
                "Output conflicts detected",
                "The output directory already contains existing data:\n\n"
                + "\n".join(messages)
                + "\n\nDo you want to proceed and overwrite?",
            )
            if not proceed:
                self._log("Conversion cancelled by user due to output conflicts.")
                return

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
                f"Failed: {result.failed}. "
                f"Compression: {result.compression_rate_percent:.2f}% "
                f"({self._format_bytes(result.input_total_bytes)} → {self._format_bytes(result.output_total_bytes)}). "
                f"JSON: {result.gallery_json_path.name}"
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

    def _refresh_output_label(self) -> None:
        if self.output_dir is None:
            self.output_label.configure(text="Output: not selected")
            return

        effective = resolve_effective_output_dir(self.output_dir)
        self.output_label.configure(text=f"Output: {effective}")

    def _refresh_selected_images_list(self) -> None:
        self.selected_images_text.configure(state="normal")
        self.selected_images_text.delete("1.0", "end")
        for path in self.selected_files:
            self.selected_images_text.insert("end", f"{path.name}\n")
        self.selected_images_text.configure(state="disabled")

    def _parse_resize_values(self) -> tuple[int | None, int | None]:
        if not self.resize_enabled_var.get():
            return None, None

        width_text = self.resize_width_entry.get().strip()
        height_text = self.resize_height_entry.get().strip()

        if not width_text and not height_text:
            raise ValueError("Provide at least width or height when resize is enabled.")

        width = int(width_text) if width_text else None
        height = int(height_text) if height_text else None

        if width is not None and width <= 0:
            raise ValueError("Resize width must be greater than zero.")
        if height is not None and height <= 0:
            raise ValueError("Resize height must be greater than zero.")

        if self.preserve_aspect_var.get() and width is not None and height is not None:
            raise ValueError("With preserve aspect ratio enabled, specify only width or only height.")

        return width, height

    def _toggle_resize_section(self) -> None:
        self.resize_section_visible = not self.resize_section_visible
        if self.resize_section_visible:
            self.resize_frame.grid(row=7, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
            self.resize_toggle_button.configure(text="Resize Options ▾")
        else:
            self.resize_frame.grid_forget()
            self.resize_toggle_button.configure(text="Resize Options ▸")

    def _validate_numeric_input(self, value: str) -> bool:
        return value.isdigit() or value == ""

    def _on_resize_input_change(self, _event: object) -> None:
        self._update_resize_field_state()

    def _update_resize_field_state(self) -> None:
        resize_enabled = self.resize_enabled_var.get()
        preserve = self.preserve_aspect_var.get()

        if not resize_enabled:
            self.preserve_aspect_checkbox.configure(state="disabled")
            self.resize_width_entry.configure(state="disabled")
            self.resize_height_entry.configure(state="disabled")
            return

        self.preserve_aspect_checkbox.configure(state="normal")

        if not preserve:
            self.resize_width_entry.configure(state="normal")
            self.resize_height_entry.configure(state="normal")
            return

        width_has_value = bool(self.resize_width_entry.get().strip())
        height_has_value = bool(self.resize_height_entry.get().strip())

        if width_has_value and not height_has_value:
            self.resize_width_entry.configure(state="normal")
            self.resize_height_entry.configure(state="disabled")
            return

        if height_has_value and not width_has_value:
            self.resize_width_entry.configure(state="disabled")
            self.resize_height_entry.configure(state="normal")
            return

        self.resize_width_entry.configure(state="normal")
        self.resize_height_entry.configure(state="normal")

    def _format_bytes(self, byte_count: int) -> str:
        units = ["B", "KB", "MB", "GB"]
        value = float(byte_count)
        unit_index = 0

        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1

        return f"{value:.2f} {units[unit_index]}"
