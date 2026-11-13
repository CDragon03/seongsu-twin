# 게임용 가벼운 도시 데이터: 건물(윤곽·높이·색·사용승인 연도) + 도로면 삼각형 + 골목 + 바닥 사진 + 역·고가
# 블렌더 없이 data/ 의 JSON 만으로 만듦 → game/data/city.json, game/data/ground.jpg
# 실행: python -I game/build_data.py
import os, json, math, random, shutil
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(D, "game", "data"); os.makedirs(G, exist_ok=True)
LAT0, LON0 = 37.543, 127.0535
KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
xy = lambda la, lo: ((lo - LON0) * KX, (la - LAT0) * KY)
r2 = lambda v: round(v, 2)
random.seed(3)
els = json.load(open(os.path.join(D, "data", "official_twin.json"), encoding="utf-8"))["elements"]
LM = json.load(open(os.path.join(D, "data", "landmarks.json"), encoding="utf-8"))
rm = {i for l in LM for i in l["remove"]}
# 47233_0 = 코오롱타워 저층부에 묻힌 부속동(build_styled 도 뺌)
els = [e for e in els if e.get("id") not in rm and e.get("id") != "47233_0"] + [{"id": l["id"], "geometry": l["geometry"], "tags": {
    "official_height": l["height"], "official_floors": l["floors"], "use": "업무시설", "structure": "철골철근콘크리트구조",
    "official_addr": l["name"], "lm": l["kind"], "approved": "2022" if l["kind"] != "haus" else "2025"}} for l in LM]
NAMES = {"45832_0": "서울숲 코오롱디지털타워1차", "47645_0": "대림창고", "44664_0": "대림창고", "47644_0": "대림창고", "45156_0": "대림창고"}
PAL = {"brick": ["#8e4a36", "#9a5640", "#7c3f2e", "#a0624a"], "concrete": ["#b8b5ae", "#c9c5bc", "#a9a69f"],
       "plaster": ["#d9d2c3", "#e3dccd", "#cfc6b4"], "apt": ["#e8e6e1", "#dcdad4"], "glass": ["#4d6273", "#3c4f5e", "#5a7080"],
       "metal": ["#9aa0a3", "#8a9094"], "lm": ["#2b3640"]}
def kind(t, h, fl):
    s, u = t.get("structure", ""), t.get("use", "")
    if t.get("lm"): return "glass"
    if "벽돌" in s or "조적" in s: return "brick"
    if "공동주택" in u and fl >= 8: return "apt"
    if "철골" in s and h > 25: return "glass"
    if "철골" in s or "공장" in u or "창고" in u: return "metal"
    if "주택" in u: return "plaster"
    return "concrete"
B = []
for e in els:
    t = e["tags"]
    if "official_height" not in t or len(e.get("geometry", [])) < 4: continue
    pts = [xy(p["lat"], p["lon"]) for p in e["geometry"]]
    if pts[0] == pts[-1]: pts = pts[:-1]
    if len(pts) < 3: continue
    a2 = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if a2 < 0: pts = pts[::-1]
    h = float(t["official_height"]); fl = int(t.get("official_floors") or 0) or max(1, round(h / 3.3))
    k = kind(t, h, fl)
    yr = str(t.get("approved", ""))[:4]
    b = {"p": [r2(v) for q in pts for v in q], "h": round(h, 1), "f": fl, "c": random.choice(PAL[k]), "k": k,
         "y": int(yr) if yr.isdigit() else 0}
    nm = NAMES.get(e.get("id")) or (t.get("official_addr") if t.get("lm") else None) or t.get("name")
    if nm: b["n"] = nm
    u = t.get("use", "")
    if "근린생활" in u or "판매" in u: b["u"] = 1   # 1층 상가(간판 표현용)
    B.append(b)
# 공식 자료에 없는 건물을 OSM 윤곽으로 채움(학교·아파트 등 147동, 2026-11-13). 높이 = OSM 층수×3.3m, 없으면 3층 추정. b["o"]=1 표시
def _inside(p, x, y):
    c = False; n = len(p) // 2
    for i in range(n):
        j = (i - 1) % n; xi, yi, xj, yj = p[2*i], p[2*i+1], p[2*j], p[2*j+1]
        if (yi > y) != (yj > y) and x < xi + (y - yi) * (xj - xi) / (yj - yi): c = not c
    return c
