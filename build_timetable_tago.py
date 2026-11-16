# 서울숲역(수인분당선) 시간표: 서울 열린데이터광장에 없어 국토교통부 (TAGO) 지하철정보(data.go.kr 15098554) GetSubwaySttnAcctoSchdulList 로 채움
# data/timetable.json 의 st["서울숲"] 을 같은 모양([시각, 행선지, 급행])으로 덮어씀. build_timetable.py 다음에 실행. 인증키: ../data/datagokr_key.txt
import json, os, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); K = open(os.path.join(G, "..", "data", "datagokr_key.txt"), encoding="utf-8-sig").read().strip()
P = os.path.join(G, "data", "timetable.json"); out = json.load(open(P, encoding="utf-8")); d = out["st"]["서울숲"] = {}
for wk, dc in (("1", "01"), ("2", "02"), ("3", "03")):
    for io_, ud in (("1", "U"), ("2", "D")):
        rows, pg = [], 1
        while True:
            q = urllib.parse.urlencode({"serviceKey": K, "subwayStationId": "MTRKRK1K211", "dailyTypeCode": dc, "upDownTypeCode": ud, "_type": "json", "numOfRows": "200", "pageNo": str(pg)})
            b = json.loads(urllib.request.urlopen("https://apis.data.go.kr/1613000/SubwayInfo/GetSubwaySttnAcctoSchdulList?" + q, timeout=30).read().decode("utf-8"))["response"]["body"]
            it = (b.get("items") or {}).get("item") or []; it = it if isinstance(it, list) else [it]; rows += it
            if len(rows) >= int(b.get("totalCount", 0)) or not it: break
            pg += 1
        f = lambda t: f"{t[0:2]}:{t[2:4]}:{t[4:6]}"
        L = sorted([[f(x.get("arrTime") or x.get("depTime")), x.get("endSubwayStationNm", ""), ""] for x in rows], key=lambda r: (r[0] < "03", r[0]))
        d[wk + io_] = L; print(wk, ud, len(L), L[:2])
out["src_bundang"] = "서울숲(수인분당선): 국토교통부 (TAGO) 지하철정보(공공데이터포털 15098554)"
json.dump(out, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
