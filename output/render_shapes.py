"""'Choose Your Diamond Shape' wheel animation - 1920x1080, 15 s seamless loop.

A gold pave band sits fixed in the centre of the ring. The cream ring turns on its own carrying
six loose diamonds; one by one each diamond leaves the ring, sets onto the band while its
description is revealed on the left, then flies back to its place as the next one comes in.

Usage: python3 render_shapes.py OUT.mp4 [t1 t2 ...]   (times => preview JPGs)
"""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
UP = os.environ.get("UPLOADS", "/root/.claude/uploads/13bdc3d8-f30d-5841-978c-ae76c1bd629a/")
ASSETS = os.path.join(HERE, "shape_assets/")
FONTS = ASSETS + "fonts/"
BASE_IMG = UP + "950f72e6-image.png"      # heart infographic: title, background, ring geometry
ICON_IMG = {"heart": UP + "950f72e6-image.png", "emerald": UP + "6c435b91-image.png"}
W0, H0 = 1672, 941                         # native size (composited here, upscaled at the end)
OUT_W, OUT_H, FPS = 1920, 1080, 30

ORDER = ["heart", "round", "emerald", "marquise", "oval", "pear"]   # 60 deg apart, presented in this order
CYCLE = 2.5                                # one shape every 2.5 s
LOOP = CYCLE * len(ORDER)                  # 15 s
OMEGA = 360.0 / LOOP                       # wheel turns once per loop -> seamless
ACTIVE = 2.75                              # each shape's own timeline (overlaps the next by 0.25 s)
C = np.array([1155.0, 466.0]); R_IN, R_OUT, R_SLOT = 255.0, 444.0, 350.0

