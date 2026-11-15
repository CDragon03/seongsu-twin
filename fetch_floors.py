# 건축물대장 층별개요(국토교통부 건축HUB getBrFlrOulnInfo)를 필지(PNU)마다 받아 ../data/flr_raw/<PNU>.json 에 보관(이미 받은 건 건너뜀)
# 인증키: ../data/datagokr_key.txt (공개 저장소 밖). 실행: python -I fetch_floors.py
import json, os, time, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(G, "..", "data"); OUT = os.path.join(D, "flr_raw"); os.makedirs(OUT, exist_ok=True)
KEY = open(os.path.join(D, "datagokr_key.txt"), encoding="utf-8-sig").read().strip()
info = json.load(open(os.path.join(G, "data", "bldg_info.json"), encoding="utf-8"))["b"]
pnus = sorted({r["pnu"] for r in info if r and r.get("pnu") and len(r["pnu"]) == 19})
print("필지", len(pnus))
URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrFlrOulnInfo"

def call(pnu, page):
    q = urllib.parse.urlencode({"serviceKey": KEY, "sigunguCd": pnu[:5], "bjdongCd": pnu[5:10], "platGbCd": "1" if pnu[10] == "2" else "0",
                                "bun": pnu[11:15], "ji": pnu[15:19], "numOfRows": "100", "pageNo": str(page), "_type": "json"})
    for t in range(4):
        try:
            j = json.loads(urllib.request.urlopen(URL + "?" + q, timeout=30).read().decode("utf-8"))
            h = j["response"]["header"]
            if h["resultCode"] != "00": raise RuntimeError(h)
            return j["response"]["body"]
        except Exception as e:
            err = e; time.sleep(2 + t * 3)
    raise err

done = calls = 0
for i, pnu in enumerate(pnus):
    f = os.path.join(OUT, pnu + ".json")
    if os.path.exists(f): continue
    items, page = [], 1
    while True:
        body = call(pnu, page); calls += 1
        it = (body.get("items") or {}) if isinstance(body.get("items"), dict) else {}
        it = it.get("item", [])
        items += it if isinstance(it, list) else [it]
        if len(items) >= int(body.get("totalCount") or 0) or not it: break
        page += 1; time.sleep(0.05)
    json.dump(items, open(f, "w", encoding="utf-8"), ensure_ascii=False); done += 1
    if done % 200 == 0: print(i + 1, "/", len(pnus), "호출", calls, flush=True)
    time.sleep(0.05)
print("새로 받은 필지", done, "호출", calls)
