import sys, math, numpy as np, cv2
from PIL import Image

D = sys.argv[1]
S = 2000
rng = np.random.default_rng(3)

# ------------------------------------------------------------------ product prep
def load_cut(i):
    a = np.array(Image.open(f'{D}/c{i}.png').convert('RGBA'))
    if i == 1:   # trim the cardboard box poking above the rim: fit the rim ellipse, clear outside
        al = a[..., 3] > 128
        pts = []
        for x in list(range(330, 880, 6)) + list(range(1500, 2650, 6)):
            ys = np.where(al[:, x])[0]
            if len(ys): pts.append((x, ys[0]))
        for y in range(520, 1060, 4):
            xs = np.where(al[y])[0]
            if len(xs): pts.append((xs[-1], y))
            if len(xs) and y > 700: pts.append((xs[0], y))
        e = cv2.fitEllipse(np.array(pts, np.float32))
        print('rim ellipse', e)
        m = np.zeros(al.shape, np.uint8); cv2.ellipse(m, e, 255, -1)
        m = cv2.dilate(m, np.ones((7, 7), np.uint8))
        keep = (m > 0) | (np.mgrid[0:al.shape[0], 0:al.shape[1]][0] > e[0][1])
        a[..., 3] = np.where(keep, a[..., 3], 0)
    if i == 1:   # pull the top-right rim edge in ~22px (a grey cardboard edge hugs it), ramped in smoothly
        al = (a[..., 3] > 128).astype(np.uint8)
        dist = cv2.distanceTransform(al, cv2.DIST_L2, 5)
        yy_, xx_ = np.mgrid[0:al.shape[0], 0:al.shape[1]].astype(np.float32)
        ox, oy = 250, 287    # crop offset of this cut in the original frame (bbox), applied below
        X, Y = xx_ - ox, yy_ - oy
        r = 26.0 * np.clip((X - 1950) / 300, 0, 1) * np.clip((1100 - Y) / 250, 0, 1)
        newa = (dist > r).astype(np.float32)
        newa = np.clip((cv2.GaussianBlur(newa, (0, 0), 9) - 0.5) * 3 + 0.5, 0, 1) * 255   # smooth the contour
        a[..., 3] = np.where(r > 0, np.minimum(a[..., 3], newa), a[..., 3]).astype(np.uint8)
    x0, y0, x1, y1 = Image.fromarray(a).getbbox()
    a = a[y0:y1, x0:x1].copy()
    rgb = a[..., :3]
    # retouch: the red wall niches reflected in the brass -> warm bronze tones (as if reflecting wood)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s_, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    red = ((h < 13) | (h > 160)) & (s_ > 45)
    w = np.clip((s_ - 45) / 60, 0, 1) * red
    w = cv2.GaussianBlur(w.astype(np.float32), (0, 0), 3)
    h2 = np.where(red, 16.0, h); s2 = s_ * (1 - 0.45 * w); v2 = v * (1 - 0.12 * w)
    hu = np.where(h > 90, h - 180, h)                      # unwrap so reds sit next to 0 on the hue circle
    hb = hu * (1 - w) + 16.0 * w
    hb = np.where(hb < 0, hb + 180, hb)
    hsv2 = np.dstack([hb, s_ * (1 - w) + s2 * w, v * (1 - w) + v2 * w])
    rgb = cv2.cvtColor(np.clip(hsv2, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    # warm the cool daylight a touch + gentle S-curve for depth
    rgb *= np.array([1.035, 1.0, 0.93])
    rgb = 255 * (0.5 + (rgb / 255 - 0.5) * 1.06)
    x = np.clip(rgb, 0, 255) / 255.
    L = x.mean(2, keepdims=True)
    gmap = np.interp(L, [0, .25, .55, .8, 1], [0, 0, 0, 0, 0])  # placeholder shape
    stops = np.array([[0, 26, 14, 6], [.28, 98, 62, 28], [.55, 192, 140, 78], [.8, 238, 206, 150], [1, 255, 246, 228]], np.float32)
    gm = np.stack([np.interp(L[..., 0], stops[:, 0], stops[:, c]) for c in (1, 2, 3)], -1) / 255.
    x = x * 0.68 + gm * 0.32                                   # warm golden toning
    x = np.clip(x, 0, 1)
    x = x + 0.28 * (x - cv2.GaussianBlur(x, (0, 0), 22))        # clarity: makes the hammer marks pop
    x = 1 / (1 + np.exp(-(x - 0.5) * 4.6))                      # S-curve: deeper shadows, brighter speculars
    x = (x - 1 / (1 + np.exp(2.3))) / (1 / (1 + np.exp(-2.3)) - 1 / (1 + np.exp(2.3)))
    hsv = cv2.cvtColor(np.clip(x * 255, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 0.9, 0, 255)
    rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    a[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    # tidy edge: shave 1px fringe picked up from the white wall
    al = a[..., 3].astype(np.float32)
    al = cv2.erode(al, np.ones((3, 3), np.uint8)); al = cv2.GaussianBlur(al, (0, 0), 0.7)
    a[..., 3] = al.astype(np.uint8)
    return a

# ------------------------------------------------------------------ textures
def fractal(h, w, octaves=6, base=4, seed=0, pers=0.55):
    r = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = r.standard_normal((n, max(2, int(n * w / h)))).astype(np.float32)
        out += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC); tot += amp; amp *= pers
    out /= tot; return (out - out.mean()) / (out.std() + 1e-6)

def stone(h, w, seed):
    """weathered grey-brown wooden table: planks run front-to-back"""
    r = np.random.default_rng(seed)
    out = np.zeros((h, w, 3), np.float32)
    PW = 230
    xs = np.arange(w)
    for k in range(-1, w // PW + 2):
        x0 = k * PW + int(r.integers(-20, 20)); x1 = x0 + PW
        lo, hi = max(x0, 0), min(x1, w)
        if hi <= lo: continue
        tone = np.array([112, 98, 86], np.float32) * r.uniform(.86, 1.08) + np.array([r.uniform(-4, 6), 0, r.uniform(-6, 2)])
        g = r.standard_normal((h // 60 + 2, (hi - lo) // 2 + 2)).astype(np.float32)
        grain = cv2.resize(g, (hi - lo, h), interpolation=cv2.INTER_CUBIC)
        fine = cv2.resize(r.standard_normal((h // 8 + 2, hi - lo)).astype(np.float32), (hi - lo, h), interpolation=cv2.INTER_LINEAR)
        streak = cv2.GaussianBlur(np.sin(np.linspace(0, r.uniform(20, 40), hi - lo))[None].repeat(h, 0).astype(np.float32) * fractal(h, hi - lo, 3, 2, int(r.integers(999))) , (0, 0), 2)
        v = grain * 9 + fine * 5 + streak * 5
        out[:, lo:hi] = tone[None, None] + v[..., None] * np.array([1, .93, .85])
        # plank seams
        for xe in (x0, x1 - 1):
            if 0 <= xe < w:
                for d, k2 in ((0, .74), (1, .86), (-1, .88)):
                    if 0 <= xe + d < w: out[:, xe + d] *= k2
    # long-wave unevenness and a few worn lighter patches
    out *= (1 + 0.06 * fractal(h, w, 4, 2, seed + 5))[..., None]
    out += r.standard_normal((h, w, 1)).astype(np.float32) * 2.0
    return np.clip(out, 0, 255)

def leaf_gobo(h, w, seed, density=1.0):
    """soft window-plant shadow mask (0..1)"""
    m = np.zeros((h, w), np.float32); r = np.random.default_rng(seed)
    for b in range(int(5 * density)):
        x, y = r.uniform(-0.1, .55) * w, r.uniform(-.1, 1.0) * h
        ang = r.uniform(-.9, .3)
        for k in range(int(r.integers(7, 14))):
            x += math.cos(ang) * w * .045; y += math.sin(ang) * w * .045; ang += r.uniform(-.25, .25)
            for side in (-1, 1):
                la = ang + side * r.uniform(.6, 1.1); L = w * r.uniform(.05, .085)
                cx, cy = x + math.cos(la) * L * .55, y + math.sin(la) * L * .55
                cv2.ellipse(m, (int(cx), int(cy)), (int(L * .55), int(L * .2)), math.degrees(la), 0, 360, 1.0, -1)
        cv2.line(m, (int(x), int(y)), (int(x - math.cos(ang) * w * .5), int(y - math.sin(ang) * w * .5)), .6, 3)
    return cv2.GaussianBlur(m, (0, 0), w * .012)

# ------------------------------------------------------------------ scene
def scene(horizon, seed, tilt=1.0):
    img = np.zeros((S, S, 3), np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    if horizon is not None:
        # plaster wall, warm, brighter upper-left (window light), soft-focus
        wall = np.array([70, 60, 52], np.float32) + fractal(S, S, 5, 3, seed + 20)[..., None] * 2.5
        pool = np.exp(-(((xx - S * .55) / (S * .55)) ** 2 + ((yy - horizon * .9) / (S * .45)) ** 2))
        wall = wall * (0.72 + 0.55 * pool)[..., None]
        img[:] = wall
    # counter plane in perspective
    TW = 2600
    tex = stone(TW, TW, seed)
    if horizon is None:
        img = tex[300:300 + S, 300:300 + S].copy()
        img *= (0.80 + 0.35 * np.exp(-(((xx - S * .5) / (S * .6)) ** 2 + ((yy - S * .55) / (S * .55)) ** 2)))[..., None]
        blurmap = np.zeros((S, S), np.float32)
    else:
        H0 = horizon
        VP = H0 - 520.0 * tilt                    # vanishing point sits above the counter's back edge
        f = 1500.0
        dy = np.maximum(yy - VP, 1.0)
        z = f / dy
        zf = f / (S - VP)
        u = (xx - S / 2) * z * 0.62 + TW / 2
        v = TW - 150 - (z - zf) * 900
        cnt = cv2.remap(tex, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # light falls off toward the back edge; front lip catches light
        shade = 0.80 + 0.35 * np.exp(-(((xx - S * .5) / (S * .6)) ** 2 + ((yy - S * .68) / (S * .45)) ** 2))
        cnt *= shade[..., None]
        below = yy > H0
        img[below] = cnt[below]
        # counter back edge: thin shadow line where it meets the wall
        edge = np.exp(-((yy - H0) / 5.0) ** 2) * (yy >= H0 - 2)
        img *= (1 - 0.22 * edge)[..., None]
        img *= (1 - 0.10 * np.exp(-np.maximum(yy - H0, 0) / 40.0) * (yy >= H0))[..., None]
        blurmap = np.where(yy < H0, 9.0, np.clip(9.0 * (1 - (yy - H0) / (S * 0.55 - H0 * 0.3)), 0, 9))
    return img, blurmap

def variable_blur(img, bm):
    out = img.copy(); levels = [0, 1.5, 3, 5, 7, 9]
    blurred = [img] + [cv2.GaussianBlur(img, (0, 0), s) for s in levels[1:]]
    for i in range(len(levels) - 1):
        lo, hi = levels[i], levels[i + 1]
        t = np.clip((bm - lo) / (hi - lo), 0, 1)[..., None]
        m = ((bm >= lo) & (bm <= hi))[..., None]
        out = np.where(m, blurred[i] * (1 - t) + blurred[i + 1] * t, out)
    return out

def over(dst, src_rgba, x, y, alpha_mul=1.0):
    h, w = src_rgba.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, S), min(y + h, S)
    s = src_rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = s[..., 3:4] / 255. * alpha_mul
    dst[y0:y1, x0:x1] = s[..., :3] * a + dst[y0:y1, x0:x1] * (1 - a)

def shift(a, dy, dx):
    o = np.zeros_like(a); h, w = a.shape
    o[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = a[max(-dy, 0):h - max(dy, 0), max(-dx, 0):w - max(dx, 0)]
    return o

def mult(dst, mask, strength, tint=(18, 11, 5)):
    k = np.clip(mask * strength, 0, 1)[..., None]
    dst *= (1 - k) + k * (np.array(tint, np.float32) / 255.)

def compose(i, cfg, logo):
    p = load_cut(i)
    ph, pw = p.shape[:2]
    sc = cfg['w'] / pw if 'w' in cfg else cfg['h'] / ph
    p = cv2.resize(p, (int(pw * sc), int(ph * sc)), interpolation=cv2.INTER_AREA)
    ph, pw = p.shape[:2]
    px, py = int(cfg['cx'] - pw / 2), int(cfg['base'] - ph)
    if 'left' in cfg: px = cfg['left']
    if 'top' in cfg: py = cfg['top']
    img, bm = scene(cfg.get('horizon'), seed=10 + i, tilt=cfg.get('tilt', 1.0))
    img = variable_blur(img, bm)
    A = np.zeros((S, S), np.float32)
    x0, y0 = max(px, 0), max(py, 0); x1, y1 = min(px + pw, S), min(py + ph, S)
    A[y0:y1, x0:x1] = p[y0 - py:y1 - py, x0 - px:x1 - px, 3] / 255.
    rows = np.where(A.max(1) > .5)[0]; bot = rows.max() if len(rows) else S
    # ----- shadows
    if cfg.get('mode') == 'side':
        cols = np.where(A[max(bot - int(ph * .025), 0)] > .5)[0]
        bx0, bx1 = (cols.min(), cols.max()) if len(cols) else (px, px + pw)
        bw, bc = (bx1 - bx0) / 2, (bx0 + bx1) / 2
        ao = np.zeros((S, S), np.float32)
        cv2.ellipse(ao, (int(bc + 3), int(bot - 2)), (int(bw * 1.05), 9), 0, 0, 360, 1, -1)
        mult(img, cv2.GaussianBlur(ao, (0, 0), 6), .85)
        mid = np.zeros((S, S), np.float32)
        cv2.ellipse(mid, (int(bc + 10), int(bot + 2)), (int(bw * 1.6), 26), 0, 0, 360, 1, -1)
        mult(img, cv2.GaussianBlur(mid, (0, 0), 18), .45)
        soft = np.zeros((S, S), np.float32)
        cv2.ellipse(soft, (int(bc + bw * .3), int(bot + 10)), (int(max(bw * 3.2, pw * .45)), int(pw * .07)), 0, 0, 360, 1, -1)
        mult(img, cv2.GaussianBlur(soft, (0, 0), 45), .32)
        # reflection in the honed stone: flipped, fading, slightly blurred
        refl = p[::-1].copy()
        rh = refl.shape[0]
        fade = np.clip(1 - np.arange(rh) / (rh * cfg.get('rlen', .28)), 0, 1) ** 1.6
        refl[..., 3] = (refl[..., 3] * fade[:, None]).astype(np.uint8)
        refl[..., :3] = cv2.GaussianBlur(refl[..., :3], (0, 0), 2.2)
        # the reflection's top row must meet the object's lowest row in each column
        yref = 2 * bot - (py + ph)  # mirror about the base line
        tmp = img.copy(); over(tmp, refl, px, yref)
        k = cfg.get('rop', .16) * 0.35
        img = img * (1 - k) + tmp * k
    else:
        dx, dy = cfg.get('sdx', 45), cfg.get('sdy', 60)
        sh = shift(A, dy, dx)
        mult(img, cv2.GaussianBlur(sh, (0, 0), 42), .42)
        mult(img, cv2.GaussianBlur(shift(A, 14, 0), (0, 0), 9), .35)
    # ----- product
    over(img, p, px, py)
    # ----- props (from reference), slightly soft: they sit outside the focal plane
    for (name, x, y, w, ang, flip) in cfg.get('props', []):
        pr = PROPS[name]
        if flip: pr = pr[:, ::-1].copy()
        sc2 = w / pr.shape[1]
        pr = cv2.resize(pr, (int(pr.shape[1] * sc2), int(pr.shape[0] * sc2)), interpolation=cv2.INTER_CUBIC)
        if ang:
            hh, ww = pr.shape[:2]; d = int(math.hypot(hh, ww))
            M = cv2.getRotationMatrix2D((ww / 2, hh / 2), ang, 1); M[0, 2] += (d - ww) / 2; M[1, 2] += (d - hh) / 2
            pr = cv2.warpAffine(pr, M, (d, d), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
        bb = Image.fromarray(pr).getbbox(); pr = pr[bb[1]:bb[3], bb[0]:bb[2]].copy()
        pr = cv2.GaussianBlur(pr, (0, 0), 1.3)
        Ap = np.zeros((S, S), np.float32); hh, ww = pr.shape[:2]
        X0, Y0, X1, Y1 = max(x, 0), max(y, 0), min(x + ww, S), min(y + hh, S)
        Ap[Y0:Y1, X0:X1] = pr[Y0 - y:Y1 - y, X0 - x:X1 - x, 3] / 255.
        mult(img, cv2.GaussianBlur(shift(Ap, 34, 26), (0, 0), 22), .5)
        mult(img, cv2.GaussianBlur(shift(Ap, 6, 4), (0, 0), 5), .35)
        # match the warm, darker key on the table
        prc = pr.astype(np.float32); prc[..., :3] *= np.array([.92, .86, .78]); pr = np.clip(prc, 0, 255).astype(np.uint8)
        over(img, pr, x, y)
    # ----- logo
    lw = cfg.get('logo_w', 300)
    L = cv2.resize(logo, (lw, int(logo.shape[0] * lw / logo.shape[1])), interpolation=cv2.INTER_AREA)
    over(img, L, int(S / 2 - lw / 2), cfg.get('logo_y', 70))
    # ----- grade: gentle vignette + unified grain
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    vig = 1 - 0.32 * np.clip(((xx - S / 2) ** 2 + (yy - S * .52) ** 2) / (S * .75) ** 2, 0, 1)
    img *= vig[..., None]
    img += rng.normal(0, 2.6, (S, S, 1)).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)

CFG = {
    1: dict(mode='hi', horizon=430, w=1380, cx=1040, base=1560, sdx=55, sdy=70,
            props=[('rosemary', -40, 1520, 560, -8, False), ('spoons', 1400, 1540, 700, 0, False)]),
    2: dict(mode='side', horizon=980, w=1300, cx=1000, base=1430, rop=.17,
            props=[('rosemary', -40, 1560, 600, -4, False), ('spoons', 1360, 1560, 720, 6, False)]),
    3: dict(mode='side', horizon=900, w=1340, cx=1010, base=1470, rop=.17,
            props=[('rosemary', -40, 1580, 580, 2, False), ('spoons', 1380, 1580, 700, 4, False)]),
    4: dict(mode='hi', horizon=420, w=1300, cx=1000, base=1660, sdx=50, sdy=60,
            props=[('rosemary', -50, 1600, 560, -14, False), ('spoons', 1420, 1640, 640, 8, False)]),
    5: dict(mode='side', horizon=1000, w=1560, cx=1000, base=1420, rop=.15,
            props=[('rosemary', -40, 1540, 620, -6, False), ('spoons', 1340, 1530, 720, 4, False)]),
    6: dict(mode='hi', horizon=None, h=1650, cx=860, base=2010, sdx=50, sdy=55, logo_y=60,
            props=[('rosemary', 1560, 330, 560, 70, True), ('spoons', 1520, 1380, 640, -60, False)]),
    7: dict(mode='hi', horizon=380, w=1540, left=-30, cx=0, base=1680, sdx=50, sdy=60,
            props=[('spoons', 1400, 1580, 660, 6, False), ('rosemary', 1560, 470, 500, 160, True)]),
    8: dict(mode='hi', horizon=420, w=1620, left=430, cx=0, base=1700, sdx=50, sdy=60,
            props=[('rosemary', -40, 1560, 600, -10, False), ('spoons', -60, 640, 560, 150, False)]),
}
PROPS = {n: np.array(Image.open(f'{D}/../props/{n}.png').convert('RGBA')) for n in ('rosemary', 'spoons')}
PROPS = {k: v[Image.fromarray(v).getbbox()[1]:Image.fromarray(v).getbbox()[3], Image.fromarray(v).getbbox()[0]:Image.fromarray(v).getbbox()[2]] for k, v in PROPS.items()}
if __name__ == '__main__':
    logo = np.array(Image.open(sys.argv[2]).convert('RGBA'))
    which = [int(a) for a in sys.argv[3:]] or list(CFG)
    for i in which:
        Image.fromarray(compose(i, CFG[i], logo)).save(f'{D}/v2_{i}.png'); print('shot', i)
