"""Compatibilidad: `python modelo.py` abre la versión actual del modelo."""
import tkinter as tk
from app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()