def clamp01(t): return min(max(t, 0.0), 1.0)
def seg(t, a, b): return clamp01((t - a) / (b - a))
def smoother(t): t = clamp01(t); return t * t * t * (t * (6 * t - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t

YY, XX = np.mgrid[0:H0, 0:W0].astype(np.float32)
RR = np.sqrt((XX - C[0]) ** 2 + (YY - C[1]) ** 2)

def polyfit_bg(img, mask, deg=3):
    ys, xs = np.where(mask)
    sel = np.random.default_rng(0).choice(len(xs), min(60000, len(xs)), replace=False)
    yi, xi = ys[sel], xs[sel]
    terms = lambda x, y: np.stack([x ** i * y ** j for i in range(deg + 1) for j in range(deg + 1 - i)], -1)
    A = terms(xi / W0, yi / H0); T = terms(XX.ravel() / W0, YY.ravel() / H0)
    out = np.zeros_like(img)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, img[yi, xi, c], rcond=None)
        out[..., c] = (T @ coef).reshape(H0, W0)
    return out

def load_rgb(p): return np.asarray(Image.open(p).convert("RGB"), np.float32)

# ---------------------------------------------------------------- static base
base = load_rgb(BASE_IMG)
lum = base.mean(2)
BG = polyfit_bg(base, (base[..., 0] > base[..., 1] + 35) & (lum < 120) & (RR > R_OUT + 15), deg=4)
med = ndimage.median_filter(lum, size=9)
CREAM = polyfit_bg(base, (RR > R_IN + 12) & (RR < R_OUT - 12) & (lum > 200) & (np.abs(lum - med) < 4)
                   & (np.abs(base[..., 0] - base[..., 2]) > 25), deg=3)
DISC = polyfit_bg(base, (RR < R_IN - 8) & (base[..., 0] > base[..., 1] + 30) & (lum < 110), deg=2)

DYN_Y0 = 345
def text_layer(img, bgm, region):
    d = np.sqrt(((img - bgm) ** 2).sum(2))
    a = np.clip((d - 8) / 110, 0, 1) * region
    col = np.clip(bgm + (img - bgm) / np.maximum(a, 1e-3)[..., None], 0, 255)
    return a, col

# icons (gold outlined circles) lifted from the original infographics
ICONS = {}
for name, path in ICON_IMG.items():
    img = load_rgb(path)
    bgm = polyfit_bg(img, (img[..., 0] > img[..., 1] + 35) & (img.mean(2) < 120) & (XX < 690), deg=4)
    a, col = text_layer(img, bgm, (XX < 690))
    centres = {"heart": {"diamond": 585, "sparkle": 698, "heart": 815},
               "emerald": {"emerald": 585, "crown": 818}}[name]
    for icon, cy in centres.items():
        y0, x0 = cy - 50, 138 - 50
        ICONS[icon] = (a[y0:y0 + 100, x0:x0 + 100].copy(), col[y0:y0 + 100, x0:x0 + 100].copy())

# clean dynamic area of the left panel, rebuild the ring
dyn = ((XX < 700) & (YY > DYN_Y0 - 8)).astype(np.float32)
m = ndimage.gaussian_filter(dyn, 14)[..., None]
base = base * (1 - m) + BG * m
ring = np.clip(R_OUT + 0.5 - RR, 0, 1) * np.clip(RR - R_IN + 0.5, 0, 1)
inner = np.clip(R_IN + 0.5 - RR, 0, 1)
oz = np.clip((R_OUT + 40 - RR) / 12, 0, 1)[..., None]
base = base * (1 - oz) + BG * oz
base = base * (1 - ring[..., None]) + CREAM * ring[..., None]
base = base * (1 - inner[..., None]) + DISC * inner[..., None]
sh = np.clip((RR - R_OUT) / 30, 0, 1); base *= (1 - (1 - sh) * (RR > R_OUT) * 0.25)[..., None]

def composite_rgba(frame, im, cx, cy, opacity=1.0, shadow=None):
    a = np.asarray(im, np.float32)
    h, w = a.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    def blend(rgb, al, ox, oy):
        xa, ya, xb, yb = max(0, ox), max(0, oy), min(W0, ox + al.shape[1]), min(H0, oy + al.shape[0])
        if xa >= xb or ya >= yb: return
        A = al[ya - oy:yb - oy, xa - ox:xb - ox, None]
        frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - A) + rgb[ya - oy:yb - oy, xa - ox:xb - ox] * A
    if shadow:
        dx, dy, blur, sop, scol = shadow
        pad = int(blur * 3)
        sa = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
        sa[pad:pad + h, pad:pad + w] = a[..., 3] / 255
        sa = ndimage.gaussian_filter(sa, blur) * sop * opacity
        blend(np.broadcast_to(np.array(scol, np.float32), sa.shape + (3,)), sa, x0 - pad + dx, y0 - pad + dy)
    blend(a[..., :3], a[..., 3] / 255 * opacity, x0, y0)

# ---------------------------------------------------------------- the band (fixed, centre)
band = Image.open(ASSETS + "band.png").convert("RGBA")
ba = np.asarray(band)[..., 3] > 200
lab, n = ndimage.label(ba)
keep = lab == (np.argmax(ndimage.sum(ba, lab, range(1, n + 1))) + 1)
keep = ndimage.binary_fill_holes(ndimage.binary_closing(keep, iterations=3))
barr = np.asarray(band).copy()
barr[..., 3] = (ndimage.gaussian_filter(keep.astype(np.float32), 0.8) * 255).astype(np.uint8)
band = Image.fromarray(barr, "RGBA"); band = band.crop(band.getbbox())
BAND_W = 450.0
band = band.resize((int(BAND_W), int(band.height * BAND_W / band.width)), Image.LANCZOS)
BAND_POS = (C[0], C[1] + 40)               # centre of the band image on screen
STONE_SEAT = (C[0], BAND_POS[1] - 30)      # where the presented stone's centre sits
composite_rgba(base, band, *BAND_POS, shadow=(0, 14, 10, 0.55, (25, 2, 6)))
BASE = base.astype(np.float32)

