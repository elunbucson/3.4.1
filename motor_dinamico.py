"""Motor reproducible de navegación sobre calles de OpenStreetMap.

Los tiempos, fases semafóricas e incidentes son simulados, no tráfico en vivo.
"""
from __future__ import annotations

import heapq
import json
import math
import random
from collections import defaultdict, deque
from pathlib import Path

BASE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
RED = BASE / "datos" / "red_vial.json"
DESTINO = (32.53339, -116.96443)  # UABC Campus Otay
try:
    from config_local import ORIGEN, ZONAS, FIELD_SIGNALS, FIELD_STOPS
except ImportError:
    ORIGEN, ZONAS, FIELD_SIGNALS, FIELD_STOPS = None, [], [], []

def distancia(a, b):
    la1, lo1 = map(math.radians, a)
    la2, lo2 = map(math.radians, b)
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 12742000*math.asin(min(1.0, math.sqrt(h)))

def cargar_red(path=RED):
    if ORIGEN is None:
        raise RuntimeError(
            "Falta config_local.py. Copia config_local.example.py como "
            "config_local.py y configura allí tu punto de origen local."
        )
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes = data["nodes"]
    graph = defaultdict(list)
    edges = {}
    for index, (u,v,meters,seconds,road,geometry) in enumerate(data["edges"]):
        mid = geometry[len(geometry)//2]
        factor = 1.0
        for zone in ZONAS:
            if distancia(mid, (zone["lat"], zone["lon"])) <= zone["radio_m"]:
                factor = max(factor, zone["factor"])
        edge = {"id": index, "u": u, "v": v, "m": meters, "s": seconds*factor,
                "road": road, "geometry": geometry, "zone_factor": factor}
        if (u,v) not in edges or edge["s"] < edges[(u,v)]["s"]:
            edges[(u,v)] = edge
    for edge in edges.values():
        graph[edge["u"]].append(edge)
    # Retain the largest weak component to remove isolated parking aisles and fragments.
    undirected = defaultdict(set)
    for u,v in edges:
        undirected[u].add(v)
        undirected[v].add(u)
    def nearest(point, choices):
        return min(choices, key=lambda n: distancia(point, nodes[n]))
    origin = nearest(ORIGEN, nodes)
    destination = nearest(DESTINO, nodes)
    fields = []
    for tag, controls in (("traffic_signals", FIELD_SIGNALS), ("stop", FIELD_STOPS)):
        for control in controls:
            n = nearest((control["lat"], control["lon"]), nodes)
            same_type = [distancia((control["lat"],control["lon"]),nodes[osm_node])
                         for osm_node,osm_tag in data["controls"].items() if osm_tag == tag]
            nearest_tag = min(same_type, default=math.inf)
            fields.append({**control, "tipo": tag, "nodo": n,
                           "distancia_m": round(distancia((control["lat"],control["lon"]),nodes[n]),1),
                           "osm_en_nodo": data["controls"].get(n),
                           "osm_mismo_tipo_m": round(nearest_tag,1) if math.isfinite(nearest_tag) else None,
                           "sin_etiqueta_igual_80m": nearest_tag > 80})
    return {"data": data, "nodes": nodes, "graph": graph, "edges": edges,
            "undirected": undirected, "origin": origin, "destination": destination,
            "fields": fields}

def controles(red):
    result = dict(red["data"]["controls"])
    for f in red["fields"]:
        result.setdefault(f["nodo"], f["tipo"])
    return result

def tiempo_arista(edge, arrival, controls, incidents):
    incident = incidents.get(edge["id"])
    if incident and incident["tipo"] == "bloqueo" and arrival < incident["hasta"]:
        return math.inf
    cost = edge["s"]
    if incident and incident["tipo"] == "reten" and arrival < incident["hasta"]:
        cost += incident["demora_s"]
    tag = controls.get(edge["v"])
    if tag == "stop":
        cost += 4.0
    elif tag == "traffic_signals":
        phase = (arrival + int(edge["v"]) % 90) % 90
        if phase < 35:
            cost += 35-phase
    return cost

def astar(red, source, target, start_time=0.0, incidents=None, controls=None):
    """A* with arrival-time edge cost and admissible straight-line heuristic."""
    incidents = incidents or {}
    controls = controls or controles(red)
    if source == target:
        return [source], 0.0, 0
    graph, nodes = red["graph"], red["nodes"]
    heuristic = lambda n: distancia(nodes[n], nodes[target]) / (110/3.6)
    best = {source: 0.0}
    previous = {}
    heap = [(heuristic(source), 0.0, source)]
    expanded = 0
    while heap:
        _, elapsed, u = heapq.heappop(heap)
        if elapsed > best.get(u, math.inf) + 1e-8:
            continue
        expanded += 1
        if u == target:
            path = [u]
            while path[-1] != source:
                path.append(previous[path[-1]])
            return path[::-1], elapsed, expanded
        for edge in graph.get(u, ()):
            v = edge["v"]
            candidate = elapsed + tiempo_arista(edge, start_time+elapsed, controls, incidents)
            if candidate + 1e-8 < best.get(v, math.inf):
                best[v] = candidate
                previous[v] = u
                heapq.heappush(heap, (candidate+heuristic(v), candidate, v))
    return [], math.inf, expanded

def rutas_alternas(red, n=3):
    """Three longitudinal routes, penalizing edges used in previous routes."""
    routes = []
    penalties = defaultdict(int)
    controls = controles(red)
    for _ in range(n):
        # Build a lightweight view by copying the adjacency edge records.
        graph = defaultdict(list)
        for u, outgoing in red["graph"].items():
            for e in outgoing:
                multiplier = 1 + 2.0*penalties[e["id"]]
                graph[u].append({**e, "s": e["s"]*multiplier})
        view = {**red, "graph": graph}
        path, _, _ = astar(view, red["origin"], red["destination"], controls=controls)
        if not path:
            break
        routes.append(path)
        for u,v in zip(path,path[1:]):
            penalties[red["edges"][(u,v)]["id"]] += 1
    return routes

def auditoria_topologia(red, routes):
    edge_sets = [{(a,b) for a,b in zip(path,path[1:])} for path in routes]
    transfers = []
    # Nodes shared by route interiors, excluding the common endpoints and vicinity.
    for n in set().union(*(set(path[1:-1]) for path in routes)):
        shared = [i+1 for i,path in enumerate(routes) if n in path[1:-1]]
        if len(shared) > 1 and distancia(red["nodes"][n], red["nodes"][red["origin"]]) > 800:
            if distancia(red["nodes"][n], red["nodes"][red["destination"]]) > 800:
                transfers.append({"nodo": n, "rutas": shared, "coordenada": red["nodes"][n]})
    # Deduplicate nearby shared nodes so distinct transfers are meaningful.
    selected = []
    for item in sorted(transfers, key=lambda t: distancia(t["coordenada"], red["nodes"][red["origin"]])):
        if all(distancia(item["coordenada"], x["coordenada"]) > 350 for x in selected):
            selected.append(item)
    return {"rutas_nodos": [len(x) for x in routes],
            "osm_senales": sum(v == "traffic_signals" for v in red["data"]["controls"].values()),
            "osm_altos": sum(v == "stop" for v in red["data"]["controls"].values()),
            "campo": red["fields"], "transferencias": selected,
            "nodos_red": len(red["nodes"]), "aristas_red": len(red["edges"])}

def corte_minimo_dirigido(red, max_paths=12):
    """Minimum directed origin-destination edge cut via unit-capacity augmenting paths."""
    origin, destination = red["origin"], red["destination"]
    residual = defaultdict(dict)
    for u,v in red["edges"]:
        residual[u][v] = residual[u].get(v, 0) + 1
        residual[v].setdefault(u, 0)
    flow = 0
    while flow < max_paths:
        parent = {origin: None}
        queue = deque([origin])
        while queue and destination not in parent:
            u = queue.popleft()
            for v, capacity in residual[u].items():
                if capacity > 0 and v not in parent:
                    parent[v] = u
                    queue.append(v)
        if destination not in parent:
            break
        v = destination
        while v != origin:
            u = parent[v]
            residual[u][v] -= 1
            residual[v][u] = residual[v].get(u, 0) + 1
            v = u
        flow += 1
    if flow == max_paths:
        return {"limite_alcanzado": True, "aristas": []}
    reachable = {origin}
    queue = deque([origin])
    while queue:
        u = queue.popleft()
        for v, cap in residual[u].items():
            if cap > 0 and v not in reachable:
                reachable.add(v)
                queue.append(v)
    cut = []
    for (u,v), edge in red["edges"].items():
        if u in reachable and v not in reachable:
            cut.append({"desde": u, "hasta": v, "coordenada": edge["geometry"][len(edge["geometry"])//2],
                        "via": edge["road"]})
    return {"limite_alcanzado": False, "aristas": cut}

def escenario(red, baseline, seed=341):
    """Four seeded incidents on the baseline path, revealed every 3 steps."""
    rng = random.Random(seed)
    pairs = list(zip(baseline, baseline[1:]))
    choices = [int(len(pairs)*rng.uniform(low, high))
               for low,high in ((.20,.28),(.38,.46),(.57,.65),(.74,.82))]
    events = []
    for i, position in enumerate(choices):
        edge = red["edges"][pairs[position]]
        if i % 2 == 0:
            # Choose a blockage with a real OSM diversion available.
            for offset in (0,1,-1,2,-2,3,-3,4,-4,5,-5):
                candidate = red["edges"][pairs[max(1,min(len(pairs)-2,position+offset))]]
                blocked = {candidate["id"]: {"tipo":"bloqueo","hasta":1e9,"demora_s":0}}
                alternate, _, _ = astar(red, candidate["u"], red["destination"],
                                        incidents=blocked)
                if alternate:
                    edge = candidate
                    break
        events.append({"paso": (i+1)*3, "arista": edge["id"],
                       "tipo": "bloqueo" if i % 2 == 0 else "reten",
                       "duracion_s": 540 if i % 2 == 0 else 660,
                       "demora_s": rng.randint(70,130), "coordenada": edge["geometry"][len(edge["geometry"])//2]})
    return events

def simular(red, policy, events, max_steps=200, stride_m=350):
    """Policies: static, each_step, event. Shared incidents and time model."""
    controls = controles(red)
    current, target = red["origin"], red["destination"]
    now = 0.0
    active = {}
    path, _, expanded = astar(red, current, target, controls=controls)
    if not path:
        raise RuntimeError("No hay camino inicial desde el origen a UABC en la red vial.")
    replans = 0
    visited = [current]
    changes = []
    waits = 0
    for step in range(1, max_steps+1):
        changed = False
        for event in events:
            if event["paso"] == step:
                active[event["arista"]] = {"tipo": event["tipo"],
                                            "hasta": now+event["duracion_s"],
                                            "demora_s": event["demora_s"]}
                changes.append({"paso": step, "tiempo_s": round(now,1), **event})
                changed = True
        active = {k:v for k,v in active.items() if now < v["hasta"]}
        planned_edges = {red["edges"][(u,v)]["id"] for u,v in zip(path,path[1:])}
        affected = changed and bool(planned_edges & active.keys())
        if policy == "each_step" or (policy == "event" and affected):
            path, _, count = astar(red, current, target, now, active, controls)
            expanded += count
            replans += 1
        if len(path) < 2:
            now += 45
            waits += 1
            if current == target:
                break
            # If temporarily disconnected, try again next iteration.
            if policy != "static":
                path, _, count = astar(red, current, target, now, active, controls)
                expanded += count
                replans += 1
            continue
        travelled = 0.0
        moved = False
        while len(path) > 1 and travelled < stride_m:
            u,v = path[:2]
            edge = red["edges"][(u,v)]
            cost = tiempo_arista(edge, now, controls, active)
            if math.isinf(cost):
                now += min(60, max(15, active[edge["id"]]["hasta"]-now))
                waits += 1
                break
            now += cost
            travelled += edge["m"]
            current = v
            visited.append(v)
            path = path[1:]
            moved = True
            if current == target:
                break
        if current == target:
            break
        if policy == "event" and not moved:
            path, _, count = astar(red, current, target, now, active, controls)
            expanded += count
            replans += 1
    return {"politica": policy, "llego": current == target, "tiempo_s": round(now,1),
            "replanificaciones": replans, "nodos_expandidos": expanded,
            "esperas": waits, "recorrido": visited, "incidentes": changes}

def ejecutar(seed=341):
    red = cargar_red()
    routes = rutas_alternas(red)
    audit = auditoria_topologia(red, routes)
    audit["corte_minimo"] = corte_minimo_dirigido(red)
    if len(routes) < 3 or len(audit["transferencias"]) < 2:
        raise RuntimeError("La red no produjo tres rutas y al menos dos vertices de transferencia.")
    events = escenario(red, routes[0], seed)
    results = [simular(red, policy, events) for policy in ("static","each_step","event")]
    return red, routes, audit, events, results

