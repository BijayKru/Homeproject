"""'Choose Your Diamond Shape' wheel animation - 1920x1080, 15 s seamless loop.

Styled with the Emerald Collection design system (same champagne satin set as the
emerald commercial and the website section; Cormorant Garamond + Jost; espresso / cocoa /
antique gold / emerald palette).

A gold pave band sits fixed on an emerald velvet disc in the centre of an ivory ring.
The ring turns on its own carrying six loose diamonds; one by one each diamond leaves the
ring, sets onto the band while its details are revealed on the left, then flies back.

Usage: python3 render_shapes.py OUT.mp4 [t1 t2 ...]   (times => preview JPGs)
"""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "shape_assets/")
FONTS = ASSETS + "fonts/"
W, H, FPS = 1920, 1080, 30
S = 1920 / 1672                            # geometry was designed on the 1672-px infographic

# ---------------------------------------------------------------- design tokens
CHAMPAGNE_LIGHT = (234, 207, 186); CHAMPAGNE = (213, 183, 160); CHAMPAGNE_DEEP = (194, 155, 129)
ESPRESSO = (58, 42, 34); COCOA = (91, 66, 52); ANTIQUE_GOLD = (111, 82, 43); HAIRLINE_GOLD = (174, 138, 87)
EMERALD = (27, 77, 62); EMERALD_DEEP = (18, 58, 46); IVORY = (251, 245, 239)

def font(name, size): return ImageFont.truetype(FONTS + name, size)
SERIF_300 = lambda s: font("cormorant-garamond-latin-300-normal.woff", s)
SERIF_400I = lambda s: font("cormorant-garamond-latin-400-italic.woff", s)
SERIF_500 = lambda s: font("cormorant-garamond-latin-500-normal.woff", s)
SANS_300 = lambda s: font("jost-latin-300-normal.woff", s)
SANS_500 = lambda s: font("jost-latin-500-normal.woff", s)

ORDER = ["heart", "round", "emerald", "marquise", "oval", "pear"]   # 60 deg apart, presented in this order
CYCLE = 2.5
LOOP = CYCLE * len(ORDER)                  # 15 s
OMEGA = 360.0 / LOOP                       # wheel turns once per loop -> seamless
ACTIVE = 2.75
C = np.array([1155.0 * S, 466.0 * S]); R_IN, R_OUT, R_SLOT = 255.0 * S, 444.0 * S, 350.0 * S

