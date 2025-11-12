#!/usr/bin/env python3
"""
ETF Overlap GUI (Alpha Vantage + UpSet)
---------------------------------------
- Enter up to 5 ETF tickers and an Alpha Vantage API key.
- Fetches holdings via ETF_PROFILE (cached in ./data/<TICKER>.json to respect 25 calls/day).
- Computes all intersections and plots an UpSet chart where bar heights equal the
  SUM of per-ETF $ values of holdings in that exact intersection.
    value_per_holding_in_etf = float(net_assets) * float(weight)
- Each holding belongs to exactly one intersection (its exact membership signature).
- Bars therefore represent the total dollars represented by those holdings across
  the ETFs participating in that intersection (sum across those ETFs).
Dependencies:
  pip install requests pandas numpy matplotlib upsetplot
"""
import os
import json
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import tkinter.font as tkfont

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from upsetplot import UpSet, from_memberships

# --- Dark mode palette + Matplotlib defaults ---
DARK_BG       = "#121212"   # app/window background
DARK_SURFACE  = "#1E1E1E"   # frames, panels, entry backgrounds
DARK_BORDER   = "#2A2A2A"
FG_PRIMARY    = "#564bd3"
FG_MUTED      = "#372f88"
ACCENT        = "#4C8BF5"

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": DARK_SURFACE,
    "savefig.facecolor": DARK_BG,
    "text.color": ACCENT,
    "axes.labelcolor": FG_PRIMARY,
    "axes.edgecolor": FG_PRIMARY,
    "xtick.color": FG_PRIMARY,
    "ytick.color": FG_PRIMARY,
    "grid.color": FG_MUTED,
})

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

AV_BASE = "https://www.alphavantage.co/query"
TIMEOUT = 30

tkrs = []

class HoldingsSumException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message})"

def log(text_widget: ScrolledText, msg: str) -> None:
    text_widget.configure(state="normal")
    text_widget.insert(tk.END, msg + "\n")
    text_widget.see(tk.END)
    text_widget.configure(state="disabled")

def cache_path_for(symbol: str) -> Path:
    return DATA_DIR / f"{symbol.upper()}.json"

def load_cached(symbol: str) -> dict | None:
    p = cache_path_for(symbol)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_cache(symbol: str, payload: dict) -> None:
    p = cache_path_for(symbol)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def fetch_etf_profile(symbol: str, api_key: str, force_refresh: bool, log_fn) -> dict:
    sym = symbol.upper().strip()
    if not sym:
        raise ValueError("Empty ticker")
    if not force_refresh:
        cached = load_cached(sym)
        if cached:
            log_fn(f"[cache] Using cached {sym}")
            return cached

    params = {
        "function": "ETF_PROFILE",
        "symbol": sym,
        "apikey": api_key.strip()
    }
    url = AV_BASE
    log_fn(f"[net] GET {url} ... ({sym})")
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    data["ticker"] = sym
    data["fetched_at"] = datetime.now().isoformat()
    data.pop("sectors", None)
    for h in data["holdings"]:
        if h['symbol'] == "n/a":
            h['symbol'] = h['description'].upper().replace(" ", "_")
    # Basic sanity checks
    if not isinstance(data, dict) or "holdings" not in data:
        # Alpha Vantage returns "Note" when rate-limited; or "Information" for guidance.
        note = data.get("Note") or data.get("Information") or str(data)[:200]
        raise RuntimeError(f"Unexpected response for {sym}: {note}")
    save_cache(sym, data)
    return data

def parse_etf_pre_series(etf_json: dict):
    """
    Returns (net_assets, holding_values) where holding_values maps holding symbol -> dollar value in this ETF.
    value = net_assets * weight
    """
    try:
        net_assets = float(etf_json.get("net_assets", "0"))
    except Exception:
        net_assets = 0.0

    etf_json['net_assets'] = net_assets
    weights_sum = 0
    for h in etf_json.get("holdings", []):
        w = float(h.get('weight', '0').replace('%', '')) * 100
        h['weight'] = w
        weights_sum += w

    if weights_sum < 99:
        raise HoldingsSumException(f"ETF {etf_json['ticker']} holdings only sum to {int(weights_sum)}%")

