# 받아 둔 층별개요(../data/flr_raw/<PNU>.json)를 data/bldg_info.json 건물마다 붙임: fl = [[층, 용도, 면적㎡], ...], road = 도로명주소
# 한 필지에 대장 건물(표제부)이 여럿이면 동 이름·건물명·층수가 맞는 것을 고르고, 가려낼 수 없으면 붙이지 않음
# 실행: python -I add_floors.py   (build_bldg_info.py → fetch_floors.py → add_floors.py 순서)
import json, os, re, collections
G = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(G, "..", "data", "flr_raw"); P = os.path.join(G, "data", "bldg_info.json")
J = json.load(open(P, encoding="utf-8")); info = J["b"]
norm = lambda s: re.sub(r"[\s()·.\-]", "", str(s or "")).replace("제", "").replace("동", "")
st = collections.Counter()
by_pnu = collections.defaultdict(list)
for i, r in enumerate(info):
    if r and r.get("pnu"): by_pnu[r["pnu"]].append(i)
for pnu, idx in by_pnu.items():
    f = os.path.join(RAW, pnu + ".json")
    if not os.path.exists(f): st["자료 없음"] += len(idx); continue
    R = json.load(open(f, encoding="utf-8"))
    if not R: st["층별개요 없음"] += len(idx); continue
    groups = collections.defaultdict(list)
    for x in R: groups[x.get("mgmBldrgstPk")].append(x)
    for i in idx:
        r = info[i]; r.pop("fl", None)
        if len(groups) == 1: g = next(iter(groups.values()))
        else:
            sc = []
            for pk, g in groups.items():
                dn, bn = norm(g[0].get("dongNm")), norm(g[0].get("bldNm"))
                up = max([x["flrNo"] for x in g if str(x.get("flrGbCd")) == "20"] or [0]); dn_ = max([x["flrNo"] for x in g if str(x.get("flrGbCd")) == "10"] or [0])
                s = (3 if r.get("dong") and dn and norm(r["dong"]) == dn else 0) + (1 if r.get("nm") and bn and norm(r["nm"]) == bn else 0) + (2 if r.get("fu") and up == r["fu"] else 0) + (1 if (r.get("fb") or 0) == dn_ else 0)
                sc.append((s, pk))
            sc.sort(reverse=True)
            if sc[0][0] < 3 or (len(sc) > 1 and sc[1][0] == sc[0][0]): st["여러 동이라 못 가림"] += 1; continue
            g = groups[sc[0][1]]
        fl = []
        for x in g:
            gb = str(x.get("flrGbCd")); n = int(x.get("flrNo") or 0)
            k = -n if gb == "10" else n if gb == "20" else 100 + n   # 30 = 옥탑
            use = (x.get("etcPurps") or "").strip() or (x.get("mainPurpsCdNm") or "").strip()
            fl.append([k, use + ("(부속)" if str(x.get("mainAtchGbCd")) == "1" else ""), round(float(x.get("area") or 0), 1)])
        fl.sort(key=lambda t: -t[0]); r["fl"] = fl
        road = (g[0].get("newPlatPlc") or "").strip()
        if road: r["road"] = road
        st["붙임"] += 1
J["src_fl"] = "국토교통부 건축HUB 건축물대장정보 서비스 층별개요(getBrFlrOulnInfo)"
json.dump(J, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(dict(st), "크기", round(os.path.getsize(P) / 1048576, 2), "MB")