def clamp01(t): return min(max(t, 0.0), 1.0)
def seg(t, a, b): return clamp01((t - a) / (b - a))
def smoother(t): t = clamp01(t); return t * t * t * (t * (6 * t - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
RR = np.sqrt((XX - C[0]) ** 2 + (YY - C[1]) ** 2)
GRAIN = np.random.default_rng(3).normal(0, 1.6, (H, W, 1)).astype(np.float32)

# ---------------------------------------------------------------- champagne satin set (same formula as the commercial)
SAT_K = np.clip(np.sqrt(((XX - W * 0.30) / (W * 0.62)) ** 2 + ((YY - H * 0.50) / (H * 0.85)) ** 2), 0, 1.4) ** 1.5
SATIN = np.stack([233 - 42 * SAT_K, 206 - 50 * SAT_K, 186 - 56 * SAT_K], -1)
FALL = np.clip(1.15 - (XX / W) * 0.7 - (YY / H) * 0.35, 0, 1)
def backdrop(t):
    drift = 40 * math.sin(2 * math.pi * t / LOOP)             # periodic -> seamless loop
    u = XX * 0.80 + YY * 0.60 - 280 - drift
    shafts = (0.55 * np.exp(-((np.mod(u + 300, 900) - 450) / 120) ** 2)
              + 0.35 * np.exp(-((np.mod(u + 40, 1300) - 650) / 70) ** 2)
              - 0.30 * np.exp(-((np.mod(u + 620, 1100) - 550) / 160) ** 2))
    return SATIN + (shafts * FALL * 22)[..., None] * np.array([1.0, 0.92, 0.82], np.float32) + GRAIN

# ---------------------------------------------------------------- the ring set (static layer, composited over the satin)
def build_ring_layer():
    rgb = np.zeros((H, W, 3), np.float32); a = np.zeros((H, W), np.float32)
    # ivory ring, lit from the top-left like the set
    lt = np.clip(((XX - C[0]) * -0.6 + (YY - C[1]) * -0.8) / R_OUT, -1, 1) * 0.5 + 0.5
    ring_col = np.stack([lerp(np.float32(CHAMPAGNE_LIGHT[i]), np.float32(IVORY[i]), lt * 0.85 + 0.1) for i in range(3)], -1)
    ring_a = np.clip(R_OUT + 0.5 - RR, 0, 1) * np.clip(RR - R_IN + 0.5, 0, 1)
    # emerald velvet disc
    rn = np.clip(RR / R_IN, 0, 1)
    disc_col = np.stack([lerp(np.float32(EMERALD[i]) * 1.12, np.float32(EMERALD_DEEP[i]) * 0.85, rn ** 1.6) for i in range(3)], -1)
    disc_col = disc_col * (1 - 0.35 * np.clip((RR - (R_IN - 40)) / 40, 0, 1) ** 2)[..., None]   # inner rim shade
    disc_col += np.random.default_rng(5).normal(0, 1.2, (H, W, 1)).astype(np.float32)          # velvet grain
    disc_a = np.clip(R_IN + 0.5 - RR, 0, 1)
    rgb = ring_col * ring_a[..., None] + disc_col * disc_a[..., None]
    a = ring_a + disc_a
    # hairline gold edges (outer, inner) and a fine inset line on the ring
    for r0, op in ((R_OUT - 0.5, 0.9), (R_IN + 0.5, 0.9), (R_OUT - 14, 0.45)):
        line = np.clip(1.0 - np.abs(RR - r0) / 0.9, 0, 1) * op
        rgb = rgb * (1 - line[..., None]) + np.array(HAIRLINE_GOLD, np.float32) * line[..., None]
    # soft shadow of the ring on the satin
    sh = np.clip(R_OUT - np.hypot(XX - C[0], YY - (C[1] - 18)), -60, 0)
    shadow = np.exp(-(sh / 26) ** 2) * (np.hypot(XX - C[0], YY - (C[1] - 18)) > R_OUT) * 0.0
    return rgb, a
RING_RGB, RING_A = build_ring_layer()
ring_mask = (RR < R_OUT).astype(np.float32)
RING_SHADOW = ndimage.gaussian_filter(np.roll(ring_mask, 18, 0), 22) * (1 - ring_mask) * 0.32

def composite_rgba(frame, im, cx, cy, opacity=1.0, shadow=None):
    a = np.asarray(im, np.float32)
    h, w = a.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    def blend(rgb, al, ox, oy):
        xa, ya, xb, yb = max(0, ox), max(0, oy), min(W, ox + al.shape[1]), min(H, oy + al.shape[0])
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

# ---------------------------------------------------------------- band (fixed, centre)
band = Image.open(ASSETS + "band.png").convert("RGBA")
ba = np.asarray(band)[..., 3] > 200
lab, n = ndimage.label(ba)
keep = lab == (np.argmax(ndimage.sum(ba, lab, range(1, n + 1))) + 1)
keep = ndimage.binary_fill_holes(ndimage.binary_closing(keep, iterations=3))
barr = np.asarray(band).copy()
barr[..., 3] = (ndimage.gaussian_filter(keep.astype(np.float32), 0.8) * 255).astype(np.uint8)
band = Image.fromarray(barr, "RGBA"); band = band.crop(band.getbbox())
BAND_W = 450.0 * S
band = band.resize((int(BAND_W), int(band.height * BAND_W / band.width)), Image.LANCZOS)
BAND_POS = (C[0], C[1] + 40 * S)
STONE_SEAT = (C[0], BAND_POS[1] - 30 * S)

STATIC = np.zeros((H, W, 3), np.float32); STATIC_A = np.zeros((H, W), np.float32)
def build_static_ring():
    """Ring + disc + band as one RGBA layer (band composited on the disc)."""
    rgb = RING_RGB.copy()
    tmp = rgb.copy()
    composite_rgba(tmp, band, *BAND_POS, shadow=(0, int(16 * S), 11, 0.6, (6, 22, 16)))
    inside = (RR < R_IN + 1).astype(np.float32)[..., None]
    return tmp * inside + rgb * (1 - inside), RING_A
STATIC, STATIC_A = build_static_ring()

# ---------------------------------------------------------------- loose stones
def load_cut(name, rot=0):
    im = Image.open(ASSETS + name + "_cut.png").convert("RGBA")
    a = np.asarray(im)[..., 3] > 128
    lab, n = ndimage.label(a)
    keep = lab == (np.argmax(ndimage.sum(a, lab, range(1, n + 1))) + 1)
    arr = np.asarray(im).copy()
    arr[..., 3] = (arr[..., 3] * ndimage.binary_dilation(keep, iterations=2)).astype(np.uint8)
    solid = ndimage.binary_erosion(ndimage.binary_fill_holes(keep), iterations=2)   # no see-through facets
    arr[..., 3] = np.maximum(arr[..., 3], (ndimage.gaussian_filter(solid.astype(np.float32), 1.0) * 255).astype(np.uint8))
    im = Image.fromarray(arr, "RGBA"); im = im.crop(im.getbbox())
    if rot:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC); im = im.crop(im.getbbox())
    return im
WHEEL_ROT = {"emerald": 90, "oval": 90}
STONES = {k: load_cut(k, WHEEL_ROT.get(k, 0)) for k in ORDER}

def upright_angle(im, tip_up=False):
    a = np.asarray(im)[..., 3] > 128
    ys, xs = np.nonzero(a)
    ev, evec = np.linalg.eigh(np.cov(np.stack([xs - xs.mean(), ys - ys.mean()])))
    vx, vy = evec[:, 1]
    rot = ((math.degrees(math.atan2(vy, vx)) + 90 + 180) % 360) - 180
    best = None
    for cand in (rot, rot + 180, rot - 180):
        if -180 <= cand <= 180:
            r = np.asarray(im.rotate(cand, expand=True))[..., 3] > 128
            ys2, _ = np.nonzero(r)
            ok = True
            if tip_up:
                rows = r.sum(1); mid = (ys2.min() + ys2.max()) // 2
                ok = rows[:mid].sum() < rows[mid:].sum()
            score = (ys2.max() - ys2.min()) + (10000 if ok else 0) - abs(cand)
            if best is None or score > best[0]: best = (score, cand)
    return best[1]
SEAT_ROT = {"marquise": upright_angle(STONES["marquise"]), "pear": upright_angle(STONES["pear"], tip_up=True)}

def wheel_scale(k): im = STONES[k]; return min(150.0 * S / im.height, 175.0 * S / im.width)
def seat_scale(k, rot):
    w, h = STONES[k].size
    c, s = abs(math.cos(math.radians(rot))), abs(math.sin(math.radians(rot)))
    return min(185.0 * S / (w * s + h * c), 200.0 * S / (w * c + h * s))
def slot_pos(k, t):
    a = math.radians(-90 - 60 * ORDER.index(k) + OMEGA * t)
    return C + R_SLOT * np.array([math.cos(a), math.sin(a)])

def draw_stone(frame, k, pos, scale, rot=0.0, on="ring"):
    im = STONES[k]
    if abs(rot) > 0.05: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    sh = (6, 10, 7, 0.26, COCOA) if on == "ring" else (0, 12, 8, 0.55, (6, 22, 16))
    composite_rgba(frame, im, pos[0], pos[1], shadow=sh)

# ---------------------------------------------------------------- typography helpers
def tracked_width(text, f, tracking):
    return sum(f.getlength(ch) for ch in text) + tracking * f.size * (len(text) - 1)
def draw_tracked(d, cx, baseline, text, f, tracking, fill):
    """Centred, letter-spaced text (PIL has no tracking)."""
    x = cx - tracked_width(text, f, tracking) / 2
    for ch in text:
        d.text((x, baseline), ch, font=f, fill=fill, anchor="ls")
        x += f.getlength(ch) + tracking * f.size
def draw_runs(d, cx, baseline, runs):
    """Centred line made of (text, font, colour) runs, e.g. a headline with an italic accent word."""
    total = sum(f.getlength(t) for t, f, _ in runs)
    x = cx - total / 2
    for t, f, col in runs:
        d.text((x, baseline), t, font=f, fill=col, anchor="ls"); x += f.getlength(t)
def draw_ornament(d, cx, cy, line_len=96, filled=False, col=HAIRLINE_GOLD, size=7):
    r = size / 2 * math.sqrt(2)
    poly = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if filled: d.polygon(poly, fill=col)
    else: d.polygon(poly, outline=col)
    if line_len:
        for i in range(int(line_len)):
            a = int(255 * (i / line_len))                     # fades out away from the diamond
            c = col + (a,)
            d.point((cx - r - 14 - (line_len - i), cy), fill=c); d.point((cx + r + 14 + (line_len - i), cy), fill=c)

COL_X = 440                                # centre of the left text column
F_EYEBROW = SANS_500(13); F_H1 = SERIF_300(92); F_H1_I = SERIF_400I(92)
F_BODY = SANS_300(19); F_LABEL = SANS_500(11); F_NAME = SERIF_300(66); F_NAME_I = SERIF_400I(66); F_DETAIL = SERIF_500(28)

def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))