# ---------------------------------------------------------------- loose stones
def load_cut(name, rot=0):
    im = Image.open(ASSETS + name + "_cut.png").convert("RGBA")
    a = np.asarray(im)[..., 3] > 128
    lab, n = ndimage.label(a)
    keep = lab == (np.argmax(ndimage.sum(a, lab, range(1, n + 1))) + 1)
    arr = np.asarray(im).copy()
    arr[..., 3] = (arr[..., 3] * ndimage.binary_dilation(keep, iterations=2)).astype(np.uint8)
    im = Image.fromarray(arr, "RGBA"); im = im.crop(im.getbbox())
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC); im = im.crop(im.getbbox())
    return im

WHEEL_ROT = {"emerald": 90, "oval": 90}
STONES = {k: load_cut(k, WHEEL_ROT.get(k, 0)) for k in ORDER}

def upright_angle(im, tip_up=False):
    """PIL rotation (deg, counter-clockwise) that makes the stone's long axis vertical."""
    a = np.asarray(im)[..., 3] > 128
    ys, xs = np.nonzero(a)
    ev, evec = np.linalg.eigh(np.cov(np.stack([xs - xs.mean(), ys - ys.mean()])))
    vx, vy = evec[:, 1]
    rot = math.degrees(math.atan2(vy, vx)) - 90 + 180
    rot = ((rot + 180) % 360) - 180
    best = None
    for cand in (rot, rot + 180, rot - 180):
        if -180 <= cand <= 180:
            r = np.asarray(im.rotate(cand, expand=True))[..., 3] > 128
            ys2, xs2 = np.nonzero(r)
            ext = ys2.max() - ys2.min()
            if tip_up:
                rows = r.sum(1); mid = (ys2.min() + ys2.max()) // 2
                ok = rows[:mid].sum() < rows[mid:].sum()
            else:
                ok = True
            score = ext + (10000 if ok else 0) - abs(cand)
            if best is None or score > best[0]: best = (score, cand)
    return best[1]
SEAT_ROT = {"marquise": upright_angle(STONES["marquise"]),
            "pear": upright_angle(STONES["pear"], tip_up=True)}

def wheel_scale(k): im = STONES[k]; return min(150.0 / im.height, 175.0 / im.width)
def seat_scale(k, rot):
    w, h = STONES[k].size
    c, s = abs(math.cos(math.radians(rot))), abs(math.sin(math.radians(rot)))
    rw, rh = w * c + h * s, w * s + h * c
    return min(185.0 / rh, 200.0 / rw)

def slot_pos(k, t):
    a = math.radians(-90 - 60 * ORDER.index(k) + OMEGA * t)
    return C + R_SLOT * np.array([math.cos(a), math.sin(a)])

def draw_stone(frame, k, pos, scale, rot=0.0, opacity=1.0, shadow_on="cream"):
    im = STONES[k]
    if abs(rot) > 0.05:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    sh = (5, 9, 6, 0.30, (95, 60, 45)) if shadow_on == "cream" else (0, 10, 7, 0.45, (20, 2, 5))
    composite_rgba(frame, im, pos[0], pos[1], opacity, shadow=sh)

