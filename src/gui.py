from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from . import pipeline
from .utils import (
    UserError,
    ensure_input_file,
    ensure_output_dir,
    open_folder,
    output_dir_for_input,
)


class MiniLangGUI:
    def __init__(self, initial_file: Path | None = None) -> None:
        self.root = tk.Tk()
        self.root.title("MiniLang Compiler (M0 stub)")
        self.file_path: Path | None = None

        self.output_var = tk.StringVar(value="Select a file to see output location.")
        self.file_var = tk.StringVar(value="No file selected.")

        self._run_buttons: list[tk.Button] = []

        self._build_menu()
        self._build_toolbar()
        self._build_body()

        if initial_file:
            self._set_file(initial_file)

    def run(self) -> None:
        self.root.mainloop()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self._choose_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        for stage in ["lexer", "table", "parse", "ir", "opt", "codegen", "all"]:
            run_menu.add_command(
                label=stage.capitalize(), command=lambda s=stage: self._run_stage(s)
            )
        menubar.add_cascade(label="Run", menu=run_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Open Output Folder", command=self._open_output_dir)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    def _build_toolbar(self) -> None:
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED, padx=4, pady=4)
        toolbar.pack(fill="x")

        tk.Button(toolbar, text="Open File", command=self._choose_file).pack(
            side=tk.LEFT, padx=2
        )

        for label, stage in [
            ("Run All", "all"),
            ("Lexer", "lexer"),
            ("Table", "table"),
            ("Parse", "parse"),
            ("IR", "ir"),
            ("Opt", "opt"),
            ("Codegen", "codegen"),
        ]:
            btn = tk.Button(toolbar, text=label, command=lambda s=stage: self._run_stage(s))
            btn.pack(side=tk.LEFT, padx=2)
            self._run_buttons.append(btn)

        open_btn = tk.Button(toolbar, text="Open Output Folder", command=self._open_output_dir)
        open_btn.pack(side=tk.LEFT, padx=2)
        self._run_buttons.append(open_btn)
        self._set_run_buttons_enabled(False)

    def _build_body(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Selected file:").pack(anchor="w")
        tk.Label(frame, textvariable=self.file_var, fg="#2c3e50", wraplength=420).pack(
            anchor="w", pady=(0, 8)
        )

        tk.Label(frame, text="Output folder:").pack(anchor="w")
        tk.Label(frame, textvariable=self.output_var, fg="#2c3e50", wraplength=420).pack(
            anchor="w", pady=(0, 12)
        )

        tk.Label(frame, text="Logs:").pack(anchor="w")
        log_frame = tk.Frame(frame)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _choose_file(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Select MiniLang source",
            filetypes=[("MiniLang files", "*.min"), ("All files", "*.*")],
        )
        if not chosen:
            return
        self._set_file(Path(chosen))

    def _set_file(self, path: Path) -> None:
        try:
            validated = ensure_input_file(path)
        except UserError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.file_path = validated
        self.file_var.set(str(self.file_path))
        self.output_var.set(str(output_dir_for_input(self.file_path)))
        self._set_run_buttons_enabled(True)
        self._log(f"Selected file: {self.file_path}")

    def _run_stage(self, stage: str) -> None:
        if not self.file_path:
            messagebox.showerror("Error", "Please open a MiniLang source file first.")
            self._log("Error: no file selected.")
            return

        self._log(f"Running '{stage}' on {self.file_path}...")
        try:
            result = pipeline.run_stage(stage, str(self.file_path))
        except UserError as exc:
            messagebox.showerror("Error", str(exc))
            self._log(f"Error: {exc}")
            return
        except Exception as exc:  # pragma: no cover - defensive catch
            messagebox.showerror("Error", f"Unexpected error: {exc}")
            self._log(f"Error: Unexpected error: {exc}")
            return

        generated = "\n".join(str(p) for p in result.generated) or "No files created."
        messagebox.showinfo(
            "Run finished",
            f"Stage '{stage}' completed.\nOutput folder: {result.output_dir}\n\nGenerated:\n{generated}",
        )
        self.output_var.set(str(result.output_dir))
        self._log(f"Success: stage '{stage}' finished. Output at {result.output_dir}")

    def _open_output_dir(self) -> None:
        if not self.file_path:
            messagebox.showinfo("Info", "No file selected yet.")
            self._log("Info: attempted to open output folder without a file.")
            return
        out_dir = ensure_output_dir(self.file_path)
        open_folder(out_dir)
        self._log(f"Opened output folder: {out_dir}")

    def _set_run_buttons_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in self._run_buttons:
            btn.config(state=state)

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def launch(initial_file: Path | None = None) -> None:
    app = MiniLangGUI(initial_file=initial_file)
    app.run()
