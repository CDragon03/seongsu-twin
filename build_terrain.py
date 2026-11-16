# 화면 지형용 높이 격자(20m) → game/data/terrain.json + 미리보기 ../data/terrain_preview.png
# 원본: AWS 공개 지형 타일(Terrarium, Mapzen/Tilezen. 한국 구간은 SRTM·NASADEM 계열 30m급, 도시는 건물 높이가 일부 섞임) → ../data/dem_tiles/15_x_y.png (없으면 받음)
# 건물 잡음: 최솟값 필터(120m) 로 바닥 쪽을 고르고 → 가우시안(σ 60m) 으로 부드럽게. 한강·중랑천 수면은 강변 높이로 채움(화면에선 물이 덮음)
# 실행: python -I build_terrain.py
import json, math, os, urllib.request
import numpy as np
from PIL import Image
from scipy.ndimage import minimum_filter, gaussian_filter
G = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(G, "..", "data", "dem_tiles"); os.makedirs(T, exist_ok=True)
LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0; Z = 15
c = json.load(open(os.path.join(G, "data", "city.json"), encoding="utf-8"))
xs = [v for b in c["buildings"] for v in b["p"][0::2]]; ys = [v for b in c["buildings"] for v in b["p"][1::2]]
for p in c["ground2"]["corners"].values(): xs.append(p[0]); ys.append(p[1])
S = 20.0; x0, y0 = math.floor(min(xs) / S) * S - 200, math.floor(min(ys) / S) * S - 200; x1, y1 = max(xs) + 200, max(ys) + 200
nx, ny = int((x1 - x0) / S) + 1, int((y1 - y0) / S) + 1
def tile_of(lat, lon): n = 2 ** Z; fx = (lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n; return fx, fy
tiles = {}
def get(tx, ty):
    if (tx, ty) in tiles: return tiles[(tx, ty)]
    f = os.path.join(T, f"{Z}_{tx}_{ty}.png")
    if not os.path.exists(f): open(f, "wb").write(urllib.request.urlopen(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{tx}/{ty}.png", timeout=60).read())
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float64); tiles[(tx, ty)] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768; return tiles[(tx, ty)]
g = np.zeros((ny, nx))
for j in range(ny):
    for i in range(nx):
        x, y = x0 + i * S, y0 + j * S; fx, fy = tile_of(LAT0 + y / KY, LON0 + x / KX); tx, ty = int(fx), int(fy)
        g[j, i] = get(tx, ty)[min(255, int((fy - ty) * 256)), min(255, int((fx - tx) * 256))]
raw = g.copy()
f = minimum_filter(g, size=7)          # 140m 안 가장 낮은 값 = 건물 높이를 걷어낸 바닥 추정
f = gaussian_filter(f, sigma=3)       # σ 60m
f = np.maximum(f, 5.0)                # 수면 아래로 파인 값 막기
out = {"x0": x0, "y0": y0, "step": S, "nx": nx, "ny": ny, "z": [round(float(v), 1) for v in f.ravel()],
       "source": "지형: AWS 공개 지형 타일(Terrarium · SRTM/NASADEM 계열 30m급) → 최솟값 필터 140m + 가우시안 60m 로 건물 잡음 걷어냄 · 오차 수 m"}
json.dump(out, open(os.path.join(G, "data", "terrain.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("격자", nx, ny, "범위", x0, y0, x1, y1, "원본", round(raw.min(), 1), round(raw.max(), 1), "정리", round(f.min(), 1), round(f.max(), 1), "백분위 5/50/95", np.percentile(f, [5, 50, 95]).round(1))
def at(x, y): i, j = int((x - x0) / S), int((y - y0) / S); return round(float(f[j, i]), 1)
for nm in ["대림창고", "서울숲 코오롱디지털타워1차", "디올 성수"]:
    L = [b for b in c["buildings"] if b.get("n") == nm]
    if L: p = L[0]["p"]; print(nm, at(sum(p[0::2]) / len(p[0::2]), sum(p[1::2]) / len(p[1::2])))
for nm, x, y in [("성수역 부근", 120, -40), ("뚝섬역 부근", -400, -250)]: print(nm, at(x, y))
# 미리보기: 음영 기복 + 등고선 2m
dy, dx = np.gradient(f, S); sh = np.clip(0.6 + (-dx * 0.7 + dy * 0.7) * 3, 0, 1)
col = np.clip((f - f.min()) / max(1, f.max() - f.min()), 0, 1)
rgb = np.stack([0.25 + 0.6 * col, 0.45 + 0.35 * col, 0.35 + 0.15 * col], -1) * sh[..., None]
cont = (np.floor(f / 2) != np.floor(np.roll(f, 1, 0) / 2)) | (np.floor(f / 2) != np.floor(np.roll(f, 1, 1) / 2)); rgb[cont] = rgb[cont] * 0.55
im = Image.fromarray((np.flipud(rgb) * 255).astype(np.uint8)).resize((nx * 3, ny * 3), Image.NEAREST); im.save(os.path.join(G, "..", "data", "terrain_preview.png"))
