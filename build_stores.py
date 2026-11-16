# 입주 업체: 소상공인시장진흥공단 상가(상권)정보(서울 파일, 분기) → 화면 건물마다 상호·업종·동·층·호 → data/stores.json
# 붙이는 법: 지번코드(19자리) = 건물 PNU 로 필지를 찾고, 한 필지에 건물이 여럿이면 업소 좌표가 들어간 건물(없으면 가장 가까운 건물)
# 실행: python -I build_stores.py <상가정보 zip>
import csv, io, json, math, os, sys, zipfile
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree
G = os.path.dirname(os.path.abspath(__file__))
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
city = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8")); B = city["buildings"]
info = json.load(open(os.path.join(G, "data", "bldg_info.json"), encoding="utf-8"))["b"]
polys = [Polygon([(b["p"][i], b["p"][i + 1]) for i in range(0, len(b["p"]), 2)]).buffer(0) for b in B]; tree = STRtree(polys)
by_pnu = {}
for i, r in enumerate(info):
    if r and r.get("pnu"): by_pnu.setdefault(r["pnu"], []).append(i)
xs = [v for b in B for v in b["p"][0::2]]; ys = [v for b in B for v in b["p"][1::2]]; X0, X1, Y0, Y1 = min(xs) - 30, max(xs) + 30, min(ys) - 30, max(ys) + 30
z = zipfile.ZipFile(sys.argv[1]); name = [n for n in z.namelist() if "서울" in n][0]
out = {}; st = {"범위 안": 0, "필지": 0, "좌표": 0, "못 붙임": 0}; ref = name.rsplit("_", 1)[-1][:6]
for r in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig")):
    try: lon, lat = float(r["경도"]), float(r["위도"])
    except ValueError: continue
    x, y = (lon - LON0) * KX, (lat - LAT0) * KY
    if not (X0 <= x <= X1 and Y0 <= y <= Y1): continue
    st["범위 안"] += 1; P = Point(x, y); bi = None
    cand = by_pnu.get(r["지번코드"], [])
    if len(cand) == 1: bi = cand[0]; st["필지"] += 1
    elif len(cand) > 1: bi = min(cand, key=lambda i: 0 if polys[i].contains(P) else polys[i].distance(P)); st["필지"] += 1
    else:
        hit = [int(k) for k in tree.query(P) if polys[int(k)].contains(P)]
        if not hit:
            near = [int(k) for k in tree.query(P.buffer(8))]
            hit = sorted(near, key=lambda i: polys[i].distance(P))[:1]
        if hit: bi = hit[0]; st["좌표"] += 1
    if bi is None: st["못 붙임"] += 1; continue
    nm = r["상호명"].strip() + (" " + r["지점명"].strip() if r["지점명"].strip() else "")
    out.setdefault(bi, []).append([nm, r["상권업종대분류명"], r["상권업종소분류명"], r["동정보"].strip(), r["층정보"].strip(), r["호정보"].strip()])
json.dump({"src": f"소상공인시장진흥공단 상가(상권)정보 {ref[:4]}-{ref[4:]} (공공데이터포털, 이용 제한 없음)", "b": out}, open(os.path.join(G, "data", "stores.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(st, "건물", len(out), round(os.path.getsize(os.path.join(G, "data", "stores.json")) / 1048576, 2), "MB")
