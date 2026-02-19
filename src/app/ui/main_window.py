from __future__ import annotations

import json
import os
import re
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

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

        self.export_records_by_file: dict[str, dict[str, Any]] = {}
        self.export_file_buttons: list[ctk.CTkButton] = []
        self.export_button_by_name: dict[str, ctk.CTkButton] = {}
        self.selected_export_image: str | None = None
        self.selected_input_image: Path | None = None
        self.input_file_buttons: list[ctk.CTkButton] = []
        self.input_button_by_name: dict[str, ctk.CTkButton] = {}
        self.input_thumbnail_image: ctk.CTkImage | None = None
        self.export_thumbnail_image: ctk.CTkImage | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        self.header_title = ctk.CTkLabel(header, text="Photography Optimizer", font=ctk.CTkFont(size=26, weight="bold"))
        self.header_title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))

        self.header_subtitle = ctk.CTkLabel(
            header,
            text="Optimize your photos for the web and manage theyr EXIF metadata easily",
        )
        self.header_subtitle.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        self.header_version = ctk.CTkLabel(header, text="Version 1.0")
        self.header_version.grid(row=0, column=1, sticky="e", padx=14, pady=(12, 2))

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.tabs.grid_columnconfigure(0, weight=1)

        self.converter_tab = self.tabs.add("Converter")
        self.export_manager_tab = self.tabs.add("Export Manager")

        self.converter_tab.grid_columnconfigure(0, weight=1)
        self.converter_tab.grid_rowconfigure(0, weight=1)
        self.export_manager_tab.grid_columnconfigure(0, weight=1)
        self.export_manager_tab.grid_rowconfigure(0, weight=1)

        self.converter_scroll = ctk.CTkScrollableFrame(self.converter_tab)
        self.converter_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.converter_scroll.grid_columnconfigure(0, weight=1)

        self._build_converter_tab(self.converter_scroll)
        self._build_export_manager_tab(self.export_manager_tab)

        if hasattr(self.tabs, "_segmented_button"):
            self.tabs._segmented_button.grid(sticky="ew", padx=0, pady=(0, 10))

        footer = ctk.CTkFrame(self)
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self.credit_label = ctk.CTkLabel(footer, text="Made by Caio Abrahão", cursor="hand2")
        self.credit_label.grid(row=0, column=0, sticky="e", padx=10, pady=8)
        self.credit_label.bind("<Button-1>", self._open_credit_link)

        self._update_action_states()

    def _build_converter_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(4, weight=1)

        controls = ctk.CTkFrame(parent)
        controls.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        controls.grid_columnconfigure((0, 1), weight=1)

        self.select_files_button = ctk.CTkButton(controls, text="Select Images", command=self._pick_files)
        self.select_files_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.select_output_button = ctk.CTkButton(controls, text="Select Output Folder", command=self._pick_output_dir)
        self.select_output_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        options = ctk.CTkFrame(parent)
        options.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 10))
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

        selected_frame = ctk.CTkFrame(parent)
        selected_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 10))
        selected_frame.grid_columnconfigure((0, 1), weight=1)
        selected_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(selected_frame, text="Selected images").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.selected_images_scroll = ctk.CTkScrollableFrame(selected_frame, height=150)
        self.selected_images_scroll.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        self.selected_images_scroll.grid_columnconfigure(0, weight=1)

        preview_frame = ctk.CTkFrame(selected_frame)
        preview_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(preview_frame, text="Thumbnail preview").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.selected_preview_label = ctk.CTkLabel(preview_frame, text="No image selected")
        self.selected_preview_label.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))
        self.selected_preview_name = ctk.CTkLabel(preview_frame, text="")
        self.selected_preview_name.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

        progress_frame = ctk.CTkFrame(parent)
        progress_frame.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 10))
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Progress: 0/0")
        self.progress_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        logs_frame = ctk.CTkFrame(parent)
        logs_frame.grid(row=4, column=0, sticky="nsew", padx=0, pady=(0, 10))
        logs_frame.grid_rowconfigure(1, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(logs_frame, text="Logs").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.logs_text = ctk.CTkTextbox(logs_frame)
        self.logs_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        actions = ctk.CTkFrame(parent)
        actions.grid(row=5, column=0, sticky="ew", padx=0, pady=(0, 0))
        actions.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(actions, text="Start Batch Conversion", command=self._start_conversion)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

    def _build_export_manager_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure((0, 1), weight=1)
        parent.grid_rowconfigure(2, weight=1)

        controls = ctk.CTkFrame(parent)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 10))
        controls.grid_columnconfigure(0, weight=1)

        self.manager_output_label = ctk.CTkLabel(controls, text="Exported directory: not selected")
        self.manager_output_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 8))

        self.open_exported_button = ctk.CTkButton(
            controls,
            text="Open Folder",
            width=120,
            command=self._open_exported_directory,
        )
        self.open_exported_button.grid(row=0, column=1, sticky="e", padx=12, pady=(10, 8))
        self.open_exported_button.configure(state="disabled")

        buttons = ctk.CTkFrame(controls)
        buttons.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)

        self.manager_select_output_button = ctk.CTkButton(buttons, text="Select Output Folder", command=self._pick_output_dir)
        self.manager_select_output_button.grid(row=0, column=0, padx=(0, 6), pady=0, sticky="ew")

        self.manager_refresh_button = ctk.CTkButton(buttons, text="Refresh Exported Data", command=self._refresh_export_manager)
        self.manager_refresh_button.grid(row=0, column=1, padx=(6, 0), pady=0, sticky="ew")

        self.manager_status_label = ctk.CTkLabel(controls, text="")
        self.manager_status_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))

        files_frame = ctk.CTkFrame(parent)
        files_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
        files_frame.grid_columnconfigure(0, weight=1)
        files_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(files_frame, text="Exported images").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.export_files_scroll = ctk.CTkScrollableFrame(files_frame)
        self.export_files_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.export_files_scroll.grid_columnconfigure(0, weight=1)

        details_frame = ctk.CTkFrame(parent)
        details_frame.grid(row=2, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(details_frame, text="Thumbnail preview").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))
        self.export_preview_label = ctk.CTkLabel(details_frame, text="No image selected")
        self.export_preview_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.export_preview_name = ctk.CTkLabel(details_frame, text="")
        self.export_preview_name.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

        ctk.CTkLabel(details_frame, text="JSON object").grid(row=3, column=0, sticky="w", padx=12, pady=(0, 6))
        self.export_json_text = ctk.CTkTextbox(details_frame)
        self.export_json_text.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.export_json_text.tag_config("json_key", foreground="#7aa2f7")
        self.export_json_text.tag_config("json_string", foreground="#9ece6a")
        self.export_json_text.tag_config("json_number", foreground="#e0af68")
        self.export_json_text.tag_config("json_boolean", foreground="#bb9af7")
        self.export_json_text.tag_config("json_null", foreground="#f7768e")
        self.export_json_text.tag_config("json_brace", foreground="#c0caf5")

        self._set_export_json_text("Select an output folder to inspect exported data.")

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
        self._update_action_states()
        self._log(f"Selected {len(filtered)} images.")

    def _pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if not selected:
            return

        self.output_dir = Path(selected)
        self._refresh_output_label()
        self._refresh_export_manager()
        self._update_action_states()
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
            self._update_action_states()
            summary = (
                f"Done. Converted: {result.succeeded}/{result.total}. "
                f"Failed: {result.failed}. "
                f"Compression: {result.compression_rate_percent:.2f}% "
                f"({self._format_bytes(result.input_total_bytes)} → {self._format_bytes(result.output_total_bytes)}). "
                f"JSON: {result.gallery_json_path.name}"
            )
            self._log(summary)
            self._refresh_export_manager()
            self.tabs.set("Export Manager")
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
        self._clear_input_file_buttons()

        for path in self.selected_files:
            button = ctk.CTkButton(
                self.selected_images_scroll,
                text=f"  {path.name}",
                anchor="w",
                command=lambda p=path: self._select_input_image(p),
            )
            button.grid(sticky="ew", padx=0, pady=(0, 6))
            self.input_file_buttons.append(button)
            self.input_button_by_name[path.name] = button

        if not self.selected_files:
            self.selected_input_image = None
            self.selected_preview_label.configure(image=None, text="No image selected")
            self.selected_preview_name.configure(text="")
            return

        if self.selected_input_image not in self.selected_files:
            self.selected_input_image = self.selected_files[0]

        if self.selected_input_image is not None:
            self._select_input_image(self.selected_input_image)

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

    def _open_credit_link(self, _event: object) -> None:
        webbrowser.open("https://github.com/caioabrahao")

    def _refresh_export_manager(self) -> None:
        if self.output_dir is None:
            self.manager_output_label.configure(text="Exported directory: not selected")
            self.manager_status_label.configure(text="Select an output folder to load exported files.")
            self._clear_export_file_buttons()
            self.open_exported_button.configure(state="disabled")
            self._set_export_json_text("Select an output folder to inspect exported data.")
            return

        exported_dir = resolve_effective_output_dir(self.output_dir)
        self.manager_output_label.configure(text=f"Exported directory: {exported_dir}")

        if not exported_dir.exists():
            self.manager_status_label.configure(text="Exported folder does not exist yet.")
            self._clear_export_file_buttons()
            self.open_exported_button.configure(state="disabled")
            self._set_export_json_text("No exported files found yet.")
            return

        self.open_exported_button.configure(state="normal")

        records = self._load_gallery_records(exported_dir)
        image_files = sorted(
            [
                path.name
                for path in exported_dir.iterdir()
                if path.is_file() and path.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
            ]
        )

        self._clear_export_file_buttons()
        for image_name in image_files:
            button = ctk.CTkButton(
                self.export_files_scroll,
                text=f"  {image_name}",
                anchor="w",
                command=lambda name=image_name: self._select_export_image(name),
            )
            button.grid(sticky="ew", padx=0, pady=(0, 6))
            self.export_file_buttons.append(button)
            self.export_button_by_name[image_name] = button

        if not image_files:
            self.manager_status_label.configure(text="No exported images found.")
            self._set_export_json_text("No exported images found in the exported directory.")
            return

        self.manager_status_label.configure(text=f"Loaded {len(image_files)} image(s) and {len(records)} JSON record(s).")

        if self.selected_export_image not in image_files:
            self.selected_export_image = image_files[0]

        if self.selected_export_image is not None:
            self._select_export_image(self.selected_export_image)

    def _load_gallery_records(self, exported_dir: Path) -> dict[str, dict[str, Any]]:
        gallery_path = exported_dir / "gallery-data.json"
        self.export_records_by_file = {}

        if not gallery_path.exists():
            return self.export_records_by_file

        try:
            with gallery_path.open("r", encoding="utf-8") as stream:
                payload = json.load(stream)
        except (json.JSONDecodeError, OSError):
            self.manager_status_label.configure(text="Could not read gallery-data.json (invalid or inaccessible).")
            return self.export_records_by_file

        if not isinstance(payload, list):
            self.manager_status_label.configure(text="gallery-data.json format is invalid.")
            return self.export_records_by_file

        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("output_file"), str):
                self.export_records_by_file[item["output_file"]] = item

        return self.export_records_by_file

    def _show_export_record(self, image_name: str) -> None:
        record = self.export_records_by_file.get(image_name)
        if record is None:
            payload = {
                "output_file": image_name,
                "message": "No matching object found in gallery-data.json",
            }
        else:
            payload = record

        pretty = json.dumps(payload, indent=2, ensure_ascii=False)
        self._set_export_json_text(pretty)

    def _select_export_image(self, image_name: str) -> None:
        self.selected_export_image = image_name
        self._refresh_export_button_highlight()
        self._show_export_record(image_name)
        self._update_export_thumbnail(image_name)

    def _refresh_export_button_highlight(self) -> None:
        for name, button in self.export_button_by_name.items():
            if name == self.selected_export_image:
                button.configure(text=f"▶ {name}", font=ctk.CTkFont(weight="bold"))
            else:
                button.configure(text=f"  {name}", font=ctk.CTkFont(weight="normal"))

    def _set_export_json_text(self, content: str) -> None:
        self.export_json_text.delete("1.0", "end")
        self.export_json_text.insert("1.0", content)
        self._apply_json_highlighting(content)

    def _apply_json_highlighting(self, content: str) -> None:
        for tag in ("json_key", "json_string", "json_number", "json_boolean", "json_null", "json_brace"):
            self.export_json_text.tag_remove(tag, "1.0", "end")

        if not content.strip():
            return

        for match in re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"\s*:', content):
            self._tag_span("json_key", match.start(), match.end() - 1)

        for match in re.finditer(r':\s*"[^"\\]*(?:\\.[^"\\]*)*"', content):
            value_start = match.group(0).find('"')
            if value_start >= 0:
                start = match.start() + value_start
                self._tag_span("json_string", start, match.end())

        for match in re.finditer(r'(?<![\w])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w])', content):
            self._tag_span("json_number", match.start(), match.end())

        for match in re.finditer(r'(?<![\w])(true|false)(?![\w])', content):
            self._tag_span("json_boolean", match.start(), match.end())

        for match in re.finditer(r'(?<![\w])null(?![\w])', content):
            self._tag_span("json_null", match.start(), match.end())

        for match in re.finditer(r'[\{\}\[\]]', content):
            self._tag_span("json_brace", match.start(), match.end())

    def _tag_span(self, tag: str, start_offset: int, end_offset: int) -> None:
        start_index = f"1.0+{start_offset}c"
        end_index = f"1.0+{end_offset}c"
        self.export_json_text.tag_add(tag, start_index, end_index)

    def _clear_export_file_buttons(self) -> None:
        for button in self.export_file_buttons:
            button.destroy()
        self.export_file_buttons.clear()
        self.export_button_by_name.clear()
        self.selected_export_image = None
        self.export_preview_label.configure(image=None, text="No image selected")
        self.export_preview_name.configure(text="")

    def _open_exported_directory(self) -> None:
        if self.output_dir is None:
            messagebox.showinfo("Output folder not set", "Select an output folder first.")
            return

        exported_dir = resolve_effective_output_dir(self.output_dir)
        if not exported_dir.exists():
            messagebox.showinfo("Exported folder not found", "The exported folder does not exist yet.")
            return

        try:
            os.startfile(exported_dir)  # type: ignore[attr-defined]
        except Exception:
            webbrowser.open(exported_dir.resolve().as_uri())

    def _update_action_states(self) -> None:
        can_convert = bool(self.selected_files) and self.output_dir is not None
        self.start_button.configure(state="normal" if can_convert else "disabled")

    def _clear_input_file_buttons(self) -> None:
        for button in self.input_file_buttons:
            button.destroy()
        self.input_file_buttons.clear()
        self.input_button_by_name.clear()

    def _select_input_image(self, image_path: Path) -> None:
        self.selected_input_image = image_path
        self._refresh_input_button_highlight()
        self._update_input_thumbnail(image_path)

    def _refresh_input_button_highlight(self) -> None:
        selected_name = self.selected_input_image.name if self.selected_input_image is not None else None
        for name, button in self.input_button_by_name.items():
            if name == selected_name:
                button.configure(text=f"▶ {name}", font=ctk.CTkFont(weight="bold"))
            else:
                button.configure(text=f"  {name}", font=ctk.CTkFont(weight="normal"))

    def _update_input_thumbnail(self, image_path: Path) -> None:
        self._set_thumbnail(self.selected_preview_label, self.selected_preview_name, image_path, "input")

    def _update_export_thumbnail(self, image_name: str) -> None:
        if self.output_dir is None:
            return

        exported_dir = resolve_effective_output_dir(self.output_dir)
        image_path = exported_dir / image_name
        self._set_thumbnail(self.export_preview_label, self.export_preview_name, image_path, "export")

    def _set_thumbnail(self, label: ctk.CTkLabel, name_label: ctk.CTkLabel, image_path: Path, target: str) -> None:
        if not image_path.exists():
            label.configure(image=None, text="Preview unavailable")
            name_label.configure(text=image_path.name)
            return

        try:
            with Image.open(image_path) as image:
                preview = image.copy()
                preview.thumbnail((360, 220), Image.Resampling.LANCZOS)

            tk_image = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
            if target == "input":
                self.input_thumbnail_image = tk_image
            else:
                self.export_thumbnail_image = tk_image

            label.configure(image=tk_image, text="")
            name_label.configure(text=image_path.name)
        except Exception:
            label.configure(image=None, text="Preview unavailable")
            name_label.configure(text=image_path.name)
