# 성수 안전 지도 추가 자료 받기 → ../../data/safety/
#  · AED: 서울 열린데이터광장 tbEmgcAedInfo(국립중앙의료원 원본 서울 재배포, 매월)
#  · 노인여가복지시설(경로당 등): fcltOpenInfo_OWI
#  · 소방용수시설·비상소화장치·노인의료복지시설: 열린데이터광장 파일(내려받기 함수와 같은 요청)
# 인증키: ../../data/seoul_general_key.txt (화면 쪽에 보내지 않음). 실행: python -I map/fetch_safety.py
import json, os, urllib.request, urllib.parse
G = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = os.path.join(G, "..", "data", "safety"); os.makedirs(D, exist_ok=True)
K = open(os.path.join(G, "..", "data", "seoul_general_key.txt"), encoding="utf-8-sig").read().strip()
def api(sv):
    rows, s = [], 1
    while True:
        j = json.loads(urllib.request.urlopen(f"http://openapi.seoul.go.kr:8088/{K}/json/{sv}/{s}/{s + 999}/", timeout=90).read().decode("utf-8"))
        if sv not in j: print(sv, j); break
        r = j[sv]["row"]; rows += r; n = j[sv]["list_total_count"]; s += 1000
        if s > n: break
    json.dump(rows, open(os.path.join(D, sv + ".json"), "w", encoding="utf-8"), ensure_ascii=False); print(sv, len(rows), "건", list(rows[0].keys()) if rows else "")
def file(inf, seq, name, iseq=1):
    req = urllib.request.Request("https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false", data=urllib.parse.urlencode({"infId": inf, "seqNo": "", "seq": seq, "infSeq": iseq}).encode())
    b = urllib.request.urlopen(req, timeout=120).read(); open(os.path.join(D, name), "wb").write(b); print(name, len(b), "바이트")
import sys
if "--files" not in sys.argv: api("tbEmgcAedInfo"); api("fcltOpenInfo_OWI")
file("OA-21071", 1, "emergency_hydrant.xlsx", 3); file("OA-22198", 2, "elder_medical.xlsx")
# 어린이집(서울 전체 → 성동구만 쓰게 저장 후 거름) · 성동구 유치원
if "--kids" in sys.argv: api("ChildCareInfo"); api("childSchoolInfo_sd")
