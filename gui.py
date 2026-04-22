"""Standard GUI for IDC."""

import logging
import os
import sys
import threading
import tkinter as tk
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, str(Path(__file__).parent))
from config import API_PROVIDER, MODEL_NAME
from main import Checker, MODEL_CONFIGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class IDC_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IDC v0.12 - Structural Verification")
        self.root.geometry("900x700")
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Independent Design Checker (IDC)",
            font=("Arial", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3)
        ttk.Label(
            frame,
            text=f"Powered by {API_PROVIDER.upper()} AI",
            foreground="gray",
        ).grid(row=1, column=0, columnspan=3, pady=(0, 10))

        ttk.Label(frame, text="Model:").grid(row=2, column=0, sticky="w", pady=5)
        self.model_var = tk.StringVar(value=MODEL_NAME)
        model_combo = ttk.Combobox(
            frame,
            textvariable=self.model_var,
            values=list(MODEL_CONFIGS.keys()),
            state="readonly",
            width=28,
        )
        model_combo.grid(row=2, column=1, sticky="w", padx=5)
        self.model_info = ttk.Label(frame, text="")
        self.model_info.grid(row=2, column=2, sticky="w")
        self.update_info()
        model_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_info())

        ttk.Label(frame, text="PDF:").grid(row=3, column=0, sticky="w", pady=5)
        self.file_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_var, width=50).grid(row=3, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_file).grid(row=3, column=2)

        ttk.Label(frame, text="Type:").grid(row=4, column=0, sticky="w", pady=5)
        self.type_var = tk.StringVar(value="building")
        ttk.Radiobutton(frame, text="Building", variable=self.type_var, value="building").grid(
            row=4,
            column=1,
            sticky="w",
            padx=5,
        )
        ttk.Radiobutton(frame, text="Temporary", variable=self.type_var, value="temporary").grid(
            row=4,
            column=1,
            padx=(100, 0),
        )

        ttk.Label(frame, text="Output:").grid(row=5, column=0, sticky="w", pady=5)
        self.output_var = tk.StringVar(value="./reports")
        ttk.Entry(frame, textvariable=self.output_var, width=50).grid(row=5, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_output).grid(row=5, column=2)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=10)

        out_frame = ttk.LabelFrame(frame, text="Output", padding=5)
        out_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=10)
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)
        self.output = scrolledtext.ScrolledText(out_frame, height=25, width=85)
        self.output.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(7, weight=1)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=10)
        self.check_btn = ttk.Button(button_frame, text="Check Design", command=self.start)
        self.check_btn.pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side="right", padx=5)

    def update_info(self):
        model = self.model_var.get()
        max_tokens = MODEL_CONFIGS.get(model, {}).get("max_context", 8000)
        self.model_info.config(text=f"Max: {max_tokens:,} tokens")

    def browse_file(self):
        selected_file = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if selected_file:
            self.file_var.set(selected_file)

    def browse_output(self):
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            self.output_var.set(selected_dir)

    def log(self, text):
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.update()

    def start(self):
        pdf_path = self.file_var.get()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("Error", "Please select a valid PDF file.")
            return

        self.clear()
        self.log("=" * 50)
        self.log("Independent Design Checker (IDC)")
        self.log("=" * 50)

        self.progress.start()
        self.check_btn.config(state="disabled")

        worker = threading.Thread(
            target=self.check,
            args=(pdf_path, self.type_var.get(), self.output_var.get(), self.model_var.get()),
        )
        worker.daemon = True
        worker.start()

    def check(self, pdf_path, structure_type, output_dir, model):
        try:
            os.makedirs(output_dir, exist_ok=True)
            checker = Checker(model_name=model)

            capture = StringIO()
            with redirect_stdout(capture):
                success = checker.check(pdf_path, structure_type, output_dir)
            report_file = checker.last_report_file

            out_text = capture.getvalue()
            if out_text:
                self.root.after(0, lambda: self.log(out_text))

            self.root.after(0, lambda: self.done(success, report_file))
        except Exception as exc:
            self.root.after(0, lambda: self.log(f"ERROR: {exc}"))
            self.root.after(0, lambda: self.done(False, None))

    def done(self, success, report_file=None):
        self.progress.stop()
        self.check_btn.config(state="normal")
        self.log("=" * 50)
        if success:
            self.log("[OK] Analysis completed.")
            if report_file:
                self.log(f"[OK] Output file: {report_file}")
                suffix = Path(report_file).suffix.lower()
                if suffix == ".txt":
                    message = f"Analysis completed.\nDOCX generation failed, so a text fallback was saved:\n{report_file}"
                else:
                    message = f"Analysis completed.\nReport saved:\n{report_file}"
            else:
                message = "Analysis completed."
            messagebox.showinfo("Success", message)
        else:
            self.log("[ERROR] Analysis failed.")
            messagebox.showerror("Error", "Check idc.log for details.")

    def clear(self):
        self.output.delete(1.0, "end")


if __name__ == "__main__":
    root = tk.Tk()
    IDC_GUI(root)
    root.mainloop()
