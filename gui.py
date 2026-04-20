"""GUI for IDC"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import logging
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).parent))
from main import Checker, MODEL_CONFIGS, estimate_tokens, API_PROVIDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class IDC_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IDC - Structural Verification")
        self.root.geometry("900x700")
        self.setup_ui()
    
    def setup_ui(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text="Independent Design Checker (IDC)", 
                 font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=3)
        provider_text = f"Powered by {API_PROVIDER.upper()} AI"
        ttk.Label(frame, text=provider_text, foreground="gray").grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Model
        ttk.Label(frame, text="Model:").grid(row=2, column=0, sticky="w", pady=5)
        self.model_var = tk.StringVar(value="grok-4-1-fast-non-reasoning")
        model_combo = ttk.Combobox(frame, textvariable=self.model_var, 
                                   values=list(MODEL_CONFIGS.keys()), state="readonly", width=20)
        model_combo.grid(row=2, column=1, sticky="w", padx=5)
        self.model_info = ttk.Label(frame, text="")
        self.model_info.grid(row=2, column=2, sticky="w")
        self.update_info()
        model_combo.bind('<<ComboboxSelected>>', lambda e: self.update_info())
        
        # File
        ttk.Label(frame, text="PDF:").grid(row=3, column=0, sticky="w", pady=5)
        self.file_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_var, width=50).grid(row=3, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_file).grid(row=3, column=2)
        
        # Type
        ttk.Label(frame, text="Type:").grid(row=4, column=0, sticky="w", pady=5)
        self.type_var = tk.StringVar(value="building")
        ttk.Radiobutton(frame, text="Building", variable=self.type_var, value="building").grid(row=4, column=1, sticky="w", padx=5)
        ttk.Radiobutton(frame, text="Temporary", variable=self.type_var, value="temporary").grid(row=4, column=1, padx=(100, 0))
        
        # Output
        ttk.Label(frame, text="Output:").grid(row=5, column=0, sticky="w", pady=5)
        self.output_var = tk.StringVar(value="./reports")
        ttk.Entry(frame, textvariable=self.output_var, width=50).grid(row=5, column=1, sticky="ew", padx=5)
        ttk.Button(frame, text="Browse...", command=self.browse_output).grid(row=5, column=2)
        
        # Progress
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=10)
        
        # Output text
        out_frame = ttk.LabelFrame(frame, text="Output", padding=5)
        out_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=10)
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(0, weight=1)
        self.output = scrolledtext.ScrolledText(out_frame, height=25, width=85)
        self.output.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(7, weight=1)
        
        # Buttons
        btn = ttk.Frame(frame)
        btn.grid(row=8, column=0, columnspan=3, pady=10)
        self.check_btn = ttk.Button(btn, text="Check Design", command=self.start)
        self.check_btn.pack(side="left", padx=5)
        ttk.Button(btn, text="Clear", command=self.clear).pack(side="left", padx=5)
        ttk.Button(btn, text="Exit", command=self.root.quit).pack(side="right", padx=5)
    
    def update_info(self):
        m = self.model_var.get()
        max_tok = MODEL_CONFIGS.get(m, {}).get('max_context', 8000)
        self.model_info.config(text=f"Max: {max_tok:,} tokens")
    
    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.file_var.set(f)
    
    def browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_var.set(d)
    
    def log(self, text):
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.update()
    
    def start(self):
        pdf = self.file_var.get()
        if not pdf or not os.path.exists(pdf):
            messagebox.showerror("Error", "Select a valid PDF file")
            return
        
        self.clear()
        self.log("=" * 50)
        self.log("Independent Design Checker (IDC)")
        self.log("=" * 50)
        
        self.progress.start()
        self.check_btn.config(state="disabled")
        
        t = threading.Thread(target=self.check, args=(
            pdf, self.type_var.get(), self.output_var.get(), self.model_var.get()
        ))
        t.daemon = True
        t.start()
    
    def check(self, pdf, stype, out, model):
        try:
            os.makedirs(out, exist_ok=True)
            checker = Checker(model_name=model)
            
            buf = StringIO()
            with redirect_stdout(buf):
                success = checker.check(pdf, stype, out)
            
            out_text = buf.getvalue()
            if out_text:
                self.root.after(0, lambda: self.log(out_text))
            
            self.root.after(0, lambda: self.done(success))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"ERROR: {e}"))
            self.root.after(0, lambda: self.done(False))
    
    def done(self, success):
        self.progress.stop()
        self.check_btn.config(state="normal")
        self.log("=" * 50)
        if success:
            self.log("✓ Analysis completed!")
            messagebox.showinfo("Success", "Analysis completed!")
        else:
            self.log("✗ Analysis failed.")
            messagebox.showerror("Error", "Check idc.log for details.")
    
    def clear(self):
        self.output.delete(1.0, "end")


if __name__ == "__main__":
    root = tk.Tk()
    IDC_GUI(root)
    root.mainloop()
