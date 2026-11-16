# 실시간 자료 모으기 → live.json
#  · 서울 실시간 도시데이터(citydata): 성수카페거리·서울숲공원·뚝섬역 — 혼잡도·인구·연령·12시간 예측·도로 소통·날씨·주차·따릉이·사고 통제
#  · 서울 실시간 대기(RealtimeCityAir): 성동구 측정소
#  · 서울 공영주차장 안내(GetParkInfo): 성동구 127곳(위치·면수·요금)
# 인증키: 환경변수 SEOUL_KEY(깃허브 액션 비밀값) 또는 ../data/seoul_general_key.txt. 실행: python -I fetch_live.py [출력 경로]
import json, os, sys, time, urllib.parse, urllib.request
G = os.path.dirname(os.path.abspath(__file__))
K = os.environ.get("SEOUL_KEY") or open(os.path.join(G, "..", "data", "seoul_general_key.txt"), encoding="utf-8-sig").read().strip()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(G, "data", "live.json")
def get(path, tries=3):
    for t in range(tries):
        try: return json.loads(urllib.request.urlopen(f"http://openapi.seoul.go.kr:8088/{K}/json/{path}", timeout=60).read().decode("utf-8"))
        except Exception as e: err = e; time.sleep(3)
    print("실패", path.split("/")[0], err); return {}
num = lambda v: float(v) if v not in (None, "", "-") else None
out = {"t": time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + (9 * 3600 if time.timezone == 0 else 0))), "areas": {}, "src": "서울 열린데이터광장 실시간 도시데이터·실시간 대기환경·공영주차장 안내"}
for a in ["성수카페거리", "서울숲공원", "뚝섬역"]:
    c = get("citydata/1/5/" + urllib.parse.quote(a)).get("CITYDATA")
    if not c: continue
    p = (c.get("LIVE_PPLTN_STTS") or [{}])[0]; r = (c.get("ROAD_TRAFFIC_STTS") or {}).get("AVG_ROAD_DATA") or {}; w = (c.get("WEATHER_STTS") or [{}])[0]
    o = {"lvl": p.get("AREA_CONGEST_LVL"), "msg": p.get("AREA_CONGEST_MSG"), "min": num(p.get("AREA_PPLTN_MIN")), "max": num(p.get("AREA_PPLTN_MAX")), "time": p.get("PPLTN_TIME"),
         "male": num(p.get("MALE_PPLTN_RATE")), "ages": [num(p.get(f"PPLTN_RATE_{k}")) for k in (0, 10, 20, 30, 40, 50, 60, 70)], "resnt": num(p.get("RESNT_PPLTN_RATE")),
         "fcst": [[f.get("FCST_TIME"), f.get("FCST_CONGEST_LVL"), num(f.get("FCST_PPLTN_MIN")), num(f.get("FCST_PPLTN_MAX"))] for f in (p.get("FCST_PPLTN") or [])],
         "road": {"idx": r.get("ROAD_TRAFFIC_IDX"), "spd": r.get("ROAD_TRAFFIC_SPD"), "msg": r.get("ROAD_MSG"), "time": r.get("ROAD_TRAFFIC_TIME")},
         "wx": {"temp": num(w.get("TEMP")), "hum": num(w.get("HUMIDITY")), "pm10": num(w.get("PM10")), "pm25": num(w.get("PM25")), "air": w.get("AIR_IDX"), "pcp": w.get("PCP_MSG"), "pty": w.get("PRECPT_TYPE"), "pre": w.get("PRECIPITATION"), "sky": ((w.get("FCST24HOURS") or [{}])[0] or {}).get("SKY_STTS"), "time": w.get("WEATHER_TIME")},
         "prk": [[q.get("PRK_NM"), num(q.get("CPCTY")), num(q.get("CUR_PRK_CNT")), num(q.get("LAT")), num(q.get("LNG")), q.get("CUR_PRK_TIME")] for q in (c.get("PRK_STTS") or [])],
         "bike": [[q.get("SBIKE_SPOT_NM"), num(q.get("SBIKE_PARKING_CNT")), num(q.get("SBIKE_RACK_CNT")), num(q.get("SBIKE_X")), num(q.get("SBIKE_Y"))] for q in (c.get("SBIKE_STTS") or [])],
         "acdnt": [[q.get("ACDNT_TYPE"), q.get("ACDNT_DTYPE"), q.get("ACDNT_INFO"), num(q.get("ACDNT_X")), num(q.get("ACDNT_Y")), q.get("ACDNT_OCCR_DT"), q.get("EXP_CLR_DT")] for q in (c.get("ACDNT_CNTRL_STTS") or []) if q.get("ACDNT_INFO")],
         "cmrcl": {"lvl": (c.get("LIVE_CMRCL_STTS") or {}).get("AREA_CMRCL_LVL"), "pay": num((c.get("LIVE_CMRCL_STTS") or {}).get("AREA_SH_PAYMENT_CNT")), "time": (c.get("LIVE_CMRCL_STTS") or {}).get("CMRCL_TIME")}}
    out["areas"][a] = o
air = [r for r in (get("RealtimeCityAir/1/30/").get("RealtimeCityAir") or {}).get("row", []) if r.get("MSRSTN_NM") == "성동구"]
if air: r = air[0]; out["air"] = {"pm10": r.get("PM"), "pm25": r.get("FPM"), "o3": r.get("OZON"), "no2": r.get("NTDX"), "grade": r.get("CAI_GRD"), "idx": r.get("CAI_IDX"), "main": r.get("CRST_SBSTN"), "time": r.get("MSRMT_DT")}
pk = (get("GetParkInfo/1/200/" + urllib.parse.quote("성동구")).get("GetParkInfo") or {}).get("row", [])
seen = set(); out["park"] = []
for r in pk:
    if r.get("PKLT_CD") in seen or not r.get("LAT"): continue
    seen.add(r.get("PKLT_CD")); out["park"].append([r.get("PKLT_NM"), r.get("ADDR"), r.get("PKLT_KND_NM"), num(r.get("TPKCT")), num(r.get("LAT")), num(r.get("LOT")), r.get("CHGD_FREE_NM"), num(r.get("PRK_CRG")), num(r.get("PRK_HM"))])
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(out["t"], {k: v.get("lvl") for k, v in out["areas"].items()}, "주차장", len(out["park"]), "대기", (out.get("air") or {}).get("grade"))
