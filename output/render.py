import sys, math, subprocess
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageChops

UP = "/root/.claude/uploads/13bdc3d8-f30d-5841-978c-ae76c1bd629a/"
OUT = sys.argv[1]
W, H, FPS, DUR = 1080, 1920, 30, 15.0
N = int(FPS * DUR)
rng = np.random.default_rng(7)

def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)

def ease_io_cubic(t):
    t = min(max(t, 0.0), 1.0)
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2

def cover_blur(img, dark=0.45, blur=40):
    s = max(W / img.width, H / img.height)
    b = img.convert("RGB").resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    l, t = (b.width - W) // 2, (b.height - H) // 2
    b = b.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(blur))
    return Image.eval(b, lambda v: int(v * dark))

def fit_width_with_bands(img, dark):
    """Image scaled to full width, centred, feathered into a blurred extension of itself."""
    s = W / img.width
    fg = img.convert("RGB").resize((W, int(img.height * s)), Image.LANCZOS)
    y0 = (H - fg.height) // 2
    # extend with the image's own edge rows (stretched + blurred), never with product content
    bg = Image.new("RGB", (W, H))
    top = fg.crop((0, 0, W, 30)).resize((W, y0 + 160), Image.BILINEAR)
    bot = fg.crop((0, fg.height - 30, W, fg.height)).resize((W, H - (y0 + fg.height) + 160), Image.BILINEAR)
    bg.paste(top, (0, 0)); bg.paste(bot, (0, y0 + fg.height - 160))
    bg = bg.filter(ImageFilter.GaussianBlur(30))
    bg = Image.eval(bg, lambda v: int(v * dark))
    m = Image.new("L", fg.size, 255)
    d = ImageDraw.Draw(m)
    f = 140
    for i in range(f):
        v = int(255 * ease(i / f))
        d.line([(0, i), (W, i)], fill=v)
        d.line([(0, fg.height - 1 - i), (W, fg.height - 1 - i)], fill=v)
    bg.paste(fg, (0, y0), m)
    return bg, y0, s

def vignette(strength=0.55):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return (1 - strength * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None]

VIG = vignette()

def glint(size):
    """Four-point star glint, float32 0..1."""
    n = size * 2 + 1
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32)
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-3
    core = np.exp(-(r / (size * 0.10)) ** 2)
    rays = np.exp(-np.abs(yy) / (size * 0.025)) * np.exp(-np.abs(xx) / (size * 0.45)) \
         + np.exp(-np.abs(xx) / (size * 0.025)) * np.exp(-np.abs(yy) / (size * 0.45))
    diag = (np.exp(-np.abs(xx - yy) / (size * 0.02)) + np.exp(-np.abs(xx + yy) / (size * 0.02))) \
         * np.exp(-r / (size * 0.18)) * 0.35
    halo = np.exp(-(r / (size * 0.35)) ** 2) * 0.25
    return np.clip(core + rays * 0.8 + diag + halo, 0, 1.5)

GL = {s: glint(s) for s in (28, 40, 56, 72)}

def add_glints(arr, pts, t):
    for (x, y, size, phase, period) in pts:
        k = math.sin(2 * math.pi * (t / period + phase))
        a = max(0.0, k) ** 6
        if a < 0.02:
            continue
        g = GL[size] * a
        x0, y0 = int(x) - size, int(y) - size
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(W, x0 + 2 * size + 1), min(H, y0 + 2 * size + 1)
        if xa >= xb or ya >= yb:
            continue
        gg = g[ya - y0:yb - y0, xa - x0:xb - x0, None]
        arr[ya:yb, xa:xb] += gg * np.array([255, 252, 245], np.float32)

def pick_sparkles(lum, mask, n, xoff=0, yoff=0, scale=1.0, sizes=(28, 40, 56)):
    ys, xs = np.where((lum > np.percentile(lum[mask], 97)) & mask)
    idx = rng.choice(len(xs), size=min(n * 6, len(xs)), replace=False)
    pts = []
    for i in idx:
        x, y = xs[i] * scale + xoff, ys[i] * scale + yoff
        if all((x - p[0]) ** 2 + (y - p[1]) ** 2 > 90 ** 2 for p in pts):
            pts.append((x, y, int(rng.choice(sizes)), rng.random(), rng.uniform(1.4, 2.6)))
        if len(pts) >= n:
            break
    return pts

