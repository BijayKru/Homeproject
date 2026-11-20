"""'Choose Your Diamond Shape' wheel animation - 1920x1080, 7.5 s seamless loop.

A cream ring turns carrying six loose diamonds. Heart, Emerald cut and Oval take turns:
each leaves the ring, flies to the centre and becomes its ring photo (with labels) while its
description is revealed on the left. After ~2 s it flies back and the next one comes in.

Usage: python3 render_shapes.py OUT.mp4 [t1 t2 ...]   (times => preview JPGs)
"""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

UP = os.environ.get("UPLOADS", "/root/.claude/uploads/13bdc3d8-f30d-5841-978c-ae76c1bd629a/")
CUTS = os.environ.get("SHAPE_CUTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "shape_assets/"))
IMG = {"heart": "950f72e6-image.png", "emerald": "6c435b91-image.png", "oval": "d0b0a508-image.png"}
W0, H0 = 1672, 941                 # native infographic size (composited here, upscaled at the end)
OUT_W, OUT_H, FPS = 1920, 1080, 30
LOOP = 7.5
CYCLE = LOOP / 3
OMEGA = 360.0 / LOOP               # wheel deg/s (clockwise) -> seamless loop
C = np.array([1155.0, 466.0])      # ring centre
R_IN, R_OUT, R_SLOT = 255.0, 444.0, 350.0

def clamp01(t): return min(max(t, 0.0), 1.0)
def seg(t, a, b): return clamp01((t - a) / (b - a))
def smoother(t): t = clamp01(t); return t * t * t * (t * (6 * t - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t

YY, XX = np.mgrid[0:H0, 0:W0].astype(np.float32)
RR = np.sqrt((XX - C[0]) ** 2 + (YY - C[1]) ** 2)

def load(name): return np.asarray(Image.open(UP + IMG[name]).convert("RGB"), np.float32)
src = {k: load(k) for k in IMG}

def polyfit_bg(img, mask, deg=3):
    ys, xs = np.where(mask)
    sel = np.random.default_rng(0).choice(len(xs), min(60000, len(xs)), replace=False)
    xi, yi = xs[sel], ys[sel]
    xs, ys = xi / W0, yi / H0
    terms = lambda x, y: np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
    A = terms(xs, ys)
    out = np.zeros_like(img)
    T = terms(XX.ravel() / W0, YY.ravel() / H0)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, img[yi, xi, c], rcond=None)
        out[..., c] = (T @ coef).reshape(H0, W0)
    return out

# ---------------------------------------------------------------- static base (image 1)
base = src["heart"].copy()
lum = base.mean(2)
# outer burgundy + left panel background model
bg_mask = (base[..., 0] > base[..., 1] + 35) & (lum < 120) & (RR > R_OUT + 15)
BG = polyfit_bg(base, bg_mask, deg=4)

# cream annulus shading model (fit on clean cream pixels)
med = ndimage.median_filter(lum, size=9)
cream_mask = (RR > R_IN + 12) & (RR < R_OUT - 12) & (lum > 200) & (np.abs(lum - med) < 4) \
    & (np.abs(base[..., 0] - base[..., 2]) > 25)
CREAM = polyfit_bg(base, cream_mask, deg=3)
# inner disc model (burgundy)
disc_mask = (RR < R_IN - 8) & (base[..., 0] > base[..., 1] + 30) & (lum < 110)
DISC = polyfit_bg(base, disc_mask, deg=2)

def text_alpha(img, bgm):
    d = np.sqrt(((img - bgm) ** 2).sum(2))
    return np.clip((d - 8) / 110, 0, 1)

# left panel: dynamic area = shape-specific block (below the subtitle)
LEFT = (XX < 690)
DYN_Y0 = 345
def extract_left(name):
    img = src[name]
    bgm = polyfit_bg(img, (img[..., 0] > img[..., 1] + 35) & (img.mean(2) < 120) & LEFT, deg=4)
    a = text_alpha(img, bgm) * (LEFT & (YY >= DYN_Y0) & (YY < 920))
    # group rows into blocks (badge, description, three feature rows)
    rows = (a > 0.5).sum(1) > 2
    blocks, start = [], None
    for y in range(H0):
        if rows[y] and start is None: start = y
        if not rows[y] and start is not None:
            if blocks and start - blocks[-1][1] < 10: blocks[-1] = (blocks[-1][0], y)
            else: blocks.append((start, y))
            start = None
    blocks = [b for b in blocks if b[1] - b[0] > 12]
    # badge pill: fill the dark letters inside it so it stays opaque
    b0 = blocks[0]
    pill = np.zeros_like(a, bool); pill[b0[0] - 4:b0[1] + 4] = a[b0[0] - 4:b0[1] + 4] > 0.5
    pill = ndimage.binary_fill_holes(pill)
    a = np.maximum(a, ndimage.gaussian_filter(pill.astype(np.float32), 0.7) * (pill | (a > 0)))
    col = np.clip(bgm + (img - bgm) / np.maximum(a, 1e-3)[..., None], 0, 255)
    col = np.where(a[..., None] > 0.02, col, 0)
    return a.astype(np.float32), col.astype(np.float32), blocks

TEXT = {k: extract_left(k) for k in IMG}
# remove image-1's dynamic text from the base
dyn = ((XX < 700) & (YY > DYN_Y0 - 8)).astype(np.float32)
m = ndimage.gaussian_filter(dyn, 14)[..., None]
base = base * (1 - m) + BG * m

# rebuild the ring: burgundy behind, cream annulus, burgundy disc (all clean)
ring = np.clip(R_OUT + 0.5 - RR, 0, 1) * np.clip(RR - R_IN + 0.5, 0, 1)
inner = np.clip(R_IN + 0.5 - RR, 0, 1)
outer_zone = np.clip((R_OUT + 40 - RR) / 12, 0, 1)[..., None]
base = base * (1 - outer_zone) + BG * outer_zone
base = base * (1 - ring[..., None]) + CREAM * ring[..., None]
base = base * (1 - inner[..., None]) + DISC * inner[..., None]
# soft contact shadow of the cream ring on burgundy
sh = np.clip((RR - R_OUT) / 30, 0, 1); sh = (1 - sh) * (RR > R_OUT) * 0.25
base *= (1 - sh)[..., None]
BASE = base.astype(np.float32)

# ---------------------------------------------------------------- centre discs (ring photo + labels)
DISC_C = {"heart": (1155, 466), "emerald": (1155, 466), "oval": (1142, 472)}
DR = 262
def centre_disc(name):
    cx, cy = DISC_C[name]
    img = src[name]
    crop = np.zeros((2 * DR, 2 * DR, 3), np.float32)
    y0, x0 = cy - DR, cx - DR
    ya, xa = max(0, y0), max(0, x0)
    sub = img[ya:cy + DR, xa:cx + DR]
    crop[ya - y0:ya - y0 + sub.shape[0], xa - x0:xa - x0 + sub.shape[1]] = sub
    # stone centre/size: bright, low-saturation pixels near the middle
    yy, xx = np.mgrid[0:2 * DR, 0:2 * DR]
    l = crop.mean(2); s = crop.max(2) - crop.min(2)
    stone = (l > 185) & (s < 40) & (np.hypot(xx - DR, yy - DR) < 120)
    stone = ndimage.binary_opening(stone, iterations=2)
    lab, n = ndimage.label(stone)
    big = lab == (np.argmax(ndimage.sum(stone, lab, range(1, n + 1))) + 1)
    ys, xs = np.where(ndimage.binary_closing(big, iterations=6))
    return crop, ((xs.min() + xs.max()) / 2 - DR, (ys.min() + ys.max()) / 2 - DR), ys.max() - ys.min()
CENTRE = {k: centre_disc(k) for k in IMG}

# ---------------------------------------------------------------- loose stones on the wheel
def load_cut(name, rot=0):
    im = Image.open(CUTS + name + "_cut.png").convert("RGBA")
    a = np.asarray(im)[..., 3] > 128
    lab, n = ndimage.label(a)
    keep = lab == (np.argmax(ndimage.sum(a, lab, range(1, n + 1))) + 1)
    arr = np.asarray(im).copy(); arr[..., 3] = (arr[..., 3] * ndimage.binary_dilation(keep, iterations=2)).astype(np.uint8)
    im = Image.fromarray(arr, "RGBA")
    im = im.crop(im.getbbox())
    if rot: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    return im
ORDER = ["heart", "round", "emerald", "marquise", "oval", "pear"]   # 60 deg apart
ROT = {"emerald": 90, "oval": 90}
STONES = {k: load_cut(k, ROT.get(k, 0)) for k in ORDER}
TARGET_H = 150.0                                  # stone height on the wheel
def stone_scale(k):
    im = STONES[k]
    return min(TARGET_H / im.height, 175.0 / im.width)
FEATURED = ["heart", "emerald", "oval"]

def slot_angle(k, t):
    j = ORDER.index(k)
    return math.radians(-90 - 60 * j + OMEGA * t)

def slot_pos(k, t):
    a = slot_angle(k, t)
    return C + R_SLOT * np.array([math.cos(a), math.sin(a)])

# ---------------------------------------------------------------- drawing helpers
def paste_rgba(frame, im, centre, scale, opacity=1.0, shadow=True):
    w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    s = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(s, np.float32)
    x0, y0 = int(round(centre[0] - w / 2)), int(round(centre[1] - h / 2))
    def blend(rgb, alpha, ox, oy):
        xa, ya, xb, yb = max(0, ox), max(0, oy), min(W0, ox + alpha.shape[1]), min(H0, oy + alpha.shape[0])
        if xa >= xb or ya >= yb: return
        al = alpha[ya - oy:yb - oy, xa - ox:xb - ox, None]
        frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - al) + rgb[ya - oy:yb - oy, xa - ox:xb - ox] * al
    if shadow:
        pad = 24
        sa = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
        sa[pad:pad + h, pad:pad + w] = a[..., 3] / 255
        sa = ndimage.gaussian_filter(sa, 7) * 0.30 * opacity
        blend(np.broadcast_to(np.array([95, 60, 45], np.float32), sa.shape + (3,)), sa, x0 - pad + 5, y0 - pad + 9)
    blend(a[..., :3], a[..., 3] / 255 * opacity, x0, y0)

def draw_disc(frame, name, radius_open):
    if radius_open <= 0:
        return
    crop, _, _ = CENTRE[name]
    y0, x0 = int(C[1]) - DR, int(C[0]) - DR
    rr = RR[y0:y0 + 2 * DR, x0:x0 + 2 * DR]
    a = np.clip((radius_open - rr) / 45, 0, 1) * np.clip(R_IN + 0.5 - rr, 0, 1)
    sub = frame[y0:y0 + 2 * DR, x0:x0 + 2 * DR]
    frame[y0:y0 + 2 * DR, x0:x0 + 2 * DR] = sub * (1 - a[..., None]) + crop * a[..., None]

def draw_text(frame, name, u_in, u_out):
    a, col, blocks = TEXT[name]
    pout = smoother(seg(u_out, 0, 0.3))
    for j, (y0, y1) in enumerate(blocks):
        p = smoother(seg(u_in, 0.10 * j, 0.10 * j + 0.5))
        if p <= 0 or pout >= 1:
            continue
        ya, yb = max(0, y0 - 6), min(H0, y1 + 6)
        al = a[ya:yb, :740].copy()
        cc = col[ya:yb, :740]
        # left-to-right soft wipe + rise
        xs = np.arange(740, dtype=np.float32)[None, :]
        wipe = np.clip((p * 900 - (xs - 60)) / 160, 0, 1)
        al = al * wipe * p * (1 - pout)
        dy = int(round((1 - p) * 16 - pout * 10))
        ta, tb = ya + dy, yb + dy
        if ta < 0 or tb > H0:
            continue
        frame[ta:tb, :740] = frame[ta:tb, :740] * (1 - al[..., None]) + cc * al[..., None]

def glint(size):
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-3
    g = np.exp(-(r / (size * 0.1)) ** 2) + 0.8 * (np.exp(-np.abs(yy) / (size * 0.03)) * np.exp(-np.abs(xx) / (size * 0.45))
                                                  + np.exp(-np.abs(xx) / (size * 0.03)) * np.exp(-np.abs(yy) / (size * 0.45)))
    return np.clip(g + 0.25 * np.exp(-(r / (size * 0.35)) ** 2), 0, 1.5)
GL = glint(34)
def add_glint(frame, x, y, a):
    if a < 0.02: return
    s = 34; x0, y0 = int(x) - s, int(y) - s
    frame[y0:y0 + 2 * s + 1, x0:x0 + 2 * s + 1] += GL[..., None] * a * 255

# ---------------------------------------------------------------- timeline per featured stone
# local time u in [0, CYCLE): 0-0.5 fly in | 0.35-0.75 ring photo opens | 0.5+ text |
# 1.85-2.15 photo closes + text out | 2.0-2.5 fly back to its (moving) slot
FLY = 0.5
def frame(t):
    t = t % LOOP
    f = BASE.copy()
    flying = []
    for k in ORDER:
        if k in FEATURED:
            i = FEATURED.index(k)
            u = (t - i * CYCLE) % LOOP
            if u < CYCLE:
                flying.append((k, u))
                continue
        paste_rgba(f, STONES[k], slot_pos(k, t), stone_scale(k))
    for k, u in flying:
        _, off, stone_h = CENTRE[k]
        cpos = C + np.array(off)
        s_wheel = stone_scale(k)
        s_centre = stone_h / STONES[k].height
        open_r = lerp(0, DR + 50, smoother(seg(u, 0.35, 0.75))) * (1 - smoother(seg(u, 1.85, 2.15)))
        draw_disc(f, k, open_r)
        draw_text(f, k, u - 0.5, u - 1.85)
        if u < FLY:
            p = smoother(u / FLY)
            pos = lerp(slot_pos(k, t), cpos, p); sc = lerp(s_wheel, s_centre, p)
            op = 1 - smoother(seg(u, 0.45, 0.7))
        elif u > CYCLE - FLY:
            p = smoother((u - (CYCLE - FLY)) / FLY)
            pos = lerp(cpos, slot_pos(k, t), p); sc = lerp(s_centre, s_wheel, p)
            op = smoother(seg(u, 1.9, 2.05))
        else:
            pos, sc = cpos, s_centre
            op = 1 - smoother(seg(u, 0.45, 0.7)) if u < 1.0 else smoother(seg(u, 1.9, 2.05))
        if op > 0:
            paste_rgba(f, STONES[k], pos, sc, op, shadow=u < 0.3 or u > CYCLE - 0.3)
        # one sparkle on the centre stone while it is presented
        add_glint(f, cpos[0] + 18, cpos[1] - stone_h * 0.18, max(0, math.sin(math.pi * seg(u, 0.85, 1.45))) ** 2)
    return f

def to_out(f):
    im = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    return im.resize((OUT_W, OUT_H), Image.LANCZOS)

if __name__ == "__main__":
    out = sys.argv[1]
    only = [float(x) for x in sys.argv[2:]]
    if only:
        for t in only:
            to_out(frame(t)).save(out.replace(".mp4", f"_{t:05.2f}.jpg"), quality=90)
    else:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                               "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                              stdin=subprocess.PIPE)
        for n in range(int(LOOP * FPS)):
            ff.stdin.write(np.asarray(to_out(frame(n / FPS))).tobytes())
            if n % 60 == 0: print(n, flush=True)
        ff.stdin.close(); ff.wait()
