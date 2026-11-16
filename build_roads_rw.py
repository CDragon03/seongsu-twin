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
clip = box(X0, Y0, X1, Y1); tri = []; nt = 0
for p in out_polys:
    p = p.buffer(0).intersection(clip).simplify(0.15)
    if p.is_empty: continue
    for g in getattr(p, "geoms", [p]):
        if g.geom_type != "Polygon" or g.area < 0.5: continue
        for t in shapely.constrained_delaunay_triangles(g).geoms:
            q = shapely.get_coordinates(t)[:3]; tri.extend(round(float(v), 2) for xy in q for v in xy); nt += 1
c["roads_rw"] = tri; c["roads_rw_src"] = "행정안전부 도로명주소 실폭도로(TL_SPRD_RW, 2026-11) · 브이월드 국가공간정보센터"
json.dump(c, open(os.path.join(G, "data", "city.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("삼각형", nt, "기존 길 삼각형", len(c.get("roads", [])) // 6)
