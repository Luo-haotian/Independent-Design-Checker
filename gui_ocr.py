"""OCR GUI for IDC."""

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
from main_ocr import CheckerOCR, MODEL_CONFIGS, TESSERACT_AVAILABLE

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class IDC_GUI_OCR:
    def __init__(self, root):
        self.root = root
        self.root.title("IDC v0.11 - Structural Verification (OCR)")
        self.root.geometry("950x750")
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Independent Design Checker (IDC) with OCR",
            font=("Arial", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3)

        if TESSERACT_AVAILABLE:
            ocr_status = "OCR: Ready (Tesseract)"
            ocr_color = "green"
        else:
            ocr_status = "OCR: Not Available - Install Tesseract"
            ocr_color = "orange"

        ttk.Label(
            frame,
            text=f"Powered by {API_PROVIDER.upper()} AI | {ocr_status}",
            foreground=ocr_color,
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

        ttk.Label(frame, text="PDF File:").grid(row=3, column=0, sticky="w", pady=5)
        self.file_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_var, width=50).grid(row=3, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_file).grid(row=3, column=2)

        ttk.Label(frame, text="Type:").grid(row=4, column=0, sticky="w", pady=5)
        self.type_var = tk.StringVar(value="building")
        type_frame = ttk.Frame(frame)
        type_frame.grid(row=4, column=1, sticky="w", padx=5)
        ttk.Radiobutton(type_frame, text="Building", variable=self.type_var, value="building").pack(side="left", padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Temporary", variable=self.type_var, value="temporary").pack(side="left")

        ttk.Label(frame, text="OCR Mode:").grid(row=5, column=0, sticky="w", pady=5)
        self.ocr_var = tk.StringVar(value="auto")
        ocr_frame = ttk.Frame(frame)
        ocr_frame.grid(row=5, column=1, sticky="w", padx=5)
        ttk.Radiobutton(ocr_frame, text="Auto (detect)", variable=self.ocr_var, value="auto").pack(side="left", padx=(0, 15))
        ttk.Radiobutton(ocr_frame, text="Force OCR", variable=self.ocr_var, value="force").pack(side="left", padx=(0, 15))
        ttk.Radiobutton(ocr_frame, text="No OCR", variable=self.ocr_var, value="no").pack(side="left")

        ttk.Label(frame, text="Output:").grid(row=6, column=0, sticky="w", pady=5)
        self.output_var = tk.StringVar(value="./reports")
        ttk.Entry(frame, textvariable=self.output_var, width=50).grid(row=6, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_output).grid(row=6, column=2)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", pady=10)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(frame, textvariable=self.status_var, foreground="blue")
        self.status_label.grid(row=8, column=0, columnspan=3)

        out_frame = ttk.LabelFrame(frame, text="Output", padding=5)
        out_frame.grid(row=9, column=0, columnspan=3, sticky="nsew", pady=10)
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)
        self.output = scrolledtext.ScrolledText(out_frame, height=25, width=90, font=("Consolas", 10))
        self.output.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(9, weight=1)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=10, column=0, columnspan=3, pady=10)
        self.check_btn = ttk.Button(button_frame, text="Check Design", command=self.start)
        self.check_btn.pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side="right", padx=5)

        if not TESSERACT_AVAILABLE:
            info_text = "To enable OCR, install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
            ttk.Label(frame, text=info_text, foreground="red", font=("Arial", 9)).grid(
                row=11,
                column=0,
                columnspan=3,
                pady=(5, 0),
            )
        else:
            info_text = "Tip: Use Force OCR for scanned PDFs, Auto for mixed files, and No OCR for text-based PDFs."
            ttk.Label(frame, text=info_text, foreground="gray", font=("Arial", 9)).grid(
                row=11,
                column=0,
                columnspan=3,
                pady=(5, 0),
            )

    def update_info(self):
        model = self.model_var.get()
        max_tokens = MODEL_CONFIGS.get(model, {}).get("max_context", 8000)
        self.model_info.config(text=f"Max: {max_tokens:,} tokens")

    def browse_file(self):
        selected_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
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
        self.log("=" * 60)
        self.log("Independent Design Checker (IDC) with OCR Support")
        self.log("=" * 60)

        if not TESSERACT_AVAILABLE and self.ocr_var.get() != "no":
            self.log("WARNING: Tesseract is not installed. OCR features are disabled.")
            self.log("Install from: https://github.com/UB-Mannheim/tesseract/wiki")
            self.log("")

        self.progress.start()
        self.check_btn.config(state="disabled")
        self.status_var.set("Processing... Please wait")

        ocr_mode = self.ocr_var.get()
        force_ocr = ocr_mode == "force"
        use_ocr = ocr_mode != "no"

        worker = threading.Thread(
            target=self.check,
            args=(pdf_path, self.type_var.get(), self.output_var.get(), self.model_var.get(), force_ocr, use_ocr),
        )
        worker.daemon = True
        worker.start()

    def check(self, pdf_path, structure_type, output_dir, model, force_ocr, use_ocr):
        try:
            os.makedirs(output_dir, exist_ok=True)
            checker = CheckerOCR(model_name=model, use_ocr=use_ocr)

            capture = StringIO()
            with redirect_stdout(capture):
                success = checker.check(pdf_path, structure_type, output_dir, force_ocr=force_ocr)

            out_text = capture.getvalue()
            if out_text:
                self.root.after(0, lambda: self.log(out_text))

            self.root.after(0, lambda: self.done(success))
        except Exception as exc:
            self.root.after(0, lambda: self.log(f"ERROR: {exc}"))
            import traceback

            self.root.after(0, lambda: self.log(traceback.format_exc()))
            self.root.after(0, lambda: self.done(False))

    def done(self, success):
        self.progress.stop()
        self.check_btn.config(state="normal")
        self.log("=" * 60)
        if success:
            self.status_var.set("Analysis completed successfully.")
            self.status_label.config(foreground="green")
            self.log("[OK] Analysis completed.")
            messagebox.showinfo("Success", "Analysis completed. Report saved.")
        else:
            self.status_var.set("Analysis failed")
            self.status_label.config(foreground="red")
            self.log("[ERROR] Analysis failed.")
            messagebox.showerror("Error", "Check idc_ocr.log for details.")

    def clear(self):
        self.output.delete(1.0, "end")
        self.status_var.set("Ready")
        self.status_label.config(foreground="blue")


if __name__ == "__main__":
    root = tk.Tk()
    IDC_GUI_OCR(root)
    root.mainloop()
