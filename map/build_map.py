# 지도형 화면 자료: 성수역~연무장길 구역만 잘라 map/data.json + map/ortho.jpg 로 만든다
#  건물: 국토교통부 GIS건물통합정보 윤곽·높이(city.json) + 건축물대장(bldg_info.json) + 출입구·입주업체
#  지붕 색: 국토지리정보원 정사영상 2025(0.25m, EPSG:5186 · ../data/ortho/georef.json)에서 건물 안쪽 픽셀 평균
#  바닥 사진: 같은 정사영상을 0.5m 로 줄여 잘라 ortho.jpg
# 실행: python -I map/build_map.py
import json, math, os, re
import numpy as np
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Polygon, LineString, Point, box, mapping
from shapely.ops import unary_union
from rasterio.features import rasterize
from rasterio.transform import Affine

G = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); M = os.path.join(G, "map"); R = os.path.join(G, "..", "data")
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
X0, X1, Y0, Y1 = -450, 850, -500, 650          # 구역(지역좌표 m): 성수역·연무장길·대림창고 일대
ll = lambda x, y: (round(LON0 + x / KX, 6), round(LAT0 + y / KY, 6))
J = lambda n: json.load(open(os.path.join(G, "data", n), encoding="utf-8"))
city, info, sto, ent = J("city.json"), J("bldg_info.json")["b"], J("stores.json"), J("entrances.json")["b"]
clip = box(X0, Y0, X1, Y1)

# ── 정사영상: 지역좌표 → EPSG:5186 → 픽셀
geo = json.load(open(os.path.join(R, "ortho", "georef.json"))); GSD = geo["gsd"]
to5186 = Transformer.from_crs(4326, 5186, always_xy=True)
def px(x, y): E, N = to5186.transform(*ll(x, y)); return (E - geo["left"]) / GSD, (geo["top"] - N) / GSD
Image.MAX_IMAGE_PIXELS = None
img = Image.open(os.path.join(R, "ortho", "ortho_2025_37705083.tif")).convert("RGB")
# 구역 네 모서리의 픽셀 → 둘러싸는 사각형으로 잘라 0.5m 로 줄임(회전 없음 가정, georef 와 같음)
cs = [px(x, y) for x, y in [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]]
c0, c1 = int(min(c[0] for c in cs)), int(max(c[0] for c in cs)); r0, r1 = int(min(c[1] for c in cs)), int(max(c[1] for c in cs))
crop = img.crop((c0, r0, c1, r1)); arr = np.asarray(crop)
SC = 2; small = crop.resize(((c1 - c0) // SC, (r1 - r0) // SC), Image.LANCZOS); small.save(os.path.join(M, "ortho.jpg"), quality=78, optimize=True, progressive=True)
inv = Transformer.from_crs(5186, 4326, always_xy=True)
corner = lambda c, r: [round(v, 7) for v in inv.transform(geo["left"] + c * GSD, geo["top"] - r * GSD)]
ortho_corners = [corner(c0, r0), corner(c1, r0), corner(c1, r1), corner(c0, r1)]   # 왼위·오른위·오른아래·왼아래(경위도)

# ── 건물
USE = [("주거", ("단독주택", "공동주택")), ("상가", ("제1종근린생활시설", "제2종근린생활시설", "근린생활시설", "판매시설", "숙박시설")),
       ("업무", ("업무시설", "교육연구시설", "방송통신시설", "교육연구및복지시설", "의료시설", "문화및집회시설", "종교시설", "노유자시설", "운동시설")),
       ("공장·창고", ("공장", "창고시설", "자동차관련시설")), ("위험물", ("위험물저장및처리시설",))]
grp = lambda u: next((g for g, L in USE if u in L), "기타")
B = city["buildings"]; feats = []; shapes = []
for i, b in enumerate(B):
    P = Polygon(list(zip(b["p"][0::2], b["p"][1::2]))).buffer(0)
    if P.is_empty or not P.intersects(clip) or not clip.contains(P.centroid): continue
    d = info[i] or {}
    core = P.buffer(-0.8) if P.area > 12 else P
    if core.is_empty: core = P
    shapes.append((Polygon([px(x, y) for x, y in core.exterior.coords]) if core.geom_type == "Polygon" else Polygon([px(x, y) for x, y in max(core.geoms, key=lambda g: g.area).exterior.coords]), len(feats) + 1))
    S = sto["b"].get(str(i), []); F = sto.get("f", {}).get(str(i), []); MN = sto.get("m", {}).get(str(i), [])
    cat = {}
    for s in S: cat[s[1]] = cat.get(s[1], 0) + 1
    shop1 = [s[0] for s in S if s[4] == "1"][:6]
    pr = {"i": i, "h": round(b["h"], 1), "hs": "대장" if d.get("h") else "추정", "g": grp(d.get("use")), "u": d.get("use") or "",
          "n": d.get("nm") or b.get("n") or "", "a": (d.get("road") or d.get("addr") or "").replace("서울특별시 성동구 ", ""),
          "fu": d.get("fu") or b.get("f") or 0, "fb": d.get("fb") or 0, "ga": round(d.get("ga") or 0), "ap": (d.get("ap") or "")[:4], "st": d.get("st") or "",
          "sn": len(S), "fn": len(F), "mn": len({m[0] for m in MN}), "cat": sorted(cat.items(), key=lambda t: -t[1])[:4], "s1": shop1,
          "fl": [[f[0], f[1]] for f in (d.get("fl") or []) if not re.search(r"복도|계단|승강기|화장실|홀", f[1])][:40],
          "e": [list(ll(e[0], e[1])) for e in ent.get(str(i), [])][:6]}
    feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[list(ll(x, y)) for x, y in P.exterior.coords]]}, "properties": pr})