def build_static_text():
    im = layer(); d = ImageDraw.Draw(im)
    draw_ornament(d, COL_X, 92)
    draw_tracked(d, COL_X, 146, "HIGH JEWELLERY  ·  THE SHAPE GUIDE", F_EYEBROW, 0.42, ANTIQUE_GOLD)
    draw_runs(d, COL_X, 252, [("Choose Your", F_H1, ESPRESSO)])
    draw_runs(d, COL_X, 346, [("Diamond", F_H1_I, EMERALD), (" Shape", F_H1, ESPRESSO)])
    draw_runs(d, COL_X, 410, [("Understand the most popular diamond shapes", F_BODY, COCOA)])
    draw_runs(d, COL_X, 444, [("and find the one that matches your style.", F_BODY, COCOA)])
    return im
STATIC_TEXT = build_static_text()

COPY = {
    "heart":    ("Heart", ["A romantic and distinctive cut", "that beautifully represents love."],
                 [("Design", "Symmetrical"), ("Sparkle", "Brilliant"), ("Meaning", "Romantic")]),
    "round":    ("Round", ["The most popular cut, celebrated", "for its unmatched brilliance."],
                 [("Design", "Circular"), ("Sparkle", "Maximum Fire"), ("Style", "Timeless")]),
    "emerald":  ("Emerald", ["A sleek, sophisticated cut known for", "its clean lines and elegant sparkle."],
                 [("Design", "Step-Cut"), ("Sparkle", "Mirror-Like"), ("Style", "Sophisticated")]),
    "marquise": ("Marquise", ["A bold, elongated cut with", "gracefully pointed ends."],
                 [("Design", "Tapered Points"), ("Sparkle", "Expansive"), ("Style", "Elongating")]),
    "oval":     ("Oval", ["An elegant, elongated cut that", "creates a graceful, flattering look."],
                 [("Design", "Softly Rounded"), ("Sparkle", "Lively Fire"), ("Style", "Versatile")]),
    "pear":     ("Pear", ["A graceful teardrop that blends", "the round and marquise cuts."],
                 [("Design", "Teardrop"), ("Sparkle", "Lively"), ("Style", "Graceful")]),
}
# animated blocks (y ranges on screen): label, name, description, details row
BLOCKS = [(y0 + 38, y1 + 38) for y0, y1 in [(500, 530), (538, 620), (628, 700), (722, 846)]]
ROW_X0, ROW_X1, ROW_TOP, ROW_BOT = COL_X - 300, COL_X + 300, 726, 840

