# 성동구 불법주정차 단속 CCTV 위치(서울 열린데이터광장 OA-20475, TbOpendataFixedcctvSD) → city.json official.pcam
# 인증키: ../data/seoul_general_key.txt. 실행: python -I build_park_cctv.py
import json, math, os, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); K = open(os.path.join(G, "..", "data", "seoul_general_key.txt"), encoding="utf-8-sig").read().strip()
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
rows, s = [], 1
while True:
    j = json.loads(urllib.request.urlopen(f"http://openapi.seoul.go.kr:8088/{K}/json/TbOpendataFixedcctvSD/{s}/{s + 999}/", timeout=30).read().decode("utf-8"))["TbOpendataFixedcctvSD"]
    rows += j.get("row") or []
    if len(rows) >= int(j.get("list_total_count", 0)) or not j.get("row"): break
    s += 1000
print(len(rows), rows[0])
P = os.path.join(G, "data", "city.json"); c = json.load(open(P, encoding="utf-8"))
def ll(r):
    for la, lo in (("LAT", "LOT"), ("LATITUDE", "LONGITUDE"), ("WGS84_Y", "WGS84_X"), ("Y_CRDNT", "X_CRDNT"), ("YCRD", "XCRD")):
        if r.get(la) and r.get(lo): return float(r[la]), float(r[lo])
    return None
out = []
for r in rows:
    p = ll(r)
    if not p: continue
    la, lo = p; out.append([round((lo - LON0) * KX, 1), round((la - LAT0) * KY, 1), r.get("CRDN_BRNCH_NM") or r.get("FIX_CCTV_ADDR") or ""])
c.setdefault("official", {})["pcam"] = out; c["official"]["pcam_src"] = "서울 열린데이터광장 「서울특별시 성동구 불법주정차 단속 CCTV 위치정보」(OA-20475)"
json.dump(c, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":")); print("위치", len(out))