# 지붕 색: 건물 안쪽(0.8m 들인) 픽셀 평균
lab = rasterize([(mapping(Polygon([(c - c0, r - r0) for c, r in s.exterior.coords])), v) for s, v in shapes], out_shape=arr.shape[:2], fill=0, dtype="int32")
cnt = np.bincount(lab.ravel(), minlength=len(feats) + 1)
RGB = np.zeros((len(feats) + 1, 3))
for ch in range(3): RGB[:, ch] = np.bincount(lab.ravel(), weights=arr[..., ch].ravel().astype(float), minlength=len(feats) + 1) / np.maximum(cnt, 1)
for k, f in enumerate(feats, 1): f["properties"]["rc"] = "#%02x%02x%02x" % tuple(int(v) for v in (RGB[k] if cnt[k] else (128, 128, 128)))
print("건물", len(feats))

# ── 길: 도로구간 중심선(w = 반폭). 폭 4m 미만 = 소방차 진입 어려움(가정)
roads = []
for w in city["ways"]:
    L = LineString(list(zip(w["p"][0::2], w["p"][1::2]))).intersection(clip)
    for g in getattr(L, "geoms", [L]):
        if g.is_empty or g.length < 2: continue
        roads.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [list(ll(x, y)) for x, y in g.coords]},
                      "properties": {"w": round(w["w"] * 2, 1), "n": w.get("n") or "", "k": w.get("k") or "", "nar": int(w["w"] * 2 < 4)}})
# ── 2호선 고가: 중심선을 8m 폭 띠로
via = []
for line in city.get("viaduct") or []:
    L = LineString(list(zip(line[0::2], line[1::2]))).buffer(4.5, cap_style=2).intersection(clip.buffer(200))
    for g in getattr(L, "geoms", [L]):
        if g.geom_type == "Polygon": via.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[list(ll(x, y)) for x, y in g.exterior.coords]]}, "properties": {}})
