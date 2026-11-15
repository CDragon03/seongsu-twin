# 바닥 사진(정사영상) 범위 안인데 건물이 없던 곳(북쪽 띠 등)에 건물통합정보 윤곽으로 건물을 덧붙임(city.json 끝에 추가 → 기존 건물 번호 그대로)
# 실행: python -I append_strip.py <AL_D010 shp(확장자 없이)>   (build_data.py 를 다시 돌린 뒤에는 이것도 다시)
import json, math, os, random, sys, shapefile
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.strtree import STRtree

G = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(G, "data", "city.json")
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
inv = Transformer.from_crs(5186, 4326, always_xy=True); fwd = Transformer.from_crs(4326, 5186, always_xy=True)
city = json.load(open(P, encoding="utf-8")); B = city["buildings"]
B = [b for b in B if not b.get("strip")]   # 다시 돌릴 때 앞서 붙인 것 빼고
c = city["ground"]["corners"]; X0, X1 = max(c["sw"][0], c["nw"][0]), min(c["se"][0], c["ne"][0]); Y0, Y1 = max(c["sw"][1], c["se"][1]), min(c["nw"][1], c["ne"][1])
to5186 = lambda x, y: fwd.transform(LON0 + x / KX, LAT0 + y / KY)
(ax, ay), (bx, by) = to5186(X0, Y0), to5186(X1, Y1)
old = [Polygon([(b["p"][i], b["p"][i + 1]) for i in range(0, len(b["p"]), 2)]).buffer(0) for b in B]; tree = STRtree(old)
PAL = {"brick": ["#8e4a36", "#9a5640", "#7c3f2e", "#a0624a"], "concrete": ["#b8b5ae", "#c9c5bc", "#a9a69f"], "plaster": ["#d9d2c3", "#e3dccd", "#cfc6b4"],
       "apt": ["#e8e6e1", "#dcdad4"], "glass": ["#4d6273", "#3c4f5e", "#5a7080"], "metal": ["#9aa0a3", "#8a9094"]}
def kind(s, u, h, fl):   # build_data.py kind() 와 같은 규칙
    if "벽돌" in s or "조적" in s: return "brick"
    if "공동주택" in u and fl >= 8: return "apt"
    if "철골" in s and h > 25: return "glass"
    if "철골" in s or "공장" in u or "창고" in u: return "metal"
    if "주택" in u: return "plaster"
    return "concrete"
random.seed(1116); add = []
r = shapefile.Reader(sys.argv[1], encoding="euc_kr")
for sr in r.iterShapeRecords():
    s = sr.shape
    if s.shapeType == 0 or not s.points: continue
    bb = s.bbox
    if bb[2] < ax or bb[0] > bx or bb[3] < ay or bb[1] > by: continue
    pts = [((lo - LON0) * KX, (la - LAT0) * KY) for lo, la in (inv.transform(x, y) for x, y in s.points[:(s.parts[1] if len(s.parts) > 1 else len(s.points))])]
    if pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    g = Polygon(pts).buffer(0)
    if g.is_empty or g.area < 12: continue
    cp = g.representative_point()
    if not (X0 <= cp.x <= X1 and Y0 <= cp.y <= Y1): continue
    if any(old[int(k)].intersection(g).area > 0.3 * g.area for k in tree.query(g)): continue   # 이미 있는 건물과 겹치면 건너뜀
    R = sr.record; h = float(R["A16"] or 0); fl = int(R["A26"] or 0)
    if h <= 0: h = (fl or 3) * 3.3
    if not fl: fl = max(1, round(h / 3.3))
    a2 = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if a2 < 0: pts = pts[::-1]
    k = kind(R["A11"] or "", R["A9"] or "", h, fl); yr = str(R["A13"] or "")[:4]
    b = {"p": [round(v, 2) for q in pts for v in q], "h": round(h, 1), "f": fl, "c": random.choice(PAL[k]), "k": k, "y": int(yr) if yr.isdigit() else 0, "strip": 1}
    if (R["A24"] or "").strip(): b["n"] = R["A24"].strip()
    if "근린생활" in (R["A9"] or "") or "판매" in (R["A9"] or ""): b["u"] = 1
    add.append(b)
city["buildings"] = B + add
json.dump(city, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("덧붙인 건물", len(add), "전체", len(city["buildings"]))
