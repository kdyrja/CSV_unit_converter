import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import re
import numpy as np

# Supported units separated into categories
CONVERSION_GROUPS = {
    "pressure": ["hPa", "mbar", "bar", "kPa", "psi"],
    "voltage": ["V", "mV"],
    "current": ["A", "mA"],
    "temperature": ["°C", "°F", "C", "F", "degree C", "degree F"],
    "distance": ["m", "km", "yd", "mi"],
    "time": ["s", "min"],
    "air_mass": ["kg/h", "g/s", "mg/hub", "mg/stroke", "mg/impulse", "mg/str"]
}

# Dictionary for boolean text states
BOOL_MAPPING = {
    "yes": 1, "no": 0,
    "on": 1, "off": 0,
    "ano": 1, "ne": 0,
    "open": 1, "close": 0, "closed": 0,
    "true": 1, "false": 0,
    "active": 1, "inactive": 0,
    "zapnuto": 1, "vypnuto": 0
}

# Map for quick category lookup by unit
UNIT_MAP = {}
for group, units in CONVERSION_GROUPS.items():
    for u in units:
        UNIT_MAP[u] = group

class CsvConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CD unit convertor")
        self.df = None
        self.widgets = {}
        self.rpm_col = None

        # Top panel (buttons and settings)
        top_frame = tk.Frame(root)
        top_frame.pack(pady=10, fill=tk.X, padx=10)
        
        btn_frame = tk.Frame(top_frame)
        btn_frame.pack(side=tk.LEFT)
        tk.Button(btn_frame, text="1. Select CSV", command=self.load_csv, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="2. Convert & Save", command=self.save_csv, width=15).pack(side=tk.LEFT, padx=5)
        
        # Engine settings
        settings_frame = tk.Frame(top_frame)
        settings_frame.pack(side=tk.RIGHT)
        tk.Label(settings_frame, text="Cylinders:").pack(side=tk.LEFT)
        self.cylinders_var = tk.IntVar(value=4)
        self.cylinders_combo = ttk.Combobox(settings_frame, textvariable=self.cylinders_var, values=[3, 4, 5, 6, 8, 10, 12], width=4, state="readonly")
        self.cylinders_combo.pack(side=tk.LEFT, padx=5)
        
        self.rpm_label_var = tk.StringVar(value="RPM: Waiting for file")
        tk.Label(settings_frame, textvariable=self.rpm_label_var, fg="blue").pack(side=tk.LEFT, padx=10)

        # Scrollable list of values
        self.canvas = tk.Canvas(root)
        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)
        
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.scrollbar.pack(side="right", fill="y")

    def load_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not filepath: return
        try:
            with open(filepath, 'r') as f:
                first_line = f.readline()
            sep = ';' if ';' in first_line else ','
            self.df = pd.read_csv(filepath, sep=sep)
            
            self.rpm_col = None
            for col in self.df.columns:
                if re.search(r'(?i)(rpm|ot/min|1/min|otáčk)', str(col)):
                    self.rpm_col = col
                    break
            
            if self.rpm_col:
                self.rpm_label_var.set("RPM: FOUND")
            else:
                self.rpm_label_var.set("RPM: NOT FOUND")
                
            self.populate_gui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def populate_gui(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.widgets.clear()
        
        mass_stroke_units = ["mg/hub", "mg/stroke", "mg/impulse", "mg/str"]

        for col in self.df.columns:
            match = re.search(r'\(([^)]+)\)\s*$', str(col).strip())
            unit = match.group(1).strip() if match else None
            
            if unit and unit in UNIT_MAP:
                group = UNIT_MAP[unit]
                available = list(CONVERSION_GROUPS[group])
                
                if group == "air_mass" and not self.rpm_col:
                    available = [u for u in available if u not in mass_stroke_units]
                    if unit not in available: continue 
                        
                self.create_gui_row(col, available, unit)
                continue
                
            try:
                sample = self.df[col].dropna().astype(str).str.lower().str.strip().head(50)
                if any(val in BOOL_MAPPING for val in sample):
                    self.create_gui_row(col, ["Original text", "1/0"], "Original text")
            except Exception:
                pass

    def create_gui_row(self, col_name, available_options, default_value):
        frame = tk.Frame(self.scroll_frame)
        frame.pack(fill=tk.X, pady=2, anchor="w")
        tk.Label(frame, text=col_name, width=75, anchor="w").pack(side=tk.LEFT)
        
        combo = ttk.Combobox(frame, values=available_options, state="readonly", width=12)
        combo.set(default_value)
        combo.pack(side=tk.LEFT, padx=10)
        self.widgets[col_name] = (default_value, combo)

    def convert_series(self, series, from_u, to_u, rpm_series, cylinders):
        s = pd.to_numeric(series, errors='coerce')
        r = pd.to_numeric(rpm_series, errors='coerce') if rpm_series is not None else None
        group = UNIT_MAP[from_u]
        
        if group == "pressure":
            factors = {"hPa": 1, "mbar": 1, "bar": 1000, "kPa": 10, "psi": 68.9476}
            return s * factors[from_u] / factors[to_u]
        elif group == "voltage":
            factors = {"V": 1, "mV": 0.001}
            return s * factors[from_u] / factors[to_u]
        elif group == "current":
            factors = {"A": 1, "mA": 0.001}
            return s * factors[from_u] / factors[to_u]
        elif group == "distance":
            factors = {"m": 1, "km": 1000, "yd": 0.9144, "mi": 1609.344}
            return s * factors[from_u] / factors[to_u]
        elif group == "time":
            factors = {"s": 1, "min": 60}
            return s * factors[from_u] / factors[to_u]
            
        elif group == "temperature":
            is_c_from = from_u in ["°C", "C", "degree C"]
            is_c_to = to_u in ["°C", "C", "degree C"]
            if is_c_from and not is_c_to: return s * 1.8 + 32
            if not is_c_from and is_c_to: return (s - 32) / 1.8
            return s
            
        elif group == "air_mass":
            mass_stroke_units = ["mg/hub", "mg/stroke", "mg/impulse", "mg/str"]
            if from_u == "g/s": 
                kg_h = s * 3.6
            elif from_u in mass_stroke_units and r is not None:
                kg_h = (s * 30 * r * cylinders) / 1000000.0
            else: 
                kg_h = s
            
            if to_u == "kg/h": return kg_h
            if to_u == "g/s": return kg_h / 3.6
            if to_u in mass_stroke_units and r is not None:
                r_safe = r.replace(0, np.nan) 
                return (kg_h * 1000000.0) / (30 * r_safe * cylinders)
                
        return s

    def save_csv(self):
        if self.df is None: return
        out_df = self.df.copy()
        
        cylinders = self.cylinders_var.get()
        rpm_series = self.df[self.rpm_col] if self.rpm_col else None
        
        for col, (orig_unit, combo) in self.widgets.items():
            target_unit = combo.get()
            if orig_unit != target_unit:
                if orig_unit == "Original text" and target_unit == "1/0":
                    mapped = out_df[col].astype(str).str.lower().str.strip().map(BOOL_MAPPING)
                    out_df[col] = mapped.fillna(out_df[col]) 
                else:
                    out_df[col] = self.convert_series(out_df[col], orig_unit, target_unit, rpm_series, cylinders)
                    out_df[col] = out_df[col].round(4)
                    
                    new_col_name = re.sub(r'\([^)]+\)\s*$', f'({target_unit})', col)
                    out_df.rename(columns={col: new_col_name}, inplace=True)
        
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if save_path:
            out_df.to_csv(save_path, index=False)
            messagebox.showinfo("Done", "Conversion complete and file successfully saved.")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x600")
    app = CsvConverterApp(root)
    root.mainloop()