# ---------------------------------------------------------------- left-panel text (typeset)
F_BADGE = ImageFont.truetype(FONTS + "libre-baskerville-latin-700-normal.woff", 31)
F_DESC = ImageFont.truetype(FONTS + "open-sans-latin-400-normal.woff", 28)
F_TITLE = ImageFont.truetype(FONTS + "open-sans-latin-700-normal.woff", 27)
F_BODY = ImageFont.truetype(FONTS + "open-sans-latin-400-normal.woff", 23)
COPY = {
    "heart": ("Heart Shape Diamond", ["A romantic and distinctive cut", "that beautifully represents love."],
              [("diamond", "Design", ["A heart silhouette with", "perfect symmetry."]),
               ("sparkle", "Sparkle", ["Brilliant cut for exceptional", "light reflection."]),
               ("heart", "Meaning", ["A timeless symbol of", "love and affection."])]),
    "round": ("Round Shape Diamond", ["The most popular cut, celebrated", "for its unmatched brilliance."],
              [("diamond", "Design", ["A perfectly circular outline", "with brilliant-cut facets."]),
               ("sparkle", "Sparkle", ["The most fire and brilliance", "of any diamond shape."]),
               ("crown", "Style", ["Classic and timeless,", "it suits every setting."])]),
    "emerald": ("Emerald Shape Diamond", ["A sleek, sophisticated cut known for", "its clean lines and elegant sparkle."],
                [("emerald", "Design", ["A rectangular shape with", "step-cut facets."]),
                 ("sparkle", "Sparkle", ["A refined, mirror-like brilliance", "with a timeless appeal."]),
                 ("crown", "Style", ["A modern and elegant choice,", "perfect for a bold, sophisticated look."])]),
    "marquise": ("Marquise Shape Diamond", ["A bold, elongated cut with", "gracefully pointed ends."],
                 [("diamond", "Design", ["A boat-shaped outline with", "two tapered points."]),
                  ("sparkle", "Sparkle", ["Brilliant facets across a", "generous surface area."]),
                  ("crown", "Style", ["Elegant and elongated, it makes", "the finger look slimmer."])]),
    "oval": ("Oval Shape Diamond", ["An elegant, elongated cut that", "creates a graceful, flattering look."],
             [("diamond", "Design", ["An elongated, rounded silhouette", "with a soft, balanced outline."]),
              ("sparkle", "Sparkle", ["Brilliant facets create lively", "light and beautiful fire."]),
              ("heart", "Style", ["Versatile, graceful and", "effortlessly timeless."])]),
    "pear": ("Pear Shape Diamond", ["A graceful teardrop that blends", "the round and marquise cuts."],
             [("diamond", "Design", ["A rounded end tapering", "to a single point."]),
              ("sparkle", "Sparkle", ["Brilliant facets for lively", "sparkle and fire."]),
              ("heart", "Style", ["Graceful and unique, with", "a vintage-inspired charm."])]),
}
WHITE, GOLD, BADGE_INK = (250, 246, 240), (252, 226, 165), (72, 14, 20)
BLOCKS = [(358, 434), (432, 512), (534, 640), (650, 756), (766, 874)]

def build_text(k):
    badge, desc, feats = COPY[k]
    img = Image.new("RGBA", (W0, H0), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # badge pill: champagne-gold gradient + soft glow
    tw = d.textlength(badge, font=F_BADGE)
    x0, y0, x1, y1 = 75, 370, int(75 + tw + 74), 422
    pm = Image.new("L", (W0, H0), 0); ImageDraw.Draw(pm).rounded_rectangle((x0, y0, x1, y1), 26, fill=255)
    glow = pm.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.35))
    img.paste(Image.new("RGBA", (W0, H0), (240, 200, 130, 255)), (0, 0), glow)
    g = np.zeros((H0, W0, 4), np.uint8)
    t = np.clip((YY - y0) / (y1 - y0), 0, 1)
    g[..., 0] = (252 - 22 * t).astype(np.uint8); g[..., 1] = (236 - 38 * t).astype(np.uint8)
    g[..., 2] = (198 - 58 * t).astype(np.uint8); g[..., 3] = 255
    img.paste(Image.fromarray(g, "RGBA"), (0, 0), pm)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1), badge, font=F_BADGE, fill=BADGE_INK, anchor="mm")
    for i, line in enumerate(desc):
        d.text((103, 436 + 35 * i), line, font=F_DESC, fill=WHITE)
    for j, (icon, title, lines) in enumerate(feats):
        ty = 540 + 116 * j
        d.text((212, ty), title, font=F_TITLE, fill=GOLD)
        for i, line in enumerate(lines):
            d.text((212, ty + 34 + 29 * i), line, font=F_BODY, fill=WHITE)
    arr = np.asarray(img, np.float32).copy()
    a = arr[..., 3] / 255; col = arr[..., :3].copy()
    for j, (icon, *_r) in enumerate(feats):
        ia, ic = ICONS[icon]
        ya, xa = 586 + 116 * j - 50, 88
        a[ya:ya + 100, xa:xa + 100] = ia
        col[ya:ya + 100, xa:xa + 100] = ic
    return a.astype(np.float32), col.astype(np.float32)
TEXT = {k: build_text(k) for k in ORDER}

