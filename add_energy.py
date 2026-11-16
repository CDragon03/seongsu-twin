# 받아 둔 건물 에너지(../data/energy/raw/<종류>_<년월>/<PNU>.json)를 data/energy.json 으로: {pnu: {"e": [년월, kWh], "g": [년월, 양]}}
# 사용량은 지번(필지) 단위라 한 필지에 건물이 여러 동이면 필지 전체 값임. 실행: python -I add_energy.py
import glob, json, os
G = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(G, "..", "data", "energy", "raw")
out, cnt = {}, {}
for d in sorted(glob.glob(os.path.join(RAW, "*_*"))):
    kind, ym = os.path.basename(d).split("_"); k = "e" if kind == "elec" else "g"
    for f in glob.glob(os.path.join(d, "*.json")):
        v = json.load(open(f))
        if not v: continue
        qty = sum(float(x[1] or 0) for x in v if x[1] is not None)
        if qty <= 0: continue
        out.setdefault(os.path.basename(f)[:-5], {})[k] = [ym, round(qty)]; cnt[k] = cnt.get(k, 0) + 1
json.dump({"src": "국토교통부 건축HUB 건물에너지정보 서비스(지번 단위 월 사용량, 전기 kWh)", "b": out}, open(os.path.join(G, "data", "energy.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("필지", len(out), cnt)
