"""UI compatibility utilities for V2 on top of the V1 Tkinter API."""
import tkinter as tk
from tkinter import ttk
from app import BG, PANEL, FG, MUTED, ACCENT, FONT

SURFACE = PANEL
SURFACE2 = "#253047"

def label(parent, text, *, size=10, color=None, bold=False, **kwargs):
    return tk.Label(parent, text=text, bg=BG, fg=color or FG,
                    font=(FONT, size, "bold" if bold else "normal"), **kwargs)

def button(parent, text, command):
    return tk.Button(parent, text=text, command=command, bg="#293a53",
                     fg=FG, activebackground=ACCENT,
                     relief="flat", font=(FONT, 10, "bold"),
                     padx=12, pady=8, cursor="hand2")