def draw_text(frame, k, u_in, u_out):
    a, col = TEXT[k]
    pout = smoother(seg(u_out, 0, 0.3))
    if pout >= 1: return
    xs = np.arange(700, dtype=np.float32)[None, :]
    for j, (y0, y1) in enumerate(BLOCKS):
        p = smoother(seg(u_in, 0.07 * j, 0.07 * j + 0.4))
        if p <= 0: continue
        al = a[y0:y1, :700] * np.clip((p * 900 - (xs - 60)) / 160, 0, 1) * p * (1 - pout)
        dy = int(round((1 - p) * 14 - pout * 10))
        frame[y0 + dy:y1 + dy, :700] = frame[y0 + dy:y1 + dy, :700] * (1 - al[..., None]) + col[y0:y1, :700] * al[..., None]

def make_glint(size):
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-3
    g = np.exp(-(r / (size * 0.1)) ** 2) + 0.8 * (np.exp(-np.abs(yy) / (size * 0.03)) * np.exp(-np.abs(xx) / (size * 0.45))
                                                  + np.exp(-np.abs(xx) / (size * 0.03)) * np.exp(-np.abs(yy) / (size * 0.45)))
    return np.clip(g + 0.25 * np.exp(-(r / (size * 0.35)) ** 2), 0, 1.5)
GL = make_glint(34)
def add_glint(frame, x, y, a):
    if a < 0.02: return
    s = 34; x0, y0 = int(x) - s, int(y) - s
    frame[y0:y0 + 2 * s + 1, x0:x0 + 2 * s + 1] += GL[..., None] * a * 255

# ---------------------------------------------------------------- timeline
# per-shape local time u: 0-0.5 fly onto band | 0.45+ text in | 2.0-2.3 text out | 2.3-2.75 fly back
FLY_IN, BACK0 = 0.5, 2.3
def frame(t):
    t = t % LOOP
    f = BASE.copy()
    active = []
    for i, k in enumerate(ORDER):
        u = (t - i * CYCLE) % LOOP
        if u < ACTIVE:
            active.append((k, u))
        else:
            draw_stone(f, k, slot_pos(k, t), wheel_scale(k))
    for k, u in sorted(active, key=lambda x: -x[1]):        # newest stone drawn last (on top)
        rot_seat = SEAT_ROT.get(k, 0.0)
        s_w, s_s = wheel_scale(k), seat_scale(k, rot_seat)
        seat = np.array(STONE_SEAT)
        if u < FLY_IN:
            p = smoother(u / FLY_IN)
            pos = lerp(slot_pos(k, t), seat, p) - np.array([0, math.sin(math.pi * p) * 30])
            sc, rot = lerp(s_w, s_s, p), lerp(0, rot_seat, p)
        elif u > BACK0:
            p = smoother((u - BACK0) / (ACTIVE - BACK0))
            pos = lerp(seat, slot_pos(k, t), p) - np.array([0, math.sin(math.pi * p) * 30])
            sc, rot = lerp(s_s, s_w, p), lerp(rot_seat, 0, p)
        else:
            settle = math.exp(-(u - FLY_IN) * 9) * math.sin((u - FLY_IN) * 30) * 4
            pos, sc, rot = seat + np.array([0, settle]), s_s, rot_seat
        on_band = FLY_IN * 0.8 < u < BACK0 + 0.1
        draw_stone(f, k, pos, sc, rot, shadow_on="band" if on_band else "cream")
        draw_text(f, k, u - 0.45, u - 2.0)
        add_glint(f, STONE_SEAT[0] + 16, STONE_SEAT[1] - 50, max(0, math.sin(math.pi * seg(u, 0.75, 1.45))) ** 2)
    return f

def to_out(f):
    return Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).resize((OUT_W, OUT_H), Image.LANCZOS)

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
        for n in range(int(round(LOOP * FPS))):
            ff.stdin.write(np.asarray(to_out(frame(n / FPS))).tobytes())
            if n % 90 == 0: print(n, flush=True)
        ff.stdin.close(); ff.wait()
