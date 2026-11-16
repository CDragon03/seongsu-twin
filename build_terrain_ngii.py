# 화면 지형: 국토지리정보원 공개DEM(2025, 도엽 37705, 90m 격자, EPSG:5179, 건물 없는 땅 높이) → 100m 격자 data/terrain_ngii.json
# 화면에는 출발 지점 높이를 0 으로 둔 상대 높이(z)를 쓰고, 해발(ref + z)은 안내에만. 원본: ../data/dem_ngii/37705/37705.img (국토정보플랫폼 국토정보맵 → 공개DEM)
# 실행: python -I build_terrain_ngii.py
import json, math, os
import numpy as np, rasterio
from rasterio.warp import transform
from scipy.ndimage import gaussian_filter
G = os.path.dirname(os.path.abspath(__file__)); LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
r = rasterio.open(os.path.join(G, "..", "data", "dem_ngii", "37705", "37705.img")); A = r.read(1).astype(float)
c = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8"))
xs = [v for b in c["buildings"] for v in b["p"][0::2]] + [p[0] for p in c["ground2"]["corners"].values()]; ys = [v for b in c["buildings"] for v in b["p"][1::2]] + [p[1] for p in c["ground2"]["corners"].values()]
S = 100.0; x0, y0 = math.floor(min(xs) / S) * S - 200, math.floor(min(ys) / S) * S - 200; nx, ny = int((max(xs) + 200 - x0) / S) + 1, int((max(ys) + 200 - y0) / S) + 1
X = [x0 + i * S for j in range(ny) for i in range(nx)]; Y = [y0 + j * S for j in range(ny) for i in range(nx)]
E, N = transform("EPSG:4326", "EPSG:5179", [LON0 + x / KX for x in X], [LAT0 + y / KY for y in Y])
z = np.zeros(nx * ny)
for k, (e, n) in enumerate(zip(E, N)):
    cc, rr = ~r.transform * (e, n); cc -= 0.5; rr -= 0.5; i, j = int(math.floor(rr)), int(math.floor(cc)); fy, fx = rr - i, cc - j
    i = min(max(i, 0), A.shape[0] - 2); j = min(max(j, 0), A.shape[1] - 2)
    z[k] = A[i, j] * (1 - fx) * (1 - fy) + A[i, j + 1] * fx * (1 - fy) + A[i + 1, j] * (1 - fx) * fy + A[i + 1, j + 1] * fx * fy
z = gaussian_filter(z.reshape(ny, nx), sigma=0.6)   # 90m 계단 무늬만 다듬음(σ 60m)
z = np.maximum(z, 5.0)                               # 한강 수면 쪽으로 파인 값 막기
sx, sy = c["start"][0], c["start"][1]; ref = float(z[int(round((sy - y0) / S)), int(round((sx - x0) / S))])
out = {"x0": x0, "y0": y0, "step": S, "nx": nx, "ny": ny, "ref": round(ref, 1), "z": [round(float(v - ref), 2) for v in z.ravel()],
       "source": "국토지리정보원 공개DEM 2025(도엽 37705, 90m 격자) · 국토정보플랫폼 · 화면 높이 = 해발 − 출발 지점 해발"}
json.dump(out, open(os.path.join(G, "data", "terrain_ngii.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("격자", nx, ny, "출발 지점 해발", round(ref, 1), "상대 높이 범위", round(float(z.min() - ref), 1), round(float(z.max() - ref), 1), "백분위", np.percentile(z - ref, [5, 50, 95]).round(1))
