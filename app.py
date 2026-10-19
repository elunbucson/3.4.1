"""Ventana de escritorio para comparar rutas y las tres políticas de replanteo."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import rutas
from motor_dinamico import ejecutar

COLORS = ["#17a398", "#3366cc", "#e08b2d"]
POLICIES = {"Ruta fija": "static", "Recalcular en cada paso": "each_step",
            "Recalcular al detectar incidente": "event"}

class App:
    def __init__(self, root):
        self.root = root
        root.title("Meta 3.4.1 | Navegación dinámica a UABC Otay")
        root.geometry("1180x770")
        self.status = tk.StringVar(value="Preparando red vial y simulación...")
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Política:").pack(side="left")
        self.policy = ttk.Combobox(top, values=list(POLICIES), state="readonly", width=34)
        self.policy.current(2)
        self.policy.pack(side="left", padx=8)
        ttk.Button(top, text="Mostrar recorrido", command=self.draw_selected).pack(side="left", padx=4)
        ttk.Button(top, text="Animar", command=self.animate).pack(side="left", padx=4)
        ttk.Label(root, textvariable=self.status, padding=(12,2)).pack(anchor="w")
        self.canvas = tk.Canvas(root, bg="#f8fafc", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=6)
        self.metrics = ttk.Label(root, text="", padding=10, justify="left")
        self.metrics.pack(fill="x")
        self.root.after(100, self.start)

    def start(self):
        threading.Thread(target=self.load, daemon=True).start()

    def load(self):
        try:
            self.red, self.routes, self.audit, self.events, self.results = ejecutar()
            local_files = [rutas.INPUT/r["file"] for r in rutas.ROUTES]
            if all(path.is_file() for path in local_files):
                self.traces = [rutas.read_trace(path) for path in local_files]
                self.trace_label = "Trazos locales"
            else:
                self.traces = [rutas.route_coordinates(self.red, route) for route in self.routes]
                self.trace_label = "Alternativas calculadas desde el origen local"
            self.root.after(0, self.ready)
        except Exception as exc:
            self.root.after(0, lambda err=str(exc): self.failed(err))

    def failed(self, err):
        self.status.set("No se pudo preparar la simulación.")
        messagebox.showerror("Error del modelo", err)

    def ready(self):
        self.status.set(f"Red vial OSM: {self.audit['nodos_red']:,} vértices; "
                        f"{len(self.audit['transferencias'])} puntos de transferencia entre rutas.")
        self.draw_selected()

    def xy(self, point):
        lon, lat = point
        width = max(self.canvas.winfo_width(), 700)
        height = max(self.canvas.winfo_height(), 450)
        x = 40 + (lon - self.min_lon) / (self.max_lon - self.min_lon) * (width-80)
        y = height-40 - (lat - self.min_lat) / (self.max_lat - self.min_lat) * (height-80)
        return x,y

    def draw_line(self, points, color, width, dash=None):
        if len(points) < 2:
            return
        flat = [coordinate for point in points for coordinate in self.xy(point)]
        self.canvas.create_line(*flat, fill=color, width=width, smooth=False, dash=dash)

    def draw_selected(self):
        if not hasattr(self, "results"):
            return
        self.canvas.delete("all")
        all_points = [p for trace in self.traces for p in trace]
        self.min_lon = min(p[0] for p in all_points)-.003
        self.max_lon = max(p[0] for p in all_points)+.003
        self.min_lat = min(p[1] for p in all_points)-.003
        self.max_lat = max(p[1] for p in all_points)+.003
        for index, trace in enumerate(self.traces):
            self.draw_line(trace, COLORS[index], 2)
        result = next(x for x in self.results if x["politica"] == POLICIES[self.policy.get()])
        selected = []
        for u,v in zip(result["recorrido"], result["recorrido"][1:]):
            edge = self.red["edges"].get((u,v))
            if edge:
                geometry = [(lon,lat) for lat,lon in edge["geometry"]]
                selected.extend(geometry if not selected else geometry[1:])
        self.draw_line(selected, "#6d28d9", 4)
        for event in self.events:
            x,y = self.xy((event["coordenada"][1], event["coordenada"][0]))
            color = "#c62828" if event["tipo"] == "bloqueo" else "#b45309"
            self.canvas.create_oval(x-6,y-6,x+6,y+6,fill=color,outline="white",width=2)
        origin_lat, origin_lon = self.red["nodes"][self.red["origin"]]
        dest_lat, dest_lon = self.red["nodes"][self.red["destination"]]
        for label, point in (("ORIGEN", (origin_lon,origin_lat)), ("UABC OTAY", (dest_lon,dest_lat))):
            x,y = self.xy(point)
            self.canvas.create_text(x+8,y-12,text=label,anchor="w",fill="#111827",font=("Segoe UI",10,"bold"))
        self.canvas.create_text(15,15,anchor="nw",text=f"{self.trace_label}: verde / azul / naranja   |   Recorrido calculado: morado   |   Incidentes: rojo / ámbar",
                                fill="#172554",font=("Segoe UI",10,"bold"))
        lines = [f"{x['politica']}: {x['tiempo_s']/60:.1f} min; "
                 f"replanificaciones {x['replanificaciones']}; "
                 f"nodos expandidos {x['nodos_expandidos']}; "
                 f"llegó: {'sí' if x['llego'] else 'no'}" for x in self.results]
        self.metrics.config(text="\n".join(lines)+"\nTiempos e incidentes simulados; no son indicaciones de conducción.")
        self.selected_points = selected

    def animate(self):
        if not getattr(self, "selected_points", None):
            return
        self.draw_selected()
        points = self.selected_points[::max(1,len(self.selected_points)//180)]
        self.animate_step(points,0,None)

    def animate_step(self, points, i, marker):
        if marker:
            self.canvas.delete(marker)
        if i >= len(points):
            return
        x,y = self.xy(points[i])
        marker = self.canvas.create_oval(x-7,y-7,x+7,y+7,fill="#111827",outline="white",width=2)
        self.root.after(45, lambda: self.animate_step(points,i+1,marker))

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()

