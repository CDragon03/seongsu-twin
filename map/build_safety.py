# 성수 안전 지도 1순위 추가 자료 → map/safety.json
#  · 소방용수시설: 서울시 소방용수시설 표준등록 현행화 2026(OA-21306, 위경도). 유형 01 지상식 소화전 / 02 지하식 소화전 / 03 급수탑 / 04 저수조 / 05 지하식 상승식 (06은 코드표에 없음 → 그대로 표기)
#  · 비상소화장치: 서울시 비상소화장치 위치정보(OA-21071, X·Y = EPSG:5186 으로 봄)
#  · AED: 서울 열린데이터광장 tbEmgcAedInfo(국립중앙의료원 원본, 위경도)
#  · 재난약자 시설: 성동구 유치원 · 노인의료복지시설(요양시설) · 노인여가복지시설
#    → 좌표가 없거나 믿기 어려워(어린이집 좌표 일부가 다른 구에 찍힘) 도로명주소를 건물 대장 도로명주소와 맞춰 건물에 붙임
# 원본: ../../data/safety/ (fetch_safety.py 로 받음). 실행: python -I map/build_safety.py
import csv, io, json, math, os, re
import openpyxl
from pyproj import Transformer
G = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); M = os.path.join(G, "map"); S = os.path.join(G, "..", "data", "safety")
D = json.load(open(os.path.join(M, "data.json"), encoding="utf-8")); (x0, y0), (x1, y1) = D["bbox"]; MG = 0.004
inb = lambda lo, la: x0 - MG <= lo <= x1 + MG and y0 - MG <= la <= y1 + MG
pt = lambda lo, la, **p: {"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lo, 6), round(la, 6)]}, "properties": p}
out = {"src": {}, "fw": [], "eh": [], "aed": [], "vul": [], "vb": {}}
# 소방용수
cl = lambda v: "" if v is None or str(v).strip().lower() in ("nan", "none", "-") else str(v).strip()   # 빈 값 표기 정리
FWT = {"01": "지상식 소화전", "02": "지하식 소화전", "03": "급수탑", "04": "저수조", "05": "지하식 상승식"}
ws = openpyxl.load_workbook(os.path.join(S, "firewater_std_2026.xlsx"), read_only=True).active
for r in list(ws.iter_rows(values_only=True))[2:]:
    try: la, lo = float(r[7]), float(r[8])
    except (TypeError, ValueError): continue
    if not inb(lo, la): continue
    out["fw"].append(pt(lo, la, t=FWT.get(str(r[1]), f"유형 코드 {r[1]}(코드표에 없음)"), c=str(r[1]), n=str(r[0]), d=cl(r[9]), sc=cl(r[10]), y=cl(r[12]), p=cl(r[13])))
out["src"]["fw"] = "서울시 소방용수시설 표준등록 현행화(2026) · 서울 열린데이터광장 OA-21306"
# 비상소화장치
inv = Transformer.from_crs(5186, 4326, always_xy=True)
ws = openpyxl.load_workbook(os.path.join(S, "emergency_hydrant.xlsx"), read_only=True).active
for r in list(ws.iter_rows(values_only=True))[1:]:
    if not r or r[4] is None or r[8] == "Y": continue
    lo, la = inv.transform(float(r[4]), float(r[5]))
    if inb(lo, la): out["eh"].append(pt(lo, la, n=str(r[6] or ""), up=str(r[9] or "")[:8]))
out["src"]["eh"] = "서울시 비상소화장치 위치정보 · 서울 열린데이터광장 OA-21071"
out["src"]["sg"] = "성동구 어린이보호구역 주변 교통안전시설 중 안전표지판(공공데이터포털, 2022-12-15)"
# 안전비상벨(행정안전부 안전비상벨위치정보 · 서울특별시 파일, 공공데이터포털에서 받음)
out["bell"] = []
b = open(os.path.join(S, "bell_seoul.csv"), "rb").read().decode("cp949", errors="replace")
for r in list(csv.reader(io.StringIO(b)))[1:]:
    try: la, lo = float(r[8]), float(r[9])
    except (ValueError, IndexError): continue
    if inb(lo, la): out["bell"].append(pt(lo, la, n=r[2], u=r[3], k=r[4], w=r[5], pol=r[11], f=r[14], y=r[15], ck=r[16], org=r[18], tel=r[19]))
out["src"]["bell"] = "행정안전부 안전비상벨위치정보(서울특별시) · 공공데이터포털 15075539"
# AED
for r in json.load(open(os.path.join(S, "tbEmgcAedInfo.json"), encoding="utf-8")):
    try: lo, la = float(r["WGS84LON"]), float(r["WGS84LAT"])
    except (TypeError, ValueError): continue
    if inb(lo, la): out["aed"].append(pt(lo, la, n=r["ORG"] or "", pl=r["BUILDPLACE"] or "", a=(r["BUILDADDRESS"] or "").replace("서울특별시 성동구 ", ""), tel=r["CLERKTEL"] or ""))
out["src"]["aed"] = "자동심장충격기 정보(국립중앙의료원 원본, 서울시 재배포 tbEmgcAedInfo)"
# 재난약자 시설 → 건물 맞추기(도로명주소 「○○로/길 번호」)
ROAD = lambda t: (m := re.search(r"([가-힣0-9]+(?:로|길)\s*\d+(?:-\d+)?)", t or "")) and re.sub(r"\s+", " ", m.group(1))
info = json.load(open(os.path.join(G, "data", "bldg_info.json"), encoding="utf-8"))["b"]
inarea = {f["properties"]["i"]: f for f in D["b"]["features"]}
by_road = {}
for i, r in enumerate(info):
    if r and r.get("road") and i in inarea: by_road.setdefault(ROAD(r["road"]), []).append(i)
cent = lambda f: [sum(c[0] for c in f["geometry"]["coordinates"][0]) / len(f["geometry"]["coordinates"][0]), sum(c[1] for c in f["geometry"]["coordinates"][0]) / len(f["geometry"]["coordinates"][0])]
stat = {}
def add(kind, name, addr, extra=""):
    st = stat.setdefault(kind, [0, 0]); st[0] += 1; c = by_road.get(ROAD(addr) or "")
    if not c: return
    i = max(c, key=lambda k: inarea[k]["properties"]["h"]); st[1] += 1
    out["vb"].setdefault(str(i), []).append([kind, name, extra]); lo, la = cent(inarea[i]); out["vul"].append(pt(lo, la, k=kind, n=name, x=extra, i=i))
# 어린이집(서울시 어린이집 정보)은 공공누리 4유형(변경 금지·상업적 이용 금지)이라 쓰지 않음 (2026-11-20 결정)
for r in json.load(open(os.path.join(S, "childSchoolInfo_sd.json"), encoding="utf-8")): add("유치원", r["KDGT_NM"], r["ADDR"], r.get("FNDN_TYPE") or "")
ws = openpyxl.load_workbook(os.path.join(S, "elder_medical.xlsx"), read_only=True).active
for r in list(ws.iter_rows(values_only=True))[3:]:
    if r and r[1] == "성동구" and r[3]: add("노인요양시설", r[3], r[32] or "", f"정원 {r[8]}명" if r[8] else "")
for r in json.load(open(os.path.join(S, "fcltOpenInfo_OWI.json"), encoding="utf-8")):
    if r["JRSD_SGG_NM"] == "성동구": add("노인여가복지시설", r["FCLT_NM"], r["FCLT_ADDR"], r.get("FCLT_KIND_NM") or "")
out["src"]["vul"] = "성동구 유치원 일반현황 · 서울시 노인의료복지시설 현황(2024.12.31) · 서울시 노인여가복지시설 목록"
out["stat"] = {k: {"성동구": a, "구역 안 건물에 붙음": b} for k, (a, b) in stat.items()}
# ── 이미 받아 둔 자료로 만든 2순위(새로 받지 않음)
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
ll = lambda x, y: (LON0 + x / KX, LAT0 + y / KY)
city = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8")); sto = json.load(open(os.path.join(G, "data", "stores.json"), encoding="utf-8"))["b"]
# 위험물 시설: 건축물대장 주용도 「위험물저장및처리시설」 건물 + 상가정보 소분류 주유소·가스(LPG) 충전소
out["hz"] = []
for i, f in inarea.items():
    if f["properties"].get("g") == "위험물": lo, la = cent(f); out["hz"].append(pt(lo, la, k="위험물 저장·처리시설(건축물대장)", n=f["properties"].get("n") or f["properties"].get("a"), i=i))
for i, L in sto.items():
    for x in L:
        if re.search(r"주유소|LPG|가스 ?충전", x[2]) and len(x) >= 8:
            lo, la = ll(x[6], x[7])
            if inb(lo, la): out["hz"].append(pt(lo, la, k=x[2] + "(상가정보)", n=x[0], i=int(i)))
out["src"]["hz"] = "건축물대장 주용도(위험물저장및처리시설) · 소상공인 상가정보 소분류(주유소·가스 충전소)"
# 침수 흔적: 서울시 침수흔적도(이미 받아 둔 flood_traces.json)
fl = json.load(open(os.path.join(G, "data", "flood_traces.json"), encoding="utf-8")); out["fl"] = []
for f in fl["features"]:
  for ring in f["r"]:   # 고리마다 한 면
    R = [list(map(lambda v: round(v, 6), ll(ring[k], ring[k + 1]))) for k in range(0, len(ring) - 1, 2)]
    if len(R) >= 3 and any(inb(lo, la) for lo, la in R): out["fl"].append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [R]}, "properties": {"n": f["n"], "y": f["y"], "d": f["d"], "c": f["c"], "z": f["z"]}})
