"""Carga de trazos locales GPX/KML o geometría de rutas calculadas."""
from pathlib import Path
import xml.etree.ElementTree as ET

INPUT = Path(__file__).resolve().parent / "rutas_habituales"
ROUTES = [
    {"id":"Ruta habitual 1","file":"ruta_habitual_1.gpx"},
    {"id":"Ruta habitual 2","file":"ruta_habitual_2.kml"},
    {"id":"Ruta habitual 3","file":"ruta_habitual_3.kml"},
]

def read_trace(path):
    path = Path(path)
    root = ET.parse(path).getroot()
    local = lambda element: element.tag.rsplit("}",1)[-1]
    if path.suffix.lower() == ".gpx":
        points = [(float(element.attrib["lon"]),float(element.attrib["lat"]))
                  for element in root.iter() if local(element) == "trkpt"]
        if not points:
            points = [(float(element.attrib["lon"]),float(element.attrib["lat"]))
                      for element in root.iter() if local(element) == "rtept"]
    else:
        points = []
        for line in root.iter():
            if local(line) != "LineString":
                continue
            for child in line.iter():
                if local(child) == "coordinates" and child.text:
                    points.extend(tuple(map(float,item.split(",")[:2])) for item in child.text.split())
    if len(points) < 2:
        raise ValueError(f"No hay línea GPX/KML utilizable en {path.name}.")
    return points

def route_coordinates(red, path):
    """Convierte una secuencia de nodos del grafo a coordenadas (lon, lat)."""
    points = []
    for u, v in zip(path, path[1:]):
        edge = red["edges"].get((u, v))
        if edge:
            segment = [(lon, lat) for lat, lon in edge["geometry"]]
            points.extend(segment if not points else segment[1:])
    return points

