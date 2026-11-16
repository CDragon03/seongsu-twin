# 지하철 시간표: 서울 열린데이터광장 「역코드로 지하철 열차 시간표 검색」(SearchSTNTimeTableByIDService) → data/timetable.json
# 역 3곳 × 평일/토요일/휴일 × 상행(내선)/하행(외선). 인증키: ../data/seoul_general_key.txt (화면에는 안 들어감). 실행: python -I build_timetable.py
import json, os, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__)); K = open(os.path.join(G, "..", "data", "seoul_general_key.txt"), encoding="utf-8-sig").read().strip()
ST = {"성수": "0211", "뚝섬": "0210", "서울숲": "1847"}; out = {"src": "서울 열린데이터광장 「역코드로 지하철 열차 시간표 검색」(OA-101)", "st": {}}
for nm, cd in ST.items():
    d = out["st"][nm] = {}
    for wk in "123":
        for io_ in "12":
            rows, s = [], 1
            while True:
                u = f"http://openapi.seoul.go.kr:8088/{K}/json/SearchSTNTimeTableByIDService/{s}/{s + 499}/{cd}/{wk}/{io_}/"
                j = json.loads(urllib.request.urlopen(u, timeout=30).read().decode("utf-8")).get("SearchSTNTimeTableByIDService") or {}
                r = j.get("row") or []; rows += r
                if len(r) < 500: break
                s += 500
            d[wk + io_] = [[x.get("ARRIVETIME") or x.get("LEFTTIME"), x.get("SUBWAYENAME") or x.get("SUBWAYSNAME"), x.get("EXPRESS_YN", "")] for x in rows]
            print(nm, wk, io_, len(rows), rows[0] if rows else "")
json.dump(out, open(os.path.join(G, "data", "timetable.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(round(os.path.getsize(os.path.join(G, "data", "timetable.json")) / 1024), "KB")
