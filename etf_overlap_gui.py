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

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from upsetplot import UpSet, from_memberships

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

AV_BASE = "https://www.alphavantage.co/query"
TIMEOUT = 30

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
    # Basic sanity checks
    if not isinstance(data, dict) or "holdings" not in data:
        # Alpha Vantage returns "Note" when rate-limited; or "Information" for guidance.
        note = data.get("Note") or data.get("Information") or str(data)[:200]
        raise RuntimeError(f"Unexpected response for {sym}: {note}")
    save_cache(sym, data)
    return data

def parse_holdings(etf_json: dict, symbol: str) -> Tuple[float, Dict[str, float]]:
    """
    Returns (net_assets, holding_values) where holding_values maps holding symbol -> dollar value in this ETF.
    value = net_assets * weight
    """
    try:
        net_assets = float(etf_json.get("net_assets", "0"))
    except Exception:
        net_assets = 0.0

    holdings = etf_json.get("holdings", [])
    values: Dict[str, float] = {}
    for h in holdings:
        try:
            hs = str(h.get("symbol", "")).upper().strip()
            wt = float(h.get("weight", "0"))
            if hs and wt > 0:
                values[hs] = values.get(hs, 0.0) + (net_assets * wt)
        except Exception:
            continue
    return net_assets, values

def compute_weighted_intersections(etf_names: List[str], per_etf_values: List[Dict[str, float]]):
    """
    Build memberships (list of sets names for each element/holding) and a parallel list of values.
    For each holding (stock), determine exactly which ETFs contain it => membership signature.
    The per-element value is the SUM of that holding's $ values across ETFs in its membership.
    """
    n = len(etf_names)
    name_list = [nm for nm in etf_names]

    # Collect all unique holdings
    all_holdings: Set[str] = set()
    for d in per_etf_values:
        all_holdings.update(d.keys())

    memberships: List[Set[str]] = []
    values: List[float] = []

    for hs in sorted(all_holdings):
        present_idxs = [i for i, d in enumerate(per_etf_values) if hs in d]
        if not present_idxs:
            continue
        member_names = {name_list[i] for i in present_idxs}
        # sum of $ value across the participating ETFs
        val = float(sum(per_etf_values[i][hs] for i in present_idxs))
        memberships.append(member_names)
        values.append(val)

    # Build a Series indexed by memberships with per-element values, then aggregate by sum
    s = from_memberships(memberships, data=values)
    # Ensure aggregation by exact membership signature
    s = s.groupby(level=s.index.names).sum()
    return s

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ETF Overlap (Alpha Vantage UpSet)")
        self.geometry("1100x800")

        # Top frame - inputs
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        ttk.Label(top, text="Alpha Vantage API Key:").grid(row=0, column=0, sticky="w")
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(top, textvariable=self.api_key_var, width=40)
        self.api_key_entry.grid(row=0, column=1, sticky="w", padx=(5,15))

        self.force_var = tk.BooleanVar(value=False)
        self.force_chk = ttk.Checkbutton(top, text="Force refresh (ignore cache)", variable=self.force_var)
        self.force_chk.grid(row=0, column=2, sticky="w", padx=(5,15))

        ttk.Label(top, text="Tickers (up to 5):").grid(row=1, column=0, sticky="w", pady=(8,0))
        self.ticker_vars = [tk.StringVar() for _ in range(5)]
        for i in range(5):
            e = ttk.Entry(top, textvariable=self.ticker_vars[i], width=10)
            e.grid(row=1, column=1+i, sticky="w", padx=5, pady=(8,0))

        self.go_btn = ttk.Button(top, text="Fetch & Plot", command=self.on_fetch_plot)
        self.go_btn.grid(row=1, column=6, padx=(15,0), pady=(8,0))

        self.clear_btn = ttk.Button(top, text="Clear", command=self.on_clear)
        self.clear_btn.grid(row=1, column=7, padx=(5,0), pady=(8,0))

        # Middle - Matplotlib canvas
        self.fig = plt.Figure(figsize=(9,6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bottom - log
        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=10, pady=(0,10))
        ttk.Label(bottom, text="Log:").pack(anchor="w")
        self.log_text = ScrolledText(bottom, height=8, state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=False)

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
        try:
            etf_jsons = []
            per_etf_values = []
            names = []

            for sym in tickers:
                try:
                    data = fetch_etf_profile(sym, api_key, force_refresh, log_fn)
                    net_assets, values = parse_holdings(data, sym)
                    if net_assets <= 0 or not values:
                        log_fn(f"[warn] {sym}: no usable holdings/net_assets")
                        continue
                    names.append(sym)
                    etf_jsons.append(data)
                    per_etf_values.append(values)
                    log_fn(f"[ok] {sym}: {len(values)} holdings parsed, net_assets=${net_assets:,.0f}")
                except Exception as e:
                    log_fn(f"[error] {sym}: {e}")

            if len(names) == 0:
                raise RuntimeError("No valid ETFs to plot.")

            # Compute weighted intersections series
            s = compute_weighted_intersections(names, per_etf_values)

            # Plot UpSet (single figure)
            self.ax.clear()
            # Create a new UpSet on a fresh figure to avoid subplot layout issues, then draw it onto canvas
            fig = plt.Figure(figsize=(9,6), dpi=100)
            upset = UpSet(s, show_counts=True)  # counts are the number of unique holdings in each intersection
            upset.plot(fig=fig)

            # Replace figure in canvas
            def update_canvas():
                # destroy old canvas widget and replace to ensure full redraw
                self.canvas.get_tk_widget().destroy()
                self.fig = fig
                self.canvas = FigureCanvasTkAgg(self.fig, master=self)
                self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
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