def compute_weighted_intersections(etfs: List, pre_series: Dict):
    # Orgnaize holdings by which ETFs hold them
    holding_map = {}
    for etf in etfs:
        etf_t = etf.get("ticker", "UNKNOWN")
        for h in etf.get("holdings", []):
            holding_t = h.get("symbol", "UNKNOWN")
            if holding_map.get(holding_t) is None:
                holding_map[holding_t] = [{'etf': etf_t, 'value': h['weight']}]
            else:
                holding_map[holding_t].append({'etf': etf_t, 'value': h['weight']})

    print(json.dumps(holding_map, indent=4))

    removed_ticker = None
    while len(holding_map) > 0:
        if removed_ticker is not None:
            holding_map.pop(removed_ticker, None)
            removed_ticker = None

        for ticker, owners in holding_map.items():
            if len(owners) == 0:
                removed_ticker = ticker
                continue

            # Handle the interesction names and data population
            intersection_name = []
            for owner in owners:
                intersection_name.append(owner['etf'])
            if intersection_name not in pre_series['intersections']:
                pre_series['intersections'].append(intersection_name)
                pre_series['data'].append(0.0)
            intersection_index = pre_series['intersections'].index(intersection_name)

            # Find which owner has the minimum weight for this holding and add that weight to the
            # intersection data.
            owners.sort(key=lambda x: x['value'])
            min_owner = owners[0]
            min_value = min_owner['value']
            pre_series['data'][intersection_index] += min_value

            # Subtract the minimum weight from all other owners for this holding.
            for owner in owners:
                owner['value'] -= min_value

            # Pop the owner with the minimum weight, and add that weight to the intersection data.
            owners.pop(0)

    # Build a Series indexed by memberships with per-element values, then aggregate by sum
    s = from_memberships(pre_series['intersections'], data=pre_series['data'])
    # Ensure aggregation by exact membership signature
    s = s.groupby(level=s.index.names).sum()

    return s

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ETF Overlap (Alpha Vantage UpSet)")
        try:
            self.state("zoomed")          # Windows
        except tk.TclError:
            self.attributes("-zoomed", 1) # Linux (if supported)

        default_font = tkfont.nametofont("TkDefaultFont")
        text_font    = tkfont.nametofont("TkTextFont")
        fixed_font   = tkfont.nametofont("TkFixedFont")

        for f in (default_font, text_font, fixed_font):
            size = f.cget("size")
            f.configure(size=int(size * 1.5))  # scale up by 2×


        # Init dark styling first
        self._init_dark_style()

        # --- Top frame (surface) ---
        top = ttk.Frame(self, style="Surface.TFrame", padding=(10, 10, 10, 10))
        top.pack(side=tk.TOP, fill=tk.X)

        # Subframe 1: API controls
        api_row = ttk.Frame(top, style="Surface.TFrame")
        api_row.grid(row=0, column=0, sticky="we")

        ttk.Label(api_row, text="Alpha Vantage API Key:", style="TLabel").grid(row=0, column=0, sticky="w")
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_row, textvariable=self.api_key_var)
        self.api_key_entry.grid(row=0, column=1, sticky="we", padx=(5, 15))

        self.force_var = tk.BooleanVar(value=False)
        self.force_chk = ttk.Checkbutton(api_row, text="Force refresh (ignore cache)", variable=self.force_var)
        self.force_chk.grid(row=0, column=2, sticky="w")

        api_row.grid_columnconfigure(1, weight=1)

        # Subframe 2: Tickers row (even spacing)
        tick_row = ttk.Frame(top, style="Surface.TFrame")
        tick_row.grid(row=1, column=0, sticky="we", pady=(8, 0))

        ttk.Label(tick_row, text="Tickers (up to 5):").grid(row=0, column=0, sticky="w")

        self.ticker_vars = [tk.StringVar() for _ in range(5)]
        for c in range(1, 8):
            tick_row.grid_columnconfigure(c, weight=1, uniform="tickers")

        for i in range(5):
            e = ttk.Entry(tick_row, textvariable=self.ticker_vars[i])
            e.grid(row=0, column=1 + i, sticky="we", padx=5)

        self.go_btn = ttk.Button(tick_row, text="Fetch & Plot", command=self.on_fetch_plot)
        self.go_btn.grid(row=0, column=6, sticky="we", padx=(15, 5))

        self.clear_btn = ttk.Button(tick_row, text="Clear", command=self.on_clear)
        self.clear_btn.grid(row=0, column=7, sticky="we")

        # --- Middle: Matplotlib canvas (inherits dark via rcParams) ---
        self.fig = plt.Figure(figsize=(9, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        # Explicit facecolors in case rcParams are overridden elsewhere:
        self.fig.patch.set_facecolor(DARK_BG)
        self.ax.set_facecolor(DARK_SURFACE)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.configure(background=DARK_BG, highlightthickness=0, bd=0)
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas.draw()

        # --- Bottom: Log (surface frame) ---
        bottom = ttk.Frame(self, style="Surface.TFrame", padding=(10, 10, 10, 10))
        bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Log:").pack(anchor="w")
        self.log_text = ScrolledText(bottom, height=8, state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=False)

        # Style the tk.ScrolledText internals (not ttk)
        self.log_text.configure(
            bg=DARK_SURFACE,
            fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY,     # caret color
            highlightbackground=DARK_BORDER, # border when unfocused
            highlightcolor=ACCENT            # border when focused
        )

    def _init_dark_style(self):
        # Window background
        self.configure(bg=DARK_BG)

        style = ttk.Style(self)
        # Use a theme that respects custom colors
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Base colors for common widgets
        style.configure(".", background=DARK_BG, foreground=FG_PRIMARY)

        # Frames/containers
        style.configure("TFrame", background=DARK_BG)
        style.configure("Surface.TFrame", background=DARK_SURFACE)

        # Labels
        style.configure("TLabel", background=DARK_BG, foreground=FG_PRIMARY)

        # Entry fields
        # Note: 'fieldbackground' drives the inside of ttk.Entry on 'clam'
        style.configure("TEntry",
                        fieldbackground=DARK_SURFACE,
                        background=DARK_SURFACE,
                        foreground=FG_PRIMARY)
        style.map("TEntry",
                fieldbackground=[("active", DARK_SURFACE)],
                foreground=[("disabled", FG_MUTED)])

        # Buttons
        style.configure("TButton",
                        background=DARK_SURFACE,
                        foreground=FG_PRIMARY,
                        bordercolor=DARK_BORDER,
                        focusthickness=1,
                        focuscolor=ACCENT)
        style.map("TButton",
                background=[("active", "#2A2F3A"), ("pressed", "#263044")],
                foreground=[("disabled", FG_MUTED)])

        # Checkbuttons
        style.configure("TCheckbutton",
                        background=DARK_BG,
                        foreground=FG_PRIMARY)
        style.map("TCheckbutton",
                foreground=[("disabled", FG_MUTED)])


    def on_clear(self):
        for v in self.ticker_vars:
            v.set("")
        self.ax.clear()
        self.ax.set_title("")
        self.canvas.draw()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def async_run(self, target, *args, **kwargs):
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        t.start()

    def on_fetch_plot(self):
        api_key = self.api_key_var.get().strip()
        tickers = [v.get().upper().strip() for v in self.ticker_vars if v.get().strip()]
        tickers = [t for t in tickers if t]
        if not tickers:
            messagebox.showwarning("Input needed", "Please enter at least one ETF ticker.")
            return
        if len(tickers) > 5:
            messagebox.showwarning("Limit", "Please enter at most 5 tickers.")
            return
        if not api_key:
            if not messagebox.askyesno("No API key", "No API key entered. Use 'demo' (very limited)?"):
                return
            api_key = "demo"

        self.go_btn.configure(state="disabled")
        self.ax.clear()
        self.ax.set_title("")
        self.canvas.draw()

        self.async_run(self._fetch_and_plot_worker, api_key, tickers, self.force_var.get())

    def _fetch_and_plot_worker(self, api_key: str, tickers: List[str], force_refresh: bool):
        def log_fn(m): self.after(0, log, self.log_text, m)

        pre_series = {
            'intersections': [],
            'data': []
        }

        etfs = []

        try:
            tickers.sort()
            for sym in tickers:
                data = fetch_etf_profile(sym, api_key, force_refresh, log_fn)

                if float(data['net_assets']) <= 0:
                    log_fn(f"[warn] {sym}: no usable holdings/net_assets")
                    continue

                try:
                    parse_etf_pre_series(data)
                except HoldingsSumException as e:
                    log_fn(f"[warn] {e}")
                    pass

                etfs.append(data)

            if len(etfs) <= 1:
                raise RuntimeError("No valid ETFs to plot.")

            s = compute_weighted_intersections(etfs, pre_series)

            # Plot UpSet (single figure)
            self.ax.clear()
            # Create a new UpSet on a fresh figure to avoid subplot layout issues, then draw it onto canvas
            fig = plt.Figure(figsize=(9,6), dpi=100)
            upset = UpSet(s, show_counts=True, sort_by='-degree', facecolor=FG_PRIMARY)
            upset.plot(fig=fig)

            # Replace figure in canvas
            def update_canvas():
                # destroy old canvas widget and replace to ensure full redraw
                self.canvas.get_tk_widget().destroy()
                self.fig = fig
                self.canvas = FigureCanvasTkAgg(self.fig, master=self)
                self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
                self.fig.patch.set_facecolor(DARK_BG)
                for a in self.fig.axes:
                    a.set_facecolor(DARK_SURFACE)
                self.canvas.draw()

                # Add a descriptive suptitle without specifying colors/styles
                self.fig.suptitle("Weighted UpSet: sum of $ values for holdings in each exact intersection", y=1.02)
                self.canvas.draw()

            self.after(0, update_canvas)
            log_fn("[done] Plot ready.")
        except Exception as e:
            log_fn(f"[fatal] {e}")
        finally:
            self.after(0, lambda: self.go_btn.configure(state="normal"))

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