def light_sweep(t, t0, t1, mask, strength=0.22, width=170, angle=0.55):
    """Diagonal soft highlight band moving across, restricted to mask (H,W float)."""
    p = ease_io_cubic((t - t0) / (t1 - t0))
    if p <= 0 or p >= 1:
        return None
    yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    pos = -600 + p * (W + H * angle + 1200)
    d = (xx + yy * angle) - pos
    band = np.exp(-(d / width) ** 2)
    band = np.array(Image.fromarray((band * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
    return (band * mask * strength)[..., None] * 255

# ---------------- Scene 1: pendant macro (image 1) ----------------
img1 = Image.open(UP + "c1b98dc9-image.png").convert("RGB")
s1_frame, s1_y0, s1_s = fit_width_with_bands(img1, dark=0.8)
s1_base = np.asarray(s1_frame, np.float32)
# jewellery mask: distance from the beige backdrop colour
a1 = np.asarray(img1.resize((W, int(img1.height * s1_s)), Image.LANCZOS), np.float32)
bgc = np.median(np.concatenate([a1[:60, :60].reshape(-1, 3), a1[-60:, -60:].reshape(-1, 3)]), 0)
dist = np.linalg.norm(a1 - bgc, axis=2)
m1 = np.zeros((H, W), np.float32)
m1[s1_y0:s1_y0 + a1.shape[0]] = np.clip((dist - 45) / 40, 0, 1)
m1 = np.asarray(Image.fromarray((m1 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
lum1 = s1_base.mean(2)
core1 = np.asarray(Image.fromarray(((m1 > 0.9) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(21)), np.float32) > 0
yy1, xx1 = np.mgrid[0:H, 0:W]
core1 &= (((xx1 - 540) / 400) ** 2 + ((yy1 - (s1_y0 + 600)) / 560) ** 2) < 1
s1_glints = pick_sparkles(lum1, core1, 9, sizes=(40, 56, 72))

def scene1(t):
    # fixed camera: no zoom, no pull-back. Only light plays on the stone.
    arr = s1_base.copy()
    sw = light_sweep(t, 0.4, 3.4, m1, strength=0.20)
    if sw is not None:
        arr += sw
    add_glints(arr, s1_glints, t)
    # gentle exposure "breath" on the emerald/diamonds
    arr = arr * (1 + 0.03 * math.sin(t * 1.6) * m1[..., None])
    return arr * VIG

# ---------------- Scene 2: pendant attaches to necklace (image 2) ----------------
neck = Image.open(UP + "3baa66a4-image.png").convert("RGBA")
SPLIT = 897                       # narrowest joint below the round connector diamond
PIV = (601, SPLIT)                # attachment point in source px
NS = 0.86
chain = neck.copy()
chain.paste((0, 0, 0, 0), (0, SPLIT, neck.width, neck.height))
pend = neck.crop((0, SPLIT, neck.width, neck.height))
pbox = pend.getbbox()
pend = pend.crop(pbox)
pend_px = PIV[0] - pbox[0]        # pivot x within cropped pendant
chain_s = chain.resize((int(neck.width * NS), int(neck.height * NS)), Image.LANCZOS)
NX = (W - chain_s.width) // 2
NY = 300
attach = (NX + PIV[0] * NS, NY + PIV[1] * NS)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
spot = np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - 880) / 900) ** 2))
s2_bg = np.stack([14 + 34 * spot, 13 + 30 * spot, 15 + 30 * spot], -1).astype(np.float32)

def place_rgba(base, im, x, y):
    base.alpha_composite(im, (int(round(x)), int(round(y)))) if x >= 0 and y >= 0 else base.paste(im, (int(round(x)), int(round(y))), im)

def pendant_img(scale, angle):
    p = pend.resize((max(1, int(pend.width * NS * scale)), max(1, int(pend.height * NS * scale))), Image.LANCZOS)
    pad = p.height
    c = Image.new("RGBA", (p.width + 2 * pad, p.height + 2 * pad), (0, 0, 0, 0))
    c.paste(p, (pad, pad))
    cx = pad + pend_px * NS * scale
    c = c.rotate(angle, resample=Image.BICUBIC, center=(cx, pad))
    return c, cx, pad

full_neck_mask = None
s2_glints = None

def scene2(t, lt):
    global full_neck_mask, s2_glints
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(chain_s, (NX, NY))
    # descent 0.3s -> 3.0s local, then damped swing
    d0, d1 = 0.25, 3.0
    p = ease_io_cubic((lt - d0) / (d1 - d0))
    scale = 1.45 + (1.0 - 1.45) * p
    start = (W / 2, 400)                     # starts in the open centre of the necklace
    ax = start[0] + (attach[0] - start[0]) * p
    ay = start[1] + (attach[1] - start[1]) * p
    if lt > d1:
        u = lt - d1
        angle = 4.5 * math.exp(-u * 2.4) * math.sin(u * 7.0)
    else:
        angle = 0.0
    im, cx, cy = pendant_img(scale, angle)
    alpha = ease(lt / 0.5)
    if alpha < 1:
        a = np.asarray(im, np.float32)
        a[..., 3] *= alpha
        im = Image.fromarray(a.astype(np.uint8), "RGBA")
    # soft shadow underneath
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.35)).filter(ImageFilter.GaussianBlur(14)))
    canvas.alpha_composite(sh, (int(ax - cx + 8), int(ay - cy + 18)))
    canvas.alpha_composite(im, (int(ax - cx), int(ay - cy)))
    # "click" glow at the moment of attachment
    rgba = np.asarray(canvas, np.float32)
    a = rgba[..., 3:4] / 255
    arr = s2_bg * (1 - a) + rgba[..., :3] * a
    if s2_glints is None and lt >= d1:
        lum = rgba[..., :3].mean(2)
        s2_glints = pick_sparkles(lum, rgba[..., 3] > 250, 12, sizes=(28, 40, 56))
        full_neck_mask = a[..., 0]
    if lt >= d1 - 0.05:
        k = math.exp(-((lt - d1 - 0.05) / 0.22) ** 2)
        r = np.exp(-(((xx - attach[0]) / 70) ** 2 + ((yy - attach[1]) / 70) ** 2))
        arr += (r * k * 140)[..., None]
        if full_neck_mask is not None:
            sw = light_sweep(lt, d1 + 0.2, d1 + 2.2, full_neck_mask, strength=0.25, width=140)
            if sw is not None:
                arr += sw
        if s2_glints is not None:
            add_glints(arr, s2_glints, t)
    return arr * VIG

