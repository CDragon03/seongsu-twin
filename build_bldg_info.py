# 건물 정보 팝업 자료: 건물통합정보(국토교통부, AL_D010 시도 파일)의 대장 항목을 화면 건물(city.json 순서)에 짝지어 data/bldg_info.json 으로
# 실행: python -I build_bldg_info.py <AL_D010 shp(확장자 없이)>
# 칸: A2 PNU, A4 주소(동까지), A5 지번, A9 용도, A11 구조, A12 건축면적, A13 사용승인일, A14 연면적, A15 대지면적, A16 높이, A17 건폐율, A18 용적률,
#     A24 건물명, A25 동명, A26 지상층수, A27 지하층수, A28 자료 기준일
import json, math, os, sys, shapefile
from pyproj import Transformer
from shapely.geometry import shape, Polygon, Point
from shapely.strtree import STRtree

G = os.path.dirname(os.path.abspath(__file__))
SHP = sys.argv[1]
LAT0, LON0 = 37.543, 127.0535
KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
inv = Transformer.from_crs(5186, 4326, always_xy=True); fwd = Transformer.from_crs(4326, 5186, always_xy=True)
city = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8")); B = city["buildings"]
xs = [b["p"][i] for b in B for i in range(0, len(b["p"]), 2)]; ys = [b["p"][i] for b in B for i in range(1, len(b["p"]), 2)]
to_ll = lambda x, y: (LON0 + x / KX, LAT0 + y / KY)
(ax, ay), (bx, by) = fwd.transform(*to_ll(min(xs) - 50, min(ys) - 50)), fwd.transform(*to_ll(max(xs) + 50, max(ys) + 50))

polys, recs = [], []
r = shapefile.Reader(SHP, encoding="euc_kr")
for sr in r.iterShapeRecords():
    s = sr.shape
    if s.shapeType == 0 or not s.points: continue
    b = s.bbox
    if b[2] < ax or b[0] > bx or b[3] < ay or b[1] > by: continue
    lonlat = [inv.transform(x, y) for x, y in s.points]
    pts = [((lo - LON0) * KX, (la - LAT0) * KY) for lo, la in lonlat]
    g = Polygon(pts).buffer(0)
    if g.is_empty: continue
    polys.append(g); recs.append(sr.record)
print("통합정보 후보", len(polys))
tree = STRtree(polys)

def num(v, nd=1):
    try: v = float(v)
    except Exception: return None
    return round(v, nd) if v > 0 else None

out, hit = [], 0
for b in B:
    p = b["p"]; P = Polygon([(p[i], p[i + 1]) for i in range(0, len(p), 2)]).buffer(0)
    c = P.representative_point() if not P.is_empty else Point(p[0], p[1])
    best, ba = None, 0
    for k in tree.query(c):
        k = int(k)
        if polys[k].contains(c):
            a = polys[k].intersection(P).area if not P.is_empty else 1
            if a > ba: best, ba = k, a
    if best is None: out.append(None); continue
    R = recs[best]; hit += 1
    d = {"pnu": R["A2"], "addr": (R["A4"] or "").strip() + (" " + R["A5"].strip() if R["A5"] else ""), "use": R["A9"] or None, "st": R["A11"] or None,
         "ba": num(R["A12"]), "ap": (R["A13"] or "").strip() or None, "ga": num(R["A14"]), "la": num(R["A15"]), "h": num(R["A16"]),
         "bc": num(R["A17"]), "fr": num(R["A18"]), "nm": (R["A24"] or "").strip() or None, "dong": (R["A25"] or "").strip() or None,
         "fu": int(R["A26"] or 0) or None, "fb": int(R["A27"] or 0) or None, "ref": str(R["A28"] or "").strip() or None}
    out.append({k: v for k, v in d.items() if v is not None})
json.dump({"src": "국토교통부 GIS건물통합정보(AL_D010, 서울) " + os.path.basename(SHP)[-8:], "b": out},
          open(os.path.join(G, "data", "bldg_info.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("짝지은 건물", hit, "/", len(B))
