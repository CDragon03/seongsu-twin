# 침수 시뮬레이션용 지형 높이 격자(10m) → game/data/dem.json
# 원본: AWS 공개 지형 타일(Terrarium, Mapzen/Tilezen · 한국은 SRTM 등 30m급, 건물 높이 일부 섞임) data/dem_tiles/
# 건물 높이가 섞인 잡음을 줄이려고 하천 값 제외 → 중앙값 → 가우시안(σ 30m) 평활
# 실행: python -I game/build_dem.py
import os, json, math
import numpy as np
from PIL import Image
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(D, "data", "dem_tiles")
LAT0, LON0 = 37.543, 127.0535
KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
Z = 15
tiles = {}
for f in os.listdir(T):
    z, x, y = map(int, f[:-4].split("_"))
    a = np.asarray(Image.open(os.path.join(T, f)).convert("RGB")).astype(np.float64)
    tiles[(x, y)] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
def elev(lat, lon):
    n = 2 ** Z; fx = (lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    tx, ty = int(fx), int(fy); px, py = (fx - tx) * 256, (fy - ty) * 256
    t = tiles.get((tx, ty))
    if t is None: return np.nan
    i, j = min(255, int(py)), min(255, int(px)); return t[i, j]
city = json.load(open(os.path.join(D, "game", "data", "city.json"), encoding="utf-8"))
xs = [v for b in city["buildings"] for v in b["p"][0::2]]; ys = [v for b in city["buildings"] for v in b["p"][1::2]]
S = 10.0
x0, y0 = math.floor(min(xs) / S) * S - 50, math.floor(min(ys) / S) * S - 50
nx, ny = int((max(xs) + 50 - x0) / S) + 1, int((max(ys) + 50 - y0) / S) + 1
g = np.full((ny, nx), np.nan)
for j in range(ny):
    for i in range(nx):
        x, y = x0 + i * S, y0 + j * S
        g[j, i] = elev(LAT0 + y / KY, LON0 + x / KX)
g[(g < 8) | (g > 45)] = np.nan   # 하천 수면·튀는 값 제외
med = np.nanmedian(g)
# 3x3 중앙값 → 빈칸 채움 → 가우시안
from scipy.ndimage import median_filter, gaussian_filter
f = np.where(np.isnan(g), med, g)
f = median_filter(f, size=5)
f = gaussian_filter(f, sigma=3)
f = np.maximum(f, np.percentile(f, 3))   # 가장 낮은 3%(움푹한 잡음)는 평평하게
out = {"x0": x0, "y0": y0, "step": S, "nx": nx, "ny": ny, "z": [round(float(v), 2) for v in f.ravel()],
       "source": "지형: AWS 공개 지형 타일(Terrarium · SRTM 등 30m급) 평활 · 건물 높이 일부 섞여 수 m 오차"}
json.dump(out, open(os.path.join(D, "game", "data", "dem.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(nx, ny, round(float(f.min()), 1), round(float(f.max()), 1), np.percentile(f, [5, 50, 95]).round(1))