def build_shape_text(k, i):
    name, desc, details = COPY[k]
    im = layer(); d = ImageDraw.Draw(im)
    draw_tracked(d, COL_X, 522, f"SHAPE  {i + 1:02d}  —  {len(ORDER):02d}", F_LABEL, 0.34, ANTIQUE_GOLD)
    draw_runs(d, COL_X, 602, [(name, F_NAME_I, EMERALD), (" Shape", F_NAME, ESPRESSO)])
    for j, line in enumerate(desc):
        draw_runs(d, COL_X, 652 + 34 * j, [(line, F_BODY, COCOA)])
    rule = HAIRLINE_GOLD + (115,)                              # 45 % opacity
    d.line((ROW_X0, ROW_TOP, ROW_X1, ROW_TOP), fill=rule, width=1)
    d.line((ROW_X0, ROW_BOT, ROW_X1, ROW_BOT), fill=rule, width=1)
    cw = (ROW_X1 - ROW_X0) / 3
    for j, (lab_, val) in enumerate(details):
        cx = ROW_X0 + cw * (j + 0.5)
        if j: d.line((ROW_X0 + cw * j, ROW_TOP, ROW_X0 + cw * j, ROW_BOT), fill=rule, width=1)
        draw_tracked(d, cx, 772, lab_.upper(), F_LABEL, 0.34, ANTIQUE_GOLD)
        draw_runs(d, cx, 812, [(val, F_DETAIL, ESPRESSO)])
    return im
