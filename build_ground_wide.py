# 넓은 바닥 사진: 정사영상 한 장(성동083) 전체를 1m/화소로 → game/data/ground_wide.webp + city.json "ground2"(네 모서리 지역좌표)
# 가운데 0.5m 사진(ground.webp)은 그대로 두고, 그 밖(한강 둔치·강변북로·다리·건너편)을 이걸로 깖. 실행: python -I build_ground_wide.py
import json, math, os, numpy as np, rasterio
from PIL import Image
from pyproj import Transformer
G = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(G, "..", "data", "ortho")
g = json.load(open(os.path.join(D, "georef.json"))); LAT0, LON0 = 37.543, 127.0535; KX = math.cos(math.radians(LAT0)) * 111320.0; KY = 110540.0
inv = Transformer.from_crs(5186, 4326, always_xy=True)
RES = 1.0; r = rasterio.open(os.path.join(D, "ortho_2025_37705083.tif")); W, H = int(r.width * g["gsd"] / RES), int(r.height * g["gsd"] / RES)
a = r.read(out_shape=(3, H, W)); Image.fromarray(np.moveaxis(a, 0, -1)).save(os.path.join(G, "data", "ground_wide.webp"), "WEBP", quality=80, method=6)
loc = lambda x, y: [round(v, 2) for v in (lambda lo, la: ((lo - LON0) * KX, (la - LAT0) * KY))(*inv.transform(x, y))]
x0, x1, y0, y1 = g["left"], g["left"] + r.width * g["gsd"], g["top"] - r.height * g["gsd"], g["top"]
P = os.path.join(G, "data", "city.json"); c = json.load(open(P, encoding="utf-8"))
c["ground2"] = {"img": "ground_wide.webp", "corners": {"sw": loc(x0, y0), "se": loc(x1, y0), "ne": loc(x1, y1), "nw": loc(x0, y1)}, "res_m": RES, "source": "국토지리정보원 정사영상 2025 성동083(37705083)"}
json.dump(c, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(W, H, c["ground2"]["corners"], round(os.path.getsize(os.path.join(G, "data", "ground_wide.webp")) / 1048576, 2), "MB")
