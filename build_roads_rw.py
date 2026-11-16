# 길 면: 도로명주소 실폭도로(행정안전부 → 브이월드 「(도로명주소)실폭도로_서울」 2026-11, TL_SPRD_RW, EPSG:5179) → city.json roads_rw(삼각형 x,y 목록)
# 지도 범위 안 도로 면만 잘라 지역좌표로 바꾸고 구멍까지 살려 삼각형으로 나눔. 원본: ../data/road_rw/TL_SPRD_RW_11_202611.shp
# 실행: python -I build_roads_rw.py
import json, math, os
import shapefile, shapely
from shapely.geometry import shape, box
from rasterio.warp import transform
G = os.path.dirname(os.path.abspath(__file__)); LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
c = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8"))
xs = [v for b in c["buildings"] for v in b["p"][0::2]] + [p[0] for p in c["ground2"]["corners"].values()]; ys = [v for b in c["buildings"] for v in b["p"][1::2]] + [p[1] for p in c["ground2"]["corners"].values()]
X0, X1, Y0, Y1 = min(xs) - 50, max(xs) + 50, min(ys) - 50, max(ys) + 50
cx = [X0, X1, X1, X0]; cy = [Y0, Y0, Y1, Y1]
E, N = transform("EPSG:4326", "EPSG:5179", [LON0 + x / KX for x in cx], [LAT0 + y / KY for y in cy]); BB = (min(E), min(N), max(E), max(N))
r = shapefile.Reader(os.path.join(G, "..", "data", "road_rw", "TL_SPRD_RW_11_202611.shp"), encoding="euc_kr")
polys = []
for sr in r.iterShapeRecords():
    b = sr.shape.bbox
    if b[2] < BB[0] or b[0] > BB[2] or b[3] < BB[1] or b[1] > BB[3]: continue
    polys.append(shape(sr.shape.__geo_interface__))
print("범위 안 실폭도로 면", len(polys))
# 좌표 변환: 5179 → 경위도 → 지역좌표(한 번에)
allpts = []; [allpts.extend(shapely.get_coordinates(p).tolist()) for p in polys]
lon, lat = transform("EPSG:5179", "EPSG:4326", [p[0] for p in allpts], [p[1] for p in allpts])
import numpy as np
loc = np.column_stack([(np.array(lon) - LON0) * KX, (np.array(lat) - LAT0) * KY]); k = 0; out_polys = []
for p in polys:
    n = len(shapely.get_coordinates(p)); out_polys.append(shapely.set_coordinates(p, loc[k:k + n])); k += n
clip = box(X0, Y0, X1, Y1)
RWU = shapely.union_all([p.buffer(0).intersection(clip) for p in out_polys])
# 보도·차도 나누기(가정): 실폭도로는 보도 포함 전체 폭 → 길 그래프(도로구간 중심선, w = 반폭)를 차도 폭으로 부풀려 차도, 나머지는 보도.
# 보도 폭(한쪽) = 전체 폭 25m↑ 4m · 15m↑ 3m · 10m↑ 2m · 그 밖(골목) 0m(보차 혼용). 길 그래프 범위 밖은 전부 차도로 둠
from shapely.geometry import LineString
W = c.get("ways") or []
def sw(hw): W2 = hw * 2; return 4 if W2 >= 25 else 3 if W2 >= 15 else 2 if W2 >= 10 else 0
WL = [LineString(list(zip(w["p"][0::2], w["p"][1::2]))) for w in W]
# 가로수(서울시 가로수 위치정보, 실제 위치)가 있는 길은 연석 = 그 길 가로수까지 거리의 중앙값 - 0.8m(나무는 보도 위). 중앙분리대 나무(반폭 40% 안쪽)는 뺌
from shapely.strtree import STRtree as _T
from shapely.geometry import Point as _P
import statistics as _st
_tr = _T(WL); _td = {}
for tx_, ty_, _k in c.get("trees", []):
    P_ = _P(tx_, ty_); i_ = int(_tr.nearest(P_)); d_ = WL[i_].distance(P_); hw_ = W[i_]["w"]
    if hw_ and 0.4 * hw_ <= d_ <= 1.3 * hw_: _td.setdefault(i_, []).append(d_)
def cwh(i, w):
    if i in _td: L_ = sorted(_td[i]); return max(1.5, min(w["w"], L_[len(L_) // 10] - 0.8))   # 가까운 쪽(하위 10%) 나무 기준
    return w["w"] - sw(w["w"])
cw = [WL[i].buffer(max(1.0, cwh(i, w)), cap_style=2) for i, w in enumerate(W) if len(w["p"]) >= 4]
print("가로수로 연석을 맞춘 길", len(_td))
if W:
    wx = [v for w in W for v in w["p"][0::2]]; wy = [v for w in W for v in w["p"][1::2]]; core = box(min(wx), min(wy), max(wx), max(wy)).buffer(-20)
    CW = shapely.union_all(cw).intersection(RWU)
    PIT = shapely.union_all([_P(x_, y_).buffer(1.2, 8) for x_, y_, _k in c.get("trees", [])]).intersection(RWU)   # 그래도 찻길 위에 남는 나무(중앙분리대 등) = 둘레 1.2m 화단
    road = shapely.union_all([CW, RWU.difference(core)]).difference(PIT); walk = shapely.union_all([RWU.intersection(core).difference(CW), PIT])
else: road, walk = RWU, None
def tris(geom):
    out = []; geom = geom.simplify(0.15)
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon" or g.area < 0.5: continue
        for t in shapely.constrained_delaunay_triangles(g).geoms:
            q = shapely.get_coordinates(t)[:3]; out.extend(round(float(v), 2) for xy in q for v in xy)
    return out
tri = tris(road); nt = len(tri) // 6
c["roads_rw"] = tri; c["roads_rw_src"] = "행정안전부 도로명주소 실폭도로(TL_SPRD_RW, 2026-11) · 브이월드 국가공간정보센터"
if walk is not None: c["walk_rw"] = tris(walk); print("보도 삼각형", len(c["walk_rw"]) // 6)
json.dump(c, open(os.path.join(G, "data", "city.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("삼각형", nt, "기존 길 삼각형", len(c.get("roads", [])) // 6)