Y_OFF = 38                                 # optical centring of the text column against the ring
def to_layer(im):
    a = np.roll(np.asarray(im, np.float32), Y_OFF, 0)
    return a[..., 3] / 255, a[..., :3]
SHAPE_TEXT = {k: to_layer(build_shape_text(k, i)) for i, k in enumerate(ORDER)}
ST_A, ST_RGB = to_layer(STATIC_TEXT)

PROG_Y, PROG_GAP = 904, 34
def progress_layer(active_k, fill):
    im = layer(); d = ImageDraw.Draw(im)
    x0 = COL_X - PROG_GAP * (len(ORDER) - 1) / 2
    for j, k in enumerate(ORDER):
        draw_ornament(d, x0 + PROG_GAP * j, PROG_Y, line_len=0, size=8, filled=False)
    return im
PROG_BASE = to_layer(progress_layer(None, 0))
PROG_DOT = {}
for j, k in enumerate(ORDER):
    im = layer(); d = ImageDraw.Draw(im)
    x0 = COL_X - PROG_GAP * (len(ORDER) - 1) / 2
    draw_ornament(d, x0 + PROG_GAP * j, PROG_Y, line_len=0, size=8, filled=True, col=EMERALD)
    PROG_DOT[k] = to_layer(im)

def over(frame, a, rgb, ys=None, opacity=1.0):
    if ys is None:
        frame[:] = frame * (1 - a[..., None] * opacity) + rgb * a[..., None] * opacity
    else:
        y0, y1 = ys
        A = a[y0:y1, None] if False else a[y0:y1][..., None] * opacity
        frame[y0:y1] = frame[y0:y1] * (1 - A) + rgb[y0:y1] * A

def draw_shape_text(frame, k, u_in, u_out):
    a, rgb = SHAPE_TEXT[k]
    pout = smoother(seg(u_out, 0, 0.3))
    if pout >= 1: return
    xs = np.arange(W, dtype=np.float32)[None, :]
    for j, (y0, y1) in enumerate(BLOCKS):
        p = smoother(seg(u_in, 0.08 * j, 0.08 * j + 0.45))
        if p <= 0: continue
        wipe = np.clip((p * 1000 - (xs - 100)) / 220, 0, 1)
        al = a[y0:y1] * wipe * p * (1 - pout)
        dy = int(round((1 - p) * 14 - pout * 10))
        frame[y0 + dy:y1 + dy] = frame[y0 + dy:y1 + dy] * (1 - al[..., None]) + rgb[y0:y1] * al[..., None]

