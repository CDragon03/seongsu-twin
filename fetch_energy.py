# 건물 에너지: 국토교통부 건축HUB 건물에너지정보 서비스(getBeElctyUsgInfo 전기 kWh / getBeGasUsgInfo 가스) → ../data/energy/raw/<종류>_<년월>/<PNU>.json
# 한 번에 한 필지·한 달이라 하루 한도 안에서 나눠 받음(이미 받은 건 건너뜀). 인증키: ../data/datagokr_key.txt
# 실행: python -I fetch_energy.py elec 202312   /   python -I fetch_energy.py gas 202312
import json, os, sys, time, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(G, "..", "data")
KIND, YM = sys.argv[1], sys.argv[2]; OP = {"elec": "getBeElctyUsgInfo", "gas": "getBeGasUsgInfo"}[KIND]
KEY = open(os.path.join(D, "datagokr_key.txt"), encoding="utf-8-sig").read().strip(); OUT = os.path.join(D, "energy", "raw", f"{KIND}_{YM}"); os.makedirs(OUT, exist_ok=True)
info = json.load(open(os.path.join(G, "data", "bldg_info.json"), encoding="utf-8"))["b"]
pnus = sorted({r["pnu"] for r in info if r and r.get("pnu") and len(r["pnu"]) == 19})
n = calls = 0
for p in pnus:
    f = os.path.join(OUT, p + ".json")
    if os.path.exists(f): continue
    q = urllib.parse.urlencode({"serviceKey": KEY, "sigunguCd": p[:5], "bjdongCd": p[5:10], "platGbCd": "1" if p[10] == "2" else "0", "bun": p[11:15], "ji": p[15:19], "useYm": YM, "numOfRows": "10", "pageNo": "1", "_type": "json"})
    for t in range(3):
        try:
            j = json.loads(urllib.request.urlopen(f"https://apis.data.go.kr/1613000/BldEngyHubService/{OP}?{q}", timeout=30).read().decode("utf-8")); calls += 1
            if j["response"]["header"]["resultCode"] != "00": raise RuntimeError(j["response"]["header"])
            it = (j["response"]["body"].get("items") or {}).get("item") or []; it = it if isinstance(it, list) else [it]
            json.dump([[x.get("useYm"), x.get("useQty")] for x in it], open(f, "w")); n += 1; break
        except Exception as e:
            if "LIMITED" in str(e) or "429" in str(e): print("하루 한도", calls); sys.exit(0)
            time.sleep(3 + t * 4)
    if n % 500 == 0 and n: print(n, "/", len(pnus), flush=True)
    time.sleep(0.04)
print("받음", n, "호출", calls)
