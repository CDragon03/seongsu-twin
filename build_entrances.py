# 건물 출입구: 도로명주소 출입구(행정안전부 → 브이월드 「(도로명주소)출입구_서울」 2026-11, TL_SPBD_ENTRC, 점, EPSG:5179) → data/entrances.json {건물번호: [[x, y, 주1/부0], ...]}
# 출입구 점이 들어 있거나 4m 안에 있는 건물에 붙임. 간판은 이 출입구가 있는 벽에 담(SIGN). 원본: ../data/road_rw/TL_SPBD_ENTRC_11_202611.shp
# 실행: python -I build_entrances.py
import json, math, os
import numpy as np, shapefile
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree
from rasterio.warp import transform
G = os.path.dirname(os.path.abspath(__file__)); LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
B = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8"))["buildings"]
polys = [Polygon([(b["p"][i], b["p"][i + 1]) for i in range(0, len(b["p"]), 2)]).buffer(0) for b in B]; tree = STRtree(polys)
xs = [v for b in B for v in b["p"][0::2]]; ys = [v for b in B for v in b["p"][1::2]]; X0, X1, Y0, Y1 = min(xs) - 10, max(xs) + 10, min(ys) - 10, max(ys) + 10
E, N = transform("EPSG:4326", "EPSG:5179", [LON0 + x / KX for x in (X0, X1)], [LAT0 + y / KY for y in (Y0, Y1)]); BB = (min(E) - 50, min(N) - 50, max(E) + 50, max(N) + 50)
r = shapefile.Reader(os.path.join(G, "..", "data", "road_rw", "TL_SPBD_ENTRC_11_202611.shp"), encoding="cp949", encodingErrors="replace")
pts, kind = [], []
for sr in r.iterShapeRecords(fields=["ENTRC_SE"]):
    x, y = sr.shape.points[0]
    if BB[0] <= x <= BB[2] and BB[1] <= y <= BB[3]: pts.append((x, y)); kind.append(1 if sr.record[0] == "RM" else 0)
lon, lat = transform("EPSG:5179", "EPSG:4326", [p[0] for p in pts], [p[1] for p in pts])
out, n = {}, 0
for lo, la, k in zip(lon, lat, kind):
    x, y = (lo - LON0) * KX, (la - LAT0) * KY; P = Point(x, y)
    cand = [int(i) for i in tree.query(P.buffer(4))]
    if not cand: continue
    bi = min(cand, key=lambda i: 0 if polys[i].contains(P) else polys[i].distance(P))
    if polys[bi].distance(P) > 4: continue
    out.setdefault(bi, []).append([round(x, 1), round(y, 1), k]); n += 1
for v in out.values(): v.sort(key=lambda e: -e[2])   # 주출입구 먼저
json.dump({"src": "행정안전부 도로명주소 출입구(TL_SPBD_ENTRC, 2026-11) · 브이월드", "b": out}, open(os.path.join(G, "data", "entrances.json"), "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
print("범위 안 출입구", len(pts), "붙임", n, "건물", len(out), "주출입구 비율", round(sum(kind) / max(1, len(kind)), 2))