def make_glint(size):
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-3
    g = np.exp(-(r / (size * 0.1)) ** 2) + 0.8 * (np.exp(-np.abs(yy) / (size * 0.03)) * np.exp(-np.abs(xx) / (size * 0.45))
                                                  + np.exp(-np.abs(xx) / (size * 0.03)) * np.exp(-np.abs(yy) / (size * 0.45)))
    return np.clip(g + 0.25 * np.exp(-(r / (size * 0.35)) ** 2), 0, 1.5)
GL = make_glint(40)
def add_glint(frame, x, y, a):
    if a < 0.02: return
    s = 40; x0, y0 = int(x) - s, int(y) - s
    frame[y0:y0 + 2 * s + 1, x0:x0 + 2 * s + 1] += GL[..., None] * a * 255

# ---------------------------------------------------------------- frame
FLY_IN, BACK0 = 0.5, 2.3
def frame(t):
    t = t % LOOP
    f = backdrop(t)
    f *= (1 - RING_SHADOW)[..., None]
    f[:] = f * (1 - STATIC_A[..., None]) + STATIC * STATIC_A[..., None]
    over(f, ST_A, ST_RGB)
    over(f, *PROG_BASE)
    active = []
    for i, k in enumerate(ORDER):
        u = (t - i * CYCLE) % LOOP
        if u < ACTIVE: active.append((k, u))
        else: draw_stone(f, k, slot_pos(k, t), wheel_scale(k))
    for k, u in sorted(active, key=lambda x: -x[1]):
        rot_seat = SEAT_ROT.get(k, 0.0)
        s_w, s_s = wheel_scale(k), seat_scale(k, rot_seat)
        seat = np.array(STONE_SEAT)
        if u < FLY_IN:
            p = smoother(u / FLY_IN)
            pos = lerp(slot_pos(k, t), seat, p) - np.array([0, math.sin(math.pi * p) * 34])
            sc, rot = lerp(s_w, s_s, p), lerp(0, rot_seat, p)
        elif u > BACK0:
            p = smoother((u - BACK0) / (ACTIVE - BACK0))
            pos = lerp(seat, slot_pos(k, t), p) - np.array([0, math.sin(math.pi * p) * 34])
            sc, rot = lerp(s_s, s_w, p), lerp(rot_seat, 0, p)
        else:
            settle = math.exp(-(u - FLY_IN) * 9) * math.sin((u - FLY_IN) * 30) * 4
            pos, sc, rot = seat + np.array([0, settle]), s_s, rot_seat
        draw_stone(f, k, pos, sc, rot, on="band" if FLY_IN * 0.8 < u < BACK0 + 0.1 else "ring")
        draw_shape_text(f, k, u - 0.45, u - 2.0)
        dot = smoother(seg(u, 0.3, 0.7)) * (1 - smoother(seg(u, 2.1, 2.5)))
        if dot > 0: over(f, *PROG_DOT[k], opacity=dot)
        add_glint(f, STONE_SEAT[0] + 18, STONE_SEAT[1] - 58, max(0, math.sin(math.pi * seg(u, 0.75, 1.45))) ** 2)
    return f

def to_img(f): return Image.fromarray(np.clip(f + 0.5, 0, 255).astype(np.uint8))

if __name__ == "__main__":
    out = sys.argv[1]
    only = [float(x) for x in sys.argv[2:]]
    if only:
        for t in only:
            to_img(frame(t)).save(out.replace(".mp4", f"_{t:05.2f}.jpg"), quality=92)
    else:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                               "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        for n in range(int(round(LOOP * FPS))):
            ff.stdin.write(np.asarray(to_img(frame(n / FPS))).tobytes())
            if n % 90 == 0: print(n, flush=True)
        ff.stdin.close(); ff.wait()