out["src"]["fl"] = fl["source"]
# 대피 장소: 지진옥외대피장소 / 이재민 임시주거시설
out["sh"] = [pt(*ll(s_["x"], s_["y"]), k="지진옥외대피장소" if s_["k"] == "outdoor" else "이재민 임시주거시설", n=s_["n"], t=s_["t"], a=s_["a"], c=s_["c"]) for s_ in city["shelters"] if inb(*ll(s_["x"], s_["y"]))]
out["src"]["sh"] = "성동구 지진옥외대피장소 현황(2026-07-23) · 임시주거시설(2025-09-12), 공공데이터포털 · 좌표는 시설 이름으로 OpenStreetMap에서 찾음"
# 어린이보호구역 대상 학교
out["sz"] = [pt(*ll(z[0], z[1]), n=z[2] + z[3]) for z in city["official"]["sz"] if inb(*ll(z[0], z[1]))]
out["src"]["sz"] = "성동구 어린이보호구역 주변 교통안전시설(공공데이터포털, 2022-12-15)"
for k in ("fw", "eh", "aed", "vul", "bell", "hz", "fl", "sh", "sz"): out[k] = {"type": "FeatureCollection", "features": out[k]}
json.dump(out, open(os.path.join(M, "safety.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("소방용수", len(out["fw"]["features"]), "비상소화장치", len(out["eh"]["features"]), "AED", len(out["aed"]["features"]), "비상벨", len(out["bell"]["features"]), "위험물", len(out["hz"]["features"]), "침수흔적", len(out["fl"]["features"]), "대피", len(out["sh"]["features"]), "보호구역", len(out["sz"]["features"]), "재난약자", out["stat"], round(os.path.getsize(os.path.join(M, "safety.json")) / 1e3), "KB")