# ── 점 자료
pt = lambda x, y, **pr: {"type": "Feature", "geometry": {"type": "Point", "coordinates": list(ll(x, y))}, "properties": pr}
inb = lambda x, y, m=0: X0 - m <= x <= X1 + m and Y0 - m <= y <= Y1 + m
O = city["official"]; T = J("transit.json")
pts = []
pts += [pt(s["x"], s["y"], t="역", n=s["name"] + "역", l=s.get("line", "")) for s in city["stations"] if inb(s["x"], s["y"], 300)]
pts += [pt(e[0], e[1], t="출구", n=f"{e[3]}역 {e[2]}번 출구") for e in T["exit"] if inb(e[0], e[1])]
pts += [pt(b[0], b[1], t="버스", n=b[2], ars=b[3]) for b in T["bus"] if inb(b[0], b[1])]
pts += [pt(c[0], c[1], t="CCTV", n=c[2]) for c in O["cam"] if inb(c[0], c[1])]
pts += [pt(s["x"], s["y"], t="대피", n=s["n"], k=s["t"]) for s in city.get("shelters", []) if inb(s["x"], s["y"])]
FAC = [f for f in city["facilities"]]
pts += [pt(f["x"], f["y"], t="소방" if f["k"] == "fire" else "경찰", n=f["n"], k=f["t"]) for f in FAC if inb(f["x"], f["y"], 1500)]
pts += [pt(h[0], h[1], t="병원", n=h[2], k=h[3], tel=h[4]) for h in O["er"] if inb(h[0], h[1], 2500)]
# 기관(구역 밖 포함): 가장 가까운 곳 찾기용
base = [{"t": "소방" if f["k"] == "fire" else "경찰", "n": f["n"], "k": f["t"], "c": list(ll(f["x"], f["y"]))} for f in FAC] + [{"t": "병원", "n": h[2], "k": h[3], "c": list(ll(h[0], h[1]))} for h in O["er"]]
# 이름난 곳(인파가 몰리는 매장): 상가 자료에서 이름으로 찾음
HOT = [["대림창고", "대림창고"], ["디올 성수", "디올 성수"], ["하우스 노웨어", "하우스 노웨어"], ["탬버린즈 성수", "탬버린즈"], ["무신사 킥스 성수", 2752], ["포인트오브뷰", 98], ["어니언 성수", 2040], ["성수연방", 2890]]
hot = []
for lab_, key in HOT:
    ix = key if isinstance(key, int) else next((int(k) for k, L in sto["b"].items() if any(key in s[0] for s in L)), None)
    if ix is None: continue
    b = B[ix]; cx, cy = sum(b["p"][0::2]) / (len(b["p"]) // 2), sum(b["p"][1::2]) / (len(b["p"]) // 2)
    if inb(cx, cy): hot.append(pt(cx, cy, t="명소", n=lab_, i=ix))
# 길 이름표: 이름별로 가장 긴 토막 하나
out = {"src": {"b": "국토교통부 GIS건물통합정보(2026-11) · 건축물대장", "ortho": "국토지리정보원 정사영상 2025", "road": "행정안전부 도로구간",
               "store": sto.get("src", ""), "cam": "서울시 CCTV 설치 현황", "fac": "서울시 소방서·119안전센터 / OpenStreetMap 경찰"},
       "ortho": ortho_corners, "bbox": [list(ll(X0, Y0)), list(ll(X1, Y1))], "center": list(ll(200, 60)),
       "b": {"type": "FeatureCollection", "features": feats}, "r": {"type": "FeatureCollection", "features": roads},
       "via": {"type": "FeatureCollection", "features": via}, "p": {"type": "FeatureCollection", "features": pts + hot}, "base": base}
json.dump(out, open(os.path.join(M, "data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("길", len(roads), "좁은 길", sum(r["properties"]["nar"] for r in roads), "고가", len(via), "점", len(pts), "명소", len(hot),
      "data.json", round(os.path.getsize(os.path.join(M, "data.json")) / 1e6, 2), "MB", "ortho.jpg", round(os.path.getsize(os.path.join(M, "ortho.jpg")) / 1e6, 2), "MB")
