#!/usr/bin/env python3
import threading
from typing import Dict, List

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import tkinter.font as tkfont

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from upsetplot import UpSet
matplotlib.use("TkAgg")

from intersections import HoldingsSumException, parse_etf_pre_series, compute_weighted_intersections
from alphavantage_api import fetch_etf_profile

DARK_BG       = "#121212"
DARK_SURFACE  = "#1E1E1E"
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

tkrs = []

def log(text_widget: ScrolledText, msg: str) -> None:
    text_widget.configure(state="normal")
    text_widget.insert(tk.END, msg + "\n")
    text_widget.see(tk.END)
    text_widget.configure(state="disabled")

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

        # Top frame (surface)
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

        # Middle: Matplotlib canvas (inherits dark via rcParams)
        self.fig = plt.Figure(figsize=(9, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor(DARK_BG)
        self.ax.set_facecolor(DARK_SURFACE)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.configure(background=DARK_BG, highlightthickness=0, bd=0)
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas.draw()

        # Bottom: Log (surface frame ---
        bottom = ttk.Frame(self, style="Surface.TFrame", padding=(10, 10, 10, 10))
        bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Log:").pack(anchor="w")
        self.log_text = ScrolledText(bottom, height=8, state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=False)

        self.log_text.configure(
            bg=DARK_SURFACE,
            fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY,     # caret color
            highlightbackground=DARK_BORDER, # border when unfocused
            highlightcolor=ACCENT            # border when focused
        )

    def _init_dark_style(self):
        self.configure(bg=DARK_BG)

        style = ttk.Style(self)
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
