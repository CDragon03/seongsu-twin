# 입주 업체: 소상공인시장진흥공단 상가(상권)정보(서울 파일, 분기) → 화면 건물마다 상호·업종·동·층·호 → data/stores.json
# 붙이는 법: 지번코드(19자리) = 건물 PNU 로 필지를 찾고, 한 필지에 건물이 여럿이면 업소 좌표가 들어간 건물(없으면 가장 가까운 건물)
# 실행: python -I build_stores.py <상가정보 zip>
import csv, io, json, math, os, re, sys, zipfile
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
ROAD = lambda t: (m := re.search(r"(?:구|시)\s+([가-힣0-9]+(?:로|길)\s*\d+(?:-\d+)?)", t or "")) and re.sub(r"\s+", " ", m.group(1))   # 도로명주소에서 「성수일로4길 25」만
out = {}; st = {"범위 안": 0, "필지": 0, "좌표": 0, "못 붙임": 0, "주소 달라 뺌": 0}; ref = name.rsplit("_", 1)[-1][:6]
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
        # 좌표로만 붙은 업소: 업소 도로명주소와 건물(대장) 도로명주소가 둘 다 있고 다르면 이웃 건물 업소이므로 뺌
        if bi is not None and ROAD(r["도로명주소"]) and info[bi] and ROAD(info[bi].get("road")) and ROAD(r["도로명주소"]) != ROAD(info[bi].get("road")): st["주소 달라 뺌"] += 1; st["좌표"] -= 1; continue
    if bi is None: st["못 붙임"] += 1; continue
    nm = r["상호명"].strip() + (" " + r["지점명"].strip() if r["지점명"].strip() else "")
    out.setdefault(bi, []).append([nm, r["상권업종대분류명"], r["상권업종소분류명"], r["동정보"].strip(), r["층정보"].strip(), r["호정보"].strip(), round(x, 1), round(y, 1)])   # 7·8번째 = 가게 좌표(지역좌표, 간판 자리용)
# 같은 건물·같은 층·같은 업종에서 이름이 같은 업소(법인 표기·브랜드 별칭만 다른 것)는 하나로 합침. 층·호가 더 채워진 쪽을 남김
ALIAS = [("코리아세븐", "세븐일레븐")]
def key(x):
    n = re.sub(r"\(주\)|주식회사|\s", "", x[0]); n = re.sub(r"주$", "", n); n = re.sub(r"서비스$", "", n)
    for a, b in ALIAS: n = n.replace(a, b)
    return (n, x[2], x[4])
dup = 0
for bi, L in out.items():
    seen = {}
    for x in L:
        k = key(x)
        if k in seen: dup += 1; y = seen[k]; seen[k] = x if sum(map(bool, x[3:6])) > sum(map(bool, y[3:6])) else y
        else: seen[k] = x
    out[bi] = list(seen.values())
st["중복 합침"] = dup
# 등록 공장: 성동구 공장등록현황(../data/more/factory_u.csv, 회사명·공장대표주소·업종명·생산품) → 도로명주소가 같은 건물에 붙임. 층·호는 주소 뒤쪽 글에서 읽음
by_road = {}
for i, r in enumerate(info):
    if r and ROAD(r.get("road")): by_road.setdefault(ROAD(r["road"]), []).append(i)
fac = {}; fst = {"공장": 0, "붙임": 0}
fp = os.path.join(G, "..", "data", "more", "factory_u.csv")
if os.path.exists(fp):
    for r in csv.DictReader(open(fp, encoding="utf-8-sig")):
        fst["공장"] += 1; a = r["공장대표주소"]; c = by_road.get(ROAD(a) or "")
        if not c: continue
        bi = max(c, key=lambda i: polys[i].area); tail = a.split(ROAD(a), 1)[-1]
        ho = list(dict.fromkeys(re.sub(r"\s", "", h).replace("-", "~") for h in re.findall(r"B?\d{3,4}(?:\s*[~\-]\s*\d{3,4})?(?=\s*호|[,.]|\s|$)", re.sub(r"B?\d+층", "", tail)))); fm = re.search(r"(B?\d+)층", tail)
        f = fm.group(1) if fm else (str(int(ho[0][:4].split("~")[0]) // 100) if ho and not ho[0].startswith("B") else "")
        fac.setdefault(bi, []).append([r["회사명"].strip(), r["업종명"].strip(), r["생산품"].strip(), f, ",".join(ho)]); fst["붙임"] += 1
print("등록 공장", fst)
# 현장 확인 입주사: data/stores_manual.json {"b": {PNU: [[회사명, 하는 일(모르면 빈 칸), 층, 호, 확인일]]}} → 그 필지의 가장 큰 건물
man = {}; mp = os.path.join(G, "data", "stores_manual.json"); MSRC = ""
if os.path.exists(mp):
    M = json.load(open(mp, encoding="utf-8")); MSRC = M.get("src", "")
    for pnu, L in M["b"].items():
        c = by_pnu.get(pnu)
        if c: man.setdefault(max(c, key=lambda i: polys[i].area), []).extend(L)
print("현장 확인", sum(map(len, man.values())))
json.dump({"src": f"소상공인시장진흥공단 상가(상권)정보 {ref[:4]}-{ref[4:]} (공공데이터포털, 이용 제한 없음)", "b": out, "f": fac, "src_f": "서울 성동구 공장등록현황(공공데이터포털, 공장대표주소 기준)", "m": man, "src_m": MSRC}, open(os.path.join(G, "data", "stores.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(st, "건물", len(out), round(os.path.getsize(os.path.join(G, "data", "stores.json")) / 1048576, 2), "MB")
