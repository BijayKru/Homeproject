"""Background for the section that sits directly under emerald_necklace_commercial_16x9.mp4.

Built from the same champagne-satin backdrop formula as the video (render_16x9.py), so the
top edge continues the video's bottom edge, then settles into its own soft spotlight.

Writes section_bg.jpg / .webp (1920 x 1080 + OVERLAP rows; the first OVERLAP rows are the
video's own bottom rows and are used by the CSS fade that hides the seam).
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, VH = 1920, 1080          # video frame
SH = 1280                   # section height (reference)
OVERLAP = 96                # rows of the video bottom repeated at the top of the image
T = 10.0                    # light-shaft phase = the video's final frame

ys = np.arange(VH - OVERLAP, VH + SH, dtype=np.float32)
XX, YY = np.meshgrid(np.arange(W, dtype=np.float32), ys)

def shafts(x, y, t, fall):
    u = x * 0.80 + y * 0.60 - 28 * t
    s = (0.55 * np.exp(-((np.mod(u + 300, 900) - 450) / 120) ** 2)
         + 0.35 * np.exp(-((np.mod(u + 40, 1300) - 650) / 70) ** 2)
         - 0.30 * np.exp(-((np.mod(u + 620, 1100) - 550) / 160) ** 2))
    return (s * fall * 22)[..., None] * np.array([1.0, 0.92, 0.82], np.float32)

def satin(r):
    k = np.clip(r, 0, 1.4) ** 1.5
    return np.stack([233 - 42 * k, 206 - 50 * k, 186 - 56 * k], -1)

# 1) the video's own backdrop, extended (exactly what render_16x9.py draws at t = 10)
rv = np.sqrt(((XX - W * 0.48) / (W * 0.62)) ** 2 + ((YY - VH * 0.50) / (VH * 0.85)) ** 2)
fall_v = np.clip(1.15 - (XX / W) * 0.7 - (YY / VH) * 0.35, 0, 1)
video_bg = satin(rv) + shafts(XX, YY, T, fall_v)

# 2) the section's own set: same satin, spotlight centred behind the text, light from top-left
yl = YY - VH
rs = np.sqrt(((XX - W * 0.50) / (W * 0.70)) ** 2 + ((yl - SH * 0.34) / (SH * 1.05)) ** 2)
fall_s = np.clip(1.05 - (XX / W) * 0.7 - (np.maximum(yl, 0) / SH) * 0.45, 0, 1)
section_bg = satin(rs) + shafts(XX, yl + 380, T, fall_s * 0.8)

w = np.clip(yl / 260, 0, 1); w = (w * w * (3 - 2 * w))[..., None]
img = video_bg * (1 - w) + section_bg * w
FLOOR = np.array([213, 183, 160], np.float32)          # = CSS --champagne, page colour below the image
fb = np.clip((yl - (SH - 360)) / 360, 0, 1); fb = (fb * fb * (3 - 2 * fb))[..., None]
img = img * (1 - fb) + FLOOR * fb
img += np.random.default_rng(3).normal(0, 1.6, img.shape[:2] + (1,)).astype(np.float32)   # same film grain
im = Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8))
im.save(os.path.join(HERE, "section_bg.jpg"), quality=92, optimize=True, progressive=True)
im.save(os.path.join(HERE, "section_bg.webp"), quality=90, method=6)
a = np.asarray(im, np.float32)
print("size", im.size, "| seam row (L,C,R):", [a[OVERLAP, x - 40:x + 40].mean(0).round().tolist() for x in (40, 960, 1880)])
print("section centre:", a[OVERLAP + 450, 920:1000].mean(0).round().tolist(), "| bottom:", a[-10, 920:1000].mean(0).round().tolist())
