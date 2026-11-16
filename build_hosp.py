# 응급의료기관 위치(서울 열린데이터광장 「서울시 병의원 위치 정보」 TbHospitalInfo, 국립중앙의료원 자료) → city.json official.er
# 응급의료기관 분류(DUTYEMCLS)가 G099(응급의료기관 이외)가 아닌 곳만, 응급실 운영(DUTYERYN=1). 인증키: ../data/seoul_general_key.txt
# 실행: python -I build_hosp.py
import json, math, os, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); K = open(os.path.join(G, "..", "data", "seoul_general_key.txt"), encoding="utf-8-sig").read().strip()
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
rows, s = [], 1
while True:
    j = json.loads(urllib.request.urlopen(f"http://openapi.seoul.go.kr:8088/{K}/json/TbHospitalInfo/{s}/{s + 999}/", timeout=60).read().decode("utf-8"))["TbHospitalInfo"]
    rows += j.get("row") or []
    if len(rows) >= int(j.get("list_total_count", 0)) or not j.get("row"): break
    s += 1000
er = [r for r in rows if (r.get("DUTYEMCLS") or "G099") != "G099" and str(r.get("DUTYERYN")) == "1" and r.get("WGS84LAT") and r.get("WGS84LON")]
out = []
for r in er:
    la, lo = float(r["WGS84LAT"]), float(r["WGS84LON"]); x, y = (lo - LON0) * KX, (la - LAT0) * KY
    out.append([round(x, 1), round(y, 1), r["DUTYNAME"], r.get("DUTYEMCLSNAME") or "", r.get("DUTYTEL3") or r.get("DUTYTEL1") or "", round(math.hypot(x, y))])
out.sort(key=lambda o: o[5])
P = os.path.join(G, "data", "city.json"); c = json.load(open(P, encoding="utf-8"))
c.setdefault("official", {})["er"] = [o[:5] for o in out[:12]]
c["official"]["er_src"] = "서울 열린데이터광장 「서울시 병의원 위치 정보」(TbHospitalInfo, 국립중앙의료원) 중 응급의료기관 · 응급실 운영"
json.dump(c, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("전체", len(rows), "응급의료기관", len(er))
for o in out[:12]: print(o)
