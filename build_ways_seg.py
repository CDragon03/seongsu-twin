# 사람·차가 다니는 길 그래프: 도로명주소 도로구간(행정안전부 → 브이월드 「(도로명주소)도로구간_서울」 2026-11, TL_SPRD_MANAGE, EPSG:5179) → city.json ways
# 교차로에서 끊어(노딩) 서로 이어지게 하고, 폭 = 도로폭(ROAD_BT, 없으면 도로 위계 기본값), 이름 = 도로명(RN). 예전 OSM 길은 ways_osm 으로 남김
# 범위 = 예전 길 그래프 범위 + 200m (사람·차·소품 계산량을 비슷하게 유지). 실행: python -I build_ways_seg.py
import json, math, os
import numpy as np, shapefile, shapely
from shapely.geometry import shape, box, LineString
from shapely.strtree import STRtree
from rasterio.warp import transform
G = os.path.dirname(os.path.abspath(__file__)); LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
P = os.path.join(G, "data", "city.json"); c = json.load(open(P, encoding="utf-8"))
old = c.get("ways_osm") or c["ways"]
xs = [v for w in old for v in w["p"][0::2]]; ys = [v for w in old for v in w["p"][1::2]]
X0, X1, Y0, Y1 = min(xs) - 200, max(xs) + 200, min(ys) - 200, max(ys) + 200
E, N = transform("EPSG:4326", "EPSG:5179", [LON0 + x / KX for x in (X0, X1, X1, X0)], [LAT0 + y / KY for y in (Y0, Y0, Y1, Y1)]); BB = (min(E), min(N), max(E), max(N))
r = shapefile.Reader(os.path.join(G, "..", "data", "road_rw", "TL_SPRD_MANAGE_11_202611.shp"), encoding="cp949", encodingErrors="replace")
src, att = [], []
for sr in r.iterShapeRecords():
    b = sr.shape.bbox
    if b[2] < BB[0] or b[0] > BB[2] or b[3] < BB[1] or b[1] > BB[3]: continue
    g = shape(sr.shape.__geo_interface__); rec = sr.record.as_dict()
    for part in getattr(g, "geoms", [g]): src.append(part); att.append(rec)
pts = np.concatenate([shapely.get_coordinates(g) for g in src]); lon, lat = transform("EPSG:5179", "EPSG:4326", pts[:, 0].tolist(), pts[:, 1].tolist())
loc = np.column_stack([(np.array(lon) - LON0) * KX, (np.array(lat) - LAT0) * KY]); k = 0; lines = []
for g in src: n = len(shapely.get_coordinates(g)); lines.append(shapely.set_coordinates(g, loc[k:k + n])); k += n
clip = box(X0, Y0, X1, Y1); keep = [(l.intersection(clip), a) for l, a in zip(lines, att)]; keep = [(l, a) for l, a in keep if not l.is_empty]
print("범위 안 도로구간", len(keep))
noded = shapely.unary_union([l for l, _ in keep])   # 교차점에서 끊음
tree = STRtree([l for l, _ in keep])
DEF = {"1": 20, "2": 25, "3": 12, "4": 4}   # 폭 없을 때 위계별 기본 폭(m, 가정)
ways = []
for seg in getattr(noded, "geoms", [noded]):
    if seg.geom_type != "LineString" or seg.length < 1: continue
    mid = seg.interpolate(0.5, normalized=True); i = tree.nearest(mid); a = keep[i][1]
    cls = str(a.get("ROA_CLS_SE") or "4"); bt = float(a.get("ROAD_BT") or 0) or DEF.get(cls, 4); hw = round(bt / 2, 1)
    kk = {"1": "motorway", "2": "primary"}.get(cls) or ("secondary" if cls == "3" and hw >= 5 else "tertiary" if cls == "3" else "residential" if hw >= 2.5 else "service")
    co = shapely.get_coordinates(seg.simplify(0.3)); ways.append({"p": [round(float(v), 2) for xy in co for v in xy], "w": hw, "k": kk, "n": a.get("RN") or ""})
if "ways_osm" not in c: c["ways_osm"] = c["ways"]
c["ways"] = ways; c["ways_src"] = "행정안전부 도로명주소 도로구간(TL_SPRD_MANAGE, 2026-11) · 브이월드 · 교차로에서 끊어 이음"
json.dump(c, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
L = sum(math.hypot(w["p"][i] - w["p"][i - 2], w["p"][i + 1] - w["p"][i - 1]) for w in ways for i in range(2, len(w["p"]), 2))
import collections; print("길 조각", len(ways), "총 길이 km", round(L / 1000, 1), "예전", len(old), collections.Counter(w["k"] for w in ways))
