# HUD(화면 가장자리 그래프)용 작은 요약: 건물 주용도·업종 분포·전기 사용량 상위 6곳 → data/hud_stats.json
# 원자료: data/bldg_info.json(건물통합정보) · data/stores.json(상가정보) · data/energy.json(건축HUB). 건물·업체·에너지를 다시 만들면 이것도 다시. 실행: python -I build_hud_stats.py
import collections, json, os
G = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(G, "data")
I = json.load(open(os.path.join(D, "bldg_info.json"), encoding="utf-8"))["b"]; S = json.load(open(os.path.join(D, "stores.json"), encoding="utf-8"))["b"]
E = json.load(open(os.path.join(D, "energy.json"), encoding="utf-8"))["b"]; C = json.load(open(os.path.join(D, "city.json"), encoding="utf-8"))["buildings"]
def top(cnt, n):
    L = cnt.most_common(); head = L[:n]; rest = sum(v for _, v in L[n:]); return [[k, v] for k, v in head] + ([["그 밖", rest]] if rest else [])
use = collections.Counter();
for d in I:
    if d: use[(d.get("use") or "미상").replace("제1종근린생활시설", "1종근생").replace("제2종근린생활시설", "2종근생")] += 1
cat = collections.Counter(s[1] for v in S.values() for s in v)
bypnu = {}
for i, d in enumerate(I):
    if d and d.get("pnu"): bypnu.setdefault(d["pnu"], []).append(i)
def name(p):
    ix = bypnu.get(p, [None])[0]; d = I[ix] if ix is not None else {}
    nm = d.get("nm") or (C[ix].get("n") if ix is not None else "") or ((S.get(str(ix)) or [[""]])[0][0]) or d.get("road") or d.get("addr") or p
    return nm.replace("서울특별시 ", "").replace("성동구 ", "").replace("광진구 ", "").split(" (")[0]
etop = sorted([(v["e"][1], p, v["e"][0]) for p, v in E.items() if "e" in v], reverse=True)[:6]
out = {"bldg_n": sum(1 for d in I if d), "store_n": sum(len(v) for v in S.values()), "use": top(use, 5), "cat": top(cat, 5),
       "elec": [[name(p), kwh, ym] for kwh, p, ym in etop],
       "src": "건물통합정보(AL_D010) · 소상공인 상가(상권)정보 · 건축HUB 건물에너지"}
json.dump(out, open(os.path.join(D, "hud_stats.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps(out, ensure_ascii=False)[:600])
