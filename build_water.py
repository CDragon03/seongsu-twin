# 한강·중랑천·호수: OSM natural=water(waterway=riverbank) → data/water.json (지역좌표, 반경 3km 안으로 자름)
# 원본 받기: ../data/water/water_osm.json (Overpass, out geom). 실행: python -I build_water.py
import json, math, os
from shapely.geometry import Polygon, LineString, box, MultiPolygon
from shapely.ops import linemerge, polygonize, unary_union
G = os.path.dirname(os.path.abspath(__file__))
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
xy = lambda p: ((p["lon"] - LON0) * KX, (p["lat"] - LAT0) * KY)
els = json.load(open(os.path.join(G, "..", "data", "water", "water_osm.json"), encoding="utf-8"))["elements"]
polys = []
for e in els:
    t = e.get("tags", {})
    if t.get("water") in ("pool", "wastewater") or t.get("leisure") == "swimming_pool": continue
    if e["type"] == "way" and len(e.get("geometry", [])) >= 4:
        g = Polygon([xy(p) for p in e["geometry"]]).buffer(0)
        if not g.is_empty: polys.append(g)
    elif e["type"] == "relation":
        outer = [LineString([xy(p) for p in m["geometry"]]) for m in e.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
        inner = [LineString([xy(p) for p in m["geometry"]]) for m in e.get("members", []) if m.get("role") == "inner" and m.get("geometry")]
        O = unary_union(list(polygonize(linemerge(outer)))) if outer else None
        if O is None or O.is_empty: continue
        I = unary_union(list(polygonize(linemerge(inner)))) if inner else None
        polys.append(O.difference(I) if I is not None and not I.is_empty else O)
W = unary_union(polys).intersection(box(-3000, -3000, 3000, 3000)).simplify(1.0)
out = []
for g in (W.geoms if isinstance(W, MultiPolygon) else [W]):
    if g.area < 50: continue
    out.append([[round(v, 1) for q in g.exterior.coords[:-1] for v in q]] + [[round(v, 1) for q in r.coords[:-1] for v in q] for r in g.interiors])
json.dump({"src": "OpenStreetMap natural=water (Overpass 2026-11-16)", "w": out}, open(os.path.join(G, "data", "water.json"), "w"), separators=(",", ":"))
print("물 도형", len(out), "넓이", round(W.area / 1e6, 2), "km2", round(os.path.getsize(os.path.join(G, "data", "water.json")) / 1024), "KB")
