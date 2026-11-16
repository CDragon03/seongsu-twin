# 건물 에너지 월별(2023-01~12): 2023-12 에 값이 있던 필지만 나머지 달을 받음(전기 2,783 · 가스 1,937 필지). 하루 한도에 걸리면 멈추고 다음 날 이어서.
# 받은 결과: ../data/energy/raw/<종류>_<년월>/<PNU>.json (fetch_energy.py 와 같은 모양). 끝나면 add_energy.py 로 data/energy.json 다시 만듦.
# 실행: python -I fetch_energy_months.py   → 마지막 줄에 "남은 달 N" (0 이면 다 받음)
import json, os, sys, time, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(G, "..", "data"); RAW = os.path.join(D, "energy", "raw")
KEY = open(os.path.join(D, "datagokr_key.txt"), encoding="utf-8-sig").read().strip()
OP = {"elec": "getBeElctyUsgInfo", "gas": "getBeGasUsgInfo"}; MONTHS = [f"2023{m:02d}" for m in range(1, 12)]
def has_data(kind):
    d = os.path.join(RAW, f"{kind}_202312"); return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json") and os.path.getsize(os.path.join(d, f)) > 4)
left = 0
for kind in ("elec", "gas"):
    pnus, limited = has_data(kind), False
    for ym in MONTHS:
        out = os.path.join(RAW, f"{kind}_{ym}"); os.makedirs(out, exist_ok=True); todo = [p for p in pnus if not os.path.exists(os.path.join(out, p + ".json"))]
        if not todo: continue
        if limited: left += 1; continue
        n = 0
        for p in todo:
            q = urllib.parse.urlencode({"serviceKey": KEY, "sigunguCd": p[:5], "bjdongCd": p[5:10], "platGbCd": "1" if p[10] == "2" else "0", "bun": p[11:15], "ji": p[15:19], "useYm": ym, "numOfRows": "10", "pageNo": "1", "_type": "json"})
            ok = False
            for t in range(3):
                try:
                    raw = urllib.request.urlopen(f"https://apis.data.go.kr/1613000/BldEngyHubService/{OP[kind]}?{q}", timeout=30).read().decode("utf-8", "replace")
                    if "LIMITED" in raw: raise RuntimeError("LIMITED")
                    j = json.loads(raw)
                    if j["response"]["header"]["resultCode"] != "00": raise RuntimeError(j["response"]["header"])
                    it = (j["response"]["body"].get("items") or {}).get("item") or []; it = it if isinstance(it, list) else [it]
                    json.dump([[x.get("useYm"), x.get("useQty")] for x in it], open(os.path.join(out, p + ".json"), "w")); ok = True; n += 1; break
                except Exception as e:
                    s = str(e)
                    if "LIMITED" in s or "429" in s: limited = True; break
                    time.sleep(3 + t * 4)
            if limited: break
            time.sleep(0.03)
        print(kind, ym, "받음", n, "/", len(todo), "(한도)" if limited else "", flush=True)
        if limited: left += 1
print("남은 달", left)