# ---------------- Scene 3: model reveal (image 3) ----------------
img3 = Image.open(UP + "72f53d4e-image.png").convert("RGB")
s3_frame, s3_y0, s3_s = fit_width_with_bands(img3, dark=0.7)
s3_base = np.asarray(s3_frame, np.float32)
a3 = np.asarray(img3.resize((W, int(img3.height * s3_s)), Image.LANCZOS), np.float32)
lum3full = np.zeros((H, W), np.float32)
lum3full[s3_y0:s3_y0 + a3.shape[0]] = a3.mean(2)
sat = np.zeros((H, W), np.float32)
sat[s3_y0:s3_y0 + a3.shape[0]] = a3.max(2) - a3.min(2)
m3 = (lum3full > 200) & (sat < 30)
m3[: s3_y0 + int(400 * s3_s)] = False       # jewellery only, below the chin
s3_glints = pick_sparkles(lum3full, m3, 11, sizes=(28, 40, 56))
m3f = np.asarray(Image.fromarray((m3 * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(4)), np.float32) / 255

def scene3(t, lt):
    arr = s3_base.copy()
    sw = light_sweep(lt, 1.0, 3.6, m3f, strength=0.30, width=150)
    if sw is not None:
        arr += sw
    add_glints(arr, s3_glints, t)
    return arr * VIG

# ---------------- timeline ----------------
X = 0.6   # crossfade length
def frame(t):
    if t < 4 - X / 2:
        return scene1(t)
    if t < 4 + X / 2:
        k = ease((t - (4 - X / 2)) / X)
        return scene1(t) * (1 - k) + scene2(t, t - 4) * k
    if t < 9 - X / 2:
        return scene2(t, t - 4)
    if t < 9 + X / 2:
        k = ease((t - (9 - X / 2)) / X)
        return scene2(t, t - 4) * (1 - k) + scene3(t, t - 9) * k
    arr = scene3(t, t - 9)
    if t > 14.4:                                   # elegant fade to black at the end
        arr = arr * (1 - ease((t - 14.4) / 0.6))
    if t < 0.5:
        pass
    return arr

def tone(arr):
    # soft highlight roll-off so glints bloom instead of clipping hard
    a = arr / 255
    a = np.where(a > 0.85, 0.85 + (1 - np.exp(-(a - 0.85) * 4)) * 0.15 / (1 - math.exp(-0.6)), a)
    return np.clip(a * 255, 0, 255).astype(np.uint8)

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                       "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
only = [float(x) for x in sys.argv[2:]]
times = only if only else [i / FPS for i in range(N)]
for i, t in enumerate(times):
    fr = tone(frame(t))
    if only:
        Image.fromarray(fr).resize((540, 960)).save(OUT.replace(".mp4", f"_{t:05.2f}.jpg"))
    else:
        ff.stdin.write(fr.tobytes())
    if i % 60 == 0:
        print(i, flush=True)
ff.stdin.close(); ff.wait()
