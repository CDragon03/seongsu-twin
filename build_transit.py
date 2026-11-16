# 대중교통 표지 자료 → data/transit.json
#  bus  : 서울 열린데이터광장 「서울시 버스정류소 위치정보」(busStopLocationXyInfo) → [x, y, 정류소명, 정류소 번호(ARS 5자리), 종류, 정류소 ID]
#  exit : OpenStreetMap railway=subway_entrance(Overpass) → [x, y, 출구번호, 가까운 역 이름]
# 인증키: ../data/seoul_general_key.txt. 실행: python -I build_transit.py
import json, math, os, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); K = open(os.path.join(G, "..", "data", "seoul_general_key.txt"), encoding="utf-8-sig").read().strip()
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
c = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8"))
xs = [v for b in c["buildings"] for v in b["p"][0::2]]; ys = [v for b in c["buildings"] for v in b["p"][1::2]]; X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
xy = (lambda la, lo: ((lo - LON0) * KX, (la - LAT0) * KY))
rows, s = [], 1
while True:
    j = json.loads(urllib.request.urlopen(f"http://openapi.seoul.go.kr:8088/{K}/json/busStopLocationXyInfo/{s}/{s + 999}/", timeout=60).read().decode("utf-8"))["busStopLocationXyInfo"]
    rows += j.get("row") or []
    if len(rows) >= int(j["list_total_count"]) or not j.get("row"): break
    s += 1000
bus = []
for r in rows:
    try: x, y = xy(float(r["YCRD"]), float(r["XCRD"]))
    except (TypeError, ValueError): continue
    if X0 <= x <= X1 and Y0 <= y <= Y1 and "한강" not in (r.get("STOPS_TYPE") or ""): bus.append([round(x, 1), round(y, 1), r["STOPS_NM"], r.get("NODE_ID") or "", r.get("STOPS_TYPE") or "", r["STOPS_NO"]])   # 4번째 = 정류소 번호(ARS 5자리, 도착 조회용), 6번째 = 정류소 ID
la0, la1, lo0, lo1 = LAT0 + Y0 / KY, LAT0 + Y1 / KY, LON0 + X0 / KX, LON0 + X1 / KX
q = f'[out:json][timeout:60];(node["railway"="subway_entrance"]({la0},{lo0},{la1},{lo1});node["railway"="station"]["station"="subway"]({la0 - .01},{lo0 - .01},{la1 + .01},{lo1 + .01}););out;'
o = json.loads(urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": "seongsu-twin-build"}), timeout=90).read().decode("utf-8"))
ST = [{"name": (e["tags"].get("name") or "").replace("역", ""), "x": xy(e["lat"], e["lon"])[0], "y": xy(e["lat"], e["lon"])[1]} for e in o["elements"] if e.get("tags", {}).get("railway") == "station"] + c.get("stations", []); ex = []
for e in o["elements"]:
    if e.get("tags", {}).get("railway") != "subway_entrance": continue
    x, y = xy(e["lat"], e["lon"]); t = e.get("tags", {})
    st = min(ST, key=lambda q: math.hypot(q["x"] - x, q["y"] - y)) if ST else None
    nm = st["name"] if st and math.hypot(st["x"] - x, st["y"] - y) < 900 else (t.get("name") or "").split(" ")[0]
    ex.append([round(x, 1), round(y, 1), t.get("ref") or "", nm])
json.dump({"bus": bus, "exit": ex, "src": "서울 열린데이터광장 버스정류소 위치정보 · OpenStreetMap 지하철 출입구"}, open(os.path.join(G, "data", "transit.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("정류소", len(bus), "출구", len(ex), sorted({(e[3], e[2]) for e in ex})[:40])