_grid = {}
for _i, _b in enumerate(B):
    _xs, _ys = _b["p"][0::2], _b["p"][1::2]
    for gx in range(int(min(_xs) // 20), int(max(_xs) // 20) + 1):
        for gy in range(int(min(_ys) // 20), int(max(_ys) // 20) + 1): _grid.setdefault((gx, gy), []).append(_i)
_cov = lambda x, y: any(_inside(B[i]["p"], x, y) for i in _grid.get((int(x // 20), int(y // 20)), []))
_X0, _X1 = min(v for b in B for v in b["p"][0::2]), max(v for b in B for v in b["p"][0::2]); _Y0, _Y1 = min(v for b in B for v in b["p"][1::2]), max(v for b in B for v in b["p"][1::2])
_add = 0; _XT = []
for e in json.load(open(os.path.join(D, "data", "osm.json"), encoding="utf-8"))["elements"]:
    t = e.get("tags", {})
    if "building" not in t or "geometry" not in e or t.get("building") == "train_station": continue
    P = [xy(q["lat"], q["lon"]) for q in e["geometry"]]
    if P[0] == P[-1]: P = P[:-1]
    if len(P) < 3: continue
    n = len(P); cx = sum(q[0] for q in P) / n; cy = sum(q[1] for q in P) / n
    if not (_X0 < cx < _X1 and _Y0 < cy < _Y1): continue
    a2 = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n))
    if abs(a2) / 2 < 80: continue
    pts = P + [(cx, cy)]
    if sum(1 for x, y in pts if not _cov(x, y)) <= len(pts) * 0.7: continue
    if a2 < 0: P = P[::-1]
    try: fl = int(float(str(t.get("building:levels", "")).split(";")[0]))
    except ValueError: fl = 0
    h = round(fl * 3.3, 1) if fl else 9.9; fl = fl or 3; bt = t.get("building")
    k = "apt" if bt == "apartments" and fl >= 8 else "plaster" if bt in ("apartments", "house", "residential") else "metal" if bt in ("industrial", "warehouse") else "glass" if fl >= 12 else "concrete"
    nb = {"p": [r2(v) for q in P for v in q], "h": h, "f": fl, "c": random.choice(PAL[k]), "k": k, "y": 0, "o": 1}
    if t.get("name"): nb["n"] = t["name"]
    B.append(nb); _add += 1
    u = "공동주택" if bt == "apartments" else "단독주택" if bt in ("house", "residential") else "공장" if bt in ("industrial", "warehouse") else "교육연구시설" if bt in ("school", "university") else "종교시설" if bt in ("church",) else "제2종근린생활시설" if bt in ("commercial", "retail") else "업무시설"
    _XT.append({"id": "osm_%s" % e["id"], "geometry": e["geometry"], "tags": {"official_height": h, "official_floors": fl, "use": u,
        "structure": "일반철골구조" if u == "공장" else "철근콘크리트구조", "official_addr": t.get("name") or "OSM %s" % e["id"], "official_src": "OSM"}})
print("OSM 로 채운 건물", _add)
# 블렌더 상세 모델용(build_styled.py 입력): data_extra/official_twin.json = OSM 건물 + 연무장길(중심 계산용)
_XD = os.path.join(D, "data_extra"); os.makedirs(_XD, exist_ok=True)
json.dump({"elements": _XT + [e for e in els if e["tags"].get("name") == "연무장길"]}, open(os.path.join(_XD, "official_twin.json"), "w", encoding="utf-8"), ensure_ascii=False)
# 도로 띠(폭 = road_widths.json, 보도 포함) → 삼각형
RW = json.load(open(os.path.join(D, "data", "road_widths.json")))
dflt = {"primary": 14, "secondary": 12, "tertiary": 10, "residential": 7, "unclassified": 6, "service": 4, "footway": 2, "pedestrian": 4}
R, W_ = [], []
for e in els:
    t = e["tags"]
    if "highway" not in t or len(e.get("geometry", [])) < 2: continue
    pts = [xy(p["lat"], p["lon"]) for p in e["geometry"]]
    d0 = dflt.get(t["highway"], 3) / 2; o = RW.get(str(e["id"]))
    wl = o["l"] if o and len(o["l"]) == len(pts) else [d0] * len(pts)
    wr = o["r"] if o and len(o["r"]) == len(pts) else [d0] * len(pts)
    sw = o.get("sw", 0) if o else 0
    n = len(pts); L_, R_ = [], []
    for i in range(n):
        a = pts[max(0, i - 1)]; b = pts[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; Lg = math.hypot(dx, dy) or 1; nx, ny = -dy / Lg, dx / Lg
        L_.append((pts[i][0] + nx * (wl[i] + sw), pts[i][1] + ny * (wl[i] + sw))); R_.append((pts[i][0] - nx * (wr[i] + sw), pts[i][1] - ny * (wr[i] + sw)))
    for i in range(n - 1):
        R += [r2(v) for q in (L_[i], L_[i + 1], R_[i + 1], L_[i], R_[i + 1], R_[i]) for v in q]
    if t["highway"] not in ("footway", "pedestrian", "steps", "path", "cycleway"):
        W_.append({"p": [r2(v) for q in pts for v in q], "w": round(sorted(wl + wr)[len(wl + wr) // 2], 1), "k": t["highway"], "n": t.get("name", "")})
AL = []   # 카카오맵에서 뽑은 골목은 공개판에서 뺌(2026-11-13)
GR = json.load(open(os.path.join(D, "data", "ground.json"), encoding="utf-8"))
shutil.copy(os.path.join(D, "data", "ground.jpg"), os.path.join(G, "ground.jpg"))
EX = json.load(open(os.path.join(D, "data", "subway_exits.json"), encoding="utf-8"))
V = []
for re_ in json.load(open(os.path.join(D, "data", "rail.json"), encoding="utf-8"))["elements"]:
    rt = re_.get("tags", {})
    if rt.get("railway") == "subway" and rt.get("bridge"):
        V.append([r2(v) for p in re_["geometry"] for v in xy(p["lat"], p["lon"])])
rp = [xy(p["lat"], p["lon"]) for e in els if e["tags"].get("name") == "연무장길" for p in e["geometry"]]
mx = sum(p[0] for p in rp) / len(rp); my = sum(p[1] for p in rp) / len(rp)
CX, CY = min(rp, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
# 역(OSM): 성수·뚝섬(2호선 고가)·서울숲(수인분당선 지하) — 승강장 윤곽 + 출구
OS = json.load(open(os.path.join(D, "data", "stations_osm.json"), encoding="utf-8"))["elements"]
ST = {"210": "뚝섬", "211": "성수", "K211": "서울숲"}
stations = [{"name": ST[e["tags"]["ref"]], "en": e["tags"].get("name:en", ""), "x": r2(xy(e["lat"], e["lon"])[0]), "y": r2(xy(e["lat"], e["lon"])[1]), "line": "수인분당선" if e["tags"]["ref"].startswith("K") else "2호선"}
            for e in OS if e["tags"].get("railway") == "station" and e["tags"].get("ref") in ST]
rail_pf = [e for e in json.load(open(os.path.join(D, "data", "rail.json"), encoding="utf-8"))["elements"] if e.get("tags", {}).get("railway") == "platform"]
for st in stations:
    st["platforms"] = [[r2(v) for p in e["geometry"] for v in xy(p["lat"], p["lon"])] for e in rail_pf
                       if min(math.hypot(xy(p["lat"], p["lon"])[0] - st["x"], xy(p["lat"], p["lon"])[1] - st["y"]) for p in e["geometry"]) < 150]
exits2 = []
for e in OS:
    if e["tags"].get("railway") != "subway_entrance": continue
    x, y = xy(e["lat"], e["lon"]); st = min(stations, key=lambda s_: math.hypot(s_["x"] - x, s_["y"] - y))
    if st["name"] == "성수": continue   # 성수역 출구는 기존 subway_exits.json
    best = None   # 가장 가까운 길 쪽을 바라보게
    for w in W_:
        for i in range(0, len(w["p"]) - 2, 2):
            d = math.hypot(w["p"][i] - x, w["p"][i + 1] - y)
            if best is None or d < best[0]: best = (d, w["p"][i], w["p"][i + 1])
    ang = math.atan2(best[1] - x, -(best[2] - y)) if best else 0.0
    exits2.append({"ref": e["tags"].get("ref", ""), "st": st["name"], "x": r2(x), "y": r2(y), "ang": round(ang, 3)})
# 가로수: 서울시 가로수 위치정보(OA-23040, 2026판, 정원도시국 조경과) 중 우리 범위 → [x, y, 수종 코드]
SPK = {"이팝나무": "ip", "양버즘나무": "pl", "느티나무": "ze", "메타세쿼이아": "me", "은행나무": "gi", "소나무": "pi"}
_TJ = os.path.join(D, "data", "street_trees", "area.json")
TREES = [[r2(t["x"]), r2(t["y"]), SPK.get(t["s"], "ot")] for t in json.load(open(_TJ, encoding="utf-8"))] if os.path.exists(_TJ) else []
print("가로수", len(TREES))
# 거리 소품(어제 블렌더 판과 같은 배치, props_layout.py 규칙으로 OSM 길에서 만든 가정 배치): 횡단보도·정지선·노면 글자·신호등·교통표지·방범 CCTV·볼라드
_PJ = os.path.join(D, "data", "props.json"); STREET = {}
if os.path.exists(_PJ):
    _P = json.load(open(_PJ, encoding="utf-8")); rr = lambda a: [round(v, 2) if isinstance(v, float) else v for v in a]
    for k, n in (("xwalks", "xw"), ("stoplines", "sl"), ("tlights", "tl"), ("rsigns", "rs"), ("cctvs", "cc"), ("bollards", "bo"), ("ymj_bollards", "yb")): STREET[n] = [rr(r) for r in _P.get(k, [])]
    STREET["rt"] = [rr(r) for r in _P.get("roadtext", []) + _P.get("ymj_text", [])]
    print("거리 소품", {k: len(v) for k, v in STREET.items()})
out = {"stations": stations, "trees": TREES, "street": STREET, "exits2": exits2, "buildings": B, "roads": R, "alleys": [r2(v) for t_ in AL for v in t_], "ways": W_,
       "ground": {"img": "ground.jpg", "corners": GR["corners"]}, "exits": EX, "viaduct": V,
       "start": [r2(CX), r2(CY)], "source": "건물: 국토교통부 GIS건물통합정보(빠진 147동은 OpenStreetMap 윤곽·높이 추정) · 도로: OpenStreetMap · 바닥: 국토지리정보원 정사영상 2025 · 가로수: 서울시 가로수 위치정보 2026"}
json.dump(out, open(os.path.join(G, "city.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("건물", len(B), "도로 삼각형", len(R) // 6, "골목", len(AL), "길", len(W_), round(os.path.getsize(os.path.join(G, "city.json")) / 1e6, 1), "MB")
