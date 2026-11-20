"""Emerald necklace commercial, 16:9 (1920x1080), 10 s, one continuous beige set.

Usage: python3 render_16x9.py OUT.mp4 [t1 t2 ...]   (times => preview JPGs instead of video)
Inputs: the three reference photos plus rembg cut-outs of image 1 (pendant) and image 3 (model).
"""
import sys, math, subprocess, os
import numpy as np
from PIL import Image, ImageFilter

UP = os.environ.get("UPLOADS", "/root/.claude/uploads/13bdc3d8-f30d-5841-978c-ae76c1bd629a/")
CUT = os.environ.get("CUTS", "/tmp/claude-0/-home-user-Homeproject/13bdc3d8-f30d-5841-978c-ae76c1bd629a/scratchpad/cut/")
OUT = sys.argv[1]
W, H, FPS, DUR = 1920, 1080, 30, 10.0
rng = np.random.default_rng(11)

def clamp01(t): return min(max(t, 0.0), 1.0)
def smooth(t): t = clamp01(t); return t * t * (3 - 2 * t)
def smoother(t): t = clamp01(t); return t * t * t * (t * (6 * t - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t
def seg(t, a, b): return clamp01((t - a) / (b - a))

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)

# ---------------------------------------------------------------- backdrop
# champagne satin sampled from image 1 (centre ~ (232,205,185), edges ~ (190,155,128))
GRAIN = rng.normal(0, 1.6, (H, W, 1)).astype(np.float32)
def backdrop(t):
    r = np.sqrt(((XX - W * 0.48) / (W * 0.62)) ** 2 + ((YY - H * 0.50) / (H * 0.85)) ** 2)
    k = np.clip(r, 0, 1.4) ** 1.5
    base = np.stack([233 - 42 * k, 206 - 50 * k, 186 - 56 * k], -1)
    # soft diagonal window-light shafts drifting slowly (same light through every scene)
    u = XX * 0.80 + YY * 0.60 - 28 * t
    shafts = (0.55 * np.exp(-((np.mod(u + 300, 900) - 450) / 120) ** 2)
              + 0.35 * np.exp(-((np.mod(u + 40, 1300) - 650) / 70) ** 2)
              - 0.30 * np.exp(-((np.mod(u + 620, 1100) - 550) / 160) ** 2))
    fall = np.clip(1.15 - (XX / W) * 0.7 - (YY / H) * 0.35, 0, 1)  # light enters top-left
    return base + (shafts * fall * 22)[..., None] * np.array([1.0, 0.92, 0.82], np.float32) + GRAIN

# ---------------------------------------------------------------- layers
class Layer:
    """RGBA source with a mip pyramid; drawn with an affine (anchor, scale, angle)."""
    def __init__(self, img, jewel_mask=None, n_glints=10):
        img = img.convert("RGBA")
        a = np.asarray(img, np.float32)
        a[..., :3] *= a[..., 3:4] / 255.0                       # premultiply
        jm = (np.asarray(jewel_mask, np.float32) / 255 if jewel_mask is not None
              else a[..., 3] / 255)
        self.levels = []
        for s in (1.0, 0.7, 0.5, 0.35, 0.25):
            sz = (max(1, int(img.width * s)), max(1, int(img.height * s)))
            rgb = [Image.fromarray(a[..., i].astype(np.uint8)).resize(sz, Image.LANCZOS) for i in range(4)]
            m = Image.fromarray((jm * 255).astype(np.uint8)).resize(sz, Image.BILINEAR)
            self.levels.append((s, rgb, m))
        lum = a[..., :3].mean(2)
        core = (jm > 0.95) & (a[..., 3] > 250)
        core = np.asarray(Image.fromarray((core * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(9))) > 0
        ys, xs = np.where(core & (lum > np.percentile(lum[core], 97)))
        pts = []
        for i in rng.permutation(len(xs)):
            x, y = xs[i], ys[i]
            if all((x - p[0]) ** 2 + (y - p[1]) ** 2 > (img.width * 0.09) ** 2 for p in pts):
                pts.append((float(x), float(y), rng.uniform(0.7, 1.3), rng.random(), rng.uniform(1.5, 2.8)))
            if len(pts) >= n_glints:
                break
        self.glints = pts

    def draw(self, anchor, pos, scale, angle=0.0):
        """Return (premult rgb HxWx3, alpha HxW, jewel mask HxW), all float 0..1/0..255."""
        lv = self.levels[0]
        for L in self.levels:
            if L[0] >= scale * 0.98:
                lv = L
        s_lv, chans, m = lv
        k = scale / s_lv
        c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        ax, ay = anchor[0] * s_lv, anchor[1] * s_lv
        # screen (X,Y) -> source (x,y)
        a_ = c / k; b_ = sn / k; d_ = -sn / k; e_ = c / k
        coeffs = (a_, b_, ax - a_ * pos[0] - b_ * pos[1], d_, e_, ay - d_ * pos[0] - e_ * pos[1])
        out = [np.asarray(ch.transform((W, H), Image.AFFINE, coeffs, Image.BICUBIC), np.float32) for ch in chans]
        jm = np.asarray(m.transform((W, H), Image.AFFINE, coeffs, Image.BILINEAR), np.float32) / 255
        return np.stack(out[:3], -1), out[3] / 255, jm

    def glint_pts(self, anchor, pos, scale, angle=0.0):
        c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        res = []
        for (x, y, sz, ph, per) in self.glints:
            dx, dy = (x - anchor[0]) * scale, (y - anchor[1]) * scale
            res.append((pos[0] + c * dx - sn * dy, pos[1] + sn * dx + c * dy, sz, ph, per))
        return res

def make_glint(size):
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-3
    core = np.exp(-(r / (size * 0.10)) ** 2)
    rays = (np.exp(-np.abs(yy) / (size * 0.025)) * np.exp(-np.abs(xx) / (size * 0.45))
            + np.exp(-np.abs(xx) / (size * 0.025)) * np.exp(-np.abs(yy) / (size * 0.45)))
    diag = (np.exp(-np.abs(xx - yy) / (size * 0.02)) + np.exp(-np.abs(xx + yy) / (size * 0.02))) \
        * np.exp(-r / (size * 0.18)) * 0.35
    return np.clip(core + rays * 0.8 + diag + np.exp(-(r / (size * 0.35)) ** 2) * 0.25, 0, 1.5)
GL = {s: make_glint(s) for s in (20, 28, 40, 56)}

def add_glints(arr, pts, t, gain=1.0, base=40):
    for (x, y, sz, ph, per) in pts:
        a = max(0.0, math.sin(2 * math.pi * (t / per + ph))) ** 6 * gain
        if a < 0.02:
            continue
        size = min(GL, key=lambda s: abs(s - base * sz))
        g = GL[size] * a
        x0, y0 = int(x) - size, int(y) - size
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + 2 * size + 1), min(H, y0 + 2 * size + 1)
        if xa < xb and ya < yb:
            arr[ya:yb, xa:xb] += g[ya - y0:yb - y0, xa - x0:xb - x0, None] * np.array([255, 252, 244], np.float32)

SHADOW_RGB = np.array([92, 62, 42], np.float32)
def composite(frame, layer_out, opacity=1.0, shadow=(18, 26, 16, 0.32), extra_alpha=None):
    rgb, a, jm = layer_out
    if extra_alpha is not None:
        a = a * extra_alpha; rgb = rgb * extra_alpha[..., None]; jm = jm * extra_alpha
    a = a * opacity; rgb = rgb * opacity
    if shadow:
        dx, dy, blur, sop = shadow
        sm = Image.fromarray((a * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
        sm = sm.filter(ImageFilter.GaussianBlur(blur / 4)).resize((W, H), Image.BILINEAR)
        sa = np.roll(np.roll(np.asarray(sm, np.float32) / 255, dy, 0), dx, 1) * sop
        frame[:] = frame * (1 - sa[..., None]) + SHADOW_RGB * sa[..., None]
    frame[:] = frame * (1 - a[..., None]) + rgb
    return jm * opacity

def light_sweep(frame, mask, p, strength=0.25, width=150):
    if p <= 0 or p >= 1:
        return
    pos = -500 + smoother(p) * (W + H * 0.55 + 1000)
    band = np.exp(-(((XX + YY * 0.55) - pos) / width) ** 2)
    frame += (band * mask * strength * 255)[..., None]

# ---------------------------------------------------------------- assets
pend1 = Image.open(CUT + "c1b98dc9_isnet-general-use.png")       # image 1 pendant cut-out
neck = Image.open(UP + "3baa66a4-image.png").convert("RGBA")       # image 2 (already transparent)
model = Image.open(CUT + "72f53d4e_u2net_human_seg.png").convert("RGBA")   # image 3 cut-out
model_src = Image.open(UP + "72f53d4e-image.png").convert("RGB")

SPLIT, PIV = 897, (601, 897)            # pendant joint below the round connector diamond
chain = neck.copy(); chain.paste((0, 0, 0, 0), (0, SPLIT, neck.width, neck.height))
pend2 = neck.copy(); pend2.paste((0, 0, 0, 0), (0, 0, neck.width, SPLIT))

# model: feather the hard left/right photo edges into the backdrop
ma = np.asarray(model, np.float32).copy()
ramp = np.clip(np.minimum(np.arange(model.width), model.width - 1 - np.arange(model.width)) / 150, 0, 1)
ma[..., 3] *= (ramp ** 1.5)[None, :]
model = Image.fromarray(ma.astype(np.uint8), "RGBA")
src = np.asarray(model_src, np.float32)
jm3 = (src.mean(2) > 195) & ((src.max(2) - src.min(2)) < 35)
jm3[:420] = False
jm3 = Image.fromarray((jm3 * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(3))

L_p1 = Layer(pend1, n_glints=9)
L_chain = Layer(chain, n_glints=12)
L_p2 = Layer(pend2, n_glints=5)
na = np.asarray(neck, np.float32)
g = np.clip((np.arange(neck.height) - 420) / 120, 0, 1)[:, None]
def with_alpha(m):
    b = na.copy(); b[..., 3] *= m; return Image.fromarray(b.astype(np.uint8), "RGBA")
L_neck = Layer(neck, n_glints=14)
L_neck_top = Layer(with_alpha(1 - g), n_glints=1)
L_neck_front = Layer(with_alpha(g), n_glints=1)
L_model = Layer(model, jewel_mask=jm3, n_glints=12)

# emerald centroids / heights measured in each source
EM1, EMH1 = (578, 613), 387
EM2, EMH2 = (598, 1082), 161
EM3, EMH3 = (590, 1157), 130

# scene 2 necklace placement
SN = 0.76
NECK_C = (601, 656)                              # source point placed at screen centre
NECK_POS = (W / 2, H / 2 + 6)
def neck_screen(p):                              # source px of image 2 -> screen
    return (NECK_POS[0] + (p[0] - NECK_C[0]) * SN, NECK_POS[1] + (p[1] - NECK_C[1]) * SN)
ATTACH = neck_screen(PIV)
P2_START_SCALE = 1.2
P2_START_POS = (W / 2, neck_screen((601, 150))[1])
# pendant-1 end pose: emerald exactly over pendant-2's emerald at its start pose
em2_start = (P2_START_POS[0] + (EM2[0] - PIV[0]) * SN * P2_START_SCALE,
             P2_START_POS[1] + (EM2[1] - PIV[1]) * SN * P2_START_SCALE)
P1_S0 = 800 / 1006
P1_S1 = EMH2 * SN * P2_START_SCALE / EMH1

# scene 3 model placement
SM = 0.82
M_EM_SCREEN = (W / 2, 1411 * SM - 40 - (1411 - EM3[1]) * SM)
NECK_TO_MODEL_SCALE = (EMH3 * SM) / (EMH2 * SN)

# ---------------------------------------------------------------- timeline (10 s)
DUR = 10.0
T_HOLD = 1.8                 # scene 1: pendant close-up
T_A0, T_A1 = 1.8, 3.6        # pendant travels straight down onto the necklace's attachment point
T_SW = 3.6                   # lands: small swing + glow + light sweep
T_B0, T_B1 = 4.8, 6.3        # complete necklace glides into the worn shot
EM_FINAL = neck_screen(EM2)
P1_END = EMH2 * SN / EMH1    # pendant-1 scale that matches the attached pendant

def pend_path(t):
    """Emerald position + size factor along a single downward move (no rise)."""
    p = smoother(seg(t, T_A0, T_A1))
    em = (lerp(W / 2, EM_FINAL[0], p), lerp(H / 2, EM_FINAL[1], p))
    return p, em

def frame(t):
    f = backdrop(t)
    jmask = np.zeros((H, W), np.float32)
    glints = []
    sweep = None
    p, em = pend_path(t)

    # ---- necklace chain fades/settles in around the descending pendant
    if T_A0 <= t < T_B0:
        q = smoother(seg(t, T_A0 + 0.1, T_A1 - 0.2))
        sc = SN * lerp(1.06, 1.0, q)
        jmask += composite(f, L_chain.draw(NECK_C, NECK_POS, sc), opacity=q)
        if q > 0.95:
            glints += L_chain.glint_pts(NECK_C, NECK_POS, sc)

    # ---- pendant (image 1 -> image 2 hand-off while moving straight down)
    swap = smooth(seg(t, T_A0 + 0.55 * (T_A1 - T_A0), T_A1 - 0.1))
    if t < T_A1 and swap < 1:
        sc1 = lerp(P1_S0, P1_END, p)
        op = 1 - swap
        jmask += composite(f, L_p1.draw(EM1, em, sc1), opacity=op,
                           shadow=(lerp(26, 14, p), lerp(34, 20, p), 20, 0.34 * op))
        if t < T_HOLD:
            glints += L_p1.glint_pts(EM1, em, sc1)
            sweep = (seg(t, 0.15, 1.75), 0.24, 170)
    if T_A0 < t < T_B0 and swap > 0:
        r = (lerp(P1_S0, P1_END, p) * EMH1) / (EMH2 * SN)      # same emerald size as pendant 1
        sc2 = SN * r
        if t < T_A1:
            jmask += composite(f, L_p2.draw(EM2, em, sc2), opacity=swap, shadow=(14, 20, 16, 0.32 * swap))
        else:
            u = t - T_SW
            ang = 2.5 * math.exp(-u * 3.5) * math.sin(u * 8.5)
            jmask += composite(f, L_p2.draw(PIV, ATTACH, SN, ang), shadow=(14, 20, 16, 0.32))
            glints += L_p2.glint_pts(PIV, ATTACH, SN, ang)
            k = math.exp(-((t - T_SW - 0.05) / 0.2) ** 2)
            f += (np.exp(-(((XX - ATTACH[0]) / 60) ** 2 + ((YY - ATTACH[1]) / 60) ** 2)) * k * 150)[..., None]
            sweep = (seg(t, T_SW + 0.15, T_B0 + 0.3), 0.26, 140)

    # ---- model materialises behind the gliding necklace
    if t >= T_B0:
        push = lerp(1.0, 1.06, smoother(seg(t, T_B1, DUR)))
        sc = SM * push
        mop = smoother(seg(t, T_B0 + 0.2, T_B1 - 0.1))
        mj = composite(f, L_model.draw(EM3, M_EM_SCREEN, sc), opacity=mop, shadow=(34, 24, 40, 0.22 * mop))
        if t >= T_B1:
            jmask += mj
            glints += L_model.glint_pts(EM3, M_EM_SCREEN, sc)
            sweep = (seg(t, T_B1 + 0.3, T_B1 + 2.6), 0.30, 150)
        else:
            b = smoother(seg(t, T_B0, T_B1))
            sc_n = SN * lerp(1.0, NECK_TO_MODEL_SCALE, b)
            em_now = (lerp(EM_FINAL[0], M_EM_SCREEN[0], b), lerp(EM_FINAL[1], M_EM_SCREEN[1], b))
            top_op = 1 - smoother(seg(t, T_B0, T_B0 + 0.75))
            front_op = 1 - smoother(seg(t, T_B0 + 0.6, T_B1))
            sh = 0.30 * (1 - mop)
            if top_op > 0:
                composite(f, L_neck_top.draw(EM2, em_now, sc_n), opacity=top_op, shadow=(14, 20, 16, sh * top_op))
            if front_op > 0:
                composite(f, L_neck_front.draw(EM2, em_now, sc_n), opacity=front_op, shadow=(14, 20, 16, sh * front_op))

    if sweep is not None:
        light_sweep(f, np.clip(jmask, 0, 1), sweep[0], sweep[1], sweep[2])
    add_glints(f, glints, t)
    return f

def tone(arr):
    a = arr / 255
    a = np.where(a > 0.86, 0.86 + (1 - np.exp(-(a - 0.86) * 5)) * 0.14, a)
    return np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    only = [float(x) for x in sys.argv[2:]]
    if only:
        for t in only:
            Image.fromarray(tone(frame(t))).save(OUT.replace(".mp4", f"_{t:05.2f}.jpg"), quality=90)
    else:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                               "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                              stdin=subprocess.PIPE)
        for i in range(int(FPS * DUR)):
            ff.stdin.write(tone(frame(i / FPS)).tobytes())
            if i % 90 == 0:
                print(i, flush=True)
        ff.stdin.close(); ff.wait()
